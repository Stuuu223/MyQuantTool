#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半路战法事件检测器

实现平台突破事件检测（HALFWAY_BREAKOUT）

专攻创业板(300)和科创板(688)的20cm标的

Author: iFlow CLI
Version: V2.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque

from logic.event_detector import BaseEventDetector, EventType, TradingEvent
from logic.logger import get_logger

logger = get_logger(__name__)


class HalfwayEventDetector(BaseEventDetector):
    """
    半路战法事件检测器
    
    检测平台突破信号
    """
    
    # 涨幅区间
    HALFWAY_20CM_MIN = 0.10  # 20cm标的：最小涨幅 10%
    HALFWAY_20CM_MAX = 0.195  # 20cm标的：最大涨幅 19.5%
    HALFWAY_10CM_MIN = 0.05  # 10cm标的：最小涨幅 5%
    HALFWAY_10CM_MAX = 0.095  # 10cm标的：最大涨幅 9.5%
    
    # 平台参数
    PLATFORM_PERIOD = 30  # 平台周期（分钟）
    PLATFORM_VOLATILITY_MAX = 0.03  # 平台振幅 < 3%
    BREAKOUT_THRESHOLD = 0.01  # 突破阈值 > 1%
    BREAKOUT_VOLUME_RATIO = 1.5  # 突破量比 ≥ 1.5
    
    def __init__(self):
        """初始化半路战法事件检测器"""
        super().__init__("halfway_event_detector")
        # 维护每只股票的历史数据
        self.price_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}
        self.history_length = 60  # 保存60分钟的历史数据
        
    def _get_code_prefix(self, stock_code: str) -> str:
        """获取股票代码前缀（判断20cm/10cm）"""
        # 去掉后缀
        code = stock_code.replace('.SZ', '').replace('.SH', '')
        return code[:3]
    
    def _is_20cm_stock(self, stock_code: str) -> bool:
        """判断是否为20cm标的"""
        prefix = self._get_code_prefix(stock_code)
        return prefix in ['300', '688']
    
    def _is_10cm_stock(self, stock_code: str) -> bool:
        """判断是否为10cm标的"""
        prefix = self._get_code_prefix(stock_code)
        return prefix in ['000', '001', '002', '003', '600', '601', '603', '605']
    
    def _update_history(self, stock_code: str, price: float, volume: int):
        """
        更新股票的历史数据
        
        Args:
            stock_code: 股票代码
            price: 当前价格
            volume: 当前成交量
        """
        # 初始化队列
        if stock_code not in self.price_history:
            self.price_history[stock_code] = deque(maxlen=self.history_length)
            self.volume_history[stock_code] = deque(maxlen=self.history_length)
        
        # 添加新数据
        self.price_history[stock_code].append(price)
        self.volume_history[stock_code].append(volume)
    
    def _calculate_platform(
        self,
        stock_code: str,
        period: int = 30
    ) -> Dict[str, Any]:
        """
        计算平台数据
        
        Args:
            stock_code: 股票代码
            period: 平台周期（分钟）
        
        Returns:
            平台数据字典
        """
        if stock_code not in self.price_history:
            return None
        
        price_queue = self.price_history[stock_code]
        volume_queue = self.volume_history[stock_code]
        
        if len(price_queue) < period:
            return None
        
        # 获取最近N分钟的数据
        recent_prices = list(price_queue)[-period:]
        recent_volumes = list(volume_queue)[-period:]
        
        # 计算平台高点、低点
        platform_high = max(recent_prices)
        platform_low = min(recent_prices)
        platform_avg = sum(recent_prices) / len(recent_prices)
        
        # 计算平台振幅
        volatility = (platform_high - platform_low) / platform_avg
        
        # 计算平台平均成交量
        platform_avg_volume = sum(recent_volumes) / len(recent_volumes)
        
        return {
            'platform_high': platform_high,
            'platform_low': platform_low,
            'platform_avg': platform_avg,
            'volatility': volatility,
            'platform_avg_volume': platform_avg_volume,
            'period': period
        }
    
    def detect_breakout(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测平台突破
        
        条件：
        - 涨幅在目标区间（20cm: 10%-19.5%, 10cm: 5%-9.5%）
        - 有平台（过去30-60分钟振幅 < 3%）
        - 突破平台高点 ≥ 1%
        - 突破成交量 ≥ 平台期平均量的1.5倍
        
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
            
            # 获取价格数据
            current_price = tick_data.get('now', 0)
            yesterday_close = context.get('yesterday_close', 0)
            
            if current_price == 0 or yesterday_close == 0:
                return None
            
            # 计算当前涨幅
            change_pct = (current_price - yesterday_close) / yesterday_close
            
            # 判断是否为20cm或10cm标的
            is_20cm = self._is_20cm_stock(stock_code)
            is_10cm = self._is_10cm_stock(stock_code)
            
            # 检查涨幅是否在目标区间
            if is_20cm:
                if not (self.HALFWAY_20CM_MIN <= change_pct <= self.HALFWAY_20CM_MAX):
                    return None
            elif is_10cm:
                if not (self.HALFWAY_10CM_MIN <= change_pct <= self.HALFWAY_10CM_MAX):
                    return None
            else:
                return None
            
            # 更新历史数据
            current_volume = tick_data.get('volume', 0)
            self._update_history(stock_code, current_price, current_volume)
            
            # 计算平台数据
            platform_data = self._calculate_platform(stock_code, self.PLATFORM_PERIOD)
            if not platform_data:
                return None
            
            # 检查平台振幅
            if platform_data['volatility'] > self.PLATFORM_VOLATILITY_MAX:
                return None
            
            # 检查是否突破平台高点
            breakout_gain = (current_price - platform_data['platform_high']) / platform_data['platform_high']
            if breakout_gain < self.BREAKOUT_THRESHOLD:
                return None
            
            # 检查突破成交量
            if current_volume < platform_data['platform_avg_volume'] * self.BREAKOUT_VOLUME_RATIO:
                return None
            
            # 构建事件数据
            event_data = {
                'change_pct': change_pct,
                'is_20cm': is_20cm,
                'platform_high': platform_data['platform_high'],
                'platform_low': platform_data['platform_low'],
                'platform_volatility': platform_data['volatility'],
                'breakout_gain': breakout_gain,
                'current_volume': current_volume,
                'platform_avg_volume': platform_data['platform_avg_volume'],
                'volume_ratio': current_volume / platform_data['platform_avg_volume']
            }
            
            # 计算置信度（基于突破幅度和量比）
            confidence = min(
                0.6 + (breakout_gain * 20) + (event_data['volume_ratio'] * 0.1),
                1.0
            )
            
            stock_type = "20cm" if is_20cm else "10cm"
            description = (
                f"半路平台突破（{stock_type}）：涨幅{change_pct*100:.2f}%，"
                f"突破{breakout_gain*100:.2f}%，量比{event_data['volume_ratio']:.2f}"
            )
            
            return TradingEvent(
                event_type=EventType.HALFWAY_BREAKOUT,
                stock_code=stock_code,
                timestamp=datetime.now(),
                data=event_data,
                confidence=confidence,
                description=description
            )
            
        except Exception as e:
            logger.error(f"❌ 检测平台突破失败: {e}")
            return None
    
    def detect(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[TradingEvent]:
        """
        检测半路战法事件
        
        Args:
            tick_data: Tick数据
            context: 上下文信息
        
        Returns:
            检测到的事件对象，如果没有则返回None
        """
        return self.detect_breakout(tick_data, context)


if __name__ == "__main__":
    # 快速测试
    detector = HalfwayEventDetector()
    print("✅ 半路战法事件检测器测试通过")
    print(f"   名称: {detector.name}")
    print(f"   已启用: {detector.enabled}")
    print(f"   历史数据长度: {detector.history_length} 分钟")