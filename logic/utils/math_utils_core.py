#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数学工具库 - CTO防御性编程：反混淆与防降级

【设计哲学】
1. 所有函数命名自带度量纲，杜绝歧义
2. 所有参数必须显式传递，无默认值
3. 所有计算封装成黑盒，AI只能调用不能修改

【反混淆规约】
- 凡是分位数计算：函数名必须带 _percentile
- 凡是倍数计算：函数名必须带 _multiplier 或 _ratio
- 凡是绝对值：函数名必须带 _absolute

Author: CTO防御工程
Date: 2026-02-26
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Optional, Union


def get_top_percentile_threshold(
    df: pd.DataFrame, 
    column: str, 
    percentile: float
) -> float:
    """
    【分位数计算专用】获取全市场前X%的门槛值
    
    【反混淆标识】函数名带 _percentile，表示这是分位数计算！
    
    Args:
        df: DataFrame数据源
        column: 要计算分位数的列名
        percentile: 分位点（0.0-1.0），如0.90表示前10%
        
    Returns:
        float: 分位数门槛值
        
    Example:
        >>> threshold = get_top_percentile_threshold(df, 'volume_ratio', 0.90)
        >>> # 这表示：全市场前10%的票，量比门槛是1.8倍
        >>> mask = df['volume_ratio'] >= threshold  # 筛选前10%
    """
    if df.empty or column not in df.columns:
        raise ValueError(f"数据为空或列不存在: {column}")
    
    if not 0.0 <= percentile <= 1.0:
        raise ValueError(f"分位点必须在0.0-1.0之间: {percentile}")
    
    # 使用.quantile()计算分位数 - 这是分位数计算的唯一正确方式！
    threshold = df[column].quantile(percentile)
    
    return float(threshold)


def calculate_volume_ratio_multiplier(
    current_volume: float, 
    avg_volume_5d: float
) -> float:
    """
    【倍数计算专用】计算量比倍数（今日是5日均量的多少倍）
    
    【反混淆标识】函数名带 _multiplier，表示这是倍数计算！
    
    Args:
        current_volume: 今日成交量（当前累计）
        avg_volume_5d: 5日平均成交量
        
    Returns:
        float: 量比倍数，如1.5表示今日是5日均量的1.5倍
        
    Example:
        >>> ratio = calculate_volume_ratio_multiplier(1500, 1000)
        >>> # ratio = 1.5，表示今日放量50%
        >>> if ratio >= 1.5:  # 直接比较倍数，无需分位数！
        ...     print("放量达标")
    """
    if avg_volume_5d <= 0:
        return 0.0
    
    return current_volume / avg_volume_5d


def calculate_turnover_rate_absolute(
    volume: float, 
    float_volume: float
) -> float:
    """
    【绝对值计算专用】计算换手率百分比
    
    【反混淆标识】函数名带 _absolute，表示这是绝对值！
    
    Args:
        volume: 成交量（股数）
        float_volume: 流通股本（股数）
        
    Returns:
        float: 换手率百分比，如5.0表示5%
    """
    if float_volume <= 0:
        return 0.0
    
    return (volume / float_volume) * 100.0


def filter_by_volume_multiplier(
    df: pd.DataFrame,
    volume_ratio_column: str,
    min_multiplier: float
) -> pd.DataFrame:
    """
    【黑盒算子】按量比倍数过滤（纯动态，无Magic Number）
    
    【使用场景】
    当Boss要求："只要今日是5日均量1.5倍以上的票"时使用此函数
    
    【严禁使用场景】
    不要拿这个去算分位数！分位数用 get_top_percentile_threshold()！
    
    Args:
        df: DataFrame
        volume_ratio_column: 量比列名（已预先计算好）
        min_multiplier: 最小倍数门槛（如1.5）
        
    Returns:
        pd.DataFrame: 过滤后的DataFrame
        
    Example:
        >>> # 正确的纯动态倍数过滤：
        >>> filtered = filter_by_volume_multiplier(df, 'volume_ratio', 1.5)
        >>> # 这表示：只要今日是5日均量1.5倍以上，直接进池！
        >>> # 无需计算全市场分位数，Zero Magic Number！
    """
    if df.empty or volume_ratio_column not in df.columns:
        return df
    
    mask = df[volume_ratio_column] >= min_multiplier
    return df[mask].copy()


