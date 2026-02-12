#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集合竞价战法事件检测器

实现两种事件检测：
1. 弱转强（OPENING_WEAK_TO_STRONG）
2. 一字板扩散（OPENING_THEME_SPREAD）

Author: iFlow CLI
Version: V2.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, time as dt_time

from logic.event_detector import BaseEventDetector, EventType, TradingEvent
from logic.market_status import MarketStatusChecker
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class AuctionEventDetector(BaseEventDetector):
    """
    集合竞价事件检测器
    
    只在 9:15-9:25 期间生效
    """
    
    # 竞价时间窗口
    AUCTION_START = dt_time(9, 15)
    AUCTION_END = dt_time(9, 25)
    AUCTION_MIDPOINT = dt_time(9, 20)  # 🔥 P1-2: 竞价中点（第一阶段结束，第二阶段开始）
    
    # 弱转强阈值
    WEAK_TO_STRONG_GAP_MIN = 0.05  # 高开幅度 ≥ 5%
    WEAK_TO_STRONG_VOLUME_RATIO = 1.5  # 竞价量比 ≥ 1.5
    WEAK_CLOSE_CHANGE_MAX = 0.03  # 昨日收盘涨幅 < 3%
    
    # 一字板阈值
    LIMIT_UP_THRESHOLD = 0.099  # 涨停阈值 ≥ 9.9%
    SEAL_RATIO = 0.05  # 封单金额 ≥ 流通盘 5%
    THEME_SPREAD_GAP_MIN = 0.03  # 同题材高开 ≥ 3%
    THEME_SPREAD_VOLUME_RATIO = 1.2  # 同题材量比 ≥ 1.2
    
    def __init__(self):
        """初始化集合竞价事件检测器"""
        super().__init__("auction_event_detector")
        self.market_checker = MarketStatusChecker()
        
    def _is_auction_time(self) -> bool:
        """判断当前是否在竞价时间"""
        current_time = self.market_checker.get_current_time()
        return self.AUCTION_START <= current_time <= self.AUCTION_END

    def _get_auction_phase(self) -> str:
        """
        🔥 P1-2: 获取当前竞价阶段

        Returns:
            str: 'PHASE1'（9:15-9:20），'PHASE2'（9:20-9:25），'NONE'（非竞价时间）
        """
        current_time = self.market_checker.get_current_time()

        if self.AUCTION_START <= current_time < self.AUCTION_MIDPOINT:
            return 'PHASE1'
        elif self.AUCTION_MIDPOINT <= current_time <= self.AUCTION_END:
            return 'PHASE2'
        else:
            return 'NONE'
    
    def detect_weak_to_strong(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测竞价弱转强
        
        条件：
        - 昨日：收盘涨幅 < 3%，或收阴线
        - 今日：高开幅度 ≥ 5%，竞价量比 ≥ 1.5
        
        Args:
            tick_data: Tick数据
            context: 上下文（昨日数据）
        
        Returns:
            如果满足条件，返回事件对象；否则返回None
        """
        try:
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
            
            # 昨日是否收阴线（假设close < open为阴线）
            yesterday_close = yesterday_data.get('close', 0)
            yesterday_open = yesterday_data.get('open', 0)
            is_bearish = yesterday_close < yesterday_open
            
            # 判断昨日是否弱势
            is_weak = (yesterday_close_change < self.WEAK_CLOSE_CHANGE_MAX) or is_bearish
            if not is_weak:
                return None
            
            # 获取今日竞价数据
            current_price = tick_data.get('now', 0)
            yesterday_close_price = yesterday_data.get('close', 0)
            
            if current_price == 0 or yesterday_close_price == 0:
                return None
            
            # 计算高开幅度
            gap_pct = (current_price - yesterday_close_price) / yesterday_close_price
            
            # 判断是否高开 ≥ 5%
            if gap_pct < self.WEAK_TO_STRONG_GAP_MIN:
                return None
            
            # 获取竞价量比
            auction_volume = tick_data.get('auction_volume', 0)
            yesterday_volume = yesterday_data.get('volume', 0)
            
            if yesterday_volume == 0:
                return None
            
            volume_ratio = auction_volume / yesterday_volume
            
            # 判断量比 ≥ 1.5
            if volume_ratio < self.WEAK_TO_STRONG_VOLUME_RATIO:
                return None
            
            # 构建事件数据
            event_data = {
                'yesterday_close_change': yesterday_close_change,
                'is_bearish': is_bearish,
                'gap_pct': gap_pct,
                'volume_ratio': volume_ratio,
                'current_price': current_price,
                'yesterday_close': yesterday_close_price
            }
            
            # 计算置信度（基于高开幅度和量比）
            confidence = min(0.7 + (gap_pct * 5) + (volume_ratio * 0.1), 1.0)
            
            description = f"竞价弱转强：高开{gap_pct*100:.2f}%，量比{volume_ratio:.2f}"
            
            return TradingEvent(
                event_type=EventType.OPENING_WEAK_TO_STRONG,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测竞价弱转强失败: {e}")
            return None
    
    def detect_limit_up_spread(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测一字板扩散（主力票）
        
        条件：
        - 竞价涨幅 ≥ 9.9%
        - 封单金额 ≥ 流通盘 5%
        
        Args:
            tick_data: Tick数据
            context: 上下文（流通市值）
        
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
            
            # 计算竞价涨幅
            gap_pct = (current_price - yesterday_close) / yesterday_close
            
            # 判断是否涨停
            if gap_pct < self.LIMIT_UP_THRESHOLD:
                return None
            
            # 获取封单数据（买一量）
            bid1_volume = tick_data.get('bid1_volume', 0)
            
            # 计算封单金额（手数 × 100 × 价格）
            seal_amount = bid1_volume * 100 * current_price
            
            # 获取流通市值
            float_market_cap = context.get('float_market_cap', 0)
            
            if float_market_cap == 0:
                return None
            
            # 判断封单比例
            seal_ratio = seal_amount / float_market_cap
            
            # 判断封单比例 ≥ 5%
            if seal_ratio < self.SEAL_RATIO:
                return None
            
            # 构建事件数据
            event_data = {
                'gap_pct': gap_pct,
                'seal_amount': seal_amount,
                'float_market_cap': float_market_cap,
                'seal_ratio': seal_ratio,
                'bid1_volume': bid1_volume
            }
            
            # 计算置信度（基于封单比例）
            confidence = min(0.7 + seal_ratio * 5, 1.0)
            
            description = f"一字板扩散：竞价涨幅{gap_pct*100:.2f}%，封单{seal_ratio*100:.2f}%"
            
            return TradingEvent(
                event_type=EventType.OPENING_THEME_SPREAD,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测一字板扩散失败: {e}")
            return None
    
    def detect(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测集合竞价事件

        按优先级检测：
        1. 一字板扩散（优先级更高）
        2. 弱转强

        Args:
            tick_data: Tick数据
            context: 上下文信息

        Returns:
            检测到的事件对象，如果没有则返回None
        """
        # 🔥 P1-2: 获取当前竞价阶段
        phase = self._get_auction_phase()

        # 只在竞价时间生效
        if phase == 'NONE':
            return None

        # 🔥 P1-2: 记录当前竞价阶段
        stock_code = tick_data.get('code', '')
        logger.debug(f"🔍 竞价检测 [{phase}]: {stock_code}")

        # 按优先级检测
        event = self.detect_limit_up_spread(tick_data, context)
        if event:
            # 🔥 P1-2: 在事件中添加竞价阶段信息
            event.metadata['auction_phase'] = phase
            return event

        event = self.detect_weak_to_strong(tick_data, context)
        if event:
            # 🔥 P1-2: 在事件中添加竞价阶段信息
            event.metadata['auction_phase'] = phase
            return event

        return None


if __name__ == "__main__":
    # 快速测试
    detector = AuctionEventDetector()
    print("✅ 集合竞价事件检测器测试通过")
    print(f"   名称: {detector.name}")
    print(f"   已启用: {detector.enabled}")
    
    # 测试竞价时间判断
    print(f"   竞价时间: {detector._is_auction_time()}")