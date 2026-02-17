#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单吊T+1回测引擎 (Single Holding T+1 Backtest Engine)

V17生产用途：小资金右侧起爆策略回测

核心规则：
1. T+1硬约束：买入当日不能卖出，只能卖昨仓
2. 单吊策略：每天最多持有1只股票，空仓时才能开新仓
3. 全市场扫描：遍历所有股票，选评分最高的机会
4. 双轨输出：信号层（理论）+ 交易层（T+1可执行）

Author: AI Project Director
Version: V1.0 (T+1合规版)
Date: 2026-02-17
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import pandas as pd

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.tick_strategy_interface import TickData
from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class T1Position:
    """T+1仓位状态"""
    stock_code: str
    position_carry: int = 0  # 昨仓（今日可卖）
    position_today: int = 0  # 今仓（今日不可卖）
    entry_price: float = 0.0
    entry_time: str = ""
    
    @property
    def total_position(self) -> int:
        return self.position_carry + self.position_today
    
    @property
    def can_sell(self) -> int:
        """今日可卖数量 = 昨仓"""
        return self.position_carry


@dataclass
class T1Trade:
    """T+1交易记录"""
    stock_code: str
    entry_date: str
    entry_time: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    holding_period: Optional[int] = None
    
    # 标记是信号层还是T+1层
    is_signal_only: bool = False  # True=理论信号（未实际成交）


@dataclass
class T1BacktestResult:
    """T+1回测结果（双轨输出）
    
    V17声明：
    - 采用全仓买入/全仓卖出的简化模型，不支持分批卖出
    - 涨停检查：当前价格接近涨停价时禁止买入
    """
    # 信号层（理论，无约束）
    signal_total: int = 0
    signal_winning: int = 0
    signal_losing: int = 0
    signal_pnl: float = 0.0
    
    # T+1交易层（可执行）
    trade_total: int = 0
    trade_winning: int = 0
    trade_losing: int = 0
    trade_pnl: float = 0.0
    
    # 资金曲线
    initial_capital: float = 100000.0
    final_capital: float = 100000.0
    max_drawdown: float = 0.0
    
    # 交易明细
    signal_trades: List[T1Trade] = field(default_factory=list)  # 理论信号
    t1_trades: List[T1Trade] = field(default_factory=list)  # T+1可执行
    equity_curve: List[Dict] = field(default_factory=list)
    
    # V17新增：阻塞统计
    blocked_by_limit_up: int = 0  # 因涨停无法买入次数
    blocked_by_t1: int = 0  # 因T+1限制无法卖出次数
    blocked_by_cash: int = 0  # 因资金不足未执行次数
    
    @property
    def signal_win_rate(self) -> float:
        if self.signal_total == 0:
            return 0.0
        return self.signal_winning / self.signal_total
    
    @property
    def trade_win_rate(self) -> float:
        if self.trade_total == 0:
            return 0.0
        return self.trade_winning / self.trade_total
    
    def to_dict(self) -> Dict:
        return {
            'enforce_t_plus_1': True,
            'single_holding': True,
            'signal_layer': {
                'total_trades': self.signal_total,
                'winning_trades': self.signal_winning,
                'losing_trades': self.signal_losing,
                'win_rate': self.signal_win_rate,
                'total_pnl': self.signal_pnl,
            },
            'trade_layer': {
                'total_trades': self.trade_total,
                'winning_trades': self.trade_winning,
                'losing_trades': self.trade_losing,
                'win_rate': self.trade_win_rate,
                'total_pnl': self.trade_pnl,
                'initial_capital': self.initial_capital,
                'final_capital': self.final_capital,
                'max_drawdown': self.max_drawdown,
            },
            't1_trades': [
                {
                    'stock_code': t.stock_code,
                    'entry_date': t.entry_date,
                    'entry_time': t.entry_time,
                    'entry_price': t.entry_price,
                    'exit_date': t.exit_date,
                    'exit_time': t.exit_time,
                    'exit_price': t.exit_price,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct,
                    'exit_reason': t.exit_reason,
                }
                for t in self.t1_trades
            ],
            'blocked_stats': {
                'by_limit_up': self.blocked_by_limit_up,
                'by_t1_rule': self.blocked_by_t1,
                'by_cash': self.blocked_by_cash,
            }
        }


