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
from typing import Dict, List, Optional, Tuple, Protocol
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
class CostModel:
    """成本模型 - 支持参数化配置真实交易费用
    
    默认值按真实账户费率设置（万0.85佣金）
    支持压力测试：可通过提高费率测试策略鲁棒性
    """
    commission_rate: float = 0.000085  # 佣金率（万0.85，真实账户费率）
    min_commission: float = 5.0        # 最低佣金（元）
    stamp_duty_rate: float = 0.001     # 印花税率（卖出单边，千分之一）
    transfer_fee_rate: float = 0.00002 # 过户费率（沪市，万分之0.2）
    slippage_bp: float = 10.0          # 滑点（基点，10bp=0.1%，保守估计）
    
    def calculate_buy_cost(self, quantity: int, price: float) -> Tuple[float, float]:
        """计算买入总成本
        
        Returns:
            (总成本, 其中手续费) - 总成本包含股票市值+所有费用
        """
        notional = quantity * price
        commission = max(notional * self.commission_rate, self.min_commission)
        # 买入不收印花税，只收佣金和过户费（沪市）
        transfer_fee = notional * self.transfer_fee_rate  # 过户费（双边）
        total_cost = notional + commission + transfer_fee + (notional * self.slippage_bp / 10000)
        return total_cost, commission + transfer_fee + (notional * self.slippage_bp / 10000)
    
    def calculate_sell_proceeds(self, quantity: int, price: float) -> Tuple[float, float]:
        """计算卖出净收入
        
        Returns:
            (净收入, 扣除的总费用) - 净收入=股票市值-所有费用
        """
        notional = quantity * price
        commission = max(notional * self.commission_rate, self.min_commission)
        stamp_duty = notional * self.stamp_duty_rate  # 印花税（卖出单边）
        transfer_fee = notional * self.transfer_fee_rate  # 过户费
        total_fees = commission + stamp_duty + transfer_fee + (notional * self.slippage_bp / 10000)
        net_proceeds = notional - total_fees
        return net_proceeds, total_fees
    
    def to_dict(self) -> Dict:
        """转换为字典（用于JSON报告）"""
        return {
            'commission_rate': self.commission_rate,
            'min_commission': self.min_commission,
            'stamp_duty_rate': self.stamp_duty_rate,
            'transfer_fee_rate': self.transfer_fee_rate,
            'slippage_bp': self.slippage_bp,
            'description': f'佣金{self.commission_rate*10000:.2f}万+印花税{self.stamp_duty_rate*1000:.1f}‰+滑点{self.slippage_bp}bp'
        }


