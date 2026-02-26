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
    - max_turnover = 60.0: 死亡换手熔断（规避主力出货）
    
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
