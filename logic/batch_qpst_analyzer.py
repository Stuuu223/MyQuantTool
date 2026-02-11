#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量四维分析器（分钟K版本）

针对全市场扫描优化的QPST四维分析引擎

核心优化：
1. 使用分钟K数据替代Tick数据
2. 向量化计算提升性能
3. 简化版 + 完整版双模式
4. 内存友好设计

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2 (Market Scanner)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

from logic.logger import get_logger

logger = get_logger(__name__)


class BatchQPSTAnalyzer:
    """
    批量四维分析器（QPST - Quantity/Price/Space/Time）
    
    针对分钟K数据优化，支持批量处理
    """
    
    def __init__(self, equity_info: dict = None):
        """
        初始化批量分析器
        
        Args:
            equity_info: 股本信息字典 {code: {'float_shares': xxx, ...}}
        """
        if equity_info is None:
            equity_info = self._load_equity_info()
        
        self.equity_info = equity_info
        logger.info(f"✅ BatchQPSTAnalyzer 初始化完成，加载 {len(equity_info)} 只股票股本信息")
    
    def _load_equity_info(self) -> dict:
        """加载本地股本信息"""
        try:
            equity_file = Path('data/equity_info.json')
            if equity_file.exists():
                with open(equity_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning("⚠️ data/equity_info.json 不存在，换手率分析将不可用")
                return {}
        except Exception as e:
            logger.error(f"❌ 加载股本信息失败: {e}")
            return {}
    
    # ========== 简化版分析（阶段2初筛） ==========
    
    def analyze_lite(self, kline_df: pd.DataFrame, code: str) -> Dict[str, str]:
        """
        简化版四维分析（用于初筛）
        
        Args:
            kline_df: 分钟K数据（至少10根）
            code: 股票代码
        
        Returns:
            {
                'quantity': 'NORMAL' | 'ABNORMAL',
                'price': 'NORMAL' | 'ABNORMAL',
                'space': 'NORMAL' | 'ABNORMAL',
                'time': 'NORMAL' | 'ABNORMAL'
            }
        """
        if len(kline_df) < 10:
            return {'quantity': 'INSUFFICIENT_DATA', 'price': 'INSUFFICIENT_DATA',
                    'space': 'INSUFFICIENT_DATA', 'time': 'INSUFFICIENT_DATA'}
        
        return {
            'quantity': self._analyze_quantity_lite(kline_df),
            'price': self._analyze_price_lite(kline_df),
            'space': self._analyze_space_lite(kline_df, code),
            'time': self._analyze_time_lite(kline_df)
        }
    
    def _analyze_quantity_lite(self, df: pd.DataFrame) -> str:
        """量能快速判断"""
        volumes = df['volume'].values
        
        # 量比（最近3分钟 vs 前7分钟）
        recent_avg = volumes[-3:].mean()
        earlier_avg = volumes[:-3].mean()
        volume_ratio = recent_avg / earlier_avg if earlier_avg > 0 else 1.0
        
        # 异常：放量超过2倍
        return 'ABNORMAL' if volume_ratio > 2.0 else 'NORMAL'
    
    def _analyze_price_lite(self, df: pd.DataFrame) -> str:
        """价格快速判断"""
        # 涨幅
        price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
        
        # 振幅
        amplitude = ((df['high'] - df['low']) / df['close']).mean()
        
        # 异常：涨幅>3% 且 振幅>3%（暴力拉升）
        return 'ABNORMAL' if (price_change > 0.03 and amplitude > 0.03) else 'NORMAL'
    
    def _analyze_space_lite(self, df: pd.DataFrame, code: str) -> str:
        """换手率快速判断"""
        float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
        if float_shares == 0:
            return 'NORMAL'  # 无股本信息，假设正常
        
        total_volume = df['volume'].sum()
        turnover = total_volume / float_shares
        
        # 异常：10分钟换手率>2%（极活跃）
        return 'ABNORMAL' if turnover > 0.02 else 'NORMAL'
    
    def _analyze_time_lite(self, df: pd.DataFrame) -> str:
        """时间持续性快速判断"""
        # 检查是否尾盘（简化判断）
        if 'time' in df.columns:
            last_time = df['time'].iloc[-1]
            if isinstance(last_time, str) and last_time >= '14:30':
                return 'ABNORMAL'  # 尾盘异动
        
        return 'NORMAL'
    
    # ========== 完整版分析（阶段3精筛） ==========
    
    def analyze_full(self, kline_df: pd.DataFrame, code: str) -> Dict:
        """
        完整版四维分析（用于精准识别）
        
        Args:
            kline_df: 分钟K数据（至少30根）
            code: 股票代码
        
        Returns:
            {
                'dimensions': {
                    'quantity': {...},
                    'price': {...},
                    'space': {...},
                    'time': {...}
                },
                'trap_signals': [...],
                'final_signal': 'STRONG_INFLOW' | 'WEAK_INFLOW' | 'NEUTRAL' | 'TRAP_WARNING',
                'confidence': 0.0-1.0,
                'reason': str
            }
        """
        if len(kline_df) < 20:
            return self._empty_result('数据不足')
        
        # 四维分析
        quantity_dim = self._analyze_quantity_full(kline_df)
        price_dim = self._analyze_price_full(kline_df)
        space_dim = self._analyze_space_full(kline_df, code)
        time_dim = self._analyze_time_full(kline_df)
        
        # 反诱多检测
        trap_signals = self._detect_traps(kline_df, code, quantity_dim, price_dim)
        
        # 综合判断
        final_signal, confidence, reason = self._synthesize_signal(
            quantity_dim, price_dim, space_dim, time_dim, trap_signals
        )
        
        return {
            'dimensions': {
                'quantity': quantity_dim,
                'price': price_dim,
                'space': space_dim,
                'time': time_dim
            },
            'trap_signals': trap_signals,
            'final_signal': final_signal,
            'confidence': confidence,
            'reason': reason
        }
    
    def _analyze_quantity_full(self, df: pd.DataFrame) -> Dict:
        """维度1：成交量分析（完整版）"""
        volumes = df['volume'].values
        
        # 量比
        recent_avg = volumes[-5:].mean()
        earlier_avg = volumes[:-5].mean()
        volume_ratio = recent_avg / earlier_avg if earlier_avg > 0 else 1.0
        
        # 量能波动率（识别脉冲 vs 持续）
        volume_std = volumes.std()
        volume_volatility = volume_std / volumes.mean() if volumes.mean() > 0 else 0
        
        # 量能趋势
        volume_trend = (volumes[-5:].mean() - volumes[:5].mean()) / volumes[:5].mean() if volumes[:5].mean() > 0 else 0
        
        # 信号判断
        if volume_ratio > 2.5 and volume_volatility < 0.8 and volume_trend > 0.3:
            signal = 'STRONG_VOLUME'  # 持续放量
        elif volume_ratio > 3.0 and volume_volatility > 1.5:
            signal = 'ABNORMAL_SPIKE'  # 单次异常（可能对倒）
        elif volume_ratio > 1.5:
            signal = 'MODERATE_VOLUME'  # 温和放量
        else:
            signal = 'NORMAL_VOLUME'
        
        return {
            'volume_ratio': volume_ratio,
            'volume_volatility': volume_volatility,
            'volume_trend': volume_trend,
            'signal': signal
        }
    
    def _analyze_price_full(self, df: pd.DataFrame) -> Dict:
        """维度2：价格分析（完整版）"""
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # 价格涨幅
        price_change = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
        
        # 振幅（识别暴力拉升）
        amplitude = ((highs - lows) / closes).mean()
        
        # 价格动量（最近5分钟 vs 前面）
        recent_avg_price = closes[-5:].mean()
        earlier_avg_price = closes[:-5].mean()
        price_momentum = (recent_avg_price - earlier_avg_price) / earlier_avg_price if earlier_avg_price > 0 else 0
        
        # 信号判断
        if price_change > 0.02 and amplitude < 0.015 and price_momentum > 0.01:
            signal = 'STEADY_RISE'  # 稳步上涨（机构特征）
        elif price_change > 0.03 and amplitude > 0.03:
            signal = 'VIOLENT_RISE'  # 暴力拉升（散户追涨）
        elif abs(price_change) < 0.005:
            signal = 'SIDEWAYS'  # 横盘
        elif price_change < -0.02:
            signal = 'DECLINE'  # 下跌
        else:
            signal = 'NORMAL_FLUCTUATION'
        
        return {
            'price_change': price_change,
            'amplitude': amplitude,
            'price_momentum': price_momentum,
            'signal': signal
        }
    
    def _analyze_space_full(self, df: pd.DataFrame, code: str) -> Dict:
        """维度3：换手率分析（完整版）"""
        float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
        
        if float_shares == 0:
            return {'signal': 'NO_EQUITY_DATA', 'turnover': 0, 'turnover_trend': 0}
        
        # 计算换手率（使用最近10分钟数据）
        total_volume = df['volume'].sum()
        turnover = total_volume / float_shares
        
        # 换手率趋势（最近5分钟 vs 前5分钟）
        if len(df) >= 10:
            recent_turnover = df['volume'].iloc[-5:].sum() / float_shares
            earlier_turnover = df['volume'].iloc[:-5].sum() / float_shares
            turnover_trend = (recent_turnover - earlier_turnover) / earlier_turnover if earlier_turnover > 0 else 0
        else:
            turnover_trend = 0
        
        # 信号判断（基于10分钟累计换手率）
        if turnover > 0.02 and turnover_trend > 0.2:
            signal = 'HIGH_TURNOVER_RISING'  # 高换手且上升
        elif 0.005 < turnover < 0.015 and abs(turnover_trend) < 0.1:
            signal = 'MODERATE_TURNOVER_STABLE'  # 中等换手且稳定
        elif turnover < 0.003:
            signal = 'LOW_TURNOVER'  # 低换手
        else:
            signal = 'NORMAL_TURNOVER'
        
        return {
            'turnover': turnover,
            'turnover_trend': turnover_trend,
            'signal': signal
        }
    
    def _analyze_time_full(self, df: pd.DataFrame) -> Dict:
        """维度4：时间持续性分析（完整版）"""
        volumes = df['volume'].values
        avg_vol = volumes.mean()
        
        # 计算持续放量的分钟数
        surge_minutes = sum(1 for v in volumes[-10:] if v > avg_vol * 1.5)
        surge_ratio = surge_minutes / min(10, len(volumes))
        
        # 时间段判断
        time_period = 'NORMAL_TRADING'
        if 'time' in df.columns:
            last_time = df['time'].iloc[-1]
            if isinstance(last_time, str):
                if last_time < '09:45':
                    time_period = 'MORNING_OPEN'
                elif last_time >= '14:30':
                    time_period = 'AFTERNOON_CLOSE'
        
        # 信号判断
        if surge_ratio > 0.7 and time_period == 'NORMAL_TRADING':
            signal = 'SUSTAINED_ACTIVITY'  # 持续异动
        elif surge_ratio > 0.5 and time_period == 'AFTERNOON_CLOSE':
            signal = 'TAIL_SURGE'  # 尾盘拉升
        elif surge_ratio > 0.4:
            signal = 'MODERATE_ACTIVITY'
        else:
            signal = 'SHORT_SPIKE'  # 短暂脉冲
        
        return {
            'surge_ratio': surge_ratio,
            'time_period': time_period,
            'signal': signal
        }
    
    # ========== 反诱多检测 ==========
    
    def _detect_traps(self, df: pd.DataFrame, code: str, 
                      quantity_dim: Dict, price_dim: Dict) -> List[str]:
        """
        反诱多检测（分钟K版本）
        
        检测：
        1. 尾盘拉升
        2. 放量滞涨
        3. 连续涨停开板
        """
        trap_signals = []
        
        # 检测1：尾盘拉升
        if 'time' in df.columns:
            last_time = df['time'].iloc[-1]
            if isinstance(last_time, str) and last_time >= '14:30':
                # 检查是否突然放量
                volumes = df['volume'].values
                recent_vols = volumes[-5:]
                earlier_vols = volumes[-10:-5]
                
                recent_avg = recent_vols.mean()
                earlier_avg = earlier_vols.mean()
                
                if recent_avg > earlier_avg * 2 and earlier_avg > 0:
                    trap_signals.append('尾盘拉升：警惕次日低开')
        
        # 检测2：放量滞涨
        if quantity_dim['signal'] in ['STRONG_VOLUME', 'ABNORMAL_SPIKE']:
            if price_dim['signal'] in ['SIDEWAYS', 'NORMAL_FLUCTUATION']:
                trap_signals.append('放量滞涨：成交量异常但价格不涨')
        
        # 检测3：连续涨停开板（需要日线数据，这里简化处理）
        # 可以通过传入额外参数判断
        
        return trap_signals
    
    # ========== 综合判断 ==========
    
    def _synthesize_signal(self, quantity_dim: Dict, price_dim: Dict,
                           space_dim: Dict, time_dim: Dict,
                           trap_signals: List[str]) -> Tuple[str, float, str]:
        """
        综合判断（投票机制）
        
        Returns:
            (final_signal, confidence, reason)
        """
        # 优先级1：诱多预警
        if trap_signals:
            return 'TRAP_WARNING', 0.9, f"诱多预警: {'; '.join(trap_signals)}"
        
        # 统计正面信号
        positive_signals = []
        
        if quantity_dim['signal'] in ['STRONG_VOLUME', 'MODERATE_VOLUME']:
            positive_signals.append('量能')
        
        if price_dim['signal'] in ['STEADY_RISE', 'SIDEWAYS']:
            positive_signals.append('价格')
        
        if space_dim['signal'] in ['MODERATE_TURNOVER_STABLE', 'HIGH_TURNOVER_RISING']:
            positive_signals.append('换手')
        
        if time_dim['signal'] in ['SUSTAINED_ACTIVITY', 'MODERATE_ACTIVITY']:
            positive_signals.append('持续性')
        
        # 投票机制
        vote_count = len(positive_signals)
        
        if vote_count >= 4:
            return 'STRONG_INFLOW', 0.85, f"机构吸筹特征明显（{'+'.join(positive_signals)}）"
        elif vote_count == 3:
            return 'WEAK_INFLOW', 0.65, f"温和流入（{'+'.join(positive_signals)}）"
        elif vote_count == 2:
            return 'NEUTRAL', 0.4, f"部分维度符合（{'+'.join(positive_signals)}）"
        else:
            # 检查是否是出货信号
            if quantity_dim['signal'] == 'SHRINKING_VOLUME' and price_dim['signal'] == 'DECLINE':
                return 'STRONG_OUTFLOW', 0.75, "缩量下跌，资金流出"
            else:
                return 'NEUTRAL', 0.3, "无明显特征"
    
    def _empty_result(self, reason: str) -> Dict:
        """空结果"""
        return {
            'dimensions': {},
            'trap_signals': [],
            'final_signal': 'NEUTRAL',
            'confidence': 0.0,
            'reason': reason
        }
