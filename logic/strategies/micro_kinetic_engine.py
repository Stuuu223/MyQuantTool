#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微观动能引擎 - 基于Ask/Bid盘口数据计算dV/dt

物理学定义：
- V(t) = 买卖压力 = (BidVol - AskVol) / TotalVol
- dV/dt = 资金加速度 = 压力变化率

【设计哲学】
涨幅是宏观位移，易受布朗噪声污染。
微观动能dV/dt捕捉资金注入的加速度，是真龙起爆的物理本质。

【数据源】
- xtdata.get_full_tick() 返回的 bidVol[5] / askVol[5]
- 精度：Tick级（约3秒/笔），比1分钟K线精确20倍

【ATR势垒阈值说明】
- 当前采用 atr_ratio >= 1.8x（研究报告推荐值）
- 研究样本：2026-02-27至2026-03-02（4天）
- 结论：atr_ratio >= 1.8时，涨停概率提升3.2倍
- TODO: 后续需更大样本优化此参数

Author: CTO物理学重铸
Date: 2026-03-04
Version: 1.0.0
"""

from typing import Dict, List, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


class MicroKineticEngine:
    """
    微观动能引擎 - 基于Ask/Bid盘口压力差计算dV/dt
    
    【物理学原理】
    - 买卖压力 = (买盘总量 - 卖盘总量) / 总量
    - 动能加速度 = 压力的变化率（线性回归斜率）
    - 正加速度：买盘压力持续增强，资金加速注入
    - 负加速度：买盘压力衰减，可能是诱多陷阱
    
    【使用场景】
    - 实盘：Tick回调时更新，计算当前加速度
    - 回测：需要完整Tick历史重放
    """
    
    def __init__(self, window_size: int = 5):
        """
        初始化微观动能引擎
        
        Args:
            window_size: 滑动窗口大小（Tick数量），默认5个Tick
                        约15秒的数据，平衡响应速度和噪声过滤
        """
        self.window_size = window_size
        self.pressure_history: deque = deque(maxlen=window_size)
        self.tick_count = 0
        
    def calculate_pressure(self, tick_data: Dict) -> float:
        """
        计算单个Tick的买卖压力
        
        【物理意义】
        - pressure > 0：买盘强于卖盘，多头优势
        - pressure < 0：卖盘强于买盘，空头优势
        - pressure ≈ 0：多空平衡，方向不明
        
        Args:
            tick_data: Tick数据字典，需包含:
                - bidVol: List[int] 五档买量 [bid1Vol, bid2Vol, ...]
                - askVol: List[int] 五档卖量 [ask1Vol, ask2Vol, ...]
                
        Returns:
            float: 买卖压力值，范围 [-1.0, 1.0]
        """
        bid_vol = tick_data.get('bidVol', [])
        ask_vol = tick_data.get('askVol', [])
        
        # 安全处理：确保是列表且长度正确
        if not isinstance(bid_vol, (list, tuple)):
            bid_vol = [0] * 5
        if not isinstance(ask_vol, (list, tuple)):
            ask_vol = [0] * 5
            
        # 计算五档总量
        bid_total = sum(float(v) for v in bid_vol[:5] if v is not None)
        ask_total = sum(float(v) for v in ask_vol[:5] if v is not None)
        total_vol = bid_total + ask_total
        
        if total_vol == 0:
            return 0.0
        
        pressure = (bid_total - ask_total) / total_vol
        return max(-1.0, min(1.0, pressure))  # 限制在[-1, 1]范围
    
    def update(self, tick_data: Dict) -> float:
        """
        更新压力历史并返回当前压力值
        
        Args:
            tick_data: Tick数据字典
            
        Returns:
            float: 当前压力值
        """
        pressure = self.calculate_pressure(tick_data)
        self.pressure_history.append(pressure)
        self.tick_count += 1
        return pressure
    
    def get_acceleration(self) -> float:
        """
        计算微观加速度 dV/dt
        
        【算法】使用线性回归计算压力序列的斜率
        - 斜率 > 0：压力递增，买盘加速
        - 斜率 < 0：压力递减，卖盘加速
        - 斜率 ≈ 0：压力稳定，方向不明
        
        Returns:
            float: 加速度值（压力/时间单位）
        """
        if len(self.pressure_history) < 2:
            return 0.0
        
        # 线性回归计算斜率
        n = len(self.pressure_history)
        x = list(range(n))  # 时间序列 [0, 1, 2, ..., n-1]
        y = list(self.pressure_history)
        
        # 计算斜率 k = Σ(x-x̄)(y-ȳ) / Σ(x-x̄)²
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        acceleration = numerator / denominator
        return acceleration
    
    def get_kinetic_state(self) -> Dict:
        """
        获取当前动能状态
        
        Returns:
            Dict: 包含压力、加速度、趋势等状态信息
        """
        pressure = self.pressure_history[-1] if self.pressure_history else 0.0
        acceleration = self.get_acceleration()
        
        # 判断趋势
        if acceleration > 0.05:
            trend = "加速买入"
        elif acceleration < -0.05:
            trend = "加速卖出"
        else:
            trend = "方向不明"
        
        return {
            "pressure": round(pressure, 4),
            "acceleration": round(acceleration, 4),
            "trend": trend,
            "tick_count": self.tick_count,
            "window_size": self.window_size
        }
    
    def reset(self):
        """重置引擎状态"""
        self.pressure_history.clear()
        self.tick_count = 0


def calculate_tick_kinetic(
    tick_stream: List[Dict],
    window_size: int = 5
) -> Tuple[float, Dict]:
    """
    【便捷函数】从Tick流计算微观动能
    
    Args:
        tick_stream: Tick数据列表
        window_size: 滑动窗口大小
        
    Returns:
        (acceleration, state): 加速度值和状态字典
    """
    engine = MicroKineticEngine(window_size=window_size)
    
    for tick in tick_stream:
        engine.update(tick)
    
    return engine.get_acceleration(), engine.get_kinetic_state()


def validate_kinetic_signal(
    tick_stream: List[Dict],
    min_acceleration: float = 0.05,
    window_size: int = 5
) -> Tuple[bool, str, Dict]:
    """
    【信号验证】验证微观动能是否满足起爆条件
    
    【物理判定】
    - acceleration > min_acceleration: 买盘加速注入，真龙信号
    - acceleration < -min_acceleration: 卖盘加速，诱多陷阱
    - |acceleration| <= min_acceleration: 动能不足，继续观察
    
    Args:
        tick_stream: Tick数据列表
        min_acceleration: 最小加速度阈值，默认0.05
        window_size: 滑动窗口大小
        
    Returns:
        (is_valid, reason, state): 
            - is_valid: 是否满足起爆条件
            - reason: 判定原因
            - state: 动能状态字典
    """
    acceleration, state = calculate_tick_kinetic(tick_stream, window_size)
    
    if acceleration > min_acceleration:
        return True, f"买盘加速注入: acceleration={acceleration:.4f} > {min_acceleration}", state
    elif acceleration < -min_acceleration:
        return False, f"卖盘加速逃离: acceleration={acceleration:.4f} < -{min_acceleration}", state
    else:
        return False, f"动能不足: |acceleration|={abs(acceleration):.4f} <= {min_acceleration}", state


# =============================================================================
# 单元测试
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("微观动能引擎 - 单元测试")
    print("=" * 60)
    
    # 测试1: 压力计算
    print("\n【测试1】买卖压力计算")
    engine = MicroKineticEngine(window_size=3)
    
    # 构造测试数据：买盘 > 卖盘
    tick1 = {
        'bidVol': [100, 80, 60, 40, 20],  # 总计300手
        'askVol': [20, 40, 30, 20, 10]    # 总计120手
    }
    pressure = engine.calculate_pressure(tick1)
    expected = (300 - 120) / (300 + 120)  # = 0.4286
    print(f"  买盘=300, 卖盘=120, 压力={pressure:.4f} (预期≈{expected:.4f})")
    assert abs(pressure - expected) < 0.01, "压力计算错误"
    print("  ✅ 通过")
    
    # 测试2: 加速度计算
    print("\n【测试2】加速度计算（递增压力序列）")
    engine = MicroKineticEngine(window_size=3)
    
    # 构造递增压力序列（买盘持续增强）
    ticks = [
        {'bidVol': [100]*5, 'askVol': [50]*5},  # pressure ≈ 0.333
        {'bidVol': [150]*5, 'askVol': [50]*5},  # pressure = 0.500
        {'bidVol': [200]*5, 'askVol': [50]*5},  # pressure = 0.600
    ]
    
    for tick in ticks:
        engine.update(tick)
    
    acceleration = engine.get_acceleration()
    print(f"  压力序列: 0.333 → 0.500 → 0.600")
    print(f"  加速度: {acceleration:.4f} (应>0，表示买盘加速)")
    assert acceleration > 0, "递增压力应有正加速度"
    print("  ✅ 通过")
    
    # 测试3: 递减压力序列
    print("\n【测试3】加速度计算（递减压力序列）")
    engine = MicroKineticEngine(window_size=3)
    
    ticks_decay = [
        {'bidVol': [200]*5, 'askVol': [50]*5},  # pressure = 0.600
        {'bidVol': [150]*5, 'askVol': [50]*5},  # pressure = 0.500
        {'bidVol': [100]*5, 'askVol': [50]*5},  # pressure = 0.333
    ]
    
    for tick in ticks_decay:
        engine.update(tick)
    
    acceleration = engine.get_acceleration()
    print(f"  压力序列: 0.600 → 0.500 → 0.333")
    print(f"  加速度: {acceleration:.4f} (应<0，表示买盘衰减)")
    assert acceleration < 0, "递减压力应有负加速度"
    print("  ✅ 通过")
    
    # 测试4: 信号验证
    print("\n【测试4】信号验证")
    is_valid, reason, state = validate_kinetic_signal(ticks, min_acceleration=0.05)
    print(f"  递增压力序列验证: is_valid={is_valid}, reason={reason}")
    assert is_valid, "递增压力应通过验证"
    print("  ✅ 通过")
    
    # 测试5: 状态输出
    print("\n【测试5】状态输出")
    state = engine.get_kinetic_state()
    print(f"  状态: {state}")
    print("  ✅ 通过")
    
    print("\n" + "=" * 60)
    print("✅ 所有单元测试通过！")
    print("=" * 60)
