#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一战法Tick回测适配器 (Unified Warfare Tick Backtest Adapter)

根据CTO指导意见，将统一战法核心集成到Tick回测系统中。
该适配器将UnifiedWarfareCore适配到backtestengine接口。

核心功能：
1. 将UnifiedWarfareCore适配到backtestengine接口
2. 实现多战法统一回测
3. 与现有Tick回测系统兼容

设计原则：
1. 保持与现有backtestengine兼容
2. 使用统一的战法检测接口
3. 遵循V12.1.0规范

验收标准：
- 能够将UnifiedWarfareCore适配到backtestengine
- 与现有Tick回测系统兼容
- 支持多战法统一回测
- 代码符合项目规范

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-17
"""

from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from logic.strategies.unified_warfare_core import get_unified_warfare_core
from logic.strategies.event_driven_warfare_adapter import get_event_driven_adapter
from logic.strategies.event_detector import EventType
from logic.strategies.tick_strategy_interface import ITickStrategy, TickData, Signal, StrategyContext
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class UnifiedWarfareBacktestAdapter(ITickStrategy):
    """
    统一战法回测适配器
    
    功能：
    1. 将UnifiedWarfareCore适配为ITickStrategy接口
    2. 在回测中提供多战法统一检测
    3. 生成标准化的Signal对象
    """

    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化统一战法回测适配器
        
        Args:
            params: 参数配置
        """
        self.params = params or {}
        
        # 获取统一战法核心
        self.warfare_core = get_unified_warfare_core()
        
        # 获取EventDriven适配器
        self.event_adapter = get_event_driven_adapter()
        
        # 内部状态
        self._price_history = {}
        self._volume_history = {}
        self._context_cache = {}  # 缓存上下文信息
        
        # 战法权重配置
        self.warfare_weights = self.params.get('warfare_weights', {
            'opening_weak_to_strong': 1.0,
            'halfway_breakout': 1.0,
            'leader_candidate': 1.0,
            'dip_buy_candidate': 1.0,
        })
        
        logger.info("✅ [统一战法回测适配器] 初始化完成")
        logger.info(f"   - 支持战法: {len(self.warfare_core.get_active_detectors())} 种")
        logger.info(f"   - 战法权重: {self.warfare_weights}")
    
    def on_tick(self, tick: TickData) -> List[Signal]:
        """
        处理单个Tick数据
        
        Args:
            tick: Tick数据
            
        Returns:
            信号列表
        """
        try:
            # 构建tick数据字典（适配UnifiedWarfareCore）
            tick_data_dict = self._convert_tick_to_dict(tick)
            
            # 构建上下文信息
            context = self._build_context(tick)
            
            # 使用UnifiedWarfareCore处理tick
            detected_events = self.warfare_core.process_tick(tick_data_dict, context)
            
            # 将检测到的事件转换为Signal对象
            signals = []
            for event in detected_events:
                signal = self._convert_event_to_signal(event, tick)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ [统一战法适配器] 处理Tick失败: {e}")
            return []
    
    def _convert_tick_to_dict(self, tick: TickData) -> Dict[str, Any]:
        """
        将TickData对象转换为字典格式
        
        Args:
            tick: TickData对象
            
        Returns:
            字典格式的tick数据
        """
        # 转换时间戳
        if isinstance(tick.time, (int, float)):
            dt = datetime.fromtimestamp(tick.time / 1000)  # 假设毫秒时间戳
        else:
            dt = datetime.now()
        
        return {
            'stock_code': getattr(tick, 'stock_code', 'UNKNOWN'),
            'datetime': dt,
            'price': tick.last_price,
            'volume': tick.volume,
            'amount': tick.amount,
            'ask_price': tick.ask_price,
            'bid_price': tick.bid_price,
            'ask_vol': tick.ask_vol,
            'bid_vol': tick.bid_vol,
            'prev_close': getattr(tick, 'prev_close', 0),  # 可能不存在
        }
    
    def _build_context(self, tick: TickData) -> Dict[str, Any]:
        """
        构建上下文信息
        
        Args:
            tick: Tick数据
            
        Returns:
            上下文信息
        """
        stock_code = getattr(tick, 'stock_code', 'UNKNOWN')
        
        # 获取或初始化价格历史
        if stock_code not in self._price_history:
            self._price_history[stock_code] = []
        if stock_code not in self._volume_history:
            self._volume_history[stock_code] = []
        
        # 添加当前价格和成交量到历史
        self._price_history[stock_code].append(tick.last_price)
        self._volume_history[stock_code].append(tick.volume)
        
        # 限制历史长度以节省内存
        max_history = self.params.get('max_history_length', 100)
        if len(self._price_history[stock_code]) > max_history:
            self._price_history[stock_code] = self._price_history[stock_code][-max_history:]
        if len(self._volume_history[stock_code]) > max_history:
            self._volume_history[stock_code] = self._volume_history[stock_code][-max_history:]
        
        # 计算技术指标（简化版）
        prices = self._price_history[stock_code]
        volumes = self._volume_history[stock_code]
        
        # 移动平均
        ma5 = np.mean(prices[-5:]) if len(prices) >= 5 else prices[0] if prices else tick.last_price
        ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else prices[0] if prices else tick.last_price
        
        # RSI (简化计算)
        rsi = 50  # 简化，默认值
        if len(prices) >= 14:
            gains = []
            losses = []
            for i in range(1, 14):
                change = prices[-i] - prices[-i-1]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0.001  # 避免除零
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
        
        # 平均成交量
        avg_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[0] if volumes else tick.volume
        
        return {
            'price_history': prices,
            'volume_history': volumes,
            'ma5': ma5,
            'ma20': ma20,
            'rsi': rsi,
            'avg_volume_5d': avg_volume,
            'auction_volume_ratio': 1.0,  # 竞价量比（简化）
            'sector_data': {},  # 板块数据（简化）
        }
    
    def _convert_event_to_signal(self, event: Dict[str, Any], tick: TickData) -> Optional[Signal]:
        """
        将检测到的事件转换为Signal对象
        
        Args:
            event: 检测到的事件
            tick: Tick数据
            
        Returns:
            Signal对象
        """
        try:
            event_type = event['event_type']
            confidence = event['confidence']
            
            # 根据事件类型确定信号类型和强度
            if event_type == 'opening_weak_to_strong':
                signal_type = 'OPENING_WEAK_TO_STRONG'
                strength = confidence * self.warfare_weights.get('opening_weak_to_strong', 1.0)
                action = 'BUY'  # 竞价弱转强通常为买入信号
            elif event_type == 'halfway_breakout':
                signal_type = 'HALFWAY_BREAKOUT'
                strength = confidence * self.warfare_weights.get('halfway_breakout', 1.0)
                action = 'BUY'  # 半路突破通常为买入信号
            elif event_type == 'leader_candidate':
                signal_type = 'LEADER_CANDIDATE'
                strength = confidence * self.warfare_weights.get('leader_candidate', 1.0)
                action = 'BUY'  # 龙头候选通常为买入信号
            elif event_type == 'dip_buy_candidate':
                signal_type = 'DIP_BUY_CANDIDATE'
                strength = confidence * self.warfare_weights.get('dip_buy_candidate', 1.0)
                action = 'BUY'  # 低吸候选通常为买入信号
            else:
                # 未知事件类型，返回None
                return None
            
            # 创建Signal对象
            signal = Signal(
                time=tick.time,
                price=tick.last_price,
                signal_type=signal_type,
                params=event.get('data', {}),
                strength=strength,
                extra_info=event
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ [统一战法适配器] 转换事件为信号失败: {e}")
            return None
    
    def get_strategy_name(self) -> str:
        """
        获取策略名称
        
        Returns:
            str: 策略名称
        """
        return "UnifiedWarfareStrategy"
    
    def get_strategy_params(self) -> Dict[str, Any]:
        """
        获取策略参数
        
        Returns:
            策略参数字典
        """
        return self.params
    
    def reset(self):
        """
        重置策略状态
        """
        self._price_history = {}
        self._volume_history = {}
        self._context_cache = {}
        logger.info("🔄 [统一战法适配器] 状态已重置")


class UnifiedWarfareBacktestEngine:
    """
    统一战法回测引擎
    
    功能：
    1. 使用统一战法适配器运行回测
    2. 管理多战法回测流程
    3. 生成统一的回测报告
    """
    
    def __init__(self, initial_capital: float = 100000.0, params: Dict[str, Any] = None):
        """
        初始化统一战法回测引擎
        
        Args:
            initial_capital: 初始资金
            params: 参数配置
        """
        self.initial_capital = initial_capital
        self.params = params or {}
        
        # 创建统一战法适配器
        self.strategy_adapter = UnifiedWarfareBacktestAdapter(self.params)
        
        # 回测状态
        self.current_capital = initial_capital
        self.positions = {}  # 持仓
        self.trades = []  # 交易记录
        self.signals = []  # 信号记录
        self.equity_curve = []  # 净值曲线
        
        logger.info("✅ [统一战法回测引擎] 初始化完成")
        logger.info(f"   - 初始资金: {initial_capital:,.2f}")
        logger.info(f"   - 使用策略: {self.strategy_adapter.get_strategy_name()}")
    
    def run_backtest(self, tick_data_feed: List[TickData]) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            tick_data_feed: Tick数据流
            
        Returns:
            回测结果
        """
        logger.info(f"🚀 [统一战法回测] 开始，数据点数: {len(tick_data_feed)}")
        
        for i, tick in enumerate(tick_data_feed):
            # 处理单个Tick
            signals = self.strategy_adapter.on_tick(tick)
            
            # 处理生成的信号
            for signal in signals:
                self._process_signal(signal, tick)
            
            # 每1000个tick记录一次进度
            if (i + 1) % 1000 == 0:
                logger.info(f"📊 [回测进度] {i + 1}/{len(tick_data_feed)} ({(i + 1) / len(tick_data_feed) * 100:.1f}%)")
        
        # 生成回测报告
        results = self._generate_report()
        
        logger.info("✅ [统一战法回测] 完成")
        return results
    
    def _process_signal(self, signal: Signal, tick: TickData):
        """
        处理生成的信号
        
        Args:
            signal: 信号
            tick: Tick数据
        """
        self.signals.append({
            'time': tick.time,
            'stock_code': getattr(tick, 'stock_code', 'UNKNOWN'),
            'signal_type': signal.signal_type,
            'strength': signal.strength,
            'price': signal.price,
            'extra_info': signal.extra_info
        })
        
        # 这里可以添加交易执行逻辑
        # 例如：根据信号类型执行买卖操作
        logger.debug(f"🎯 [回测信号] {signal.signal_type} - 强度: {signal.strength:.3f}, 价格: {signal.price:.2f}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """
        生成回测报告
        
        Returns:
            回测结果报告
        """
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        
        report = {
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_return': total_return,
            'total_signals': len(self.signals),
            'total_trades': len(self.trades),
            'warfare_stats': self.strategy_adapter.warfare_core.get_warfare_stats(),
            'signal_distribution': self._analyze_signal_distribution(),
            'execution_summary': {
                'signals_by_type': self._count_signals_by_type()
            }
        }
        
        return report
    
    def _analyze_signal_distribution(self) -> Dict[str, int]:
        """
        分析信号分布
        
        Returns:
            信号类型分布
        """
        distribution = {}
        for signal in self.signals:
            signal_type = signal['signal_type']
            distribution[signal_type] = distribution.get(signal_type, 0) + 1
        return distribution
    
    def _count_signals_by_type(self) -> Dict[str, Any]:
        """
        按类型统计信号
        
        Returns:
            按类型统计的结果
        """
        by_type = {}
        for signal in self.signals:
            signal_type = signal['signal_type']
            if signal_type not in by_type:
                by_type[signal_type] = {
                    'count': 0,
                    'avg_strength': 0,
                    'total_strength': 0
                }
            
            by_type[signal_type]['count'] += 1
            by_type[signal_type]['total_strength'] += signal['strength']
        
        # 计算平均强度
        for signal_type, stats in by_type.items():
            if stats['count'] > 0:
                stats['avg_strength'] = stats['total_strength'] / stats['count']
        
        return by_type


def create_unified_warfare_backtest_strategy(params: Dict[str, Any] = None) -> ITickStrategy:
    """
    创建统一战法回测策略
    
    Args:
        params: 策略参数
        
    Returns:
        ITickStrategy: 策略实例
    """
    return UnifiedWarfareBacktestAdapter(params)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试UnifiedWarfareBacktestAdapter
    print("=" * 80)
    print("统一战法Tick回测适配器测试")
    print("=" * 80)
    
    # 创建适配器
    params = {
        'warfare_weights': {
            'opening_weak_to_strong': 1.0,
            'halfway_breakout': 1.0,
            'leader_candidate': 1.0,
            'dip_buy_candidate': 1.0,
        },
        'max_history_length': 50
    }
    
    adapter = UnifiedWarfareBacktestAdapter(params)
    
    # 模拟tick数据
    from logic.strategies.tick_strategy_interface import TickData
    import time
    
    # 创建一些模拟tick数据
    mock_ticks = []
    base_time = int(time.time() * 1000) - 1000000  # 1000秒前
    base_price = 100.0
    
    for i in range(100):
        tick = TickData(
            time=base_time + i * 1000,  # 每秒一个tick
            last_price=base_price + (i % 20) * 0.1,  # 简单的价格波动
            volume=1000 * (i + 1),
            amount=base_price * 1000 * (i + 1),
            bid_price=base_price + (i % 20) * 0.1 - 0.01,
            ask_price=base_price + (i % 20) * 0.1 + 0.01,
            bid_vol=500,
            ask_vol=500
        )
        tick.stock_code = "000001.SZ"  # 添加股票代码
        mock_ticks.append(tick)
    
    print(f"\n模拟Tick数据: {len(mock_ticks)} 个")
    print(f"时间范围: {datetime.fromtimestamp(mock_ticks[0].time/1000)} -> {datetime.fromtimestamp(mock_ticks[-1].time/1000)}")
    
    # 测试信号生成
    signals = []
    for i, tick in enumerate(mock_ticks):
        tick_signals = adapter.on_tick(tick)
        if tick_signals:
            signals.extend(tick_signals)
            print(f"📈 Tick {i+1}: 生成 {len(tick_signals)} 个信号")
            for signal in tick_signals:
                print(f"     - {signal.signal_type}: 强度 {signal.strength:.3f}, 价格 {signal.price:.2f}")
    
    print(f"\n总计生成信号: {len(signals)} 个")
    
    # 测试回测引擎
    print(f"\n测试回测引擎...")
    engine = UnifiedWarfareBacktestEngine(initial_capital=100000, params=params)
    results = engine.run_backtest(mock_ticks[:10])  # 只用前10个进行快速测试
    
    print(f"\n回测结果:")
    for key, value in results.items():
        if key != 'warfare_stats' and key != 'execution_summary':
            print(f"  {key}: {value}")
    
    print(f"\n战法统计:")
    warfare_stats = results.get('warfare_stats', {})
    for key, value in warfare_stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n信号统计:")
    signal_stats = results.get('execution_summary', {}).get('signals_by_type', {})
    for signal_type, stats in signal_stats.items():
        print(f"  {signal_type}: {stats}")
    
    print("\n✅ 测试完成")
    print("=" * 80)