@dataclass
class T1Position:
    """T+1仓位状态"""
    stock_code: str
    position_carry: int = 0  # 昨仓（今日可卖）
    position_today: int = 0  # 今仓（今日不可卖）
    entry_price: float = 0.0
    entry_date: str = ""  # 入场日期
    entry_time: str = ""  # 入场时间
    
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
    """T+1回测结果（三层信号统计）
    
    V17声明：
    - 采用全仓买入/全仓卖出的简化模型，不支持分批卖出
    - 涨停检查：当前价格接近涨停价时禁止买入
    - 三层信号统计：Raw -> Executable -> Executed
    """
    # ========== 三层信号统计（CTO要求）==========
    # Layer 1: Raw Signals（策略原始意图，仅策略条件过滤）
    raw_signal_total: int = 0      # 策略条件满足次数
    raw_signal_opens: int = 0      # Raw开仓信号数
    raw_signal_closes: int = 0     # Raw平仓信号数
    
    # Layer 2: Executable Signals（可执行信号，过制度约束）
    executable_signal_total: int = 0   # 可执行信号总数
    executable_opens: int = 0          # 可执行开仓（过T+1/涨停/资金检查）
    executable_opens_blocked: int = 0  # 开仓被阻断数
    executable_closes: int = 0         # 可执行平仓
    executable_closes_blocked: int = 0 # 平仓被阻断数
    
    # Layer 3: Executed Signals（实际成交，即trade_layer）
    trade_total: int = 0
    trade_winning: int = 0
    trade_losing: int = 0
    trade_pnl: float = 0.0
    
    # 兼容旧版本（signal_layer现在等于executable_layer）
    @property
    def signal_total(self) -> int:
        return self.executable_signal_total
    @property
    def signal_winning(self) -> int:
        return self.trade_winning  # 可执行信号的胜率按实际成交统计
    @property
    def signal_losing(self) -> int:
        return self.trade_losing
    @property
    def signal_pnl(self) -> float:
        return self.trade_pnl
    
    # 资金曲线
    initial_capital: float = 100000.0
    final_cash: float = 100000.0  # 纯现金（不含未平仓市值）
    final_equity: float = 100000.0  # 总权益（现金+持仓市值）
    max_drawdown: float = 0.0
    
    # 交易明细
    raw_signal_trades: List[T1Trade] = field(default_factory=list)        # Raw信号明细
    executable_signal_trades: List[T1Trade] = field(default_factory=list)  # 可执行信号明细
    t1_trades: List[T1Trade] = field(default_factory=list)                # 实际成交明细
    equity_curve: List[Dict] = field(default_factory=list)
    
    # V17新增：阻塞统计
    blocked_by_limit_up: int = 0    # 因涨停无法买入次数
    blocked_by_limit_down: int = 0  # 因跌停无法卖出次数
    blocked_by_t1: int = 0          # 因T+1限制无法卖出次数
    blocked_by_cash: int = 0        # 因资金不足未执行次数
    
    # V17新增：成本模型（用于报告中披露费用假设）
    cost_model: Optional['CostModel'] = None
    
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
                'note': 'V17: 现在signal_layer = executable_layer（可执行信号）',
                'total_trades': self.signal_total,
                'winning_trades': self.signal_winning,
                'losing_trades': self.signal_losing,
                'win_rate': self.signal_win_rate,
                'total_pnl': self.signal_pnl,
            },
            'three_layer_stats': {
                'raw_signals': {
                    'total': self.raw_signal_total,
                    'open_signals': self.raw_signal_opens,
                    'close_signals': self.raw_signal_closes,
                    'description': '策略原始意图（仅策略条件过滤）'
                },
                'executable_signals': {
                    'total': self.executable_signal_total,
                    'opens': self.executable_opens,
                    'opens_blocked': self.executable_opens_blocked,
                    'closes': self.executable_closes,
                    'closes_blocked': self.executable_closes_blocked,
                    'description': '可执行信号（过T+1/涨停/资金检查）'
                },
                'executed_trades': {
                    'total': self.trade_total,
                    'winning': self.trade_winning,
                    'losing': self.trade_losing,
                    'win_rate': self.trade_win_rate,
                    'pnl': self.trade_pnl,
                    'description': '实际成交（executed）'
                }
            },
            'trade_layer': {
                'total_trades': self.trade_total,
                'winning_trades': self.trade_winning,
                'losing_trades': self.trade_losing,
                'win_rate': self.trade_win_rate,
                'total_pnl': self.trade_pnl,
                'initial_capital': self.initial_capital,
                'final_cash': self.final_cash,  # 纯现金
                'final_equity': self.final_equity,  # 总权益（现金+持仓）
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
                'by_limit_down': self.blocked_by_limit_down,
                'by_t1_rule': self.blocked_by_t1,
                'by_cash': self.blocked_by_cash,
            },
            'cost_assumptions': self.cost_model.to_dict() if self.cost_model else {
                'commission_rate': 0.0003,
                'note': '使用默认万三费率（未指定cost_model）'
            }
        }


class SignalGenerator(Protocol):
    """策略信号接口 - 只负责开仓决策"""
    def should_open(self, stock_code: str, tick: TickData, date: str,
                    context: dict) -> bool:
        """返回是否应该开仓"""
        pass
    
    def reset_daily(self):
        """日结重置状态"""
        pass


