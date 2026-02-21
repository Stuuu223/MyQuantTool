#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一战法核心模块 (Unified Warfare Core)

根据CTO指导意见，实现统一的多战法核心逻辑。
该模块提供统一的接口来管理所有战法事件检测器，实现"一套吃多战法"的目标。

核心功能：
1. 统一管理所有战法事件检测器
2. 提供统一的战法核心接口
3. 实现多战法事件的集中检测和分发
4. 与实时EventDriven和离线回测系统对齐

设计原则：
1. 遵循单一职责原则
2. 使用组合模式管理多个检测器
3. 提供统一的事件检测接口
4. 遵循V12.1.0规范

验收标准：
- 能够统一管理多战法事件检测器
- 与现有EventDriven系统兼容
- 性能满足实时检测要求
- 代码符合项目规范

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-17
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from logic.strategies.event_detector import EventManager, BaseEventDetector
from logic.strategies.opening_weak_to_strong_detector import OpeningWeakToStrongDetector
from logic.strategies.halfway_breakout_detector import HalfwayBreakoutDetector
from logic.strategies.leader_candidate_detector import LeaderCandidateDetector
from logic.strategies.dip_buy_candidate_detector import DipBuyCandidateDetector
from logic.analyzers.trap_detector import TrapDetector
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class UnifiedWarfareCore:
    """
    统一战法核心
    
    功能：
    1. 统一管理所有战法事件检测器
    2. 提供统一的事件检测接口
    3. 集中处理多战法事件
    4. 与回测引擎和实时系统对齐
    """

    def __init__(self):
        """初始化统一战法核心"""
        # 创建事件管理器
        self.event_manager = EventManager()
        
        # 初始化各个战法检测器
        self._init_detectors()
        
        # 性能统计
        self._total_ticks = 0
        self._total_events = 0
        
        logger.info("✅ [统一战法核心] 初始化完成")
        logger.info(f"   - 已注册检测器: {len(self.event_manager.detectors)} 个")
        logger.info(f"   - 支持事件类型: {[detector.name for detector in self.event_manager.detectors.values()]}")
    
    def _init_detectors(self):
        """初始化各个战法检测器"""
        # 集合竞价弱转强检测器
        opening_detector = OpeningWeakToStrongDetector()
        self.event_manager.register_detector(opening_detector)
        
        # 半路突破检测器
        halfway_detector = HalfwayBreakoutDetector()
        self.event_manager.register_detector(halfway_detector)
        
        # 龙头候选检测器
        leader_detector = LeaderCandidateDetector()
        self.event_manager.register_detector(leader_detector)
        
        # 低吸候选检测器
        dip_buy_detector = DipBuyCandidateDetector()
        self.event_manager.register_detector(dip_buy_detector)
        
        # 🔥 P1: 诱多陷阱检测器（veto机制）
        try:
            trap_detector = TrapDetector()
            self.event_manager.register_detector(trap_detector)
            logger.info("✅ [统一战法核心] TrapDetector注册成功")
        except Exception as e:
            logger.warning(f"⚠️ [统一战法核心] TrapDetector注册失败: {e}")
        
        logger.info("✅ [统一战法核心] 检测器初始化完成")
    
    def process_tick(self, tick_data: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        处理单个Tick数据，检测多战法事件
        
        Args:
            tick_data: Tick数据字典
            context: 上下文信息
            
        Returns:
            检测到的事件列表
        """
        try:
            # 更新总tick计数
            self._total_ticks += 1
            
            # 使用事件管理器检测所有战法事件
            detected_events = self.event_manager.detect_events(tick_data, context)
            
            # 更新事件计数
            self._total_events += len(detected_events)
            
            # 转换事件为字典格式（便于后续处理）
            event_dicts = []
            for event in detected_events:
                event_dict = {
                    'event_type': event.event_type.value,
                    'stock_code': event.stock_code,
                    'timestamp': event.timestamp,
                    'data': event.data,
                    'confidence': event.confidence,
                    'description': event.description
                }
                event_dicts.append(event_dict)
                
                # 记录检测到的事件
                logger.debug(f"📊 [统一战法] 检测事件: {event.event_type.value} - {event.stock_code} @ {event.confidence:.2f}")
            
            if detected_events:
                logger.info(f"🎯 [统一战法] 本tick检测到 {len(detected_events)} 个事件")
            
            return event_dicts
            
        except Exception as e:
            logger.error(f"❌ [统一战法核心] 处理Tick失败: {e}")
            return []
    
    def get_active_detectors(self) -> List[str]:
        """获取当前激活的检测器列表"""
        return [name for name, detector in self.event_manager.detectors.items() if detector.enabled]
    
    def get_warfare_stats(self) -> Dict[str, Any]:
        """获取战法统计信息"""
        stats = {
            '总处理Tick数': self._total_ticks,
            '总检测事件数': self._total_events,
            '事件检测率': f"{self._total_events/self._total_ticks*100:.4f}%" if self._total_ticks > 0 else "0.0000%",
            '活跃检测器': len(self.get_active_detectors()),
            '检测器详情': {}
        }
        
        # 获取每个检测器的详细统计
        for name, detector in self.event_manager.detectors.items():
            if hasattr(detector, 'get_detection_stats'):
                stats['检测器详情'][name] = detector.get_detection_stats()
        
        return stats
    
    def enable_warfare(self, warfare_type: str):
        """启用特定战法检测器"""
        detector_map = {
            'opening_weak_to_strong': 'OpeningWeakToStrongDetector',
            'halfway_breakout': 'HalfwayBreakoutDetector',
            'leader_candidate': 'LeaderCandidateDetector',
            'dip_buy_candidate': 'DipBuyCandidateDetector',
        }
        
        detector_name = detector_map.get(warfare_type)
        if detector_name:
            self.event_manager.enable_detector(detector_name)
            logger.info(f"✅ 启用战法: {warfare_type}")
    
    def disable_warfare(self, warfare_type: str):
        """禁用特定战法检测器"""
        detector_map = {
            'opening_weak_to_strong': 'OpeningWeakToStrongDetector',
            'halfway_breakout': 'HalfwayBreakoutDetector',
            'leader_candidate': 'LeaderCandidateDetector',
            'dip_buy_candidate': 'DipBuyCandidateDetector',
        }
        
        detector_name = detector_map.get(warfare_type)
        if detector_name:
            self.event_manager.disable_detector(detector_name)
            logger.info(f"⏸️ 禁用战法: {warfare_type}")
    
    def reset_warfare_stats(self):
        """重置所有检测器统计"""
        for detector in self.event_manager.detectors.values():
            detector.reset()
        self._total_ticks = 0
        self._total_events = 0
        logger.info("🔄 重置战法统计")


# ==================== 全局实例 ====================

_unified_warfare_core: Optional[UnifiedWarfareCore] = None


def get_unified_warfare_core() -> UnifiedWarfareCore:
    """获取统一战法核心单例"""
    global _unified_warfare_core
    if _unified_warfare_core is None:
        _unified_warfare_core = UnifiedWarfareCore()
    return _unified_warfare_core


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试UnifiedWarfareCore
    print("=" * 80)
    print("统一战法核心测试")
    print("=" * 80)
    
    core = get_unified_warfare_core()
    
    # 模拟tick数据 - 测试竞价战法
    auction_tick_data = {
        'stock_code': '000001',
        'datetime': datetime(2026, 2, 17, 9, 28, 0),  # 竞价时间
        'open': 16.5,
        'prev_close': 15.0,
        'high': 16.8,
        'low': 16.2,
        'volume': 150000000,
        'amount': 2500000000,
        'is_limit_up': False,
        'price': 16.5
    }
    
    auction_context = {
        'auction_volume_ratio': 2.5,
        'avg_volume_5d': 60000000,
        'price_history': [14.8, 14.9, 15.0, 15.2, 15.1, 14.95, 15.05, 14.98, 15.02, 15.0],
        'volume_history': [50000000, 55000000, 60000000, 58000000, 62000000, 59000000, 61000000, 57000000, 63000000, 60000000]
    }
    
    # 模拟tick数据 - 测试半路战法
    halfway_tick_data = {
        'stock_code': '300750',
        'datetime': datetime(2026, 2, 17, 10, 15, 0),  # 非竞价时间
        'price': 205.0,
        'volume': 1200000
    }
    
    # 构造平台突破的历史数据
    import random
    base_price = 200.0
    platform_prices = [base_price + random.uniform(-0.5, 0.5) for _ in range(15)]
    breakout_prices = [201.0, 202.5, 204.0, 205.0]
    all_prices = platform_prices + breakout_prices
    
    platform_volumes = [800000 + random.randint(-100000, 100000) for _ in range(15)]
    breakout_volumes = [1000000, 1100000, 1150000, 1200000]
    all_volumes = platform_volumes + breakout_volumes
    
    halfway_context = {
        'price_history': all_prices,
        'volume_history': all_volumes,
        'ma5': 203.0,
        'ma20': 201.5,
        'avg_volume_5d': 950000
    }
    
    # 测试用例
    test_cases = [
        {
            'name': '竞价战法测试',
            'tick_data': auction_tick_data,
            'context': auction_context
        },
        {
            'name': '半路战法测试',
            'tick_data': halfway_tick_data,
            'context': halfway_context
        }
    ]
    
    print(f"\n测试用例数: {len(test_cases)}")
    print("\n开始测试...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试用例 {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        
        events = core.process_tick(test_case['tick_data'], test_case['context'])
        
        print(f"\n股票代码: {test_case['tick_data']['stock_code']}")
        print(f"时间: {test_case['tick_data']['datetime']}")
        print(f"价格: {test_case['tick_data'].get('price', test_case['tick_data'].get('open', 'N/A'))}")
        
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
    print("战法统计:")
    print("=" * 80)
    stats = core.get_warfare_stats()
    for key, value in stats.items():
        if key != '检测器详情':
            print(f"  {key}: {value}")
    
    print("\n检测器详情:")
    for detector_name, detector_stats in stats.get('检测器详情', {}).items():
        print(f"  {detector_name}:")
        for stat_key, stat_value in detector_stats.items():
            print(f"    - {stat_key}: {stat_value}")
    
    print("\n✅ 测试完成")
    print("=" * 80)
