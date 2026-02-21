#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半路突破专题回放回测 (Halfway Breakout Replay Backtest)

⚠️  V17生产约束声明 / 研究用途标记
==============================================================================
【重要】本脚本为"研究用途"（Research Use Only），不是V17官方回测流水线

根据 SIGNAL_AND_PORTFOLIO_CONTRACT.md V17生产约束：
- V17上线前唯一认可的回测命令：run_tick_replay_backtest.py
- 本脚本（run_halfway_replay_backtest.py）禁止作为V17上线决策依据
- 本脚本仅用于：Halfway战法离线研究、参数调优、样本挖掘

V18任务：将此脚本统一迁移到BacktestEngine框架（Issue待创建）
==============================================================================

功能：
1. 专门回放和评估Halfway Breakout策略的表现
2. 独立于FullMarketScanner三漏斗体系，专注单一战法研究
3. 统计触发频率、胜率、盈亏比等指标
4. 生成可视化报告

与FullMarketScanner的区别：
- FullMarketScanner：三漏斗综合策略，实战使用
- HalfwayReplay：单一战法研究，参数调优使用（研究用途）

Author: AI Project Director  
Version: V1.0（研究用途版）
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

from logic.strategies.unified_warfare_core import get_unified_warfare_core
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.tick_strategy_interface import TickData
from logic.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HalfwayTrade:
    """半路突破交易记录"""
    stock_code: str
    entry_date: str
    entry_time: str
    entry_price: float
    entry_confidence: float
    exit_date: Optional[str] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None  # 'take_profit', 'stop_loss', 'end_of_day'
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    holding_period: Optional[int] = None  # 持有周期（秒）


@dataclass
class HalfwayBacktestResult:
    """半路突破回测结果"""
    total_signals: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    avg_holding_period: float = 0.0
    trades: List[HalfwayTrade] = field(default_factory=list)
    daily_stats: Dict = field(default_factory=dict)
    
    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    @property
    def profit_factor(self) -> float:
        """盈亏比"""
        total_profit = sum(t.pnl for t in self.trades if t.pnl and t.pnl > 0)
        total_loss = abs(sum(t.pnl for t in self.trades if t.pnl and t.pnl < 0))
        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0
        return total_profit / total_loss
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'total_signals': self.total_signals,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'max_drawdown': self.max_drawdown,
            'avg_holding_period': self.avg_holding_period,
            'trades': [
                {
                    'stock_code': t.stock_code,
                    'entry_date': t.entry_date,
                    'entry_time': t.entry_time,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct,
                    'exit_reason': t.exit_reason,
                }
                for t in self.trades
            ]
        }