def filter_by_turnover_range(
    df: pd.DataFrame,
    turnover_column: str,
    min_turnover: float,
    max_turnover: float
) -> pd.DataFrame:
    """
    【黑盒算子】按换手率范围过滤（大哥起步线+死亡换手熔断）
    
    【Boss战略参数】
    - min_turnover = 5.0: 大哥起步线（无5%不妖股）
    - max_turnover = 70.0: 死亡换手熔断（V20.5.2：70%统一阈值）
    
    Args:
        df: DataFrame
        turnover_column: 换手率列名
        min_turnover: 最小换手率（%）
        max_turnover: 最大换手率（%，死亡熔断线）
        
    Returns:
        pd.DataFrame: 过滤后的DataFrame
    """
    if df.empty or turnover_column not in df.columns:
        return df
    
    mask = (df[turnover_column] >= min_turnover) & (df[turnover_column] <= max_turnover)
    return df[mask].copy()


# =============================================================================
# CTO防御性编程：类型检查装饰器
# =============================================================================

def validate_multiplier(func):
    """
    【防御装饰器】验证倍数参数合法性
    """
    def wrapper(*args, **kwargs):
        # 检查所有带multiplier的参数
        for key, value in kwargs.items():
            if 'multiplier' in key and value is not None:
                if value <= 0:
                    raise ValueError(f"倍数必须大于0: {key}={value}")
        return func(*args, **kwargs)
    return wrapper


def validate_percentile(func):
    """
    【防御装饰器】验证分位点合法性
    """
    def wrapper(*args, **kwargs):
        for key, value in kwargs.items():
            if 'percentile' in key and value is not None:
                if not 0.0 <= value <= 1.0:
                    raise ValueError(f"分位点必须在0.0-1.0之间: {key}={value}")
        return func(*args, **kwargs)
    return wrapper


# =============================================================================
# CTO终极量纲对齐算子 - 强制单位统一 (V20.1量纲隔离墙)
# =============================================================================

SHOU_TO_GU = 100  # 1手 = 100股


def safe_calculate_volume_ratio(current_volume_shou: float, avg_volume_5d_gu: float) -> float:
    """
    【量纲对齐算子】安全计算量比
    
    自动处理手和股的单位对齐:
    - current_volume_shou: QMT get_full_tick返回的volume，单位是手
    - avg_volume_5d_gu: 日K数据计算的5日均量，单位是股
    
    Args:
        current_volume_shou: 当前成交量(手)
        avg_volume_5d_gu: 5日平均成交量(股)
        
    Returns:
        float: 量比倍数(如1.5表示1.5倍)
        
    Raises:
        ValueError: 当avg_volume_5d_gu <= 0时
    """
    if avg_volume_5d_gu <= 0:
        return 0.0
    
    # 将当前成交量(手)转换为股，与5日均量单位对齐
    current_volume_gu = current_volume_shou * SHOU_TO_GU
    
    return current_volume_gu / avg_volume_5d_gu


def safe_calculate_turnover_rate(current_volume_shou: float, float_volume_gu: float) -> float:
    """
    【量纲对齐算子】安全计算换手率
    
    自动对齐单位并返回百分比:
    - current_volume_shou: QMT get_full_tick返回的volume，单位是手
    - float_volume_gu: get_instrument_detail返回的FloatVolume，单位是股
    
    Args:
        current_volume_shou: 当日成交量(手)
        float_volume_gu: 流通股本(股)
        
    Returns:
        float: 换手率百分比(如5.0表示5%)
        
    Raises:
        ValueError: 当float_volume_gu <= 0时
    """
    if float_volume_gu <= 0:
        return 0.0
    
    # 将当日成交量(手)转换为股
    current_volume_gu = current_volume_shou * SHOU_TO_GU
    
    # 计算换手率并转换为百分比
    turnover_rate = (current_volume_gu / float_volume_gu) * 100.0
    
    return turnover_rate


def safe_calculate_estimated_volume(current_volume_shou: float, minutes_passed: float) -> float:
    """
    【量纲对齐算子】安全计算预估全天成交量
    
    用于盘中计算量比时使用的时间进度加权:
    estimated_full_day_volume = current_volume / minutes_passed * 240
    
    Args:
        current_volume_shou: 当前已成交数量(手)
        minutes_passed: 开盘后经过的分钟数
        
    Returns:
        float: 预估全天成交量(手)
    """
    if minutes_passed <= 0:
        minutes_passed = 1.0  # 防止除0
    
    # 限制最大240分钟(4小时交易时间)
    minutes_passed = min(minutes_passed, 240.0)
    
    return (current_volume_shou / minutes_passed) * 240.0


