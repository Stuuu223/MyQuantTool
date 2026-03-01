# -*- coding: utf-8 -*-
"""
指标定义模块 - Metric Definitions
========================================
集中定义所有量化指标的计算方法

设计原则：
1. 无状态 - 纯静态方法，不保存任何状态
2. 可复用 - 实盘/回测/热复盘共用
3. 零硬编码 - 所有参数可配置

Author: CTO重构
Date: 2026-03-02
Version: V1.0.0
"""

import pandas as pd
import numpy as np
from typing import Union, Optional


def safe_float(value, default=0.0):
    """安全转换为float"""
    if value is None:
        return default
    try:
        if pd.isna(value) or np.isinf(value):
            return default
    except:
        pass
    try:
        result = float(value)
        if pd.isna(result) or np.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


class MetricDefinitions:
    """
    指标定义类 - 所有指标计算方法的静态集合
    
    命名规范：
    - TRUE_* = 真实值（基于收盘价计算）
    - RATIO_* = 比率值（基于前收盘价计算）
    """
    
    # ─────────────────────────────────────────────────────────────────
    # 涨跌幅计算
    # ─────────────────────────────────────────────────────────────────
    
    @staticmethod
    def TRUE_CHANGE(close: float, pre_close: float) -> float:
        """
        真实涨跌幅计算
        
        公式: (close - pre_close) / pre_close * 100
        
        Args:
            close: 当日收盘价
            pre_close: 前收盘价
            
        Returns:
            float: 涨跌幅百分比
        """
        close = safe_float(close)
        pre_close = safe_float(pre_close)
        if pre_close == 0:
            return 0.0
        return (close - pre_close) / pre_close * 100
    
    @staticmethod
    def TRUE_CHANGE_RATIO(close: float, pre_close: float) -> float:
        """
        真实涨跌比率（不带百分比）
        
        公式: (close - pre_close) / pre_close
        
        Args:
            close: 当日收盘价
            pre_close: 前收盘价
            
        Returns:
            float: 涨跌比率
        """
        close = safe_float(close)
        pre_close = safe_float(pre_close)
        if pre_close == 0:
            return 0.0
        return (close - pre_close) / pre_close
    
    # ─────────────────────────────────────────────────────────────────
    # 量比计算
    # ─────────────────────────────────────────────────────────────────
    
    @staticmethod
    def VOLUME_RATIO(volume: float, avg_volume_5d: float) -> float:
        """
        量比计算
        
        公式: volume / avg_volume_5d
        
        Args:
            volume: 当日成交量
            avg_volume_5d: 5日均量
            
        Returns:
            float: 量比
        """
        volume = safe_float(volume)
        avg_volume_5d = safe_float(avg_volume_5d)
        if avg_volume_5d == 0:
            return 0.0
        return volume / avg_volume_5d
    
    # ─────────────────────────────────────────────────────────────────
    # 换手率计算
    # ─────────────────────────────────────────────────────────────────
    
    @staticmethod
    def TURNOVER_RATE(volume: float, float_volume: float) -> float:
        """
        换手率计算
        
        公式: volume / float_volume * 100
        
        Args:
            volume: 当日成交量（股）
            float_volume: 流通股本（股）
            
        Returns:
            float: 换手率百分比
        """
        volume = safe_float(volume)
        float_volume = safe_float(float_volume)
        if float_volume == 0:
            return 0.0
        return volume / float_volume * 100
    
    # ─────────────────────────────────────────────────────────────────
    # 振幅计算
    # ─────────────────────────────────────────────────────────────────
    
    @staticmethod
    def AMPLITUDE(high: float, low: float, pre_close: float) -> float:
        """
        振幅计算
        
        公式: (high - low) / pre_close * 100
        
        Args:
            high: 当日最高价
            low: 当日最低价
            pre_close: 前收盘价
            
        Returns:
            float: 振幅百分比
        """
        high = safe_float(high)
        low = safe_float(low)
        pre_close = safe_float(pre_close)
        if pre_close == 0:
            return 0.0
        return (high - low) / pre_close * 100
    
    # ─────────────────────────────────────────────────────────────────
    # 资金流入比率计算
    # ─────────────────────────────────────────────────────────────────
    
    @staticmethod
    def INFLOW_RATIO(amount: float, market_amount: float) -> float:
        """
        资金流入比率
        
        公式: amount / market_amount
        
        Args:
            amount: 个股成交额
            market_amount: 市场总成交额
            
        Returns:
            float: 流入比率
        """
        amount = safe_float(amount)
        market_amount = safe_float(market_amount)
        if market_amount == 0:
            return 0.0
        return amount / market_amount
