#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件检测器基类和事件类型定义

定义所有战法的事件类型和统一的事件检测接口

Author: iFlow CLI
Version: V2.0
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from logic.logger import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    
    # 集合竞价战法事件
    OPENING_WEAK_TO_STRONG = "opening_weak_to_strong"  # 竞价弱转强
    OPENING_THEME_SPREAD = "opening_theme_spread"  # 一字板扩散
    
    # 半路战法事件
    HALFWAY_BREAKOUT = "halfway_breakout"  # 半路平台突破
    
    # 低吸战法事件
    DIP_BUY_CANDIDATE = "dip_buy_candidate"  # 低吸候选
    
    # 龙头战法事件
    LEADER_CANDIDATE = "leader_candidate"  # 龙头候选
    
    # 通用事件
    TICK_UPDATE = "tick_update"  # Tick数据更新


@dataclass
class TradingEvent:
    """
    交易事件数据结构
    
    Attributes:
        event_type: 事件类型
        stock_code: 股票代码
        timestamp: 事件时间戳
        data: 事件相关数据（字典）
        confidence: 置信度（0-1）
        description: 事件描述
    """
    event_type: EventType
    stock_code: str
    timestamp: datetime
    data: Dict[str, Any]
    confidence: float
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'event_type': self.event_type.value,
            'stock_code': self.stock_code,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'confidence': self.confidence,
            'description': self.description
        }


class BaseEventDetector(ABC):
    """
    事件检测器基类
    
    所有战法的事件检测器都应该继承这个基类
    """
    
    def __init__(self, name: str):
        """
        初始化事件检测器
        
        Args:
            name: 检测器名称
        """
        self.name = name
        self.enabled = True
        self.event_count = 0
        
    @abstractmethod
    def detect(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[TradingEvent]:
        """
        检测事件（抽象方法，子类必须实现）
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息（历史数据、均线等）
        
        Returns:
            如果检测到事件，返回TradingEvent对象；否则返回None
        """
        pass
    
    def enable(self):
        """启用检测器"""
        self.enabled = True
        logger.info(f"✅ [{self.name}] 检测器已启用")
    
    def disable(self):
        """禁用检测器"""
        self.enabled = False
        logger.info(f"⏸️  [{self.name}] 检测器已禁用")
    
    def reset(self):
        """重置检测器计数器"""
        self.event_count = 0
        logger.info(f"🔄 [{self.name}] 检测器已重置")


class EventManager:
    """
    事件管理器
    
    负责管理所有事件检测器，收集和分发事件
    """
    
    def __init__(self):
        """初始化事件管理器"""
        self.detectors: Dict[str, BaseEventDetector] = {}
        self.event_queue: List[TradingEvent] = []
        self.last_scan_time = None
        self.cooldown_seconds = 60  # 冷却时间（秒）
        
    def register_detector(self, detector: BaseEventDetector):
        """
        注册事件检测器
        
        Args:
            detector: 事件检测器实例
        """
        self.detectors[detector.name] = detector
        logger.info(f"📝 注册事件检测器: {detector.name}")
    
    def unregister_detector(self, name: str):
        """
        注销事件检测器
        
        Args:
            name: 检测器名称
        """
        if name in self.detectors:
            del self.detectors[name]
            logger.info(f"🗑️  注销事件检测器: {name}")
    
    def enable_detector(self, name: str):
        """启用指定的检测器"""
        if name in self.detectors:
            self.detectors[name].enable()
    
    def disable_detector(self, name: str):
        """禁用指定的检测器"""
        if name in self.detectors:
            self.detectors[name].disable()
    
    def detect_events(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> List[TradingEvent]:
        """
        使用所有启用的检测器检测事件
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息
        
        Returns:
            检测到的事件列表
        """
        events = []
        
        for detector in self.detectors.values():
            if not detector.enabled:
                continue
            
            try:
                event = detector.detect(tick_data, context)
                if event:
                    events.append(event)
                    detector.event_count += 1
                    logger.info(f"🔔 [{detector.name}] 检测到事件: {event.stock_code} - {event.description}")
            except Exception as e:
                logger.error(f"❌ [{detector.name}] 检测失败: {e}")
        
        return events
    
    def has_events(self) -> bool:
        """检查是否有待处理的事件"""
        return len(self.event_queue) > 0
    
    def get_events(self) -> List[TradingEvent]:
        """获取所有待处理的事件"""
        return self.event_queue
    
    def clear_events(self):
        """清空事件队列"""
        self.event_queue.clear()
        logger.info(f"🗑️  事件队列已清空")
    
    def should_trigger_scan(self) -> bool:
        """
        判断是否应该触发全链路扫描
        
        触发条件：
        1. 有待处理的事件
        2. 距离上次扫描超过冷却时间
        
        Returns:
            True表示应该触发扫描
        """
        if not self.has_events():
            return False
        
        if self.last_scan_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_scan_time).total_seconds()
        if elapsed >= self.cooldown_seconds:
            return True
        
        logger.info(f"⏳ 冷却中，距离上次扫描还有 {self.cooldown_seconds - elapsed:.1f} 秒")
        return False
    
    def mark_scan_complete(self):
        """标记扫描完成，重置冷却计时器"""
        self.last_scan_time = datetime.now()
        self.clear_events()


if __name__ == "__main__":
    # 快速测试
    manager = EventManager()
    print("✅ 事件管理器测试通过")
    print(f"   已注册检测器: {len(manager.detectors)}")
    print(f"   事件队列: {manager.event_queue}")
    print(f"   应触发扫描: {manager.should_trigger_scan()}")