class HalfwayReplayBacktester:
    """半路突破回放回测器"""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        position_size: float = 0.1,  # 每笔仓位（总资金比例）
        stop_loss_pct: float = 0.03,  # 止损比例
        take_profit_pct: float = 0.05,  # 止盈比例
        max_holding_minutes: int = 30,  # 最大持有时间（分钟）
        min_confidence: float = 0.3,  # 最小置信度
    ):
        """
        初始化回测器
        
        Args:
            initial_capital: 初始资金
            position_size: 每笔仓位比例
            stop_loss_pct: 止损比例
            take_profit_pct: 止盈比例
            max_holding_minutes: 最大持有时间（分钟）
            min_confidence: 最小置信度阈值
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_holding_minutes = max_holding_minutes
        self.min_confidence = min_confidence
        
        # 获取统一战法核心
        self.warfare_core = get_unified_warfare_core()
        
        # 回测状态
        self.current_capital = initial_capital
        self.open_trades: Dict[str, HalfwayTrade] = {}  # 当前持仓
        self.completed_trades: List[HalfwayTrade] = []
        
        logger.info(f"✅ [Halfway回放回测器] 初始化完成")
        logger.info(f"   - 初始资金: {initial_capital:,.2f}")
        logger.info(f"   - 每笔仓位: {position_size*100:.0f}%")
        logger.info(f"   - 止损/止盈: {stop_loss_pct*100:.1f}% / {take_profit_pct*100:.1f}%")
        logger.info(f"   - 最大持有: {max_holding_minutes}分钟")
        logger.info(f"   - 最小置信度: {min_confidence}")
    
    def run_backtest(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> HalfwayBacktestResult:
        """
        运行回测
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            回测结果
        """
        result = HalfwayBacktestResult()
        
        logger.info(f"🎯 [Halfway回放回测] 开始")
        logger.info(f"   - 股票数量: {len(stock_codes)}")
        logger.info(f"   - 回测区间: {start_date} 至 {end_date}")
        
        # 遍历每只股票
        for stock_code in stock_codes:
            logger.info(f"\n📊 处理股票: {stock_code}")
            
            # 处理单只股票
            self._process_single_stock(stock_code, start_date, end_date, result)
        
        # 整理结果
        result.total_trades = len(result.trades)
        result.winning_trades = len([t for t in result.trades if t.pnl and t.pnl > 0])
        result.losing_trades = len([t for t in result.trades if t.pnl and t.pnl < 0])
        result.total_pnl = sum(t.pnl for t in result.trades if t.pnl)
        result.total_pnl_pct = sum(t.pnl_pct for t in result.trades if t.pnl_pct)
        
        if result.trades:
            result.avg_holding_period = sum(
                t.holding_period for t in result.trades if t.holding_period
            ) / len(result.trades)
        
        return result
    
    def _process_single_stock(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        result: HalfwayBacktestResult
    ):
        """处理单只股票"""
        # 解析日期
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            
            try:
                self._process_single_day(stock_code, date_str, result)
            except Exception as e:
                logger.error(f"   {date_str}: 处理失败 - {e}")
            
            current_dt += timedelta(days=1)
    
    def _process_single_day(
        self,
        stock_code: str,
        date_str: str,
        result: HalfwayBacktestResult
    ):
        """处理单日数据"""
        # 获取当日Tick数据
        provider = QMTHistoricalProvider(
            stock_code=stock_code,
            start_time=f"{date_str.replace('-', '')}093000",
            end_time=f"{date_str.replace('-', '')}150000",
            period="tick"
        )
        
        ticks = []
        for tick in provider.iter_ticks():
            ticks.append(tick)
        
        if len(ticks) < 20:
            return
        
        # 滑动窗口处理
        window_size = 20
        for i in range(window_size, len(ticks)):
            current_tick = ticks[i]
            window_ticks = ticks[i-window_size:i+1]
            
            # 构建tick_data
            tick_data = {
                'stock_code': stock_code,
                'datetime': datetime.fromtimestamp(float(current_tick['time']) / 1000),  # 🔥 V11.0修复：time字符串转float
                'price': current_tick['last_price'],
                'volume': current_tick['volume'],
                'amount': current_tick.get('amount', 0),
            }
            
            # 构建上下文
            price_history = [t['last_price'] for t in window_ticks]
            volume_history = [t['volume'] for t in window_ticks]
            
            context = {
                'price_history': price_history,
                'volume_history': volume_history,
                'ma5': sum(price_history[-5:]) / 5,
                'ma20': sum(price_history) / len(price_history),
                'pre_close': current_tick.get('preClose', current_tick.get('last_price', 0)),  # 🔥 V11.0修复：添加pre_close
            }
            
            # 检查是否有持仓需要处理
            self._check_exit_conditions(stock_code, current_tick, result)
            
            # 检测Halfway信号
            events = self.warfare_core.process_tick(tick_data, context)
            halfway_events = [e for e in events if e['event_type'] == 'halfway_breakout']
            
            for event in halfway_events:
                result.total_signals += 1
                
                if event['confidence'] >= self.min_confidence:
                    # 检查是否已有持仓
                    if stock_code not in self.open_trades:
                        # 开仓
                        trade = HalfwayTrade(
                            stock_code=stock_code,
                            entry_date=date_str,
                            entry_time=datetime.fromtimestamp(float(current_tick['time']) / 1000).strftime("%H:%M:%S"),  # 🔥 V11.0修复：time字符串转float
                            entry_price=current_tick['last_price'],
                            entry_confidence=event['confidence']
                        )
                        self.open_trades[stock_code] = trade
                        logger.info(f"   🟢 开仓: {stock_code} @ {trade.entry_price:.2f} (置信度:{event['confidence']:.2f})")
    
    def _check_exit_conditions(
        self,
        stock_code: str,
        current_tick: Dict,
        result: HalfwayBacktestResult
    ):
        """检查平仓条件"""
        if stock_code not in self.open_trades:
            return
        
        trade = self.open_trades[stock_code]
        current_price = current_tick['last_price']
        current_time = datetime.fromtimestamp(float(current_tick['time']) / 1000)  # 🔥 V11.0修复：time字符串转float
        entry_time = datetime.strptime(f"{trade.entry_date} {trade.entry_time}", "%Y-%m-%d %H:%M:%S")
        
        # 计算盈亏
        pnl_pct = (current_price - trade.entry_price) / trade.entry_price
        
        # 检查止损
        if pnl_pct <= -self.stop_loss_pct:
            trade.exit_price = current_price
            trade.exit_reason = 'stop_loss'
            trade.pnl_pct = pnl_pct
            trade.holding_period = int((current_time - entry_time).total_seconds())
            
            result.trades.append(trade)
            del self.open_trades[stock_code]
            logger.info(f"   🔴 止损平仓: {stock_code} @ {current_price:.2f} (盈亏:{pnl_pct*100:.2f}%)")
            return
        
        # 检查止盈
        if pnl_pct >= self.take_profit_pct:
            trade.exit_price = current_price
            trade.exit_reason = 'take_profit'
            trade.pnl_pct = pnl_pct
            trade.holding_period = int((current_time - entry_time).total_seconds())
            
            result.trades.append(trade)
            del self.open_trades[stock_code]
            logger.info(f"   🟢 止盈平仓: {stock_code} @ {current_price:.2f} (盈亏:{pnl_pct*100:.2f}%)")
            return
        
        # 检查最大持有时间
        holding_minutes = (current_time - entry_time).total_seconds() / 60
        if holding_minutes >= self.max_holding_minutes:
            trade.exit_price = current_price
            trade.exit_reason = 'time_exit'
            trade.pnl_pct = pnl_pct
            trade.holding_period = int((current_time - entry_time).total_seconds())
            
            result.trades.append(trade)
            del self.open_trades[stock_code]
            logger.info(f"   ⏰ 时间平仓: {stock_code} @ {current_price:.2f} (盈亏:{pnl_pct*100:.2f}%)")
            return
    
    def close_all_positions(self, result: HalfwayBacktestResult):
        """平仓所有持仓（收盘时）"""
        for stock_code, trade in list(self.open_trades.items()):
            # 使用最后已知价格平仓
            trade.exit_reason = 'end_of_day'
            trade.pnl_pct = 0.0  # 未知，设为0
            
            result.trades.append(trade)
            logger.info(f"   📌 收盘强平: {stock_code}")
        
        self.open_trades.clear()


def print_backtest_report(result: HalfwayBacktestResult):
    """打印回测报告"""
    print("\n" + "="*80)
    print("🎯 Halfway Breakout 专题回测报告")
    print("="*80)
    
    print(f"\n📊 信号统计:")
    print(f"   - 总信号数: {result.total_signals}")
    print(f"   - 实际交易数: {result.total_trades}")
    print(f"   - 信号转化率: {result.total_trades/result.total_signals*100:.1f}%" if result.total_signals > 0 else "   - 信号转化率: N/A")
    
    print(f"\n💰 盈亏统计:")
    print(f"   - 盈利笔数: {result.winning_trades}")
    print(f"   - 亏损笔数: {result.losing_trades}")
    print(f"   - 胜率: {result.win_rate*100:.1f}%")
    print(f"   - 盈亏比: {result.profit_factor:.2f}")
    print(f"   - 总盈亏: {result.total_pnl:+.2f}")
    print(f"   - 总盈亏率: {result.total_pnl_pct:+.2f}%")
    
    print(f"\n⏱️ 时间统计:")
    print(f"   - 平均持有时间: {result.avg_holding_period/60:.1f}分钟")
    
    print(f"\n📈 最近5笔交易:")
    for trade in result.trades[-5:]:
        status = "🟢" if trade.pnl_pct and trade.pnl_pct > 0 else "🔴"
        print(f"   {status} {trade.stock_code} {trade.entry_date} {trade.entry_time}")
        print(f"      入场:{trade.entry_price:.2f} 出场:{trade.exit_price:.2f} 盈亏:{trade.pnl_pct*100:+.2f}%")
        print(f"      原因:{trade.exit_reason}")
    
    print("="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Halfway Breakout专题回放回测')
    parser.add_argument('--stocks', type=str, help='股票代码文件')
    parser.add_argument('--start-date', type=str, required=True, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, default='backtest/reports/halfway_replay_result.json',
                       help='输出报告路径')
    parser.add_argument('--stop-loss', type=float, default=0.03, help='止损比例')
    parser.add_argument('--take-profit', type=float, default=0.05, help='止盈比例')
    parser.add_argument('--holding-time', type=int, default=30, help='最大持有时间(分钟)')
    parser.add_argument('--min-confidence', type=float, default=0.3, help='最小置信度')
    
    args = parser.parse_args()
    
    # 加载股票列表
    if args.stocks:
        with open(args.stocks, 'r') as f:
            stock_codes = [line.strip() for line in f if line.strip()]
    else:
        # 默认使用前20只热门股
        hot_stocks_path = PROJECT_ROOT / "config" / "hot_stocks.json"
        with open(hot_stocks_path, 'r') as f:
            stock_codes = json.load(f)
        stock_codes = stock_codes[:20]
    
    logger.info(f"🎯 Halfway Breakout 专题回放回测")
    logger.info(f"   股票数: {len(stock_codes)}")
    logger.info(f"   回测区间: {args.start_date} 至 {args.end_date}")
    
    # 创建回测器
    backtester = HalfwayReplayBacktester(
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
        max_holding_minutes=args.holding_time,
        min_confidence=args.min_confidence
    )
    
    # 运行回测
    result = backtester.run_backtest(
        stock_codes=stock_codes,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # 打印报告
    print_backtest_report(result)
    
    # 保存报告
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n💾 报告已保存: {output_path}")


if __name__ == "__main__":
    main()
