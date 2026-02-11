#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量QPST四维分析器（分钟K优化版）

针对全市场扫描优化的四维分析引擎：
- 基于分钟K数据（而非Tick）
- 批量计算优化
- 内存友好设计

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

from logic.logger import get_logger

logger = get_logger(__name__)


class BatchQPSTAnalyzer:
    """
    批量QPST四维分析器
    
    四个维度：
    - Quantity (量): 成交量脉冲分析
    - Price (价): 价格走势形态
    - Space (空): 换手率/流通性
    - Time (时): 持续时间验证
    """
    
    def __init__(self, equity_info: dict):
        """
        初始化批量分析器
        
        Args:
            equity_info: 股本信息字典 {code: {float_shares: xxx}}
        """
        self.equity_info = equity_info
        logger.info("✅ BatchQPSTAnalyzer 初始化完成")
    
    def analyze(self, code: str, kline_df: pd.DataFrame) -> Dict:
        """
        执行完整的四维分析
        
        Args:
            code: 股票代码
            kline_df: 分钟K数据 DataFrame，至少包含:
                - time: 时间
                - open, high, low, close: 价格
                - volume: 成交量
        
        Returns:
            {
                'quantity': {...},
                'price': {...},
                'space': {...},
                'time': {...},
                'vote_result': {...}  # 投票结果
            }
        """
        if len(kline_df) < 10:
            return self._empty_result('数据不足')
        
        # 维度1: 量能分析
        quantity_dim = self._analyze_quantity(kline_df)
        
        # 维度2: 价格分析
        price_dim = self._analyze_price(kline_df)
        
        # 维度3: 换手率分析
        space_dim = self._analyze_space(kline_df, code)
        
        # 维度4: 时间持续性分析
        time_dim = self._analyze_time(kline_df)
        
        # 投票机制
        vote_result = self._vote(
            quantity_dim['signal'],
            price_dim['signal'],
            space_dim['signal'],
            time_dim['signal']
        )
        
        return {
            'quantity': quantity_dim,
            'price': price_dim,
            'space': space_dim,
            'time': time_dim,
            'vote_result': vote_result
        }
    
    def _analyze_quantity(self, df: pd.DataFrame) -> Dict:
        """
        维度1: 量能分析（基于分钟K）
        
        检测:
        - 量比（最近3分钟 vs 前7分钟）
        - 量能波动率（识别脉冲 vs 持续）
        - 量价配合度
        """
        volumes = df['volume'].values
        
        if len(volumes) < 10:
            return {'signal': 'INSUFFICIENT_DATA', 'metrics': {}}
        
        # 计算量比
        recent_avg = volumes[-3:].mean()
        earlier_avg = volumes[:-3].mean()
        volume_ratio = recent_avg / earlier_avg if earlier_avg > 0 else 1.0
        
        # 计算量能标准差
        volume_std = volumes.std()
        volume_volatility = volume_std / volumes.mean() if volumes.mean() > 0 else 0
        
        # 计算整体放量倍数
        avg_volume = volumes.mean()
        current_volume = volumes[-1]
        volume_surge = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # 判断逻辑
        if volume_ratio > 2.0 and volume_volatility < 0.8:
            signal = 'STRONG_VOLUME'  # 持续放量
        elif volume_ratio > 3.0 and volume_volatility > 1.5:
            signal = 'ABNORMAL_SPIKE'  # 单次异常（可能对倒）
        elif volume_ratio > 1.5:
            signal = 'MODERATE_VOLUME'  # 温和放量
        elif volume_ratio < 0.8:
            signal = 'SHRINKING_VOLUME'  # 缩量
        else:
            signal = 'NORMAL_VOLUME'
        
        return {
            'signal': signal,
            'metrics': {
                'volume_ratio': round(volume_ratio, 2),
                'volume_volatility': round(volume_volatility, 2),
                'volume_surge': round(volume_surge, 2)
            }
        }
    
    def _analyze_price(self, df: pd.DataFrame) -> Dict:
        """
        维度2: 价格分析（基于分钟K）
        
        检测:
        - 价格涨幅
        - 振幅（识别暴力拉升）
        - 价格趋势稳定性
        """
        # 价格涨幅
        price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
        
        # 平均振幅
        amplitude = ((df['high'] - df['low']) / df['close']).mean()
        
        # 价格标准差（稳定性）
        price_std = df['close'].std()
        price_stability = price_std / df['close'].mean() if df['close'].mean() > 0 else 0
        
        # 判断逻辑
        if price_change > 0.02 and amplitude < 0.015 and price_stability < 0.01:
            signal = 'STEADY_RISE'  # 稳步上涨（机构特征）
        elif price_change > 0.03 and amplitude > 0.03:
            signal = 'VIOLENT_RISE'  # 暴力拉升（散户追涨）
        elif abs(price_change) < 0.005 and amplitude < 0.01:
            signal = 'SIDEWAYS'  # 横盘
        elif price_change < -0.02:
            signal = 'DECLINE'  # 下跌
        else:
            signal = 'NORMAL_FLUCTUATION'
        
        return {
            'signal': signal,
            'metrics': {
                'price_change': round(price_change, 4),
                'amplitude': round(amplitude, 4),
                'price_stability': round(price_stability, 4)
            }
        }
    
    def _analyze_space(self, df: pd.DataFrame, code: str) -> Dict:
        """
        维度3: 换手率分析（基于流通股本）
        
        检测:
        - 累计换手率（10分钟）
        - 换手率趋势
        """
        # 获取流通股本
        float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
        
        if float_shares == 0:
            return {'signal': 'NO_EQUITY_DATA', 'metrics': {}}
        
        # 计算累计换手率（10分钟）
        total_volume = df['volume'].sum()
        turnover = total_volume / float_shares
        
        # 计算换手率趋势（前5分钟 vs 后5分钟）
        if len(df) >= 10:
            early_turnover = df['volume'].iloc[:5].sum() / float_shares
            late_turnover = df['volume'].iloc[-5:].sum() / float_shares
            turnover_trend = (late_turnover - early_turnover) / early_turnover if early_turnover > 0 else 0
        else:
            turnover_trend = 0
        
        # 判断逻辑（10分钟累计换手率）
        if 0.005 < turnover < 0.015 and abs(turnover_trend) < 0.2:
            signal = 'MODERATE_TURNOVER_STABLE'  # 中等稳定（正常）
        elif turnover > 0.02 and turnover_trend > 0.2:
            signal = 'HIGH_TURNOVER_RISING'  # 高换手且上升（活跃）
        elif turnover > 0.03:
            signal = 'EXTREMELY_HIGH_TURNOVER'  # 极高换手（警惕）
        elif turnover < 0.002:
            signal = 'LOW_TURNOVER'  # 低换手（冷门）
        else:
            signal = 'NORMAL_TURNOVER'
        
        return {
            'signal': signal,
            'metrics': {
                'turnover': round(turnover, 4),
                'turnover_trend': round(turnover_trend, 2)
            }
        }
    
    def _analyze_time(self, df: pd.DataFrame) -> Dict:
        """
        维度4: 时间持续性分析
        
        检测:
        - 异动持续时间
        - 时间段特征（早盘/午盘/尾盘）
        """
        volumes = df['volume'].values
        avg_vol = volumes.mean()
        
        # 计算持续放量的分钟数
        surge_minutes = sum(1 for v in volumes[-5:] if v > avg_vol * 1.5)
        surge_ratio = surge_minutes / 5 if len(volumes) >= 5 else 0
        
        # 判断时间段
        try:
            last_time = pd.to_datetime(df['time'].iloc[-1])
            current_hour = last_time.hour
            current_minute = last_time.minute
            
            if current_hour == 9 and current_minute < 45:
                time_period = 'MORNING_OPEN'  # 早盘开盘
            elif current_hour == 14 and current_minute >= 30:
                time_period = 'AFTERNOON_CLOSE'  # 尾盘
            else:
                time_period = 'NORMAL_TRADING'  # 正常交易时段
        except:
            time_period = 'UNKNOWN'
        
        # 判断逻辑
        if surge_ratio > 0.6 and time_period == 'NORMAL_TRADING':
            signal = 'SUSTAINED_ACTIVITY'  # 持续异动（真实）
        elif surge_ratio < 0.3 and time_period == 'AFTERNOON_CLOSE':
            signal = 'TAIL_SURGE'  # 尾盘拉升（警惕诱多）
        elif surge_ratio > 0.4:
            signal = 'MODERATE_ACTIVITY'
        else:
            signal = 'SHORT_SPIKE'  # 短暂脉冲
        
        return {
            'signal': signal,
            'metrics': {
                'surge_ratio': round(surge_ratio, 2),
                'time_period': time_period
            }
        }
    
    def _vote(self, quantity_signal: str, price_signal: str, 
              space_signal: str, time_signal: str) -> Dict:
        """
        投票机制：综合四个维度的信号
        
        规则:
        - 4个维度同时符合 → STRONG (85%置信度)
        - 3个维度符合 → MODERATE (65%置信度)
        - 2个维度符合 → WEAK (40%置信度)
        - ≤1个维度符合 → NEUTRAL (20%置信度)
        """
        # 定义正面信号
        positive_signals = {
            'quantity': ['STRONG_VOLUME', 'MODERATE_VOLUME'],
            'price': ['STEADY_RISE', 'SIDEWAYS'],
            'space': ['MODERATE_TURNOVER_STABLE', 'HIGH_TURNOVER_RISING'],
            'time': ['SUSTAINED_ACTIVITY', 'MODERATE_ACTIVITY']
        }
        
        # 统计正面维度数量
        positive_count = 0
        positive_dims = []
        
        if quantity_signal in positive_signals['quantity']:
            positive_count += 1
            positive_dims.append('量能')
        
        if price_signal in positive_signals['price']:
            positive_count += 1
            positive_dims.append('价格')
        
        if space_signal in positive_signals['space']:
            positive_count += 1
            positive_dims.append('换手')
        
        if time_signal in positive_signals['time']:
            positive_count += 1
            positive_dims.append('持续性')
        
        # 投票结果
        if positive_count >= 4:
            level = 'STRONG'
            confidence = 0.85
        elif positive_count == 3:
            level = 'MODERATE'
            confidence = 0.65
        elif positive_count == 2:
            level = 'WEAK'
            confidence = 0.40
        else:
            level = 'NEUTRAL'
            confidence = 0.20
        
        return {
            'level': level,
            'confidence': confidence,
            'positive_count': positive_count,
            'positive_dims': positive_dims
        }
    
    def _empty_result(self, reason: str) -> Dict:
        """空结果"""
        return {
            'quantity': {'signal': 'INSUFFICIENT_DATA'},
            'price': {'signal': 'INSUFFICIENT_DATA'},
            'space': {'signal': 'INSUFFICIENT_DATA'},
            'time': {'signal': 'INSUFFICIENT_DATA'},
            'vote_result': {
                'level': 'NEUTRAL',
                'confidence': 0.0,
                'positive_count': 0,
                'positive_dims': [],
                'reason': reason
            }
        }