def calculate_estimated_flow(volume_delta: float, price: float, float_volume_shares: float) -> float:
    """
    【资金流量算子】真实资金推算器 - 量纲嗅探，手转股强制*100
    
    计算流入/流出的预估资金量，自动处理单位转换：
    - volume_delta: 可以是手(来自tick)或股(来自日K)，根据数值范围自动识别
    - price: 当前价格(元)
    - float_volume_shares: 流通股本(股)
    
    Args:
        volume_delta: 成交量变化量(手或股，自动识别)
        price: 当前股价
        float_volume_shares: 流通股本(股)
        
    Returns:
        float: 预估资金流量(万元)
        
    Example:
        >>> flow = calculate_estimated_flow(15000, 25.5, 100000000)
        >>> # 如果volume_delta是手: 15000手 = 150万股，资金=150万*25.5=3825万元
        >>> print(f"预估资金: {flow:.0f}万元")
    """
    if volume_delta <= 0 or price <= 0 or float_volume_shares <= 0:
        return 0.0
    
    # 【量纲嗅探】自动识别单位：
    # - 如果volume_delta相对于流通股本很小(比如<0.1%)，则认为是股
    # - 如果较大，则认为是手，需要*100转换为股
    ratio_to_float = volume_delta / float_volume_shares
    
    if ratio_to_float < 0.001:  # 小于0.1%流通股，认为是股
        volume_in_shares = volume_delta
    else:
        # 手转股的强制转换
        volume_in_shares = volume_delta * SHOU_TO_GU
    
    # 计算资金量(元)，然后转换为万元
    amount_wan = (volume_in_shares * price) / 10000.0
    
    return float(amount_wan)


def calculate_space_gap(current_price: float, high_60d: float) -> float:
    """
    【空间算子】突破纯度算子 - 返回距离60日高点的百分比
    
    正值表示还有上涨空间(距离高点有差距)，负值表示已突破新高
    
    Args:
        current_price: 当前价格
        high_60d: 60日最高价
        
    Returns:
        float: 距离60日高点的百分比(%)
              正值 = 距离高点还有X%空间
              0 = 正好在高点
              负值 = 已突破X%创新高
              
    Example:
        >>> gap = calculate_space_gap(95.0, 100.0)
        >>> # gap = 5.0，表示距离60日高点还有5%空间
        >>> if gap < 10:  # 距离高点不到10%
        ...     print("临近突破")
    """
    if high_60d <= 0:
        return float('inf')  # 无效数据返回无穷大
    
    # 计算距离高点的百分比差距
    gap_percent = ((high_60d - current_price) / high_60d) * 100.0
    
    return float(gap_percent)


def calculate_pullback_ratio(high_price: float, current_price: float, pre_close: float) -> float:
    """
    【回调算子】骗炮计算器 - 回吐利润比例
    
    计算从高点回落的回撤比例，用于识别"冲高回落"骗炮行为：
    - 0%: 还在高点，未回落
    - 50%: 回落到涨幅的一半
    - 100%: 完全回吐，跌回昨收
    - >100%: 翻绿，跌破昨收
    
    Args:
        high_price: 日内最高价
        current_price: 当前价格
        pre_close: 昨日收盘价
        
    Returns:
        float: 回吐利润比例(%)
              
    Example:
        >>> ratio = calculate_pullback_ratio(110.0, 105.0, 100.0)
        >>> # 最高涨幅10元，当前回落到5元，回吐比例=50%
        >>> if ratio > 50:  # 回吐超过50%
        ...     print("骗炮嫌疑，谨慎追高")
    """
    if high_price <= pre_close:
        return 0.0  # 根本没涨，不存在回吐
    
    if current_price > high_price:
        return 0.0  # 还在创新高
    
    # 计算最大涨幅和当前回吐
    max_gain = high_price - pre_close
    current_gain = current_price - pre_close
    
    if max_gain <= 0:
        return 0.0
    
    # 回吐比例 = (最大涨幅 - 当前涨幅) / 最大涨幅 * 100
    pullback = ((max_gain - current_gain) / max_gain) * 100.0
    
    return float(max(0.0, min(pullback, 200.0)))  # 限制在0-200%范围内


# =============================================================================
# 【CTO V172】连续函数库 - 废除布尔逻辑断崖，启用平滑物理函数
# =============================================================================

import math


