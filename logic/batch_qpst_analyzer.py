#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量四维分析器（QPST分钟K版本）

针对全市场批量扫描优化的四维分析算法
- 输入：分钟K数据（DataFrame）
- 输出：四维信号 + 置信度

与阶段1的区别：
- 阶段1：基于实时Tick数据，适合单股票监控
- 阶段2：基于分钟K数据，适合批量扫描

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2 (批量扫描版)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import statistics
from datetime import datetime

from logic.logger import get_logger

logger = get_logger(__name__)


class BatchQPSTAnalyzer:
    """
    批量四维分析器（分钟K版本）
    
    QPST框架：
    - Quantity: 成交量脉冲分析
    - Price: 价格走势形态
    - Space: 换手率/流通性
    - Time: 持续时间验证
    """
    
    def __init__(self, equity_info: dict):
        """
        初始化批量分析器
        
        Args:
            equity_info: 股本信息字典 {code: {float_shares: xxx, ...}}
        """
        self.equity_info = equity_info
        logger.debug(f"BatchQPSTAnalyzer 初始化完成，加载 {len(equity_info)} 只股票股本信息")
    
    def analyze(self, code: str, kline_df: pd.DataFrame) -> dict:
        """
        执行完整QPST四维分析
        
        Args:
            code: 股票代码
            kline_df: 分钟K数据（至少10根K线）
                     列：time, open, high, low, close, volume, amount
        
        Returns:
            {
                'code': str,
                'final_signal': 'STRONG_INFLOW' | 'WEAK_INFLOW' | 'NEUTRAL' | 'TRAP_WARNING',
                'confidence': float,
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
        if len(kline_df) < 10:
            return self._empty_result(code, '数据不足（需要至少10根K线）')
        
        # ===== 维度1：成交量分析 =====
        quantity_dim = self._analyze_quantity(kline_df)
        
        # ===== 维度2：价格分析 =====
        price_dim = self._analyze_price(kline_df)
        
        # ===== 维度3：换手率分析 =====
        space_dim = self._analyze_space(kline_df, code)
        
        # ===== 维度4：时间持续性分析 =====
        time_dim = self._analyze_time(kline_df)
        
        # ===== 反诱多检测 =====
        trap_signals = self._detect_traps(kline_df, code)
        
        # ===== 综合判断（投票机制） =====
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
    
    def _analyze_quantity(self, df: pd.DataFrame) -> dict:
        """
        维度1：成交量分析
        
        检测：
        - 成交量脉冲（突然放量）
        - 成交量趋势（持续放量 vs 单次放量）
        - 量能波动率（剔除单次异常）
        """
        volumes = df['volume'].values
        
        # 当前量比（最近3分钟 vs 前7分钟）
        if len(volumes) >= 10:
            recent_avg = volumes[-3:].mean()
            earlier_avg = volumes[:-3].mean()
            volume_ratio = recent_avg / earlier_avg if earlier_avg > 0 else 1.0
        else:
            volume_ratio = 1.0
        
        # 量能趋势（最近5分钟 vs 前5分钟）
        if len(volumes) >= 10:
            recent_5min = volumes[-5:].mean()
            earlier_5min = volumes[-10:-5].mean()
            volume_trend = (recent_5min - earlier_5min) / earlier_5min if earlier_5min > 0 else 0
        else:
            volume_trend = 0
        
        # 量能波动率（标准差/均值）
        volume_std = volumes.std()
        volume_mean = volumes.mean()
        volume_volatility = volume_std / volume_mean if volume_mean > 0 else 0
        
        # 信号判断
        if volume_ratio > 2.0 and volume_trend > 0.2 and volume_volatility < 0.8:
            signal = 'STRONG_VOLUME'  # 持续放量（机构特征）
        elif volume_ratio > 3.0 and volume_volatility > 1.5:
            signal = 'ABNORMAL_SPIKE'  # 单次异常（可能对倒）
        elif volume_ratio > 1.5:
            signal = 'MODERATE_VOLUME'  # 温和放量
        elif volume_ratio < 0.8:
            signal = 'SHRINKING_VOLUME'  # 缩量
        else:
            signal = 'NORMAL_VOLUME'
        
        return {
            'volume_ratio': round(volume_ratio, 2),
            'volume_trend': round(volume_trend, 2),
            'volume_volatility': round(volume_volatility, 2),
            'signal': signal
        }
    
    def _analyze_price(self, df: pd.DataFrame) -> dict:
        """
        维度2：价格分析
        
        检测：
        - 价格走势（上涨/下跌/横盘）
        - 价格波动率（急涨急跌 vs 稳步上涨）
        - 量价配合（放量上涨 vs 放量横盘）
        """
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # 价格涨幅（期间涨幅）
        price_change = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
        
        # 平均振幅（识别暴力拉升）
        amplitudes = (highs - lows) / closes
        avg_amplitude = amplitudes.mean()
        
        # 价格动量（最近5分钟 vs 前5分钟）
        if len(closes) >= 10:
            recent_avg_price = closes[-5:].mean()
            earlier_avg_price = closes[-10:-5].mean()
            price_momentum = (recent_avg_price - earlier_avg_price) / earlier_avg_price if earlier_avg_price > 0 else 0
        else:
            price_momentum = 0
        
        # 信号判断
        if price_change > 0.02 and avg_amplitude < 0.015 and price_momentum > 0.01:
            signal = 'STEADY_RISE'  # 稳步上涨（机构特征）
        elif price_change > 0.03 and avg_amplitude > 0.03:
            signal = 'VIOLENT_RISE'  # 暴力拉升（散户追涨）
        elif abs(price_change) < 0.005 and avg_amplitude < 0.01:
            signal = 'SIDEWAYS'  # 横盘整理
        elif price_change < -0.02:
            signal = 'DECLINE'  # 下跌
        else:
            signal = 'NORMAL_FLUCTUATION'
        
        return {
            'price_change': round(price_change, 4),
            'avg_amplitude': round(avg_amplitude, 4),
            'price_momentum': round(price_momentum, 4),
            'signal': signal
        }
    
    def _analyze_space(self, df: pd.DataFrame, code: str) -> dict:
        """
        维度3：换手率分析
        
        检测：
        - 期间换手率（10分钟累计）
        - 换手率趋势（逐步放大 vs 逐步缩小）
        """
        # 获取流通股本
        float_shares = self.equity_info.get(code, {}).get('float_shares', 0)
        
        if float_shares == 0:
            return {'signal': 'NO_EQUITY_DATA', 'turnover': 0, 'trend': 0}
        
        # 计算期间总换手率
        total_volume = df['volume'].sum()
        turnover = total_volume / float_shares
        
        # 换手率趋势（最近5分钟 vs 前5分钟）
        if len(df) >= 10:
            recent_turnover = df['volume'].iloc[-5:].sum() / float_shares
            earlier_turnover = df['volume'].iloc[-10:-5].sum() / float_shares
            turnover_trend = (recent_turnover - earlier_turnover) / earlier_turnover if earlier_turnover > 0 else 0
        else:
            turnover_trend = 0
        
        # 信号判断（10分钟换手率）
        if turnover > 0.02 and turnover_trend > 0.2:
            signal = 'HIGH_TURNOVER_RISING'  # 高换手且上升
        elif 0.005 < turnover < 0.015 and abs(turnover_trend) < 0.1:
            signal = 'MODERATE_TURNOVER_STABLE'  # 中等换手且稳定（可能吸筹）
        elif turnover < 0.003:
            signal = 'LOW_TURNOVER'  # 低换手（冷门）
        else:
            signal = 'NORMAL_TURNOVER'
        
        return {
            'turnover': round(turnover, 4),
            'turnover_trend': round(turnover_trend, 2),
            'signal': signal
        }
    
    def _analyze_time(self, df: pd.DataFrame) -> dict:
        """
        维度4：时间持续性分析
        
        检测：
        - 异动持续时间（3秒冲高 vs 持续10分钟）
        - 时段特征（早盘 vs 尾盘）
        """
        volumes = df['volume'].values
        avg_vol = volumes.mean()
        
        # 计算持续放量的分钟数
        surge_minutes = sum(1 for v in volumes[-5:] if v > avg_vol * 1.5)
        surge_ratio = surge_minutes / 5 if len(volumes) >= 5 else 0
        
        # 时间段判断
        if 'time' in df.columns:
            last_time = df['time'].iloc[-1]
            if isinstance(last_time, str):
                current_hour = int(last_time.split(':')[0])
                current_minute = int(last_time.split(':')[1])
            else:
                current_hour = last_time.hour
                current_minute = last_time.minute
            
            if current_hour == 9 and current_minute < 45:
                time_period = 'MORNING_OPEN'  # 早盘开盘
            elif current_hour == 14 and current_minute >= 30:
                time_period = 'AFTERNOON_CLOSE'  # 尾盘
            else:
                time_period = 'NORMAL_TRADING'  # 正常交易时段
        else:
            time_period = 'UNKNOWN'
        
        # 信号判断
        if surge_ratio > 0.6 and time_period == 'NORMAL_TRADING':
            signal = 'SUSTAINED_ACTIVITY'  # 持续异动（真实）
        elif surge_ratio < 0.3 and time_period == 'AFTERNOON_CLOSE':
            signal = 'TAIL_SURGE'  # 尾盘拉升（警惕诱多）
        elif surge_ratio > 0.4:
            signal = 'MODERATE_ACTIVITY'
        else:
            signal = 'SHORT_SPIKE'  # 短暂脉冲
        
        return {
            'surge_ratio': round(surge_ratio, 2),
            'time_period': time_period,
            'signal': signal
        }
    
    def _detect_traps(self, df: pd.DataFrame, code: str) -> List[str]:
        """
        反诱多检测层
        
        检测：
        1. 对倒识别：成交量暴增但价格横盘
        2. 尾盘拉升：14:30后突然异动
        3. 连板开板：涨停后首次开板
        4. 单边挂单：买盘或卖盘长时间为0（分钟K无法检测，跳过）
        """
        trap_signals = []
        
        volumes = df['volume'].values
        closes = df['close'].values
        
        # 检测1：对倒识别（放量横盘）
        if len(volumes) >= 5:
            recent_vol_avg = volumes[-3:].mean()
            earlier_vol_avg = volumes[:-3].mean()
            volume_surge = recent_vol_avg / earlier_vol_avg if earlier_vol_avg > 0 else 1.0
            
            price_change = abs((closes[-1] - closes[-3]) / closes[-3]) if closes[-3] > 0 else 0
            
            if volume_surge > 3.0 and price_change < 0.005:  # 放量3倍但涨幅<0.5%
                trap_signals.append('对倒嫌疑：成交量异常但价格横盘')
        
        # 检测2：尾盘拉升
        if 'time' in df.columns:
            last_time = df['time'].iloc[-1]
            if isinstance(last_time, str):
                current_hour = int(last_time.split(':')[0])
                current_minute = int(last_time.split(':')[1])
            else:
                current_hour = last_time.hour
                current_minute = last_time.minute
            
            if current_hour == 14 and current_minute >= 30:
                # 检查最近5分钟是否突然放量
                if len(volumes) >= 10:
                    recent_vols = volumes[-5:]
                    earlier_vols = volumes[-10:-5]
                    
                    recent_avg = recent_vols.mean()
                    earlier_avg = earlier_vols.mean()
                    
                    if recent_avg > earlier_avg * 2:
                        trap_signals.append('尾盘拉升：警惕次日低开')
        
        # 检测3：连板开板（需要多日数据，这里简化处理）
        # 如果今日涨幅>9%但收盘涨幅<9%，可能是涨停开板
        if len(closes) >= 10:
            max_price = df['high'].max()
            open_price = closes[0]
            close_price = closes[-1]
            
            max_change = (max_price - open_price) / open_price if open_price > 0 else 0
            close_change = (close_price - open_price) / open_price if open_price > 0 else 0
            
            if max_change > 0.095 and close_change < 0.08:
                trap_signals.append('疑似涨停开板：可能是主力出货')
        
        return trap_signals
    
    def _synthesize_signal(self, quantity_dim: dict, price_dim: dict, 
                          space_dim: dict, time_dim: dict, 
                          trap_signals: List[str]) -> tuple:
        """
        综合判断（多维度投票机制）
        
        规则：
        1. 如果有诱多信号 → 直接返回 TRAP_WARNING
        2. 四个维度同时符合 → STRONG_INFLOW（高置信度）
        3. 3个维度符合 → WEAK_INFLOW（中置信度）
        4. 2个及以下 → NEUTRAL（低置信度）
        """
        # 优先级1：诱多检测
        if trap_signals:
            return 'TRAP_WARNING', 0.9, f"诱多预警: {'; '.join(trap_signals)}"
        
        # 统计各维度的正面信号
        positive_signals = []
        
        # 成交量维度
        if quantity_dim['signal'] in ['STRONG_VOLUME', 'MODERATE_VOLUME']:
            positive_signals.append('量能')
        
        # 价格维度
        if price_dim['signal'] in ['STEADY_RISE']:
            positive_signals.append('价格')
        
        # 换手率维度
        if space_dim['signal'] in ['MODERATE_TURNOVER_STABLE', 'HIGH_TURNOVER_RISING']:
            positive_signals.append('换手')
        
        # 时间维度
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
    
    def _empty_result(self, code: str, reason: str) -> dict:
        """空结果"""
        return {
            'code': code,
            'final_signal': 'NEUTRAL',
            'confidence': 0.0,
            'dimensions': {},
            'trap_signals': [],
            'reason': reason,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
