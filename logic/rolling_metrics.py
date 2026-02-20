#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滚动指标计算模块 (Rolling Metrics Module)
CTO指令：封装多周期资金切片逻辑，供CapitalService和策略层统一调用

核心功能：
1. 多周期滚动资金流计算（1min/5min/15min/30min）
2. 波段涨幅计算（基于pre_close）
3. 资金持续性评估
4. 脉冲流与承接流分离

系统哲学：资金为王，看资金的"持续性"与"爆发力"
"""

from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import numpy as np


@dataclass
class FlowSlice:
    """资金切片数据类"""
    window_minutes: int
    total_flow: float          # 总净流入（元）
    total_volume: int          # 总成交量（股）
    avg_price: float           # 均价
    price_change_pct: float    # 价格变化率（%）
    tick_count: int            # tick数量
    
    @property
    def flow_direction(self) -> str:
        """资金流向判断"""
        return "INFLOW" if self.total_flow > 0 else "OUTFLOW"
    
    @property
    def flow_intensity(self) -> float:
        """资金强度（单位：百万）"""
        return self.total_flow / 1e6


@dataclass
class RollingFlowMetrics:
    """滚动资金流指标集合"""
    timestamp: int             # 当前时间戳
    current_price: float       # 当前价格
    pre_close: float           # 昨收价
    
    # 多周期资金切片
    instant_flow: float        # 瞬时流（最新tick）
    flow_1min: FlowSlice       # 1分钟脉冲流
    flow_5min: FlowSlice       # 5分钟波段流
    flow_15min: FlowSlice      # 15分钟阶段流
    flow_30min: FlowSlice      # 30分钟趋势流
    
    # 综合评估
    confidence: float          # 综合置信度
    
    @property
    def true_change_pct(self) -> float:
        """真实涨幅（相对昨收）"""
        if self.pre_close > 0:
            return (self.current_price - self.pre_close) / self.pre_close * 100
        return 0.0
    
    @property
    def band_gain_pct(self, daily_low: float = 0) -> float:
        """
        波段涨幅（从日内低点起算）
        作为辅助指标，反映资金承接力度
        """
        if daily_low > 0:
            return (self.current_price - daily_low) / daily_low * 100
        return self.true_change_pct
    
    @property
    def flow_sustainability(self) -> float:
        """
        资金持续性指标
        计算15分钟流与5分钟流的比率，>1.2表示资金在持续流入
        """
        if abs(self.flow_5min.total_flow) > 0:
            return self.flow_15min.total_flow / self.flow_5min.total_flow
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'timestamp': self.timestamp,
            'current_price': self.current_price,
            'pre_close': self.pre_close,
            'true_change_pct': self.true_change_pct,
            'instant_flow': self.instant_flow,
            'flow_1min_total': self.flow_1min.total_flow,
            'flow_1min_intensity': self.flow_1min.flow_intensity,
            'flow_5min_total': self.flow_5min.total_flow,
            'flow_5min_intensity': self.flow_5min.flow_intensity,
            'flow_15min_total': self.flow_15min.total_flow,
            'flow_15min_intensity': self.flow_15min.flow_intensity,
            'flow_30min_total': self.flow_30min.total_flow,
            'flow_sustainability': self.flow_sustainability,
            'confidence': self.confidence
        }


class RollingFlowCalculator:
    """
    滚动资金流计算器
    CTO指令：替代愚蠢的单笔Tick计算，实现多周期切片
    """
    
    def __init__(self, windows: List[int] = [1, 5, 15, 30], max_buffer_size: int = 10000):
        """
        初始化
        
        Args:
            windows: 时间窗口列表（分钟），默认[1, 5, 15, 30]
            max_buffer_size: tick缓冲区最大大小
        """
        self.windows = windows
        self.tick_buffer = deque(maxlen=max_buffer_size)
        self.pre_close = 0.0       # 昨收价
        self.daily_low = float('inf')  # 日内低点
        self.daily_high = 0.0      # 日内高点
        
    def set_pre_close(self, pre_close: float):
        """设置昨收价（必须在开始计算前调用）"""
        self.pre_close = pre_close
        
    def add_tick(self, tick_data: Dict[str, Any], last_tick_data: Optional[Dict] = None) -> RollingFlowMetrics:
        """
        添加tick数据并计算滚动指标
        
        Args:
            tick_data: 当前tick数据
            last_tick_data: 上一个tick数据（用于计算增量）
            
        Returns:
            RollingFlowMetrics: 滚动指标集合
        """
        timestamp = int(tick_data.get('time', 0))
        price = tick_data.get('lastPrice', 0)
        volume = tick_data.get('volume', 0)
        
        # 更新日内高低点
        self.daily_high = max(self.daily_high, price)
        self.daily_low = min(self.daily_low, price)
        
        # 计算成交量和资金增量
        if last_tick_data:
            volume_delta = volume - last_tick_data.get('volume', 0)
            price_change = price - last_tick_data.get('lastPrice', price)
        else:
            volume_delta = 0
            price_change = 0
        
        # 估算单笔tick资金流（简化版：价格上涨=流入，下跌=流出）
        # 注意单位：volume_delta是"股"(从Tick数据直接获取)，price是"元/股"
        # 正确计算：volume_delta(股) * price(元/股) = 金额(元)
        if volume_delta > 0:
            if price_change > 0:
                estimated_flow = volume_delta * price  # 主买流入（元）
            elif price_change < 0:
                estimated_flow = -volume_delta * price  # 主卖流出（元）
            else:
                estimated_flow = 0
        else:
            estimated_flow = 0
        
        # 存储到buffer
        tick_record = {
            'timestamp': timestamp,
            'price': price,
            'volume_delta': volume_delta,
            'estimated_flow': estimated_flow
        }
        self.tick_buffer.append(tick_record)
        
        # 计算各周期切片
        flow_slices = self._calculate_flow_slices(timestamp)
        
        # 计算综合置信度
        confidence = self._calculate_confidence(flow_slices, price)
        
        return RollingFlowMetrics(
            timestamp=timestamp,
            current_price=price,
            pre_close=self.pre_close,
            instant_flow=estimated_flow,
            flow_1min=flow_slices.get(1, FlowSlice(1, 0, 0, price, 0, 0)),
            flow_5min=flow_slices.get(5, FlowSlice(5, 0, 0, price, 0, 0)),
            flow_15min=flow_slices.get(15, FlowSlice(15, 0, 0, price, 0, 0)),
            flow_30min=flow_slices.get(30, FlowSlice(30, 0, 0, price, 0, 0)),
            confidence=confidence
        )
    
    def _calculate_flow_slices(self, current_timestamp: int) -> Dict[int, FlowSlice]:
        """
        计算各时间窗口的资金切片
        
        Args:
            current_timestamp: 当前时间戳（毫秒）
            
        Returns:
            Dict[int, FlowSlice]: 窗口分钟数 -> 切片数据
        """
        results = {}
        
        for window_minutes in self.windows:
            window_ms = window_minutes * 60 * 1000
            cutoff_time = current_timestamp - window_ms
            
            # 取窗口内tick
            window_ticks = [t for t in self.tick_buffer if t['timestamp'] >= cutoff_time]
            
            if window_ticks:
                total_flow = sum([t['estimated_flow'] for t in window_ticks])
                total_volume = sum([t['volume_delta'] for t in window_ticks])
                avg_price = sum([t['price'] for t in window_ticks]) / len(window_ticks)
                price_change_pct = ((window_ticks[-1]['price'] - window_ticks[0]['price']) 
                                   / window_ticks[0]['price'] * 100) if window_ticks[0]['price'] > 0 else 0
                tick_count = len(window_ticks)
            else:
                total_flow = 0
                total_volume = 0
                avg_price = 0
                price_change_pct = 0
                tick_count = 0
            
            results[window_minutes] = FlowSlice(
                window_minutes=window_minutes,
                total_flow=total_flow,
                total_volume=total_volume,
                avg_price=avg_price,
                price_change_pct=price_change_pct,
                tick_count=tick_count
            )
        
        return results
    
    def _calculate_confidence(self, flow_slices: Dict[int, FlowSlice], current_price: float) -> float:
        """
        计算综合置信度
        基于：资金强度 + 资金持续性 + 价格位置
        """
        # 获取关键切片
        flow_5min = flow_slices.get(5, FlowSlice(5, 0, 0, current_price, 0, 0))
        flow_15min = flow_slices.get(15, FlowSlice(15, 0, 0, current_price, 0, 0))
        
        # 资金强度得分（5分钟流 > 3000万得高分）
        intensity_score = min(1.0, abs(flow_5min.flow_intensity) / 30.0)
        
        # 资金持续性得分（15分钟流/5分钟流 > 1.2表示持续）
        sustainability_ratio = (flow_15min.total_flow / flow_5min.total_flow 
                               if abs(flow_5min.total_flow) > 0 else 0)
        sustainability_score = min(1.0, max(0, sustainability_ratio - 0.5) / 1.5)
        
        # 综合置信度
        confidence = intensity_score * 0.6 + sustainability_score * 0.4
        
        return min(1.0, max(0.0, confidence))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'buffer_size': len(self.tick_buffer),
            'pre_close': self.pre_close,
            'daily_low': self.daily_low,
            'daily_high': self.daily_high,
            'windows': self.windows
        }


class CapitalFlowService:
    """
    资金服务统一出口
    CTO指令：资金因子统一出口，"资金为王"的落地实现
    """
    
    def __init__(self):
        # 每个股票一个计算器
        self._calculators: Dict[str, RollingFlowCalculator] = {}
        
    def get_calculator(self, stock_code: str) -> RollingFlowCalculator:
        """获取或创建指定股票的计算器"""
        if stock_code not in self._calculators:
            self._calculators[stock_code] = RollingFlowCalculator()
        return self._calculators[stock_code]
    
    def process_tick(self, stock_code: str, tick_data: Dict, 
                     last_tick_data: Optional[Dict] = None,
                     pre_close: Optional[float] = None) -> RollingFlowMetrics:
        """
        处理tick数据并返回资金指标
        
        Args:
            stock_code: 股票代码
            tick_data: 当前tick
            last_tick_data: 上一tick
            pre_close: 昨收价（首次调用时需要）
            
        Returns:
            RollingFlowMetrics: 资金指标
        """
        calc = self.get_calculator(stock_code)
        
        # 设置昨收价
        if pre_close and calc.pre_close == 0:
            calc.set_pre_close(pre_close)
        
        return calc.add_tick(tick_data, last_tick_data)
    
    def reset(self, stock_code: Optional[str] = None):
        """重置计算器"""
        if stock_code:
            if stock_code in self._calculators:
                del self._calculators[stock_code]
        else:
            self._calculators.clear()


# 全局实例
_capital_flow_service = CapitalFlowService()


def get_capital_flow_service() -> CapitalFlowService:
    """获取资金服务单例"""
    return _capital_flow_service


def calculate_true_change_pct(current_price: float, pre_close: float) -> float:
    """
    计算真实涨幅（相对昨收）
    CTO指令：全局统一使用pre_close作为基准，严禁使用open
    """
    if pre_close > 0:
        return (current_price - pre_close) / pre_close * 100
    return 0.0


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("Rolling Metrics 模块测试")
    print("=" * 80)
    
    # 创建计算器
    calc = RollingFlowCalculator(windows=[1, 5, 15])
    calc.set_pre_close(11.48)  # 网宿1月26日昨收价
    
    # 模拟tick数据
    test_ticks = [
        {'time': 1769391000000, 'lastPrice': 11.77, 'volume': 17157},
        {'time': 1769391003000, 'lastPrice': 11.79, 'volume': 26217},
        {'time': 1769391006000, 'lastPrice': 11.84, 'volume': 31628},
        {'time': 1769391009000, 'lastPrice': 11.85, 'volume': 38900},
        {'time': 1769391012000, 'lastPrice': 11.89, 'volume': 45000},
    ]
    
    print("\n模拟网宿科技早盘tick数据：")
    print(f"昨收价: {calc.pre_close}")
    print("-" * 80)
    
    last_tick = None
    for tick in test_ticks:
        metrics = calc.add_tick(tick, last_tick)
        print(f"时间戳: {metrics.timestamp}")
        print(f"  价格: {metrics.current_price:.2f}")
        print(f"  真实涨幅: {metrics.true_change_pct:.2f}%")
        print(f"  1分钟流: {metrics.flow_1min.flow_intensity:.2f}M")
        print(f"  5分钟流: {metrics.flow_5min.flow_intensity:.2f}M")
        print(f"  资金持续性: {metrics.flow_sustainability:.2f}")
        print(f"  置信度: {metrics.confidence:.2f}")
        print()
        last_tick = tick
    
    print("=" * 80)
    print("✅ Rolling Metrics 模块测试完成")
    print("=" * 80)
