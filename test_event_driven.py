#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件驱动测试脚本

测试内容：
1. 事件检测器导入测试
2. 事件管理器测试
3. 事件驱动监控器测试
4. 事件触发测试

Author: iFlow CLI
Version: V2.0
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger

logger = get_logger(__name__)


def test_event_detectors():
    """测试事件检测器"""
    print("\n" + "=" * 80)
    print("🧪 测试事件检测器")
    print("=" * 80)
    
    try:
        from logic.event_detector import BaseEventDetector, EventType, EventManager, TradingEvent
        print("✅ 事件检测器基类导入成功")
        
        from logic.auction_event_detector import AuctionEventDetector
        print("✅ 集合竞价事件检测器导入成功")
        
        from logic.halfway_event_detector import HalfwayEventDetector
        print("✅ 半路战法事件检测器导入成功")
        
        from logic.dip_buy_event_detector import DipBuyEventDetector
        print("✅ 低吸战法事件检测器导入成功")
        
        from logic.leader_event_detector import LeaderEventDetector
        print("✅ 龙头战法事件检测器导入成功")
        
        # 创建检测器实例
        auction_detector = AuctionEventDetector()
        print(f"   集合竞价检测器: {auction_detector.name}")
        
        halfway_detector = HalfwayEventDetector()
        print(f"   半路战法检测器: {halfway_detector.name}")
        
        dip_detector = DipBuyEventDetector()
        print(f"   低吸战法检测器: {dip_detector.name}")
        
        leader_detector = LeaderEventDetector()
        print(f"   龙头战法检测器: {leader_detector.name}")
        
        print("\n✅ 事件检测器测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 事件检测器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_manager():
    """测试事件管理器"""
    print("\n" + "=" * 80)
    print("🧪 测试事件管理器")
    print("=" * 80)
    
    try:
        from logic.event_detector import EventManager
        from logic.auction_event_detector import AuctionEventDetector
        
        # 创建事件管理器
        manager = EventManager()
        print(f"✅ 事件管理器创建成功")
        
        # 创建并注册检测器
        detector = AuctionEventDetector()
        manager.register_detector(detector)
        print(f"✅ 注册检测器成功: {detector.name}")
        print(f"   已注册检测器数: {len(manager.detectors)}")
        
        # 测试冷却时间
        print(f"   冷却时间: {manager.cooldown_seconds} 秒")
        
        # 测试事件队列
        print(f"   事件队列: {manager.event_queue}")
        print(f"   是否有事件: {manager.has_events()}")
        
        print("\n✅ 事件管理器测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 事件管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tick_monitor():
    """测试QMT Tick监控器"""
    print("\n" + "=" * 80)
    print("🧪 测试QMT Tick监控器")
    print("=" * 80)
    
    try:
        from logic.qmt_tick_monitor import get_tick_monitor, QMT_AVAILABLE
        
        print(f"   QMT可用: {QMT_AVAILABLE}")
        
        if not QMT_AVAILABLE:
            print("⚠️  QMT不可用，跳过测试")
            return True
        
        # 创建Tick监控器
        monitor = get_tick_monitor()
        print(f"✅ Tick监控器创建成功")
        
        print(f"   订阅数: {len(monitor.subscribed_stocks)}")
        print(f"   股票状态数: {len(monitor.stock_states)}")
        print(f"   事件回调数: {len(monitor.event_callbacks)}")
        
        print("\n✅ QMT Tick监控器测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ QMT Tick监控器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_driven_monitor():
    """测试事件驱动监控器"""
    print("\n" + "=" * 80)
    print("🧪 测试事件驱动监控器")
    print("=" * 80)
    
    try:
        from tasks.run_event_driven_monitor import EventDrivenMonitor
        
        # 创建监控器（固定间隔模式）
        monitor = EventDrivenMonitor(
            scan_interval=300,
            mode='fixed_interval'
        )
        print(f"✅ 事件驱动监控器创建成功")
        print(f"   模式: {monitor.mode}")
        print(f"   扫描间隔: {monitor.scan_interval} 秒")
        print(f"   事件检测器数: {len(monitor.event_manager.detectors)}")
        
        # 列出所有检测器
        print(f"   检测器列表:")
        for name, detector in monitor.event_manager.detectors.items():
            print(f"      - {name}")
        
        print("\n✅ 事件驱动监控器测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 事件驱动监控器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_trigger():
    """测试事件触发"""
    print("\n" + "=" * 80)
    print("🧪 测试事件触发")
    print("=" * 80)
    
    try:
        from logic.event_detector import EventManager, EventType, TradingEvent
        from logic.auction_event_detector import AuctionEventDetector
        from datetime import datetime
        
        # 创建事件管理器
        manager = EventManager()
        
        # 创建并注册检测器
        detector = AuctionEventDetector()
        manager.register_detector(detector)
        
        # 创建测试事件
        test_event = TradingEvent(
            event_type=EventType.OPENING_WEAK_TO_STRONG,
            stock_code='000001.SZ',
            timestamp=datetime.now(),
            data={'gap_pct': 0.06, 'volume_ratio': 2.0},
            confidence=0.85,
            description='竞价弱转强：高开6.00%，量比2.00'
        )
        
        # 添加到事件队列
        manager.event_queue.append(test_event)
        print(f"✅ 测试事件创建成功")
        print(f"   事件类型: {test_event.event_type.value}")
        print(f"   股票代码: {test_event.stock_code}")
        print(f"   描述: {test_event.description}")
        print(f"   置信度: {test_event.confidence}")
        
        # 测试是否应该触发扫描
        should_trigger = manager.should_trigger_scan()
        print(f"   应触发扫描: {should_trigger}")
        
        print("\n✅ 事件触发测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 事件触发测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🎯 事件驱动功能测试")
    print("=" * 80)
    
    results = {}
    
    # 测试1：事件检测器
    results['事件检测器'] = test_event_detectors()
    
    # 测试2：事件管理器
    results['事件管理器'] = test_event_manager()
    
    # 测试3：QMT Tick监控器
    results['QMT Tick监控器'] = test_tick_monitor()
    
    # 测试4：事件驱动监控器
    results['事件驱动监控器'] = test_event_driven_monitor()
    
    # 测试5：事件触发
    results['事件触发'] = test_event_trigger()
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过！")
        print("=" * 80)
        print("\n下一步：")
        print("1. 运行事件驱动监控器: python tasks/run_event_driven_monitor.py --mode fixed_interval")
        print("2. 或者监控指定股票: python tasks/run_event_driven_monitor.py --mode event_driven --stocks 000001.SZ 000002.SZ")
        print("=" * 80 + "\n")
    else:
        print("❌ 部分测试失败，请检查错误信息")
        print("=" * 80 + "\n")
        sys.exit(1)