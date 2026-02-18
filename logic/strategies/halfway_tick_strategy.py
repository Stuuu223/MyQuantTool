#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Halfway策略实现
基于Tick数据的半路策略
现在使用halfway_core作为统一的Halfway战法定义
"""

from typing import List, Dict, Any
from datetime import datetime
from logic.strategies.tick_strategy_interface import ITickStrategy, TickData, Signal, StrategyContext
from logic.strategies.halfway_core import evaluate_halfway_state, create_halfway_platform_detector


class HalfwayTickStrategy(ITickStrategy):
    """
    Halfway Tick策略实现
    基于低波动平台后突然放量突破的模式
    使用halfway_core作为统一的Halfway战法定义
    """
    
    def __init__(self, params: Dict[str, Any]):
        """
        初始化策略
        
        Args:
            params: 策略参数
                - volatility_threshold: 波动率阈值 (默认0.03)
                - volume_surge: 量能放大倍数阈值 (默认1.5) 
                - breakout_strength: 突破强度阈值 (默认0.01)
                - window_minutes: 平台期计算窗口(分钟) (默认30)
                - history_limit: 历史数据最大数量 (默认500)
                - min_history_points: 计算波动率最小历史点数 (默认60)
        """
        self.params = params
        self.history_limit = params.get('history_limit', 500)
        
        # 策略状态
        self.current_price = None
        self.current_time = None
        self.price_history = []  # [(time, price), ...]
        self.volume_history = []  # [(time, volume), ...]
        self.signals = []
        
        # 使用halfway_core创建平台检测器
        self.platform_detector = create_halfway_platform_detector(params)
        
        # V17 Debug: 添加计数器用于诊断策略活性
        self.debug_counters = {
            'ticks_seen': 0,           # 看到的tick总数
            'volatility_pass': 0,      # 通过波动率阈值
            'volume_surge_pass': 0,    # 通过量能阈值
            'breakout_pass': 0,        # 通过突破阈值
            'all_conditions_pass': 0,  # 同时通过三个条件
            'raw_signals_generated': 0, # 最终生成的信号数
            'history_insufficient': 0,  # 历史数据不足次数
        }
        
    def on_tick(self, tick: TickData) -> List[Signal]:
        """
        处理单个Tick数据
        
        Args:
            tick: Tick数据
            
        Returns:
            List[Signal]: 产生的信号列表
        """
        # V17 Debug: 记录tick总数
        self.debug_counters['ticks_seen'] += 1
        
        # 更新当前状态
        self.current_time = tick.time
        self.current_price = tick.last_price
        
        # 记录历史数据
        self.price_history.append((self.current_time, self.current_price))
        self.volume_history.append((self.current_time, tick.volume))
        
        # 限制历史记录长度
        if len(self.price_history) > self.history_limit:
            self.price_history = self.price_history[-self.history_limit:]
        if len(self.volume_history) > self.history_limit:
            self.volume_history = self.volume_history[-self.history_limit:]
        
        # 使用halfway_core进行信号检测
        result = self.platform_detector(
            self.price_history,
            self.volume_history,
            self.current_time,
            self.current_price
        )
        
        # V17 Debug: 记录各条件通过情况
        factors = result.get('factors', {})
        conditions = result.get('conditions', {})
        
        # 检查历史数据是否足够
        if len(self.price_history) < self.params.get('min_history_points', 5):
            self.debug_counters['history_insufficient'] += 1
            return []
        
        # 记录各条件通过情况
        volatility_val = factors.get('volatility', 999)
        volume_surge_val = factors.get('volume_surge', 0)
        breakout_val = factors.get('breakout_strength', 0)
        
        volatility_threshold = self.params.get('volatility_threshold', 0.03)
        volume_surge_threshold = self.params.get('volume_surge', 1.5)
        breakout_threshold = self.params.get('breakout_strength', 0.01)
        
        volatility_ok = volatility_val <= volatility_threshold
        volume_surge_ok = volume_surge_val >= volume_surge_threshold
        breakout_ok = breakout_val >= breakout_threshold
        
        # V17 Debug: 采样记录前10个非零突破值
        if breakout_val != 0 and self.debug_counters['breakout_pass'] < 10:
            print(f"[Debug] breakout_val={breakout_val:.4f}, threshold={breakout_threshold}, current={self.current_price}, platform_high={result.get('platform_state', {}).get('platform_high', 'N/A')}")
        
        if volatility_ok:
            self.debug_counters['volatility_pass'] += 1
        if volume_surge_ok:
            self.debug_counters['volume_surge_pass'] += 1
        if breakout_ok:
            self.debug_counters['breakout_pass'] += 1
        if volatility_ok and volume_surge_ok and breakout_ok:
            self.debug_counters['all_conditions_pass'] += 1
        
        # 检查是否满足半路条件
        signals = []
        if result['is_signal']:
            # V17 Debug: 记录信号生成
            self.debug_counters['raw_signals_generated'] += 1
            
            signal = Signal(
                time=self.current_time,
                price=self.current_price,
                signal_type='HALFWAY',
                params=self.params.copy(),
                strength=1.0,
                extra_info={
                    'factors': result['factors'],
                    'conditions': result['conditions'],
                    'platform_state': result['platform_state'],
                    'current_volatility': result['factors']['volatility'],
                    'current_volume_surge': result['factors']['volume_surge'],
                    'breakout_strength': result['factors']['breakout_strength'],
                    'platform_high': result['platform_state']['platform_high']
                }
            )
            signals.append(signal)
            self.signals.append(signal)
        
        return signals
    
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return "Halfway_Tick_Strategy"
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前策略状态"""
        # 使用halfway_core计算当前状态
        if len(self.price_history) > 0 and len(self.volume_history) > 0:
            result = evaluate_halfway_state(
                self.price_history,
                self.volume_history,
                self.current_time or self.price_history[-1][0],
                self.current_price or self.price_history[-1][1],
                self.params
            )
            
            return {
                'current_price': self.current_price,
                'current_volatility': result['factors']['volatility'],
                'current_volume_surge': result['factors']['volume_surge'],
                'current_breakout_strength': result['factors']['breakout_strength'],
                'price_history_length': len(self.price_history),
                'total_signals': len(self.signals),
                'platform_state': result.get('platform_state', {}),
                'debug_counters': self.debug_counters  # V17 Debug: 包含计数器
            }
        else:
            return {
                'current_price': self.current_price,
                'current_volatility': 0.0,
                'current_volume_surge': 0.0,
                'current_breakout_strength': 0.0,
                'price_history_length': 0,
                'total_signals': len(self.signals),
                'platform_state': {},
                'debug_counters': self.debug_counters  # V17 Debug: 包含计数器
            }


if __name__ == "__main__":
    print("✅ Halfway策略实现完成（基于halfway_core）")