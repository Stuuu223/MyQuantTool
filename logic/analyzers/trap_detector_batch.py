#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量反诱多检测器

针对分钟K数据优化的诱多陷阱检测器：
- 对倒识别
- 尾盘拉升
- 连板开板
- 放量滞涨

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class TrapDetectorBatch:
    """
    批量反诱多检测器
    
    四大检测规则：
    1. 对倒识别：成交量异常但价格波动小
    2. 尾盘拉升：14:30后突然异动
    3. 连板开板：涨停后首次开板
    4. 放量滞涨：放量但价格不涨
    """
    
    def __init__(self):
        logger.info("✅ TrapDetectorBatch 初始化完成")
    
    def detect(self, code: str, kline_df: pd.DataFrame, 
               qpst_result: Dict) -> List[str]:
        """
        检测诱多陷阱
        
        Args:
            code: 股票代码
            kline_df: 分钟K数据
            qpst_result: QPST四维分析结果
        
        Returns:
            诱多信号列表（如 ['对倒嫌疑', '尾盘拉升']）
        """
        trap_signals = []
        
        if len(kline_df) < 10:
            return trap_signals
        
        # 检测1: 对倒识别
        if self._detect_wash_trading(kline_df, qpst_result):
            trap_signals.append('对倒嫌疑：成交量异常但价格波动小')
        
        # 检测2: 尾盘拉升
        if self._detect_tail_pump(kline_df):
            trap_signals.append('尾盘拉升：警惕次日低开')
        
        # 检测3: 连板开板（需要日线数据，这里简化处理）
        # 由于分钟K难以判断，此功能暂时保留为占位符
        
        # 检测4: 放量滞涨
        if self._detect_volume_stagnation(kline_df, qpst_result):
            trap_signals.append('放量滞涨：资金流出迹象')
        
        return trap_signals
    
    def _detect_wash_trading(self, df: pd.DataFrame, 
                             qpst_result: Dict) -> bool:
        """
        检测1: 对倒识别
        
        特征:
        - 成交量异常放大（>3倍）
        - 价格波动很小（<1%）
        - 振幅小（<1.5%）
        """
        quantity_metrics = qpst_result.get('quantity', {}).get('metrics', {})
        price_metrics = qpst_result.get('price', {}).get('metrics', {})
        
        volume_surge = quantity_metrics.get('volume_surge', 0)
        price_change = abs(price_metrics.get('price_change', 0))
        amplitude = price_metrics.get('amplitude', 0)
        
        # 判断逻辑
        if volume_surge > 3.0 and price_change < 0.01 and amplitude < 0.015:
            return True
        
        return False
    
    def _detect_tail_pump(self, df: pd.DataFrame) -> bool:
        """
        检测2: 尾盘拉升
        
        特征:
        - 时间在14:30之后
        - 最近3分钟成交量突然放大（>2倍）
        - 价格快速上涨（>1.5%）
        """
        try:
            # 检查时间
            last_time = pd.to_datetime(df['time'].iloc[-1])
            if last_time.hour < 14 or (last_time.hour == 14 and last_time.minute < 30):
                return False
            
            # 检查成交量
            volumes = df['volume'].values
            if len(volumes) < 10:
                return False
            
            recent_avg = volumes[-3:].mean()
            earlier_avg = volumes[-10:-3].mean()
            volume_ratio = recent_avg / earlier_avg if earlier_avg > 0 else 0
            
            # 检查价格涨幅
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-3]) / df['close'].iloc[-3]
            
            # 判断逻辑
            if volume_ratio > 2.0 and price_change > 0.015:
                return True
        
        except Exception as e:
            logger.debug(f"尾盘拉升检测失败 {e}")
        
        return False
    
    def _detect_volume_stagnation(self, df: pd.DataFrame, 
                                  qpst_result: Dict) -> bool:
        """
        检测4: 放量滞涨
        
        特征:
        - 成交量放大（>1.8倍）
        - 价格涨幅很小（<0.5%）
        - 持续3根K线以上
        """
        quantity_signal = qpst_result.get('quantity', {}).get('signal', '')
        price_metrics = qpst_result.get('price', {}).get('metrics', {})
        
        price_change = price_metrics.get('price_change', 0)
        
        # 判断逻辑
        if quantity_signal in ['STRONG_VOLUME', 'MODERATE_VOLUME'] and price_change < 0.005:
            # 额外检查：是否持续3根K线
            volumes = df['volume'].values
            prices = df['close'].values
            
            if len(volumes) >= 5 and len(prices) >= 5:
                avg_vol = volumes[:-3].mean()
                recent_surge_count = sum(1 for v in volumes[-3:] if v > avg_vol * 1.5)
                
                price_change_3min = (prices[-1] - prices[-4]) / prices[-4] if prices[-4] > 0 else 0
                
                if recent_surge_count >= 2 and abs(price_change_3min) < 0.008:
                    return True
        
        return False