def sigmoid_multiplier(value: float, midpoint: float, steepness: float) -> float:
    """
    S型平滑激活函数，输出范围 (0, 1)
    
    【物理意义】
    - value=midpoint 时输出 0.5（中性点）
    - steepness 越大，曲线越陡（阈值敏感度）
    - 输出平滑趋近0或1，无断崖式跳跃
    
    【用途】
    - MFE、sustain_ratio 等正向特征的平滑激活
    - 替代 `if value > threshold: pass else: return` 的布尔切断
    
    Args:
        value: 输入值（如MFE、sustain_ratio）
        midpoint: 中心点（阈值），value等于此时输出0.5
        steepness: 曲线陡峭度，越大越接近阶跃函数
        
    Returns:
        float: 激活乘数，范围(0, 1)
        
    Example:
        >>> mfe_factor = sigmoid_multiplier(mfe=1.8, midpoint=1.2, steepness=2.0)
        >>> # MFE=1.8时，中心点1.2，输出约0.70（已充分激活）
        >>> final_score = base_score * mfe_factor  # 平滑乘法，无断崖
    """
    if value is None or midpoint is None or steepness is None:
        return 0.5  # 缺失数据时返回中性值
    try:
        return 1.0 / (1.0 + math.exp(-steepness * (value - midpoint)))
    except (OverflowError, ValueError):
        # 数值溢出时返回边界值
        if value > midpoint:
            return 1.0
        return 0.0


def gaussian_penalty(value: float, optimal: float, sigma: float) -> float:
    """
    高斯钟形惩罚函数，输出范围 (0, 1]
    
    【物理意义】
    - value=optimal 时输出 1.0（最优）
    - 偏离optimal越多，输出越小
    - 双向惩罚：太高或太低都不行
    
    【用途】
    - limit_proximity（涨停逼近率）：居中最优，太高风险大，太低动能不足
    - 换手率甜点区：太高分歧大，太低活跃度不够
    
    Args:
        value: 输入值（如涨停逼近率0.8）
        optimal: 最优值（如0.75，表示涨幅距涨停25%最优）
        sigma: 标准差，控制容忍范围
        
    Returns:
        float: 惩罚乘数，范围(0, 1]，最优时=1.0
        
    Example:
        >>> prox_factor = gaussian_penalty(proximity=0.8, optimal=0.75, sigma=0.15)
        >>> # 逼近率0.8接近最优0.75，输出约0.97（几乎无惩罚）
        >>> # 如果proximity=0.5或0.95，输出会显著下降
    """
    if value is None or optimal is None or sigma is None or sigma <= 0:
        return 0.5  # 缺失数据或非法sigma时返回中性值
    try:
        return math.exp(-0.5 * ((value - optimal) / sigma) ** 2)
    except (OverflowError, ValueError):
        return 0.0


def exponential_decay(time_passed: float, half_life: float) -> float:
    """
    指数衰减函数，输出范围 (0, 1]
    
    【物理意义】
    - time_passed=0 时输出 1.0（无衰减）
    - 每经过 half_life 时间，输出衰减一半
    - 物理放射性衰变模型
    
    【用途】
    - 跨日情绪衰减：昨日涨停记忆随天数衰减
    - 日内时间衰减：尾盘信号权重降低
    
    Args:
        time_passed: 经过的时间（如天数、分钟数）
        half_life: 半衰期，输出衰减到0.5所需时间
        
    Returns:
        float: 衰减乘数，范围(0, 1]
        
    Example:
        >>> decay_factor = exponential_decay(time_passed=2, half_life=1)
        >>> # 经过2天，半衰期1天，输出=0.25（衰减75%）
        >>> memory_score = original_score * decay_factor
    """
    if time_passed is None or half_life is None or half_life <= 0:
        return 0.0
    if time_passed <= 0:
        return 1.0
    try:
        return math.exp(-math.log(2) * time_passed / half_life)
    except (OverflowError, ValueError):
        return 0.0


def calculate_ignition_probability(
    mfe: float, 
    sustain_ratio: float,
    proximity: float,
    mfe_midpoint: float = 1.2,
    mfe_steepness: float = 2.0,
    sustain_midpoint: float = 1.5,
    sustain_steepness: float = 2.0,
    proximity_optimal: float = 0.75,
    proximity_sigma: float = 0.15
) -> float:
    """
    【连乘点火概率模型】综合计算买入信号的总能量
    
    【物理哲学】
    废除 if-else 布尔切断，改用连续函数乘积：
    ignition_prob = mfe_factor * sustain_factor * proximity_factor
    
    每个因子输出(0,1)，只有三者同时高，总概率才高。
    任何一项短板都会平滑拉低总概率，无断崖式拒绝。
    
    Args:
        mfe: MFE做功效率
        sustain_ratio: 资金持续比
        proximity: 涨停逼近率
        其他参数: 各连续函数的超参数
        
    Returns:
        float: 综合点火概率(0, 1)
    """
    mfe_factor = sigmoid_multiplier(mfe, mfe_midpoint, mfe_steepness)
    sustain_factor = sigmoid_multiplier(sustain_ratio, sustain_midpoint, sustain_steepness)
    proximity_factor = gaussian_penalty(proximity, proximity_optimal, proximity_sigma)
    
    return mfe_factor * sustain_factor * proximity_factor
