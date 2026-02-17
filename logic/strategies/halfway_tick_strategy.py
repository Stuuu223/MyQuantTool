#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Halfway策略实现
基于Tick数据的半路策略
"""

import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from logic.strategies.tick_strategy_interface import ITickStrategy, TickData, Signal, StrategyContext


class HalfwayTickStrategy(ITickStrategy):
    """
    Halfway Tick策略实现
    基于低波动平台后突然放量突破的模式
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
        self.volatility_threshold = params.get('volatility_threshold', 0.03)
        self.volume_surge = params.get('volume_surge', 1.5)
        self.breakout_strength = params.get('breakout_strength', 0.01)
        self.window_minutes = params.get('window_minutes', 30)
        self.history_limit = params.get('history_limit', 500)
        self.min_history_points = params.get('min_history_points', 60)  # 最小历史点数
        
        # 策略状态
        self.current_price = None
        self.current_time = None
        self.price_history = []  # [(time, price), ...]
        self.volume_history = []  # [(time, volume), ...]
        self.signals = []
        
        # 用于计算的中间变量
        self.last_volume = 0
        self.last_price = 0
        self.platform_high = 0  # 平台期间的最高价
        self.platform_recognized = False  # 是否已识别平台
        
    def on_tick(self, tick: TickData) -> List[Signal]:
        """
        处理单个Tick数据
        
        Args:
            tick: Tick数据
            
        Returns:
            List[Signal]: 产生的信号列表
        """
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
        
        # 更新平台期间的最高价
        # 只有在已识别平台或当前处于低波动状态时才更新平台高点
        if self.platform_recognized or self._is_low_volatility_state():
            if self.current_price > self.platform_high:
                self.platform_high = self.current_price
        
        # 检查是否满足半路条件
        signals = []
        if self._is_halfway_condition():
            signal = Signal(
                time=self.current_time,
                price=self.current_price,
                signal_type='HALFWAY',
                params=self.params.copy(),
                strength=1.0,
                extra_info={
                    'current_volatility': self._calculate_volatility(),
                    'current_volume_surge': self._calculate_volume_surge(),
                    'breakout_strength': self._calculate_breakout_strength(),
                    'platform_high': self.platform_high
                }
            )
            signals.append(signal)
            self.signals.append(signal)
        
        # 更新最后的价格和成交量
        self.last_price = self.current_price
        self.last_volume = tick.volume
        
        return signals
    
    def _is_low_volatility_state(self) -> bool:
        """
        检查是否处于低波动状态（用于识别平台）
        
        Returns:
            bool: 是否处于低波动状态
        """
        # 检查历史数据点数是否足够
        if len(self.price_history) < self.min_history_points:
            return False
        
        # 计算当前波动率
        current_volatility = self._calculate_volatility()
        
        # 检查波动率是否低于阈值
        return current_volatility <= self.volatility_threshold
    
    def _is_halfway_condition(self) -> bool:
        """
        检查是否满足半路条件
        
        Returns:
            bool: 是否满足半路条件
        """
        # 检查历史数据点数是否足够
        if len(self.price_history) < self.min_history_points:
            return False
        
        # 1. 必须已识别平台（或当前处于低波动状态）
        if not self.platform_recognized:
            if self._is_low_volatility_state():
                # 识别到平台，记录平台高点
                self.platform_recognized = True
                # 取最近一段时间的最高价作为平台高点
                recent_prices = [p[1] for p in self.price_history[-60:] if p[0] >= self.current_time - 30 * 60 * 1000]
                if recent_prices:
                    self.platform_high = max(recent_prices)
            else:
                # 还未识别到平台，不触发信号
                return False
        
        # 2. 平台波动率仍低于阈值（确认仍在平台状态）
        current_volatility = self._calculate_volatility()
        if current_volatility > self.volatility_threshold:
            # 如果波动率上升，可能平台已破坏，重置平台识别
            self.platform_recognized = False
            self.platform_high = 0
            return False
        
        # 3. 量能放大倍数超过阈值
        current_volume_surge = self._calculate_volume_surge()
        if current_volume_surge < self.volume_surge:
            return False
        
        # 4. 价格突破平台高点（相对于已识别的平台高点）
        current_breakout_strength = self._calculate_breakout_strength_from_platform()
        if current_breakout_strength < self.breakout_strength:
            return False
        
        return True
    
    def _calculate_volatility(self, window_minutes: int = None) -> float:
        """
        计算平台波动率
        
        Args:
            window_minutes: 计算窗口（分钟），如果为None则使用默认值
            
        Returns:
            float: 波动率
        """
        if window_minutes is None:
            window_minutes = self.window_minutes
        
        if len(self.price_history) < 2:
            return 0.0
        
        # 找到最近window_minutes的数据点
        target_time = self.current_time - window_minutes * 60 * 1000  # 转换为毫秒
        
        recent_prices = []
        for i in range(len(self.price_history)-1, -1, -1):
            if self.price_history[i][0] >= target_time:
                recent_prices.append(self.price_history[i][1])  # price
            else:
                break
        
        if len(recent_prices) < 2:
            return 0.0
        
        # 计算波动率（使用价格变化率的标准差）
        returns = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i-1] != 0:
                ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                returns.append(ret)
        
        volatility = np.std(returns) if len(returns) > 0 else 0.0
        return volatility
    
    def _calculate_volume_surge(self, window_minutes: int = 5) -> float:
        """
        计算量能放大倍数
        
        Args:
            window_minutes: 基准窗口（分钟）
            
        Returns:
            float: 量能放大倍数
        """
        if len(self.volume_history) < 2:
            return 0.0
        
        # 计算当前成交量变化
        current_volume = self.volume_history[-1][1] - self.volume_history[-2][1]
        if current_volume <= 0:
            return 0.0
        
        # 计算基准成交量（过去一段时间的平均值）
        target_time = self.current_time - window_minutes * 60 * 1000  # 转换为毫秒
        
        recent_volumes = []
        # 使用滑动窗口计算基准成交量，避免单笔大单影响
        volume_window_size = min(20, len(self.volume_history)-1)  # 最多取20个点
        for i in range(len(self.volume_history)-2, max(-1, len(self.volume_history)-volume_window_size-2), -1):
            if i >= 0:
                vol_change = self.volume_history[i][1] - (self.volume_history[i-1][1] if i > 0 else 0)
                if vol_change > 0:
                    recent_volumes.append(vol_change)
        
        if len(recent_volumes) == 0:
            return 0.0
        
        avg_volume = np.mean(recent_volumes)
        
        if avg_volume <= 0:
            return 0.0
        
        return current_volume / avg_volume

    def _calculate_breakout_strength_from_platform(self) -> float:
        """
        计算相对于已识别平台高点的突破强度
        
        Returns:
            float: 突破强度
        """
        if self.platform_high <= 0 or self.current_price <= 0:
            return 0.0
        
        # 计算相对于平台高点的突破强度
        strength = (self.current_price - self.platform_high) / self.platform_high
        return strength
    
    def _calculate_breakout_strength(self) -> float:
        """
        计算突破强度
        
        Returns:
            float: 突破强度
        """
        if len(self.price_history) < 10:
            return 0.0
        
        # 计算近期最高价
        window_size = min(30, len(self.price_history))
        recent_prices = [p[1] for p in self.price_history[-window_size:]]
        recent_high = max(recent_prices) if recent_prices else 0
        
        if recent_high <= 0 or self.current_price <= 0:
            return 0.0
        
        # 计算相对于近期高点的突破强度
        strength = (self.current_price - recent_high) / recent_high
        return strength
    
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return "Halfway_Tick_Strategy"
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前策略状态"""
        return {
            'current_price': self.current_price,
            'current_volatility': self._calculate_volatility(),
            'current_volume_surge': self._calculate_volume_surge(),
            'current_breakout_strength': self._calculate_breakout_strength(),
            'price_history_length': len(self.price_history),
            'total_signals': len(self.signals)
        }


if __name__ == "__main__":
    print("✅ Halfway策略实现完成")