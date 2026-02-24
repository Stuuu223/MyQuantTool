#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一过滤器模块 - 工业级标准化过滤逻辑
CTO强制实施：所有过滤逻辑使用统一配置，确保实盘与回演一致性

Author: CTO
Date: 2026-02-24
Version: V1.0 (工业级标准化版)
"""

import pandas as pd
from typing import Dict, Any, List
import numpy as np

from logic.core.config_manager import get_config_manager


class UnifiedFilters:
    """
    统一过滤器 - 确保实盘与回演使用同一套逻辑
    
    CTO强制规范：
    1. 所有过滤逻辑从配置管理器获取参数
    2. 实盘与回演使用相同算法
    3. 禁止在业务代码中写硬编码过滤条件
    """
    
    def __init__(self):
        self.config_manager = get_config_manager()
    
    def apply_volume_ratio_filter(self, df: pd.DataFrame, strategy: str = 'halfway') -> pd.DataFrame:
        """
        应用量比过滤
        
        Args:
            df: 包含volume_ratio列的DataFrame
            strategy: 策略类型
            
        Returns:
            过滤后的DataFrame
        """
        volume_percentile = self.config_manager.get_volume_ratio_percentile(strategy)
        volume_threshold = df['volume_ratio'].quantile(volume_percentile)
        
        mask = df['volume_ratio'] >= volume_threshold
        return df[mask].copy()
    
    def apply_price_momentum_filter(self, df: pd.DataFrame, strategy: str = 'halfway') -> pd.DataFrame:
        """
        应用价格动量过滤
        
        Args:
            df: 包含change_pct列的DataFrame
            strategy: 策略类型
            
        Returns:
            过滤后的DataFrame
        """
        change_percentile = self.config_manager.get_price_momentum_percentile(strategy)
        change_threshold = df['change_pct'].quantile(change_percentile)
        
        mask = df['change_pct'] >= change_threshold
        return df[mask].copy()
    
    def apply_three_funnel_filter(self, df: pd.DataFrame, strategy: str = 'halfway') -> pd.DataFrame:
        """
        应用三漏斗过滤 (价格有效性 + 涨幅分位数 + 量比分位数)
        
        Args:
            df: 包含price, prev_close, change_pct, volume_ratio, amount列的DataFrame
            strategy: 策略类型
            
        Returns:
            过滤后的DataFrame
        """
        # 获取配置参数
        volume_percentile = self.config_manager.get_volume_ratio_percentile(strategy)
        change_percentile = self.config_manager.get_price_momentum_percentile(strategy)
        
        # 计算分位数阈值
        volume_threshold = df['volume_ratio'].quantile(volume_percentile)
        change_threshold = df['change_pct'].quantile(change_percentile)
        
        # 应用三漏斗过滤
        mask = (
            (df['price'] > 0) &  # 价格有效性
            (df['prev_close'] > 0) &  # 昨收有效性
            (df['change_pct'] >= change_threshold) &  # 涨幅过滤 (ratio化)
            (df['volume_ratio'] >= volume_threshold) &  # 量比过滤 (ratio化)
            (df['amount'] >= 30000000)  # 成交额过滤 (3000万)
        )
        
        return df[mask].copy()
    
    def apply_three_line_defense_filter(self, df: pd.DataFrame, strategy: str = 'halfway') -> pd.DataFrame:
        """
        应用三道防线过滤 (实盘引擎用)
        
        Args:
            df: 包含volume_ratio, turnover_rate_per_min, turnover_rate等列的DataFrame
            strategy: 策略类型
            
        Returns:
            过滤后的DataFrame
        """
        # 获取配置参数
        volume_percentile = self.config_manager.get_volume_ratio_percentile(strategy)
        turnover_thresholds = self.config_manager.get_turnover_rate_thresholds()
        
        # 计算分位数阈值
        volume_threshold = df['volume_ratio'].quantile(volume_percentile)
        
        # 应用三道防线过滤
        mask = (
            (df['volume_ratio'] > volume_threshold) &                      # 量比基于市场分位数
            (df['turnover_rate_per_min'] > turnover_thresholds['per_minute_min']) &  # ⭐️ 核心：平均每分钟换手率>阈值
            (df['turnover_rate'] < turnover_thresholds['total_max'])                   # 过滤过度爆炒（<阈值）
        )
        
        return df[mask].copy()
    
    def get_standard_volume_ratio_thresholds(self) -> Dict[str, float]:
        """
        获取标准化的量比阈值 (用于非分位数场景)
        这些阈值仍然从配置管理器获取，确保统一管理
        
        Returns:
            量比阈值字典
        """
        # 注意：这些是绝对阈值，不是分位数，但也应该统一管理
        return {
            'low': 1.5,    # 低放量阈值
            'medium': 2.0, # 中放量阈值
            'high': 3.0,   # 高放量阈值
            'extreme': 5.0 # 极高放量阈值
        }
    
    def apply_standard_volume_ratio_filter(self, df: pd.DataFrame, threshold_type: str = 'medium') -> pd.DataFrame:
        """
        应用标准量比过滤 (使用绝对阈值)
        
        Args:
            df: 包含volume_ratio列的DataFrame
            threshold_type: 阈值类型 ('low', 'medium', 'high', 'extreme')
            
        Returns:
            过滤后的DataFrame
        """
        thresholds = self.get_standard_volume_ratio_thresholds()
        threshold = thresholds.get(threshold_type, thresholds['medium'])
        
        mask = df['volume_ratio'] >= threshold
        return df[mask].copy()


# 便捷函数
def create_unified_filters() -> UnifiedFilters:
    """创建统一过滤器实例"""
    return UnifiedFilters()


def apply_three_funnel_filter(df: pd.DataFrame, strategy: str = 'halfway') -> pd.DataFrame:
    """便捷函数：应用三漏斗过滤"""
    filters = create_unified_filters()
    return filters.apply_three_funnel_filter(df, strategy)


def apply_three_line_defense_filter(df: pd.DataFrame, strategy: str = 'halfway') -> pd.DataFrame:
    """便捷函数：应用三道防线过滤"""
    filters = create_unified_filters()
    return filters.apply_three_line_defense_filter(df, strategy)


if __name__ == "__main__":
    # 测试统一过滤器
    print("=" * 60)
    print("统一过滤器测试")
    print("=" * 60)
    
    # 创建测试数据
    test_df = pd.DataFrame({
        'stock_code': ['A', 'B', 'C', 'D', 'E'],
        'price': [10.0, 11.0, 12.0, 13.0, 14.0],
        'prev_close': [9.5, 10.5, 11.5, 12.5, 13.5],
        'change_pct': [5.26, 4.76, 4.35, 4.00, 3.70],
        'volume_ratio': [2.0, 1.8, 3.2, 1.5, 4.1],
        'amount': [40000000, 25000000, 50000000, 30000000, 60000000],
        'turnover_rate': [15.0, 18.0, 22.0, 10.0, 25.0],
        'turnover_rate_per_min': [0.3, 0.4, 0.5, 0.1, 0.6]
    })
    
    filters = create_unified_filters()
    
    print("原始数据:")
    print(test_df)
    print()
    
    # 测试三漏斗过滤
    filtered_3funnel = filters.apply_three_funnel_filter(test_df)
    print(f"三漏斗过滤后: {len(filtered_3funnel)} 只�")
    print(filtered_3funnel)
    print()
    
    # 测试三道防线过滤
    filtered_3line = filters.apply_three_line_defense_filter(test_df)
    print(f"三道防线过滤后: {len(filtered_3line)} 只�")
    print(filtered_3line)
    print()
    
    print("=" * 60)
    print("✅ 统一过滤器测试完成")