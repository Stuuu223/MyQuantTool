#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量QPST四维分析器（分钟K优化版）

核心优化：
1. 适配分钟K数据（不再依赖Tick级别数据）
2. 简化版QPST用于初筛（快速判断异常）
3. 完整版QPST用于精筛（详细分析）

使用场景：
- 全市场批量扫描（5000+股票）
- 分钟K级别分析
- 三阶段渐进式筛选

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time as dt_time
import json
from pathlib import Path

from logic.logger import get_logger

logger = get_logger(__name__)


class BatchQPSTAnalyzer:
    """
    批量QPST四维分析器
    
    功能：
    1. 简化版QPST：快速判断异常特征（用于Phase2初筛）
    2. 完整版QPST：详细四维分析（用于Phase3精筛）
    3. 反诱多检测：识别对倒、尾盘拉升、连板开板
    """
    
    def __init__(self, equity_info: dict):
        """
        初始化分析器
        
        Args:
            equity_info: 股本信息字典 {code: {float_shares, total_shares}}
        """
        self.equity_info = equity_info
        logger.info(f"✅ BatchQPSTAnalyzer 初始化完成（股本信息: {len(equity_info)} 只股票）")
    
    
    # ========== 简化版QPST（Phase2初筛） ==========
    
    def analyze_lite(self, kline_df: pd.DataFrame, code: str) -> Dict[str, str]:
        """
        简化版QPST四维分析（快速判断异常）
        
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
            return {'quantity': 'NORMAL', 'price': 'NORMAL', 'space': 'NORMAL', 'time': 'NORMAL'}
        
        return {
            'quantity': self._analyze_quantity_lite(kline_df),
            'price': self._analyze_price_lite(kline_df),
            'space': self._analyze_space_lite(kline_df, code),
            'time': self._analyze_time_lite(kline_df)
        }
    
    
    def _analyze_quantity_lite(self, kline_df: pd.DataFrame) -> str:
        """
        简化版量能分析
        
        异常特征：
        - 量比 > 2.5 倍（最近3分钟 vs 前7分钟）
        - 量能波动率 > 1.0（识别脉冲）
        """
        volumes = kline_df['volume'].values
        
        # 量比
        recent_avg = volumes[-3:].mean()
        earlier_avg = volumes[:-3].mean()
        volume_ratio = recent_avg / earlier_avg if earlier_avg > 0 else 1.0
        
        # 波动率
        volume_std = volumes.std()
        volume_volatility = volume_std / volumes.mean() if volumes.mean() > 0 else 0
        
        # 判断异常
        if volume_ratio > 2.5 or volume_volatility > 1.0:
            return 'ABNORMAL'
        return 'NORMAL'
    
    
    def _analyze_price_lite(self, kline_df: pd.DataFrame) -> str:
        """
        简化版价格分析
        
        异常特征：
        - 涨幅 > 3%
        - 振幅 > 4%（识别暴力拉升）
        """
        # 涨幅
        price_change = (kline_df['close'].iloc[-1] - kline_df['close'].iloc[0]) / kline_df['close'].iloc[0]
        
        # 振幅
        amplitude = ((kline_df['high'] - kline_df['low']) / kline_df['close']).mean()
        
        # 判断异常
        if price_change > 0.03 or amplitude > 0.04:
            return 'ABNORMAL'
        return 'NORMAL'
    
    
    def _analyze_space_lite(self, kline_df: pd.DataFrame, code: str) -> str:
        """
        简化版换手率分析
        
        异常特征：
        - 10分钟累计换手率 > 2%
        - 或 < 0.3%（过低也异常）
        """
        float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
        if float_shares == 0:
            return 'NORMAL'
        
        total_volume = kline_df['volume'].sum()
        turnover = total_volume / float_shares
        
        # 判断异常
        if turnover > 0.02 or turnover < 0.003:
            return 'ABNORMAL'
        return 'NORMAL'
    
    
    def _analyze_time_lite(self, kline_df: pd.DataFrame) -> str:
        """
        简化版时间持续性分析
        
        异常特征：
        - 尾盘异动（14:30后）
        - 或短时脉冲（只有1-2分钟放量）
        """
        # 检查时间段（假设kline_df有time列）
        if 'time' in kline_df.columns:
            last_time_str = str(kline_df['time'].iloc[-1])
            try:
                last_time = datetime.strptime(last_time_str, '%H:%M:%S').time()
                if last_time >= dt_time(14, 30):
                    return 'ABNORMAL'  # 尾盘异动
            except:
                pass
        
        # 检查持续性
        volumes = kline_df['volume'].values
        avg_vol = volumes.mean()
        surge_minutes = sum(1 for v in volumes[-5:] if v > avg_vol * 1.5)
        
        if surge_minutes <= 2:
            return 'ABNORMAL'  # 短时脉冲
        
        return 'NORMAL'
    
    
    # ========== 完整版QPST（Phase3精筛） ==========
    
    def analyze_full(self, kline_df: pd.DataFrame, code: str) -> dict:
        """
        完整版QPST四维分析
        
        Args:
            kline_df: 分钟K数据（至少20根）
            code: 股票代码
        
        Returns:
            {
                'final_signal': 'STRONG_INFLOW' | 'WEAK_INFLOW' | 'NEUTRAL' | 'TRAP_WARNING',
                'confidence': 0.0-1.0,
                'dimensions': {
                    'quantity': {...},
                    'price': {...},
                    'space': {...},
                    'time': {...}
                },
                'trap_signals': [...],
                'reason': str,
                'timestamp': str
            }
        """
        if len(kline_df) < 20:
            return self._empty_result('数据不足（<20根分钟K）')
        
        # 四维分析
        quantity_dim = self._analyze_quantity_full(kline_df)
        price_dim = self._analyze_price_full(kline_df)
        space_dim = self._analyze_space_full(kline_df, code)
        time_dim = self._analyze_time_full(kline_df)
        
        # 反诱多检测
        trap_signals = self._detect_traps_batch(kline_df, code)
        
        # 综合判断（投票机制）
        final_signal, confidence, reason = self._synthesize_signal(
            quantity_dim, price_dim, space_dim, time_dim, trap_signals
        )
        
        return {
            'code': code,
            'final_signal': final_signal,
            'confidence': confidence,
            'dimensions': {
                'quantity': quantity_dim,
                'price': price_dim,
                'space': space_dim,
                'time': time_dim
            },
            'trap_signals': trap_signals,
            'reason': reason,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
    
    
    def _analyze_quantity_full(self, kline_df: pd.DataFrame) -> dict:
        """
        完整版量能分析
        """
        volumes = kline_df['volume'].values
        
        # 量比（最近5分钟 vs 前15分钟）
        recent_avg = volumes[-5:].mean()
        earlier_avg = volumes[:-5].mean()
        volume_ratio = recent_avg / earlier_avg if earlier_avg > 0 else 1.0
        
        # 量能趋势
        volume_trend = (volumes[-5:].mean() - volumes[:5].mean()) / volumes[:5].mean() if volumes[:5].mean() > 0 else 0
        
        # 波动率
        volume_std = volumes.std()
        volume_volatility = volume_std / volumes.mean() if volumes.mean() > 0 else 0
        
        # 判断信号
        if volume_ratio > 2.5 and volume_trend > 0.2 and volume_volatility < 1.0:
            signal = 'STRONG_VOLUME'  # 持续放量
        elif volume_ratio > 2.0 and volume_volatility > 2.0:
            signal = 'ABNORMAL_SPIKE'  # 单次异常
        elif volume_ratio > 1.5 and volume_trend > 0.1:
            signal = 'MODERATE_VOLUME'  # 温和放量
        elif volume_ratio < 0.8:
            signal = 'SHRINKING_VOLUME'  # 缩量
        else:
            signal = 'NORMAL_VOLUME'
        
        return {
            'volume_ratio': volume_ratio,
            'volume_trend': volume_trend,
            'volume_volatility': volume_volatility,
            'signal': signal
        }
    
    
    def _analyze_price_full(self, kline_df: pd.DataFrame) -> dict:
        """
        完整版价格分析
        """
        # 涨幅
        price_change = (kline_df['close'].iloc[-1] - kline_df['close'].iloc[0]) / kline_df['close'].iloc[0]
        
        # 振幅
        amplitude = ((kline_df['high'] - kline_df['low']) / kline_df['close']).mean()
        
        # 价格动量（最近5分钟 vs 前15分钟）
        recent_avg_price = kline_df['close'].iloc[-5:].mean()
        earlier_avg_price = kline_df['close'].iloc[:-5].mean()
        price_momentum = (recent_avg_price - earlier_avg_price) / earlier_avg_price if earlier_avg_price > 0 else 0
        
        # 判断信号
        if price_change > 0.02 and amplitude < 0.015 and price_momentum > 0.01:
            signal = 'STEADY_RISE'  # 稳步上涨
        elif price_change > 0.03 and amplitude > 0.03:
            signal = 'VIOLENT_RISE'  # 暴力拉升
        elif abs(price_change) < 0.005 and amplitude < 0.01:
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
    
    
    def _analyze_space_full(self, kline_df: pd.DataFrame, code: str) -> dict:
        """
        完整版换手率分析
        """
        float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
        if float_shares == 0:
            return {'signal': 'NO_EQUITY_DATA', 'turnover': 0, 'turnover_trend': 0}
        
        # 计算换手率（分段）
        total_volume = kline_df['volume'].sum()
        recent_volume = kline_df['volume'].iloc[-5:].sum()
        earlier_volume = kline_df['volume'].iloc[:-5].sum()
        
        total_turnover = total_volume / float_shares
        recent_turnover = recent_volume / float_shares
        earlier_turnover = earlier_volume / float_shares
        
        turnover_trend = (recent_turnover - earlier_turnover) / earlier_turnover if earlier_turnover > 0 else 0
        
        # 判断信号
        if total_turnover > 0.02 and turnover_trend > 0.2:
            signal = 'HIGH_TURNOVER_RISING'  # 高换手且上升
        elif 0.01 < total_turnover < 0.02 and abs(turnover_trend) < 0.1:
            signal = 'MODERATE_TURNOVER_STABLE'  # 中等换手且稳定
        elif total_turnover < 0.005:
            signal = 'LOW_TURNOVER'  # 低换手
        else:
            signal = 'NORMAL_TURNOVER'
        
        return {
            'total_turnover': total_turnover,
            'turnover_trend': turnover_trend,
            'signal': signal
        }
    
    
    def _analyze_time_full(self, kline_df: pd.DataFrame) -> dict:
        """
        完整版时间持续性分析
        """
        volumes = kline_df['volume'].values
        avg_vol = volumes.mean()
        
        # 计算持续放量的分钟数
        surge_minutes = sum(1 for v in volumes[-10:] if v > avg_vol * 1.5)
        surge_duration = surge_minutes / 10
        
        # 时间段判断
        time_period = 'NORMAL_TRADING'
        if 'time' in kline_df.columns:
            last_time_str = str(kline_df['time'].iloc[-1])
            try:
                last_time = datetime.strptime(last_time_str, '%H:%M:%S').time()
                if last_time < dt_time(9, 45):
                    time_period = 'MORNING_OPEN'
                elif last_time >= dt_time(14, 30):
                    time_period = 'AFTERNOON_CLOSE'
            except:
                pass
        
        # 判断信号
        if surge_duration > 0.7 and time_period == 'NORMAL_TRADING':
            signal = 'SUSTAINED_ACTIVITY'  # 持续异动
        elif surge_duration < 0.3 and time_period == 'AFTERNOON_CLOSE':
            signal = 'TAIL_SURGE'  # 尾盘拉升
        elif surge_duration > 0.5:
            signal = 'MODERATE_ACTIVITY'  # 温和活跃
        else:
            signal = 'SHORT_SPIKE'  # 短暂脉冲
        
        return {
            'surge_duration': surge_duration,
            'time_period': time_period,
            'signal': signal
        }
    
    
    def _detect_traps_batch(self, kline_df: pd.DataFrame, code: str) -> List[str]:
        """
        反诱多检测（批量版）
        
        检测：
        1. 放量滞涨（价格不涨但成交量大）
        2. 尾盘拉升（14:30后异动）
        3. 振幅异常（单根分钟K振幅>5%）
        """
        trap_signals = []
        
        # 检测1：放量滞涨
        volumes = kline_df['volume'].values
        prices = kline_df['close'].values
        
        volume_change = (volumes[-5:].mean() - volumes[:-5].mean()) / volumes[:-5].mean() if volumes[:-5].mean() > 0 else 0
        price_change = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
        
        if volume_change > 0.5 and price_change < 0.01:
            trap_signals.append('放量滞涨：成交量大增但价格不涨')
        
        # 检测2：尾盘拉升
        if 'time' in kline_df.columns:
            last_time_str = str(kline_df['time'].iloc[-1])
            try:
                last_time = datetime.strptime(last_time_str, '%H:%M:%S').time()
                if last_time >= dt_time(14, 30):
                    recent_volumes = volumes[-5:]
                    earlier_volumes = volumes[-10:-5]
                    if recent_volumes.mean() > earlier_volumes.mean() * 2:
                        trap_signals.append('尾盘拉升：警惕次日低开')
            except:
                pass
        
        # 检测3：振幅异常（单根K线振幅>5%）
        amplitudes = ((kline_df['high'] - kline_df['low']) / kline_df['close']).values
        max_amplitude = amplitudes.max()
        if max_amplitude > 0.05:
            trap_signals.append(f'振幅异常：单根分钟K振幅{max_amplitude:.1%}')
        
        return trap_signals
    
    
    def _synthesize_signal(self, quantity_dim: dict, price_dim: dict, 
                          space_dim: dict, time_dim: dict, 
                          trap_signals: List[str]) -> Tuple[str, float, str]:
        """
        综合判断（投票机制）
        
        规则：
        1. 有诱多信号 → TRAP_WARNING
        2. 4维符合 → STRONG_INFLOW
        3. 3维符合 → WEAK_INFLOW
        4. 其他 → NEUTRAL
        """
        # 优先级1：诱多检测
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
        
        # 投票
        vote_count = len(positive_signals)
        
        if vote_count >= 4:
            return 'STRONG_INFLOW', 0.85, f"机构吸筹特征明显（{'+'.join(positive_signals)}）"
        elif vote_count == 3:
            return 'WEAK_INFLOW', 0.65, f"温和流入（{'+'.join(positive_signals)}）"
        elif vote_count == 2:
            return 'NEUTRAL', 0.4, f"部分维度符合（{'+'.join(positive_signals)}）"
        else:
            # 检查出货信号
            if quantity_dim['signal'] == 'SHRINKING_VOLUME' and price_dim['signal'] == 'DECLINE':
                return 'STRONG_OUTFLOW', 0.75, "缩量下跌，资金流出"
            return 'NEUTRAL', 0.3, "无明显特征"
    
    
    def _empty_result(self, reason: str) -> dict:
        """空结果"""
        return {
            'final_signal': 'NEUTRAL',
            'confidence': 0.0,
            'dimensions': {},
            'trap_signals': [],
            'reason': reason,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