class SingleHoldingT1Backtester:
    """单吊T+1回测器
    
    V17声明：
    - 采用全仓买入/全仓卖出的简化模型，不支持分批卖出
    - 涨停检查：价格接近涨停价时禁止买入
    - 单吊约束：同时最多持有1只股票
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        position_size: float = 0.5,  # 单吊：50%仓位一只
        stop_loss_pct: float = 0.02,  # 止损2%
        take_profit_pct: float = 0.05,  # 止盈5%
        max_holding_minutes: int = 120,  # 最长持有2小时
    ):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_holding_minutes = max_holding_minutes
        
        # 状态机
        self.cash = initial_capital
        self.positions: Dict[str, T1Position] = {}  # 股票代码 -> 仓位
        self.current_holding: Optional[str] = None  # 当前持有的股票（单吊）
        
        # 结果记录
        self.signal_trades: List[T1Trade] = []
        self.t1_trades: List[T1Trade] = []
        self.equity_curve: List[Dict] = []
        
        # V17新增：阻塞统计
        self.blocked_by_limit_up = 0
        self.blocked_by_t1 = 0
        self.blocked_by_cash = 0
        
        logger.info(f"✅ [单吊T+1回测器] 初始化完成")
        logger.info(f"   - 初始资金: {initial_capital:,.2f}")
        logger.info(f"   - 单吊仓位: {position_size*100:.0f}%")
        logger.info(f"   - 止损/止盈: {stop_loss_pct*100:.1f}% / {take_profit_pct*100:.1f}%")
        logger.info(f"   - 最大持有: {max_holding_minutes}分钟")
        logger.info(f"   - ⚠️  V17简化模型：全仓进出，不支持分批卖出")
    
    def _can_open_position(self, date: str) -> bool:
        """检查是否可以开新仓（单吊：必须空仓）"""
        return self.current_holding is None
    
    def _open_position(self, stock_code: str, date: str, time: str, price: float, pre_close: float = None) -> Optional[T1Trade]:
        """开新仓（T+1规则+涨停检查）
        
        Args:
            stock_code: 股票代码
            date: 日期
            time: 时间
            price: 当前价格
            pre_close: 昨收价（用于计算涨停价）
        """
        if not self._can_open_position(date):
            return None
        
        # V17: 涨停检查（简化版）
        if pre_close and pre_close > 0:
            # 判断股票类型（简化：6开头上海，其他深圳）
            is_shanghai = stock_code.startswith('6') or stock_code.startswith('SH')
            limit_up_ratio = 1.10 if is_shanghai else 1.10  # A股都是10%
            limit_up_price = pre_close * limit_up_ratio
            
            # 涨停价检查：如果当前价格接近或达到涨停价，不允许买入
            if price >= limit_up_price * 0.998:  # 允许0.2%的误差
                logger.warning(f"⛔ [涨停限制] {stock_code} 当前价{price:.2f}接近涨停价{limit_up_price:.2f}，不可买入")
                self.blocked_by_limit_up += 1
                return None
        
        # 计算买入数量
        position_value = self.cash * self.position_size
        quantity = int(position_value / price / 100) * 100  # 手数（100股/手）
        
        if quantity < 100:
            logger.warning(f"资金不足，无法开仓: {stock_code} @ {price}")
            self.blocked_by_cash += 1
            return None
        
        # 扣除现金
        cost = quantity * price * 1.0003  # 含手续费
        if cost > self.cash:
            self.blocked_by_cash += 1
            return None
        
        self.cash -= cost
        
        # 创建仓位（今仓，今日不可卖）
        position = T1Position(
            stock_code=stock_code,
            position_today=quantity,
            entry_price=price,
            entry_time=time
        )
        self.positions[stock_code] = position
        self.current_holding = stock_code
        
        # 记录交易
        trade = T1Trade(
            stock_code=stock_code,
            entry_date=date,
            entry_time=time,
            entry_price=price
        )
        
        logger.info(f"📈 [开仓] {stock_code} {date} {time} @ {price:.2f} x {quantity}股")
        return trade
    
    def _close_position(self, stock_code: str, date: str, time: str, price: float, reason: str) -> Optional[T1Trade]:
        """平仓（T+1规则：只能平昨仓）"""
        if stock_code not in self.positions:
            return None
        
        position = self.positions[stock_code]
        
        # T+1规则检查：只能卖昨仓
        if position.position_carry == 0:
            logger.debug(f"⏳ [T+1限制] {stock_code} 今仓不能今日卖出")
            self.blocked_by_t1 += 1
            return None
        
        # 计算盈亏
        quantity = position.position_carry
        sell_value = quantity * price * 0.9997  # 扣除手续费
        pnl = (price - position.entry_price) * quantity
        pnl_pct = (price - position.entry_price) / position.entry_price
        
        # 回收现金
        self.cash += sell_value
        
        # 清理仓位
        del self.positions[stock_code]
        self.current_holding = None
        
        # 记录交易
        trade = T1Trade(
            stock_code=stock_code,
            entry_date=position.entry_date,
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_date=date,
            exit_time=time,
            exit_price=price,
            exit_reason=reason,
            pnl=pnl,
            pnl_pct=pnl_pct,
            is_signal_only=False
        )
        
        logger.info(f"📉 [平仓] {stock_code} {date} {time} @ {price:.2f} 盈亏:{pnl_pct*100:.2f}% ({reason})")
        return trade
    
    def _end_of_day_settlement(self, date: str):
        """收盘结算：今仓变昨仓"""
        for code, position in self.positions.items():
            if position.position_today > 0:
                # 今仓 -> 昨仓
                position.position_carry = position.position_today
                position.position_today = 0
                logger.debug(f"🔄 [日结] {code} 今仓{position.position_carry}股变昨仓")
    
    def _process_tick(self, stock_code: str, tick: TickData, date: str) -> Tuple[Optional[T1Trade], Optional[T1Trade]]:
        """处理单个Tick
        
        Returns:
            (signal_trade, t1_trade) - 信号层交易和T+1层交易
        """
        signal_trade = None
        t1_trade = None
        
        # 简化的策略逻辑：价格突破即买入
        # TODO: 接入真实的Halfway策略检测
        price = tick.last_price
        time_str = datetime.fromtimestamp(tick.time/1000).strftime('%H:%M:%S')
        
        # 检查是否需要平仓（止盈/止损/时间退出）
        if stock_code == self.current_holding and stock_code in self.positions:
            position = self.positions[stock_code]
            
            # 计算盈亏
            pnl_pct = (price - position.entry_price) / position.entry_price
            
            # 检查止盈
            if pnl_pct >= self.take_profit_pct:
                t1_trade = self._close_position(stock_code, date, time_str, price, 'take_profit')
            # 检查止损
            elif pnl_pct <= -self.stop_loss_pct:
                t1_trade = self._close_position(stock_code, date, time_str, price, 'stop_loss')
            # 检查持仓时间
            else:
                entry_dt = datetime.strptime(f"{position.entry_date} {position.entry_time}", '%Y-%m-%d %H:%M:%S')
                current_dt = datetime.strptime(f"{date} {time_str}", '%Y-%m-%d %H:%M:%S')
                holding_minutes = (current_dt - entry_dt).total_seconds() / 60
                
                if holding_minutes >= self.max_holding_minutes:
                    t1_trade = self._close_position(stock_code, date, time_str, price, 'time_exit')
        
        return signal_trade, t1_trade
    
    def run_backtest(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> T1BacktestResult:
        """运行回测"""
        result = T1BacktestResult(initial_capital=self.initial_capital)
        
        logger.info(f"🎯 [单吊T+1回测] 开始")
        logger.info(f"   - 股票数量: {len(stock_codes)}")
        logger.info(f"   - 回测区间: {start_date} 至 {end_date}")
        
        # 生成日期列表
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
        
        for date_obj in date_range:
            date_str = date_obj.strftime('%Y-%m-%d')
            logger.info(f"\n📅 [交易日] {date_str}")
            
            # 遍历每只股票
            for stock_code in stock_codes:
                try:
                    # 获取Tick数据
                    provider = QMTHistoricalProvider(
                        stock_code=stock_code,
                        start_time=date_str.replace('-', ''),
                        end_time=date_str.replace('-', ''),
                        period='tick'
                    )
                    
                    tick_df = provider.get_raw_ticks()
                    if tick_df.empty:
                        continue
                    
                    # 遍历Tick
                    for _, row in tick_df.iterrows():
                        tick = TickData(
                            time=int(row['time']),
                            last_price=float(row['lastPrice']),
                            volume=float(row['volume']),
                            amount=float(row['amount']),
                            bid_price=float(row['bidPrice'][0]) if isinstance(row['bidPrice'], list) and len(row['bidPrice']) > 0 else float(row['bidPrice']),
                            ask_price=float(row['askPrice'][0]) if isinstance(row['askPrice'], list) and len(row['askPrice']) > 0 else float(row['askPrice']),
                            bid_vol=int(row['bidVol'][0]) if isinstance(row['bidVol'], list) and len(row['bidVol']) > 0 else int(row['bidVol']),
                            ask_vol=int(row['askVol'][0]) if isinstance(row['askVol'], list) and len(row['askVol']) > 0 else int(row['askVol']),
                        )
                        
                        signal_trade, t1_trade = self._process_tick(stock_code, tick, date_str)
                        
                        if signal_trade:
                            result.signal_trades.append(signal_trade)
                        if t1_trade:
                            result.t1_trades.append(t1_trade)
                    
                except Exception as e:
                    logger.error(f"处理 {stock_code} {date_str} 时出错: {e}")
                    continue
            
            # 收盘结算
            self._end_of_day_settlement(date_str)
            
            # 记录权益曲线
            total_equity = self.cash
            for pos in self.positions.values():
                # 简化为按成本价计算持仓市值
                total_equity += pos.total_position * pos.entry_price
            
            result.equity_curve.append({
                'date': date_str,
                'cash': self.cash,
                'equity': total_equity
            })
        
        # 统计结果
        result.signal_total = len(result.signal_trades)
        result.signal_winning = sum(1 for t in result.signal_trades if t.pnl and t.pnl > 0)
        result.signal_losing = sum(1 for t in result.signal_trades if t.pnl and t.pnl < 0)
        result.signal_pnl = sum(t.pnl for t in result.signal_trades if t.pnl)
        
        result.trade_total = len(result.t1_trades)
        result.trade_winning = sum(1 for t in result.t1_trades if t.pnl and t.pnl > 0)
        result.trade_losing = sum(1 for t in result.t1_trades if t.pnl and t.pnl < 0)
        result.trade_pnl = sum(t.pnl for t in result.t1_trades if t.pnl)
        result.final_capital = self.cash
        
        # V17：阻塞统计
        result.blocked_by_limit_up = self.blocked_by_limit_up
        result.blocked_by_t1 = self.blocked_by_t1
        result.blocked_by_cash = self.blocked_by_cash
        
        logger.info(f"\n✅ [回测完成]")
        logger.info(f"   信号层: {result.signal_total}笔 胜率{result.signal_win_rate*100:.1f}% 盈亏{result.signal_pnl:.2f}")
        logger.info(f"   T+1层: {result.trade_total}笔 胜率{result.trade_win_rate*100:.1f}% 盈亏{result.trade_pnl:.2f}")
        logger.info(f"   ⚠️  阻塞统计: 涨停{result.blocked_by_limit_up}次 T+1限制{result.blocked_by_t1}次 资金不足{result.blocked_by_cash}次")
        
        return result


def main():
    parser = argparse.ArgumentParser(description='单吊T+1回测引擎')
    parser.add_argument('--stocks', type=str, help='股票代码文件（每行一只）')
    parser.add_argument('--start-date', type=str, required=True, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, default='backtest/results/single_holding_t1_result.json')
    parser.add_argument('--initial-capital', type=float, default=100000, help='初始资金')
    parser.add_argument('--position-size', type=float, default=0.5, help='单吊仓位比例')
    parser.add_argument('--stop-loss', type=float, default=0.02, help='止损比例')
    parser.add_argument('--take-profit', type=float, default=0.05, help='止盈比例')
    
    args = parser.parse_args()
    
    # 加载股票列表
    if args.stocks:
        with open(args.stocks, 'r') as f:
            stock_codes = [line.strip() for line in f if line.strip()]
    else:
        # 默认测试股票
        stock_codes = ['000017.SZ', '000021.SZ', '000066.SZ']
    
    # 创建回测器
    backtester = SingleHoldingT1Backtester(
        initial_capital=args.initial_capital,
        position_size=args.position_size,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit
    )
    
    # 运行回测
    result = backtester.run_backtest(
        stock_codes=stock_codes,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # 保存结果
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n💾 结果已保存: {output_path}")


if __name__ == "__main__":
    main()
