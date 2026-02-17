#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EventDriven系统适配器 (EventDriven System Adapter)

根据CTO指导意见，将统一战法核心集成到实时EventDriven监控系统中。
该适配器连接UnifiedWarfareCore和现有的EventDriven架构。

核心功能：
1. 集成UnifiedWarfareCore到EventDriven系统
2. 适配现有EventDrivenScanner接口
3. 实现多战法事件的实时检测和分发

设计原则：
1. 保持与现有EventDriven系统兼容
2. 使用统一的事件发布机制
3. 遵循V12.1.0规范

验收标准：
- 能够无缝集成到现有EventDriven系统
- 与现有EventDriven系统兼容
- 性能满足实时检测要求
- 代码符合项目规范

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-17
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from logic.strategies.unified_warfare_core import get_unified_warfare_core
from logic.strategies.event_detector import EventType, TradingEvent
from logic.utils.logger import get_logger
# 临时使用一个简单的事件发布器实现，或注释掉相关功能
# from logic.network.event_publisher import EventPublisher  # 假设存在事件发布器

logger = get_logger(__name__)


class EventDrivenWarfareAdapter:
    """
    EventDriven战法适配器
    
    功能：
    1. 连接UnifiedWarfareCore与EventDriven系统
    2. 适配Tick数据格式
    3. 处理和分发多战法事件
    4. 维护系统兼容性
    """

    def __init__(self):
        """
        初始化适配器
        """
        # 获取统一战法核心
        self.warfare_core = get_unified_warfare_core()
        
        # 性能统计
        self._total_ticks_processed = 0
        self._total_events_published = 0
        
        logger.info("✅ [EventDriven战法适配器] 初始化完成")
        logger.info(f"   - 连接战法核心: {type(self.warfare_core).__name__}")
        logger.info(f"   - 支持战法数量: {len(self.warfare_core.get_active_detectors())}")
    
    def process_tick(self, tick_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理单个Tick数据，触发战法检测
        
        Args:
            tick_data: Tick数据字典
            
        Returns:
            检测到的事件列表
        """
        try:
            # 更新处理计数
            self._total_ticks_processed += 1
            
            # 从tick_data中提取上下文信息
            context = self._extract_context_from_tick(tick_data)
            
            # 使用统一战法核心处理tick
            detected_events = self.warfare_core.process_tick(tick_data, context)
            
            # 发布检测到的事件
            for event in detected_events:
                self._publish_event(event)
            
            # 更新事件计数
            self._total_events_published += len(detected_events)
            
            if detected_events:
                logger.info(f"🎯 [适配器] 发布 {len(detected_events)} 个战法事件")
            
            return detected_events
            
        except Exception as e:
            logger.error(f"❌ [EventDriven适配器] 处理Tick失败: {e}")
            return []
    
    def _extract_context_from_tick(self, tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从Tick数据中提取上下文信息
        
        Args:
            tick_data: Tick数据
            
        Returns:
            dict: 上下文信息
        """
        # 从tick_data中提取基本上下文
        context = {
            'price_history': tick_data.get('price_history', []),
            'volume_history': tick_data.get('volume_history', []),
            'ma5': tick_data.get('ma5', 0),
            'ma20': tick_data.get('ma20', 0),
            'rsi': tick_data.get('rsi', 50),
            'avg_volume_5d': tick_data.get('avg_volume_5d', 0),
            'auction_volume_ratio': tick_data.get('auction_volume_ratio', 0),
            'sector_data': tick_data.get('sector_data', {}),
        }
        
        return context
    
    def _publish_event(self, event: Dict[str, Any]):
        """
        发布检测到的事件
        
        Args:
            event: 事件字典
        """
        try:
            # 记录事件（或可扩展为其他发布方式）
            logger.info(f"📢 [适配器] 检测到事件: {event['event_type']} - {event['stock_code']}")
                
        except Exception as e:
            logger.error(f"❌ [EventDriven适配器] 处理事件失败: {e}")
    
    def enable_warfare(self, warfare_type: str):
        """启用特定战法"""
        self.warfare_core.enable_warfare(warfare_type)
    
    def disable_warfare(self, warfare_type: str):
        """禁用特定战法"""
        self.warfare_core.disable_warfare(warfare_type)
    
    def get_warfare_stats(self) -> Dict[str, Any]:
        """获取战法统计信息"""
        core_stats = self.warfare_core.get_warfare_stats()
        adapter_stats = {
            '总处理Tick数': self._total_ticks_processed,
            '总发布事件数': self._total_events_published,
            '发布率': f"{self._total_events_published/self._total_ticks_processed*100:.4f}%" if self._total_ticks_processed > 0 else "0.0000%",
        }
        
        # 合并统计数据
        all_stats = {**core_stats, **adapter_stats}
        return all_stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.warfare_core.reset_warfare_stats()
        self._total_ticks_processed = 0
        self._total_events_published = 0
        logger.info("🔄 [适配器] 统计信息已重置")


# ==================== 全局实例 ====================

_event_driven_adapter: Optional[EventDrivenWarfareAdapter] = None


def get_event_driven_adapter() -> EventDrivenWarfareAdapter:
    """获取EventDriven战法适配器单例"""
    global _event_driven_adapter
    if _event_driven_adapter is None:
        _event_driven_adapter = EventDrivenWarfareAdapter()
    return _event_driven_adapter


# ==================== 与现有EventDrivenScanner集成 ====================

def integrate_with_event_driven_scanner(scanner):
    """
    与现有的EventDrivenScanner集成
    
    Args:
        scanner: 现有的EventDrivenScanner实例
    """
    # 替换scanner的事件检测逻辑为适配器的逻辑
    adapter = get_event_driven_adapter()
    
    # 保存原始方法
    original_scan = getattr(scanner, 'scan_tick', None)
    
    def new_scan_tick(tick_data: Dict[str, Any]):
        """新的Tick扫描方法"""
        # 首先执行原有逻辑
        if original_scan:
            original_scan(tick_data)
        
        # 然后使用统一战法核心检测
        detected_events = adapter.process_tick(tick_data)
        
        # 如果需要，还可以执行其他处理
        for event in detected_events:
            logger.debug(f"📋 [集成] 战法事件: {event['event_type']} - {event['stock_code']}")
        
        return detected_events
    
    # 替换scanner的方法
    scanner.scan_tick = new_scan_tick
    
    logger.info("✅ [适配器] 已集成到EventDrivenScanner")
    return scanner


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试EventDrivenWarfareAdapter
    print("=" * 80)
    print("EventDriven战法适配器测试")
    print("=" * 80)
    
    adapter = get_event_driven_adapter()
    
    # 模拟tick数据 - 测试多战法检测
    test_tick_data = {
        'stock_code': '300750',
        'datetime': datetime(2026, 2, 17, 10, 30, 0),
        'price': 205.0,
        'prev_close': 200.0,
        'open': 201.0,
        'high': 206.0,
        'low': 200.5,
        'volume': 1200000,
        'amount': 246000000,
        'is_limit_up': False,
        # 上下文数据
        'price_history': [200.1, 200.5, 201.0, 202.5, 203.0, 204.0, 205.0],
        'volume_history': [800000, 850000, 900000, 950000, 1000000, 1100000, 1200000],
        'ma5': 202.5,
        'ma20': 201.0,
        'rsi': 25,
        'avg_volume_5d': 900000,
        'auction_volume_ratio': 2.5,
        'sector_data': {
            'stocks': [
                {'code': '300750', 'change_pct': 2.5},
                {'code': '300015', 'change_pct': 1.8},
            ]
        }
    }
    
    # 测试用例
    test_cases = [
        {
            'name': '多战法检测',
            'tick_data': test_tick_data
        }
    ]
    
    print(f"\n测试用例数: {len(test_cases)}")
    print("\n开始测试...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试用例 {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        
        events = adapter.process_tick(test_case['tick_data'])
        
        print(f"\n股票代码: {test_case['tick_data']['stock_code']}")
        print(f"当前价格: {test_case['tick_data']['price']:.2f}")
        print(f"涨跌幅: {(test_case['tick_data']['price'] - test_case['tick_data']['prev_close']) / test_case['tick_data']['prev_close'] * 100:.2f}%")
        print(f"RSI: {test_case['tick_data']['rsi']}")
        
        if events:
            print(f"\n✅ 检测到 {len(events)} 个事件:")
            for j, event in enumerate(events, 1):
                print(f"   事件 {j}:")
                print(f"     - 类型: {event['event_type']}")
                print(f"     - 描述: {event['description']}")
                print(f"     - 置信度: {event['confidence']:.2f}")
        else:
            print(f"\n❌ 未检测到事件")
    
    # 获取统计信息
    print("\n" + "=" * 80)
    print("适配器统计:")
    print("=" * 80)
    stats = adapter.get_warfare_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    - {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")
    
    print("\n✅ 测试完成")
    print("=" * 80)
