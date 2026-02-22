#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Halfway策略核心逻辑模块
统一的Halfway战法定义，供所有场景调用
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime


def evaluate_halfway_state(
    prices: List,  # [(timestamp, price), ...] 或 [price, ...]
    volumes: List,  # [(timestamp, volume), ...] 或 [volume, ...]
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    评估当前是否满足Halfway条件
    
    Args:
        prices: 价格历史 [(timestamp, price), ...] 或 [price, ...]
        volumes: 成交量历史 [(timestamp, volume), ...] 或 [volume, ...]
        params: 策略参数
        
    Returns:
        Dict包含：
        - is_signal: 是否触发信号
        - factors: 关键因子 {volatility, volume_surge, breakout_strength}
        - extra_info: 额外信息
    """
    # 参数提取
    volatility_threshold = params.get('volatility_threshold', 0.03)
    volume_surge_threshold = params.get('volume_surge', 1.5)
    breakout_strength_threshold = params.get('breakout_strength', 0.01)
    window_minutes = params.get('window_minutes', 30)
    min_history_points = params.get('min_history_points', 5)  # 降低最小历史点数要求
    
    # 检查历史数据点数是否足够
    if len(prices) < min_history_points:
        return {
            'is_signal': False,
            'factors': {
                'volatility': 0.0,
                'volume_surge': 0.0,
                'breakout_strength': 0.0
            },
            'extra_info': {
                'reason': '历史数据不足',
                'history_length': len(prices)
            }
        }
    
    # 检查数据格式
    is_tuple_format = len(prices) > 0 and isinstance(prices[0], tuple)
    
    # 如果是元组格式，提取当前时间用于计算
    current_time = None
    if is_tuple_format and len(prices) > 0:
        current_time = prices[-1][0]  # 使用最后一个时间戳
    else:
        import time
        current_time = int(time.time() * 1000)  # 使用当前时间
    
    # 计算各项指标
    current_volatility = _calculate_volatility(prices, current_time, window_minutes)
    current_volume_surge = _calculate_volume_surge(volumes, current_time)
    # 提取当前价格（处理tuple格式 (timestamp, price) 或纯price格式）
    current_price_val = prices[-1][1] if prices and isinstance(prices[-1], tuple) else (prices[-1] if prices else 0)
    current_breakout_strength = _calculate_breakout_strength(prices, current_price_val)
    
    # 检查是否满足Halfway条件
    volatility_ok = current_volatility <= volatility_threshold
    volume_surge_ok = current_volume_surge >= volume_surge_threshold
    breakout_strength_ok = current_breakout_strength >= breakout_strength_threshold
    
    is_signal = volatility_ok and volume_surge_ok and breakout_strength_ok
    
    return {
        'is_signal': is_signal,
        'factors': {
            'volatility': current_volatility,
            'volume_surge': current_volume_surge,
            'breakout_strength': current_breakout_strength
        },
        'conditions': {
            'volatility_ok': volatility_ok,
            'volume_surge_ok': volume_surge_ok,
            'breakout_strength_ok': breakout_strength_ok
        },
        'extra_info': {
            'volatility_threshold': volatility_threshold,
            'volume_surge_threshold': volume_surge_threshold,
            'breakout_strength_threshold': breakout_strength_threshold
        }
    }


def _calculate_volatility(
    prices: List, 
    current_time: int, 
    window_minutes: int
) -> float:
    """
    计算平台波动率
    
    Args:
        prices: 价格历史 [(timestamp, price), ...] 或 [price, ...]
        current_time: 当前时间戳
        window_minutes: 计算窗口（分钟）
        
    Returns:
        float: 波动率
    """
    if len(prices) < 2:
        return 0.0
    
    # 检查数据格式
    is_tuple_format = len(prices) > 0 and isinstance(prices[0], tuple)
    
    if is_tuple_format:
        # 处理元组格式 [(timestamp, price), ...]
        target_time = current_time - window_minutes * 60 * 1000  # 转换为毫秒
        
        recent_prices = []
        for i in range(len(prices)-1, -1, -1):
            if prices[i][0] >= target_time:
                recent_prices.append(prices[i][1])  # price
            else:
                break
    else:
        # 处理列表格式 [price, ...]
        # 直接使用所有价格数据
        recent_prices = prices[-min(len(prices), 20):]  # 限制为最近20个数据点
    
    if len(recent_prices) < 2:
        return 0.0
    
    # 计算波动率（使用价格变化率的标准差）
    returns = []
    for i in range(1, len(recent_prices)):
        if recent_prices[i-1] != 0 and recent_prices[i-1] is not None:
            ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            returns.append(ret)
    
    volatility = np.std(returns) if len(returns) > 0 else 0.0
    return volatility


def _calculate_volume_surge(
    volumes: List, 
    current_time: int,
    baseline_window_minutes: int = 5
) -> float:
    """
    计算量能放大倍数
    
    Args:
        volumes: 成交量历史 [(timestamp, volume), ...] 或 [volume, ...]
        current_time: 当前时间戳
        baseline_window_minutes: 基准窗口（分钟）
        
    Returns:
        float: 量能放大倍数
    """
    if len(volumes) < 2:
        return 0.0
    
    # 检查数据格式
    is_tuple_format = len(volumes) > 0 and isinstance(volumes[0], tuple)
    
    if is_tuple_format:
        # 处理元组格式 [(timestamp, volume), ...]
        # 计算当前成交量变化
        current_volume = volumes[-1][1] - volumes[-2][1]
        if current_volume <= 0:
            return 0.0
        
        # 计算基准成交量（过去一段时间的平均值）
        target_time = current_time - baseline_window_minutes * 60 * 1000  # 转换为毫秒
        
        recent_volumes = []
        # 使用滑动窗口计算基准成交量，避免单笔大单影响
        volume_window_size = min(20, len(volumes)-1)  # 最多取20个点
        for i in range(len(volumes)-2, max(-1, len(volumes)-volume_window_size-2), -1):
            if i >= 0:
                vol_change = volumes[i][1] - (volumes[i-1][1] if i > 0 else 0)
                if vol_change > 0:
                    recent_volumes.append(vol_change)
    else:
        # 处理列表格式 [volume, ...]
        # 计算当前成交量变化（累计成交量）
        current_volume = volumes[-1] - volumes[-2] if len(volumes) >= 2 else volumes[-1]
        if current_volume <= 0:
            return 0.0
        
        # 计算基准成交量（历史平均变化量）
        recent_volumes = []
        for i in range(1, len(volumes)):
            vol_change = volumes[i] - volumes[i-1]
            if vol_change > 0:
                recent_volumes.append(vol_change)
    
    if len(recent_volumes) == 0:
        return 0.0
    
    avg_volume = np.mean(recent_volumes)
    
    if avg_volume <= 0:
        return 0.0
    
    return current_volume / avg_volume


def _calculate_breakout_strength(
    prices: List[Tuple[int, float]], 
    current_price: float,
    platform_window_minutes: int = 30
) -> float:
    """
    计算突破强度（相对于平台高点）
    
    Args:
        prices: 价格历史
        current_price: 当前价格
        platform_window_minutes: 平台窗口（分钟）
        
    Returns:
        float: 突破强度
    """
    if len(prices) < 2:
        return 0.0
    
    # 如果价格数据是列表格式而不是元组格式
    if len(prices) > 0 and not isinstance(prices[0], tuple):
        # 处理列表格式 [price1, price2, ...]
        # 取最后几项作为平台期（排除当前价格）
        platform_prices = prices[:-1] if len(prices) > 1 else prices
        if len(platform_prices) == 0:
            return 0.0
        platform_high = max(platform_prices)
    else:
        # 处理元组格式 [(timestamp, price), ...]
        platform_end_time = prices[-1][0]
        platform_start_time = platform_end_time - platform_window_minutes * 60 * 1000
        
        platform_prices = []
        for i in range(len(prices)-1, -1, -1):
            if prices[i][0] >= platform_start_time:
                platform_prices.append(prices[i][1])
            else:
                break
        
        if len(platform_prices) == 0:
            return 0.0
        
        platform_high = max(platform_prices)
    
    if platform_high <= 0 or current_price <= 0:
        return 0.0
    
    # 计算相对于平台高点的突破强度
    strength = (current_price - platform_high) / platform_high
    return strength


def create_halfway_platform_detector(params: Dict[str, Any]):
    """
    创建Halfway平台检测器（状态保持版本）
    用于需要连续跟踪平台状态的场景
    
    Args:
        params: 策略参数
        
    Returns:
        callable: 检测函数
    """
    # 内部状态
    platform_high = 0  # 平台高点
    platform_recognized = False  # 是否已识别平台
    
    def detector(
        prices: List[Tuple[int, float]], 
        volumes: List[Tuple[int, float]], 
        current_time: int, 
        current_price: float
    ) -> Dict[str, Any]:
        nonlocal platform_high, platform_recognized
        
        # 使用核心函数评估状态
        result = evaluate_halfway_state(prices, volumes, params)
        
        # 如果还没有识别到平台，检查是否可以识别
        if not platform_recognized:
            # 如果当前处于低波动状态，识别为平台
            if result['factors']['volatility'] <= params.get('volatility_threshold', 0.03):
                platform_recognized = True
                # 记录平台期间的高点
                window_minutes = params.get('window_minutes', 30)
                platform_start_time = current_time - window_minutes * 60 * 1000
                platform_prices = []
                for i in range(len(prices)-1, -1, -1):
                    if prices[i][0] >= platform_start_time:
                        platform_prices.append(prices[i][1])
                    else:
                        break
                if platform_prices:
                    platform_high = max(platform_prices)
        
        # 如果已识别平台，但当前波动率过高，可能平台被破坏
        if platform_recognized and result['factors']['volatility'] > params.get('volatility_threshold', 0.03):
            # 重置平台识别
            platform_recognized = False
            platform_high = 0
        
        # 更新平台高点（如果当前价格更高）
        if platform_recognized and current_price > platform_high:
            platform_high = current_price
        
        # 重新评估信号：必须在识别平台的基础上突破
        if platform_recognized and 'conditions' in result:
            # 重新计算突破强度，基于已识别的平台高点
            breakout_strength = (current_price - platform_high) / platform_high if platform_high > 0 else 0.0
            result['factors']['breakout_strength'] = breakout_strength
            result['conditions']['breakout_strength_ok'] = breakout_strength >= params.get('breakout_strength', 0.01)
            result['is_signal'] = (
                result['conditions']['volatility_ok'] and 
                result['conditions']['volume_surge_ok'] and 
                result['conditions']['breakout_strength_ok']
            )
        
        result['platform_state'] = {
            'platform_recognized': platform_recognized,
            'platform_high': platform_high
        }
        
        return result
    
    return detector


if __name__ == "__main__":
    # 测试代码
    print("✅ Halfway核心模块加载成功")
    
    # 创建测试数据
    import time
    current_time = int(time.time() * 1000)  # 毫秒时间戳
    test_prices = [(current_time - i * 60 * 1000, 10.0 + i * 0.01) for i in range(100, 0, -1)]
    test_volumes = [(current_time - i * 60 * 1000, 1000000 + i * 10000) for i in range(100, 0, -1)]
    
    # 测试参数
    test_params = {
        'volatility_threshold': 0.03,
        'volume_surge': 1.5,
        'breakout_strength': 0.01
    }
    
    # 测试评估函数
    result = evaluate_halfway_state(
        test_prices, 
        test_volumes, 
        current_time, 
        11.0, 
        test_params
    )
    print(f"评估结果: {result['is_signal']}")
    print(f"波动率: {result['factors']['volatility']:.4f}")
    print(f"量能放大: {result['factors']['volume_surge']:.2f}")
    print(f"突破强度: {result['factors']['breakout_strength']:.4f}")
    
    # 测试平台检测器
    detector = create_halfway_platform_detector(test_params)
    platform_result = detector(test_prices, test_volumes, current_time, 11.0)
    print(f"平台检测结果: {platform_result['is_signal']}")
    print(f"平台识别状态: {platform_result['platform_state']['platform_recognized']}")