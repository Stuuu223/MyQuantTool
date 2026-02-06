#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场阶段策略判断器 - 简化版

功能：
- 判断当前应该使用哪种监控策略
- 策略：auction（竞价）、event_driven（盘中）、idle（空闲）

Author: iFlow CLI
Version: V1.0
"""

from datetime import datetime
from typing import Optional

from logic.logger import get_logger

logger = get_logger(__name__)


class MarketPhaseChecker:
    """市场阶段策略判断器"""
    
    def __init__(self, market_checker):
        """
        初始化市场阶段检查器
        
        Args:
            market_checker: 市场状态检查器（提供 is_trading_time() 方法）
        """
        self.market_checker = market_checker
        logger.info("✅ MarketPhaseChecker 初始化成功")
    
    def determine_strategy(self) -> str:
        """
        根据当前时间确定策略（简化版）
        
        策略规则：
        1. 非交易时间 → 'idle'
        2. 交易时间 + 9:15-9:30 → 'auction'
        3. 交易时间 + 其他 → 'event_driven'
        
        Returns:
            str: 策略名称 ('auction'/'event_driven'/'idle')
        """
        # 1. 先问QMT/市场检查器：是否在交易时间
        try:
            is_trading = self.market_checker.is_trading_time()
        except Exception as e:
            logger.warning(f"⚠️ 无法获取交易状态，默认为非交易时间: {e}")
            is_trading = False
        
        if not is_trading:
            return 'idle'
        
        # 2. 交易时间中，用本地时间区分"竞价" vs "盘中"
        now = datetime.now()
        hour, minute = now.hour, now.minute
        
        # 竞价窗口 (09:15-09:30)
        if hour == 9 and 15 <= minute < 30:
            return 'auction'
        
        # 其他交易时间：统一归为事件驱动
        return 'event_driven'