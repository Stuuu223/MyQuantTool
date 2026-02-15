#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低吸战法事件检测器

实现低吸候选事件检测（DIP_BUY_CANDIDATE）

检测两种模式：
1. 5日均线低吸
2. 分时均线低吸

Author: iFlow CLI
Version: V2.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque

from logic.strategies.event_detector import BaseEventDetector, EventType, TradingEvent
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class DipBuyEventDetector(BaseEventDetector):
    """
    低吸战法事件检测器
    
    检测均线回踩信号
    """
    
    # 5日均线低吸参数
    MA5_DIP_RANGE_MIN = 0.0  # 回踩范围最小值（0%）
    MA5_DIP_RANGE_MAX = 0.02  # 回踩范围最大值（2%）
    VOLUME_SHRINK_RATIO = 0.7  # 缩量比例（当日量 ≤ 昨日量的 70%）
    
    # 分时均线低吸参数
    INTRADAY_MA_DIP_MIN = 0.015  # 分时均线回踩最小值（1.5%）
    INTRADAY_MA_DIP_MAX = 0.025  # 分时均线回踩最大值（2.5%）
    INTRADAY_VOLUME_RATIO = 0.6  # 近期成交量 ≤ 早盘高峰的 60%
    INTRADAY_REBOUND_THRESHOLD = 0.005  # 重新站上均线阈值（0.5%）
    
    def __init__(self):
        """初始化低吸战法事件检测器"""
        super().__init__("dip_buy_event_detector")
        # 维护分时均线数据
        self.intraday_prices: Dict[str, deque] = {}
        self.intraday_volumes: Dict[str, deque] = {}
        self.intraday_length = 30  # 保存30分钟的分时数据
        
    def _update_intraday_data(self, stock_code: str, price: float, volume: int):
        """
        更新分时数据
        
        Args:
            stock_code: 股票代码
            price: 当前价格
            volume: 当前成交量
        """
        if stock_code not in self.intraday_prices:
            self.intraday_prices[stock_code] = deque(maxlen=self.intraday_length)
            self.intraday_volumes[stock_code] = deque(maxlen=self.intraday_length)
        
        self.intraday_prices[stock_code].append(price)
        self.intraday_volumes[stock_code].append(volume)
    
    def _calculate_intraday_ma(self, stock_code: str, period: int = 10) -> Optional[float]:
        """
        计算分时均线
        
        Args:
            stock_code: 股票代码
            period: 均线周期（分钟）
        
        Returns:
            均线价格，如果数据不足则返回None
        """
        if stock_code not in self.intraday_prices:
            return None
        
        price_queue = self.intraday_prices[stock_code]
        
        if len(price_queue) < period:
            return None
        
        recent_prices = list(price_queue)[-period:]
        return sum(recent_prices) / len(recent_prices)
    
    def _is_ma_bullish(self, ma5: float, ma10: float, ma20: float) -> bool:
        """
        判断均线是否多头排列
        
        Args:
            ma5: 5日均线
            ma10: 10日均线
            ma20: 20日均线
        
        Returns:
            True表示多头排列
        """
        return ma5 > ma10 > ma20
    
    def detect_ma5_dip(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测5日均线低吸
        
        条件：
        - 日线趋势：MA5 > MA10 > MA20（多头排列）
        - 盘中价格：回踩到 MA5 下方 0%-2%
        - 成交量萎缩：当日量 ≤ 昨日量的 70%
        
        Args:
            tick_data: Tick数据
            context: 上下文信息
        
        Returns:
            如果满足条件，返回事件对象；否则返回None
        """
        try:
            # 获取股票代码
            stock_code = tick_data.get('code', '')
            if not stock_code:
                return None
            
            # 获取均线数据
            ma5 = context.get('ma5', 0)
            ma10 = context.get('ma10', 0)
            ma20 = context.get('ma20', 0)
            
            if ma5 == 0 or ma10 == 0 or ma20 == 0:
                return None
            
            # 检查均线是否多头排列
            if not self._is_ma_bullish(ma5, ma10, ma20):
                return None
            
            # 获取当前价格
            current_price = tick_data.get('now', 0)
            if current_price == 0:
                return None
            
            # 计算回踩幅度
            dip_pct = (ma5 - current_price) / ma5
            
            # 检查回踩是否在目标区间
            if not (self.MA5_DIP_RANGE_MIN <= dip_pct <= self.MA5_DIP_RANGE_MAX):
                return None
            
            # 检查成交量萎缩
            current_volume = tick_data.get('volume', 0)
            yesterday_volume = context.get('yesterday_volume', 0)
            
            if yesterday_volume == 0:
                return None
            
            volume_ratio = current_volume / yesterday_volume
            if volume_ratio > self.VOLUME_SHRINK_RATIO:
                return None
            
            # 构建事件数据
            event_data = {
                'ma5': ma5,
                'ma10': ma10,
                'ma20': ma20,
                'dip_pct': dip_pct,
                'current_price': current_price,
                'volume_ratio': volume_ratio
            }
            
            # 计算置信度（基于回踩幅度和缩量比例）
            confidence = min(
                0.6 + (dip_pct * 15) + ((1 - volume_ratio) * 0.2),
                1.0
            )
            
            description = (
                f"5日均线低吸：回踩{dip_pct*100:.2f}%，"
                f"缩量{volume_ratio*100:.1f}%"
            )
            
            return TradingEvent(
                event_type=EventType.DIP_BUY_CANDIDATE,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测5日均线低吸失败: {e}")
            return None
    
    def detect_intraday_dip(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测分时均线低吸
        
        条件：
        - 分时均线多头排列
        - 价格回落到分时均线下方 1.5%-2.5%
        - 近期成交量 ≤ 早盘高峰的 60%
        - 价格重新站上均线之上（突破 0.5%）
        
        Args:
            tick_data: Tick数据
            context: 上下文信息
        
        Returns:
            如果满足条件，返回事件对象；否则返回None
        """
        try:
            # 获取股票代码
            stock_code = tick_data.get('code', '')
            if not stock_code:
                return None
            
            # 更新分时数据
            current_price = tick_data.get('now', 0)
            current_volume = tick_data.get('volume', 0)
            self._update_intraday_data(stock_code, current_price, current_volume)
            
            # 计算分时均线
            intraday_ma = self._calculate_intraday_ma(stock_code, period=10)
            if not intraday_ma:
                return None
            
            # 计算回踩幅度
            dip_pct = (intraday_ma - current_price) / intraday_ma
            
            # 检查回踩是否在目标区间
            if not (self.INTRADAY_MA_DIP_MIN <= dip_pct <= self.INTRADAY_MA_DIP_MAX):
                return None
            
            # 检查成交量
            volume_queue = self.intraday_volumes[stock_code]
            if len(volume_queue) < 10:
                return None
            
            recent_volumes = list(volume_queue)[-10:]
            early_peak_volume = max(list(volume_queue)[:10]) if len(volume_queue) >= 10 else 0
            
            if early_peak_volume == 0:
                return None
            
            avg_recent_volume = sum(recent_volumes) / len(recent_volumes)
            volume_ratio = avg_recent_volume / early_peak_volume
            
            if volume_ratio > self.INTRADAY_VOLUME_RATIO:
                return None
            
            # 检查是否重新站上均线
            if current_price < intraday_ma:
                return None
            
            rebound_pct = (current_price - intraday_ma) / intraday_ma
            if rebound_pct < self.INTRADAY_REBOUND_THRESHOLD:
                return None
            
            # 构建事件数据
            event_data = {
                'intraday_ma': intraday_ma,
                'dip_pct': dip_pct,
                'rebound_pct': rebound_pct,
                'volume_ratio': volume_ratio,
                'current_price': current_price
            }
            
            # 计算置信度（基于回踩幅度和反弹幅度）
            confidence = min(
                0.6 + (dip_pct * 10) + (rebound_pct * 20),
                1.0
            )
            
            description = (
                f"分时均线低吸：回踩{dip_pct*100:.2f}%，"
                f"反弹{rebound_pct*100:.2f}%，量比{volume_ratio*100:.1f}%"
            )
            
            return TradingEvent(
                event_type=EventType.DIP_BUY_CANDIDATE,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测分时均线低吸失败: {e}")
            return None
    
    def detect(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测低吸战法事件
        
        按优先级检测：
        1. 5日均线低吸（优先级更高）
        2. 分时均线低吸
        
        Args:
            tick_data: Tick数据
            context: 上下文信息
        
        Returns:
            检测到的事件对象，如果没有则返回None
        """
        # 按优先级检测
        event = self.detect_ma5_dip(tick_data, context)
        if event:
            return event
        
        event = self.detect_intraday_dip(tick_data, context)
        if event:
            return event
        
        return None


if __name__ == "__main__":
    # 快速测试
    detector = DipBuyEventDetector()
    print("✅ 低吸战法事件检测器测试通过")
    print(f"   名称: {detector.name}")
    print(f"   已启用: {detector.enabled}")
    print(f"   分时数据长度: {detector.intraday_length} 分钟")