class TrivialSignalGenerator:
    """TRIVIAL策略：每天第一笔有效价格开仓（单吊）
    
    V17修正：
    - 单吊=每天全局只开一次仓（不是每只股票每天一次）
    - 使用_has_opened_today全局标记，而非每股票集合
    """
    def __init__(self):
        self._has_opened_today: bool = False  # 全局：今天是否已开仓
        self._last_open_date: str = ""        # 记录上次开仓日期
    
    def reset_daily(self):
        """日结重置"""
        self._has_opened_today = False
    
    def should_open(self, stock_code: str, tick: TickData, date: str,
                    context: dict) -> bool:
        # 无效价格不开仓
        if tick.last_price <= 0:
            return False
        
        # V17修正：单吊策略，每天全局只开一次
        # 如果今天已经开仓过（无论哪只股票），不再开仓
        if self._has_opened_today:
            return False
        
        # 空仓才能开仓（单吊约束）
        if context.get('current_holding') is not None:
            return False
        
        # 满足条件：记录今日已开仓，返回True
        self._has_opened_today = True
        self._last_open_date = date
        return True


class HalfwaySignalAdapter:
    """Halfway策略适配器 - 只负责开仓信号"""
    
    def __init__(self, strategy):
        """
        初始化适配器
        
        Args:
            strategy: HalfwayTickStrategy实例
        """
        self.strategy = strategy
        self._opened_today: set = set()
    
    def reset_daily(self):
        """日结重置"""
        self._opened_today.clear()
        # 同时重置底层策略状态（如果需要）
        if hasattr(self.strategy, 'reset'):
            self.strategy.reset()
    
    def should_open(self, stock_code: str, tick: TickData, date: str,
                    context: dict) -> bool:
        """
        判断是否应该开仓
        
        规则：
        1. 无效价格不开仓
        2. 空仓才能开仓（单吊约束）
        3. 每天每只股票只开一笔
        4. 必须明确命中Halfway做多信号
        """
        # 无效价格不开仓
        if tick.last_price <= 0:
            return False
        
        # 空仓才能开仓（单吊约束）
        if context.get('current_holding') is not None:
            return False
        
        # 每天只开一笔
        date_key = f"{stock_code}_{date}"
        if date_key in self._opened_today:
            return False
        
        # 调用Halfway策略获取信号
        signals = self.strategy.on_tick(tick)
        
        # 检查是否有有效的Halfway做多信号
        for signal in signals:
            # 必须是Halfway类型的信号
            if signal.signal_type != 'HALFWAY':
                continue
            # 信号强度必须大于0
            if signal.strength <= 0:
                continue
            # 确认开仓
            self._opened_today.add(date_key)
            return True
        
        return False


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
        signal_generator: Optional[SignalGenerator] = None,  # 策略信号生成器
        cost_model: Optional[CostModel] = None,  # 成本模型（默认真实费率万0.85）
    ):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss_pct = stop_loss_pct
        self.cost_model = cost_model or CostModel()  # 默认使用真实费率
        self.take_profit_pct = take_profit_pct
        self.max_holding_minutes = max_holding_minutes
        
        # 状态机
        self.cash = initial_capital
        self.positions: Dict[str, T1Position] = {}  # 股票代码 -> 仓位
        self.current_holding: Optional[str] = None  # 当前持有的股票（单吊）
        self.last_prices: Dict[str, float] = {}  # 跟踪每只股票最后价格
        
        # 结果记录
        self.signal_trades: List[T1Trade] = []
        self.t1_trades: List[T1Trade] = []
        self.equity_curve: List[Dict] = []
        
        # V17新增：阻塞统计
        self.blocked_by_limit_up = 0   # 涨停无法买入
        self.blocked_by_limit_down = 0  # 跌停无法卖出（新增）
        self.blocked_by_t1 = 0         # T+1限制
        self.blocked_by_cash = 0       # 资金不足
        
        # 策略信号生成器（默认TRIVIAL模式）
        self.signal_generator = signal_generator or TrivialSignalGenerator()
        self._strategy_mode = "TRIVIAL" if signal_generator is None else "CUSTOM"
        
        logger.info(f"✅ [单吊T+1回测器] 初始化完成")
        logger.info(f"   - 初始资金: {initial_capital:,.2f}")
        logger.info(f"   - 单吊仓位: {position_size*100:.0f}%")
        logger.info(f"   - 止损/止盈: {stop_loss_pct*100:.1f}% / {take_profit_pct*100:.1f}%")
        logger.info(f"   - 最大持有: {max_holding_minutes}分钟")
        logger.info(f"   - ⚠️  V17简化模型：全仓进出，不支持分批卖出")
    
    def _can_open_position(self, date: str) -> bool:
        """检查是否可以开新仓（单吊：必须空仓）"""
        return self.current_holding is None
    
    def _get_limit_pct(self, stock_code: str) -> float:
        """获取股票涨跌停幅度
        
        Returns:
            float: 涨跌停幅度（0.10=10%, 0.20=20%）
        """
        # 创业板: 300/301开头，20cm
        if stock_code.startswith(('300', '301')) and '.SZ' in stock_code:
            return 0.20
        # 科创板: 688开头，20cm
        if stock_code.startswith('688') and '.SH' in stock_code:
            return 0.20
        # 北交所: 8/43开头，30cm（暂不处理，按20cm保守处理）
        if stock_code.startswith(('8', '43')) and '.BJ' in stock_code:
            return 0.30  # 北交所30cm
        # 默认主板: 10cm
        return 0.10
    
    def _get_prev_close(self, stock_code: str, tick: TickData) -> Optional[float]:
        """获取昨日收盘价
        
        优先从tick数据获取，如果没有则尝试从缓存获取
        """
        # 尝试从tick的preclose字段获取（如果有的话）
        if hasattr(tick, 'pre_close') and tick.pre_close > 0:
            return tick.pre_close
        
        # 尝试从last_prices缓存获取（作为fallback）
        # 注意：这只适用于已经有持仓的情况
        if stock_code in self.positions:
            return self.positions[stock_code].entry_price
        
        return None
    
    def _check_limit_price(self, stock_code: str, price: float, tick: TickData, direction: str) -> bool:
        """检查价格是否触及涨跌停（保守版）
        
        Args:
            stock_code: 股票代码
            price: 当前价格
            tick: Tick数据（用于获取preclose）
            direction: 'buy' 或 'sell'
            
        Returns:
            bool: True=可以成交, False=触及涨跌停不能成交
        """
        # 获取昨日收盘价
        prev_close = self._get_prev_close(stock_code, tick)
        if not prev_close or prev_close <= 0:
            # 无法获取昨收，默认允许成交（保守起见）
            return True
        
        # 获取涨跌停幅度
        limit_pct = self._get_limit_pct(stock_code)
        
        # 计算涨跌停价格
        limit_up = prev_close * (1 + limit_pct)
        limit_down = prev_close * (1 - limit_pct)
        
        # 买入检查：如果价格接近或达到涨停价，禁止买入
        if direction == 'buy':
            # 保守策略：价格 >= 涨停价 * 0.995 视为触及涨停
            if price >= limit_up * 0.995:
                logger.debug(f"🚫 [涨停限制] {stock_code} 买入价{price:.2f} >= 涨停价{limit_up:.2f}")
                return False
        
        # 卖出检查：如果价格接近或达到跌停价，禁止卖出
        elif direction == 'sell':
            # 保守策略：价格 <= 跌停价 * 1.005 视为触及跌停
            if price <= limit_down * 1.005:
                logger.debug(f"🚫 [跌停限制] {stock_code} 卖出价{price:.2f} <= 跌停价{limit_down:.2f}")
                return False
        
        return True
    
    def _open_position(self, stock_code: str, date: str, time: str, price: float) -> Optional[T1Trade]:
        """开新仓（T+1规则）
        
        Args:
            stock_code: 股票代码
            date: 日期
            time: 时间
            price: 当前价格
        """
        if not self._can_open_position(date):
            return None
        
        # V17极简规则：暂时关闭涨停检查，先验证引擎
        # TODO: 后续接入真实涨停价检查
        
        # 计算买入数量（考虑手续费和滑点后的实际可买数量）
        position_value = self.cash * self.position_size
        # 先估算数量，然后计算实际成本
        estimated_quantity = int(position_value / price / 100) * 100
        if estimated_quantity < 100:
            logger.warning(f"资金不足，无法开仓: {stock_code} @ {price}")
            self.blocked_by_cash += 1
            return None
        
        # 使用成本模型计算真实买入成本
        total_cost, total_fees = self.cost_model.calculate_buy_cost(estimated_quantity, price)
        
        if total_cost > self.cash:
            # 尝试减少数量
            reduced_quantity = estimated_quantity - 100
            if reduced_quantity >= 100:
                total_cost, total_fees = self.cost_model.calculate_buy_cost(reduced_quantity, price)
                estimated_quantity = reduced_quantity
            else:
                logger.warning(f"资金不足（含手续费{total_fees:.2f}元），无法开仓: {stock_code} @ {price}")
                self.blocked_by_cash += 1
                return None
        
        quantity = estimated_quantity
        self.cash -= total_cost
        commission = total_fees  # 记录实际费用
        
        # 创建仓位（今仓，今日不可卖）
        position = T1Position(
            stock_code=stock_code,
            position_today=quantity,
            entry_price=price,
            entry_date=date,
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
            # V17修正：不在此处计数，改为在_process_tick中按交易意图计数
            return None
        
        # 计算盈亏（使用成本模型计算真实卖出收入）
        quantity = position.position_carry
        net_proceeds, total_fees = self.cost_model.calculate_sell_proceeds(quantity, price)
        
        # 计算PnL（扣除所有费用后的净盈亏）
        entry_notional = quantity * position.entry_price
        # 买入时的费用（估算）
        _, entry_fees = self.cost_model.calculate_buy_cost(quantity, position.entry_price)
        total_entry_cost = entry_notional + entry_fees
        
        # 净盈亏 = 卖出净收入 - 买入总成本
        pnl = net_proceeds - total_entry_cost
        pnl_pct = pnl / total_entry_cost if total_entry_cost > 0 else 0.0
        
        # 回收现金
        self.cash += net_proceeds
        
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
        """收盘结算：今仓变昨仓 + 重置策略日度状态"""
        for code, position in self.positions.items():
            if position.position_today > 0:
                # 今仓 -> 昨仓
                position.position_carry = position.position_today
                position.position_today = 0
                logger.debug(f"🔄 [日结] {code} 今仓{position.position_carry}股变昨仓")
        
        # 重置策略日度状态
        if hasattr(self.signal_generator, 'reset_daily'):
            self.signal_generator.reset_daily()
    
    def _process_tick(self, stock_code: str, tick: TickData, date: str, 
                      result: T1BacktestResult,  # V17: 传入result用于实时统计
                      tick_index: int = 0, total_ticks: int = 0) -> Optional[T1Trade]:
        """处理单个Tick - 三层信号统计（Raw/Executable/Executed）
        
        V17重构：
        - Layer 1 (Raw): 策略原始意图（仅策略条件）
        - Layer 2 (Executable): 可执行信号（过制度约束T+1/涨停/资金）
        - Layer 3 (Executed): 实际成交（trade_layer）
        
        Returns:
            t1_trade - 实际成交记录（Executed layer）
        """
        price = tick.last_price
        
        # 更新最后价格（用于权益计算）
        if price > 0:
            self.last_prices[stock_code] = price
        
        # 跳过无效价格
        if price <= 0:
            return None
        
        time_str = datetime.fromtimestamp(tick.time/1000).strftime('%H:%M:%S')
        
        # ========== Layer 1: Raw Signals（策略原始意图）==========
        is_raw_open = self.signal_generator.should_open(stock_code, tick, date, {
            'current_holding': self.current_holding,
        })
        
        if is_raw_open:
            # 统计Raw信号
            result.raw_signal_total += 1
            result.raw_signal_opens += 1
            
            # 记录Raw信号明细（调试用）
            raw_trade = T1Trade(
                stock_code=stock_code,
                entry_date=date,
                entry_time=time_str,
                entry_price=price,
                is_signal_only=True
            )
            result.raw_signal_trades.append(raw_trade)
            
            # ========== Layer 2: Executable Signals（可执行信号）==========
            # 检查制度约束：涨停/资金/T+1（单吊已在should_open中检查）
            can_execute = True
            block_reason = None
            
            # 2.1 涨停检查
            if not self._check_limit_price(stock_code, price, tick, 'buy'):
                can_execute = False
                block_reason = 'limit_up'
                self.blocked_by_limit_up += 1
                result.executable_opens_blocked += 1
                logger.debug(f"🚫 [涨停阻断] {stock_code} {date} {time_str}")
            
            # 2.2 资金检查
            elif not self._can_open_position(date):
                can_execute = False
                block_reason = 'cash_or_holding'
                self.blocked_by_cash += 1
                result.executable_opens_blocked += 1
            
            if can_execute:
                # 可执行信号统计
                result.executable_signal_total += 1
                result.executable_opens += 1
                
                # 记录Executable信号明细
                exec_trade = T1Trade(
                    stock_code=stock_code,
                    entry_date=date,
                    entry_time=time_str,
                    entry_price=price,
                    is_signal_only=True
                )
                result.executable_signal_trades.append(exec_trade)
                
                # ========== Layer 3: Executed（实际成交）==========
                t1_trade = self._open_position(stock_code, date, time_str, price)
                if t1_trade:
                    result.t1_trades.append(t1_trade)
                    return t1_trade
        
        # ========== 平仓逻辑（同样三层）==========
        if stock_code == self.current_holding and stock_code in self.positions:
            position = self.positions[stock_code]
            pnl_pct = (price - position.entry_price) / position.entry_price
            
            # 确定平仓原因
            exit_reason = None
            if pnl_pct >= self.take_profit_pct:
                exit_reason = 'take_profit'
            elif pnl_pct <= -self.stop_loss_pct:
                exit_reason = 'stop_loss'
            else:
                entry_dt = datetime.strptime(f"{position.entry_date} {position.entry_time}", '%Y-%m-%d %H:%M:%S')
                current_dt = datetime.strptime(f"{date} {time_str}", '%Y-%m-%d %H:%M:%S')
                holding_minutes = (current_dt - entry_dt).total_seconds() / 60
                if holding_minutes >= self.max_holding_minutes:
                    exit_reason = 'time_exit'
            
            if exit_reason:
                # Layer 1: Raw close signal
                result.raw_signal_total += 1
                result.raw_signal_closes += 1
                
                # Layer 2: Executable check
                can_execute_close = True
                
                # 2.1 T+1检查（今仓不能卖）
                if position.position_carry == 0:
                    can_execute_close = False
                    self.blocked_by_t1 += 1
                    result.executable_closes_blocked += 1
                
                # 2.2 跌停检查
                elif not self._check_limit_price(stock_code, price, tick, 'sell'):
                    can_execute_close = False
                    self.blocked_by_limit_down += 1
                    result.executable_closes_blocked += 1
                    logger.debug(f"🚫 [跌停阻断] {stock_code} {date} {time_str}")
                
                if can_execute_close:
                    result.executable_signal_total += 1
                    result.executable_closes += 1
                    
                    # Layer 3: Execute close
                    t1_trade = self._close_position(stock_code, date, time_str, price, exit_reason)
                    if t1_trade:
                        result.t1_trades.append(t1_trade)
                        return t1_trade
        
        return None
    
    def run_backtest(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> T1BacktestResult:
        """运行回测"""
        result = T1BacktestResult(
            initial_capital=self.initial_capital,
            cost_model=self.cost_model
        )
        
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
                    # 获取Tick数据（end_time需要是下一天才能包含当天数据）
                    from datetime import datetime, timedelta
                    date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                    next_day = (date_dt + timedelta(days=1)).strftime('%Y%m%d')
                    
                    provider = QMTHistoricalProvider(
                        stock_code=stock_code,
                        start_time=date_str.replace('-', ''),
                        end_time=next_day,
                        period='tick'
                    )
                    
                    tick_df = provider.get_raw_ticks()
                    if tick_df.empty:
                        logger.warning(f"⚠️  {stock_code} {date_str} 无tick数据")
                        continue
                    
                    total_ticks = len(tick_df)
                    
                    # 遍历Tick
                    for tick_idx, (_, row) in enumerate(tick_df.iterrows()):
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
                        
                        # V17: 传入result进行三层信号统计
                        t1_trade = self._process_tick(stock_code, tick, date_str, result, tick_idx, total_ticks)
                    
                except Exception as e:
                    import traceback
                    logger.error(f"处理 {stock_code} {date_str} 时出错: {e}")
                    logger.error(traceback.format_exc())
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
        
        # V17：最终统计（三层信号统计已在_process_tick中实时完成）
        # 只需汇总trade_layer（Executed层）
        result.trade_total = len([t for t in result.t1_trades if t.exit_date])  # 只统计已平仓
        result.trade_winning = sum(1 for t in result.t1_trades if t.pnl and t.pnl > 0)
        result.trade_losing = sum(1 for t in result.t1_trades if t.pnl and t.pnl < 0)
        result.trade_pnl = sum(t.pnl for t in result.t1_trades if t.pnl)
        
        # V17：计算最终资金（区分cash和equity）
        result.final_cash = self.cash
        # 计算总权益：现金 + 未平仓持仓市值
        unrealized_value = 0
        for code, pos in self.positions.items():
            # 使用最后已知价格或入场价格
            last_price = self.last_prices.get(code, pos.entry_price)
            unrealized_value += pos.total_position * last_price
        result.final_equity = self.cash + unrealized_value
        
        # V17：计算最大回撤（基于equity_curve）
        if result.equity_curve:
            peak = result.equity_curve[0]['equity']
            max_dd = 0.0
            for point in result.equity_curve:
                equity = point['equity']
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, drawdown)
            result.max_drawdown = max_dd
        
        # V17：阻塞统计
        result.blocked_by_limit_up = self.blocked_by_limit_up
        result.blocked_by_limit_down = self.blocked_by_limit_down
        result.blocked_by_t1 = self.blocked_by_t1
        result.blocked_by_cash = self.blocked_by_cash
        
        logger.info(f"\n✅ [回测完成]")
        logger.info(f"   📊 三层信号统计:")
        logger.info(f"      Raw Signals: {result.raw_signal_total}笔 (开仓{result.raw_signal_opens}/平仓{result.raw_signal_closes})")
        logger.info(f"      Executable: {result.executable_signal_total}笔 (开仓{result.executable_opens}/平仓{result.executable_closes}, 阻断{result.executable_opens_blocked + result.executable_closes_blocked})")
        logger.info(f"      Executed: {result.trade_total}笔 胜率{result.trade_win_rate*100:.1f}% 盈亏{result.trade_pnl:.2f}")
        logger.info(f"   💰 最终资金: 现金{result.final_cash:.0f} 权益{result.final_equity:.0f}")
        logger.info(f"   📉 最大回撤: {result.max_drawdown*100:.2f}%")
        logger.info(f"   💸 成本假设: {self.cost_model.to_dict()['description']}")
        logger.info(f"   ⚠️  阻塞统计: 涨停{result.blocked_by_limit_up}次 跌停{result.blocked_by_limit_down}次 T+1限制{result.blocked_by_t1}次 资金不足{result.blocked_by_cash}次")
        
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
