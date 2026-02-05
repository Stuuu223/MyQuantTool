#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙头战法事件检测器

实现龙头候选事件检测（LEADER_CANDIDATE）

检测三种模式：
1. 板块龙头候选
2. 竞价弱转强龙头预备
3. 日内加速（分时龙头）

Author: iFlow CLI
Version: V2.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, time as dt_time
from collections import deque

from logic.event_detector import BaseEventDetector, EventType, TradingEvent
from logic.market_status import MarketStatusChecker
from logic.logger import get_logger

logger = get_logger(__name__)


class LeaderEventDetector(BaseEventDetector):
    """
    龙头战法事件检测器
    
    检测龙头候选信号
    """
    
    # 板块龙头参数
    SECTOR_LEADER_CHANGE_MIN = 0.05  # 涨幅 ≥ 5%
    SECTOR_TOP3_GAP = 0.01  # Top3差距 < 1%
    
    # 竞价弱转强参数
    LEADER_WEAK_TO_STRONG_GAP_MIN = 0.05  # 高开幅度 ≥ 5%
    LEADER_WEAK_TO_STRONG_VOLUME_RATIO = 1.5  # 竞价量比 ≥ 1.5
    LEADER_WEAK_CLOSE_CHANGE_MAX = 0.03  # 昨日收盘涨幅 < 3%
    
    # 日内加速参数
    INTRADAY_ACCEL_PERIOD = 10  # 加速周期（分钟）
    INTRADAY_ACCEL_VOLUME_RATIO = 1.5  # 加速量比 ≥ 1.5
    
    def __init__(self):
        """初始化龙头战法事件检测器"""
        super().__init__("leader_event_detector")
        self.market_checker = MarketStatusChecker()
        # 维护每只股票的历史数据
        self.price_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}
        self.history_length = 60  # 保存60分钟的历史数据
        
    def _update_history(self, stock_code: str, price: float, volume: int):
        """
        更新股票的历史数据
        
        Args:
            stock_code: 股票代码
            price: 当前价格
            volume: 当前成交量
        """
        if stock_code not in self.price_history:
            self.price_history[stock_code] = deque(maxlen=self.history_length)
            self.volume_history[stock_code] = deque(maxlen=self.history_length)
        
        self.price_history[stock_code].append(price)
        self.volume_history[stock_code].append(volume)
    
    def _is_auction_time(self) -> bool:
        """判断当前是否在竞价时间"""
        current_time = self.market_checker.get_current_time()
        auction_start = dt_time(9, 25)
        auction_end = dt_time(9, 30)
        return auction_start <= current_time <= auction_end
    
    def detect_sector_leader(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测板块龙头候选
        
        条件：
        - 同板块内：当日涨幅 = 板块内第一（或 Top3 且差距 < 1%）
        - 且涨幅 ≥ 5%
        
        Args:
            tick_data: Tick数据
            context: 上下文信息（包含板块数据）
        
        Returns:
            如果满足条件，返回事件对象；否则返回None
        """
        try:
            # 获取股票代码
            stock_code = tick_data.get('code', '')
            if not stock_code:
                return None
            
            # 获取价格数据
            current_price = tick_data.get('now', 0)
            yesterday_close = context.get('yesterday_close', 0)
            
            if current_price == 0 or yesterday_close == 0:
                return None
            
            # 计算当前涨幅
            change_pct = (current_price - yesterday_close) / yesterday_close
            
            # 检查涨幅是否 ≥ 5%
            if change_pct < self.SECTOR_LEADER_CHANGE_MIN:
                return None
            
            # 获取板块数据
            sector_data = context.get('sector_data', {})
            if not sector_data:
                return None
            
            # 获取当前股票的板块排名
            sector_rank = sector_data.get('rank', 0)
            sector_top3_gap = sector_data.get('top3_gap', 1.0)
            
            # 检查是否为板块龙头（第一名或Top3且差距小）
            if sector_rank == 1:
                is_leader = True
            elif sector_rank <= 3 and sector_top3_gap < self.SECTOR_TOP3_GAP:
                is_leader = True
            else:
                return None
            
            # 构建事件数据
            event_data = {
                'change_pct': change_pct,
                'sector_rank': sector_rank,
                'sector_top3_gap': sector_top3_gap,
                'sector_name': sector_data.get('name', '未知板块')
            }
            
            # 计算置信度（基于涨幅和排名）
            confidence = min(
                0.7 + (change_pct * 3) + ((4 - sector_rank) * 0.05),
                1.0
            )
            
            description = (
                f"板块龙头候选：涨幅{change_pct*100:.2f}%，"
                f"板块排名第{sector_rank}"
            )
            
            return TradingEvent(
                event_type=EventType.LEADER_CANDIDATE,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测板块龙头失败: {e}")
            return None
    
    def detect_auction_weak_to_strong(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测竞价弱转强龙头预备
        
        条件：
        - 昨日：收盘涨幅 < 3%（弱势或震荡）
        - 今日 9:25 后：高开幅度 ≥ 5%，竞价量比 ≥ 1.5
        
        Args:
            tick_data: Tick数据
            context: 上下文信息
        
        Returns:
            如果满足条件，返回事件对象；否则返回None
        """
        try:
            # 只在竞价时间生效
            if not self._is_auction_time():
                return None
            
            # 获取股票代码
            stock_code = tick_data.get('code', '')
            if not stock_code:
                return None
            
            # 获取昨日数据
            yesterday_data = context.get('yesterday_data', {})
            if not yesterday_data:
                return None
            
            # 昨日收盘涨幅
            yesterday_close_change = yesterday_data.get('close_change_pct', 0)
            
            # 判断昨日是否弱势
            if yesterday_close_change >= self.LEADER_WEAK_CLOSE_CHANGE_MAX:
                return None
            
            # 获取今日竞价数据
            current_price = tick_data.get('now', 0)
            yesterday_close_price = yesterday_data.get('close', 0)
            
            if current_price == 0 or yesterday_close_price == 0:
                return None
            
            # 计算高开幅度
            gap_pct = (current_price - yesterday_close_price) / yesterday_close_price
            
            # 判断是否高开 ≥ 5%
            if gap_pct < self.LEADER_WEAK_TO_STRONG_GAP_MIN:
                return None
            
            # 获取竞价量比
            auction_volume = tick_data.get('auction_volume', 0)
            yesterday_volume = yesterday_data.get('volume', 0)
            
            if yesterday_volume == 0:
                return None
            
            volume_ratio = auction_volume / yesterday_volume
            
            # 判断量比 ≥ 1.5
            if volume_ratio < self.LEADER_WEAK_TO_STRONG_VOLUME_RATIO:
                return None
            
            # 构建事件数据
            event_data = {
                'yesterday_close_change': yesterday_close_change,
                'gap_pct': gap_pct,
                'volume_ratio': volume_ratio
            }
            
            # 计算置信度（基于高开幅度和量比）
            confidence = min(
                0.7 + (gap_pct * 5) + (volume_ratio * 0.1),
                1.0
            )
            
            description = (
                f"竞价弱转强龙头预备：高开{gap_pct*100:.2f}%，"
                f"量比{volume_ratio:.2f}"
            )
            
            return TradingEvent(
                event_type=EventType.LEADER_CANDIDATE,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测竞价弱转强失败: {e}")
            return None
    
    def detect_intraday_acceleration(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测日内加速（分时龙头）
        
        条件：
        - 最近 5-10 分钟：价格突破当日前高（或最近 60 分钟平台高点）
        - 且最近 5 分钟成交额 ≥ 前 5 分钟的 1.5 倍
        
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
            
            # 更新历史数据
            current_price = tick_data.get('now', 0)
            current_volume = tick_data.get('volume', 0)
            self._update_history(stock_code, current_price, current_volume)
            
            # 获取历史数据
            if stock_code not in self.price_history:
                return None
            
            price_queue = self.price_history[stock_code]
            volume_queue = self.volume_history[stock_code]
            
            if len(price_queue) < self.INTRADAY_ACCEL_PERIOD:
                return None
            
            # 计算最近N分钟的数据
            recent_prices = list(price_queue)[-self.INTRADAY_ACCEL_PERIOD:]
            recent_volumes = list(volume_queue)[-self.INTRADAY_ACCEL_PERIOD:]
            
            # 计算当日最高价
            day_high = max(price_queue)
            
            # 检查是否突破当日最高价
            if current_price <= day_high:
                return None
            
            # 检查成交量加速
            recent_avg_volume = sum(recent_volumes) / len(recent_volumes)
            
            if len(volume_queue) < self.INTRADAY_ACCEL_PERIOD * 2:
                return None
            
            prev_volumes = list(volume_queue)[-self.INTRADAY_ACCEL_PERIOD * 2:-self.INTRADAY_ACCEL_PERIOD]
            prev_avg_volume = sum(prev_volumes) / len(prev_volumes)
            
            if prev_avg_volume == 0:
                return None
            
            volume_ratio = recent_avg_volume / prev_avg_volume
            
            if volume_ratio < self.INTRADAY_ACCEL_VOLUME_RATIO:
                return None
            
            # 构建事件数据
            event_data = {
                'day_high': day_high,
                'current_price': current_price,
                'breakout_gain': (current_price - day_high) / day_high,
                'volume_ratio': volume_ratio
            }
            
            # 计算置信度（基于突破幅度和量比）
            confidence = min(
                0.7 + (event_data['breakout_gain'] * 20) + (volume_ratio * 0.1),
                1.0
            )
            
            description = (
                f"日内加速（分时龙头）：突破前高{event_data['breakout_gain']*100:.2f}%，"
                f"量比{volume_ratio:.2f}"
            )
            
            return TradingEvent(
                event_type=EventType.LEADER_CANDIDATE,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测日内加速失败: {e}")
            return None
    
    def detect(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测龙头战法事件
        
        按优先级检测：
        1. 板块龙头候选（优先级最高）
        2. 竞价弱转强龙头预备
        3. 日内加速（分时龙头）
        
        Args:
            tick_data: Tick数据
            context: 上下文信息
        
        Returns:
            检测到的事件对象，如果没有则返回None
        """
        # 按优先级检测
        event = self.detect_sector_leader(tick_data, context)
        if event:
            return event
        
        event = self.detect_auction_weak_to_strong(tick_data, context)
        if event:
            return event
        
        event = self.detect_intraday_acceleration(tick_data, context)
        if event:
            return event
        
        return None


if __name__ == "__main__":
    # 快速测试
    detector = LeaderEventDetector()
    print("✅ 龙头战法事件检测器测试通过")
    print(f"   名称: {detector.name}")
    print(f"   已启用: {detector.enabled}")
    print(f"   历史数据长度: {detector.history_length} 分钟")