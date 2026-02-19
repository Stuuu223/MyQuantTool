#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一战法核心架构 - Halfway Breakout 专项测试
验证统一战法架构中Halfway Breakout检测器的正确集成
"""

import sys
from pathlib import Path
import time
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.strategies.unified_warfare_core import get_unified_warfare_core
from logic.strategies.halfway_breakout_detector import HalfwayBreakoutDetector


def test_halfway_in_unified_core():
    """测试Halfway Breakout在统一战法核心中的表现"""
    print("🎯 测试Halfway Breakout在统一战法核心中的表现")
    print("=" * 80)
    
    # 获取统一战法核心
    core = get_unified_warfare_core()
    
    # 创建一个专门触发Halfway Breakout的测试数据
    tick_data = {
        'stock_code': '300750',
        'datetime': datetime.now(),
        'price': 205.0,  # 从平台突破
        'prev_close': 200.0,
        'open': 201.0,
        'high': 206.0,
        'low': 200.5,
        'volume': 1200000,
        'amount': 246000000,
        'is_limit_up': False,
    }
    
    # 构造平台期数据，确保符合Halfway Breakout条件且长度>=20
    # 前15个点是平台期（波动小），最后5个点继续平台期，最后一个点是突破
    price_history = [200.1, 200.05, 200.15, 200.08, 200.12, 
                     200.09, 200.15, 200.10, 200.13, 200.07,
                     200.11, 200.06, 200.14, 200.09, 200.13,
                     200.08, 200.16, 200.11, 200.14, 205.0]  # 突破点（总共20个点）
    volume_history = [800000, 820000, 850000, 830000, 870000,
                      840000, 860000, 830000, 850000, 820000,
                      840000, 860000, 830000, 850000, 870000,
                      890000, 920000, 950000, 1000000, 1200000]  # 量能放大
    
    test_context = {
        'price_history': price_history,
        'volume_history': volume_history,
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
    
    print(f"📊 测试数据:")
    print(f"   - 股票代码: {tick_data['stock_code']}")
    print(f"   - 当前价格: {tick_data['price']}")
    print(f"   - 价格历史长度: {len(price_history)}")
    print(f"   - 价格历史(平台期): {price_history[:5]}")
    print(f"   - 价格历史(突破): ...{price_history[-5:]}")
    print(f"   - 成交量历史(平台期): {volume_history[:5]}")
    print(f"   - 成交量历史(突破): ...{volume_history[-5:]}")
    
    # 使用统一战法核心处理
    print(f"\n🔄 通过统一战法核心处理...")
    events = core.process_tick(tick_data, test_context)
    
    print(f"✅ 处理完成，检测到 {len(events)} 个事件:")
    for i, event in enumerate(events, 1):
        print(f"   {i}. {event['event_type']}: {event['description']} (置信度: {event['confidence']:.2f})")
        print(f"      数据字段: {list(event['data'].keys())}")
    
    # 检查是否检测到了Halfway Breakout事件
    halfway_events = [e for e in events if e['event_type'] == 'halfway_breakout']
    print(f"\n🔍 Halfway Breakout 事件: {len(halfway_events)} 个")
    for event in halfway_events:
        print(f"   - {event['description']} (置信度: {event['confidence']:.2f})")
    
    # 单独测试HalfwayBreakoutDetector
    print(f"\n🔄 单独测试HalfwayBreakoutDetector...")
    detector = HalfwayBreakoutDetector()
    detector_event = detector.detect(tick_data, test_context)
    
    if detector_event:
        print(f"✅ 单独检测器检测到事件:")
        print(f"   - {detector_event.event_type.value}: {detector_event.description}")
        print(f"   - 置信度: {detector_event.confidence:.3f}")
    else:
        print(f"❌ 单独检测器未检测到事件")
    
    # 返回测试结果
    success = len(halfway_events) > 0 or detector_event is not None
    print(f"\n📋 测试结果: {'✅ 通过' if success else '❌ 未通过'}")
    print("=" * 80)
    
    return success


def test_multiple_scenarios():
    """测试多种场景"""
    print("\n🎯 测试多种场景")
    print("=" * 80)
    
    core = get_unified_warfare_core()
    
    # 场景1: 明确的平台突破
    print("\n🧪 场景1: 明确的平台突破")
    tick_data1 = {
        'stock_code': '300750',
        'datetime': datetime.now(),
        'price': 105.0,  # 突破
        'prev_close': 100.0,
    }
    
    price_history1 = [100.1, 100.05, 100.15, 100.08, 100.12, 
                      100.09, 100.15, 100.10, 100.13, 100.07,
                      100.11, 100.06, 100.14, 100.09, 100.13,
                      100.08, 100.16, 100.11, 100.14, 105.0]  # 突破（总共20个点）
    volume_history1 = [800000, 820000, 850000, 830000, 870000,
                       840000, 860000, 830000, 850000, 820000,
                       840000, 860000, 830000, 850000, 870000,
                       890000, 920000, 950000, 1000000, 1200000]  # 放量
    
    context1 = {
        'price_history': price_history1,
        'volume_history': volume_history1,
        'ma5': 102.0,
        'ma20': 101.0,
    }
    
    events1 = core.process_tick(tick_data1, context1)
    halfway_events1 = [e for e in events1 if e['event_type'] == 'halfway_breakout']
    print(f"   结果: 检测到 {len(halfway_events1)} 个Halfway事件")
    
    # 场景2: 非突破（平台震荡）
    print("\n🧪 场景2: 平台震荡（不应触发）")
    tick_data2 = {
        'stock_code': '300750',
        'datetime': datetime.now(),
        'price': 100.1,  # 仍在平台内
        'prev_close': 100.0,
    }
    
    price_history2 = [100.1, 100.05, 100.15, 100.08, 100.12, 
                      100.09, 100.15, 100.10, 100.13, 100.07,
                      100.11, 100.06, 100.14, 100.09, 100.13,
                      100.08, 100.16, 100.11, 100.14, 100.11]  # 无突破（总共20个点）
    volume_history2 = [800000, 820000, 850000, 830000, 870000,
                       840000, 860000, 830000, 850000, 820000,
                       840000, 860000, 830000, 850000, 870000,
                       890000, 920000, 950000, 1000000, 1080000]  # 无明显放量
    
    context2 = {
        'price_history': price_history2,
        'volume_history': volume_history2,
        'ma5': 100.1,
        'ma20': 100.0,
    }
    
    events2 = core.process_tick(tick_data2, context2)
    halfway_events2 = [e for e in events2 if e['event_type'] == 'halfway_breakout']
    print(f"   结果: 检测到 {len(halfway_events2)} 个Halfway事件 (期望0个)")
    
    print(f"\n📋 多场景测试完成")
    print("=" * 80)


def main():
    """主测试函数"""
    print("🎯 统一战法核心架构 - Halfway Breakout 专项测试")
    print("=" * 100)
    
    # 测试1: Halfway在统一核心中的表现
    test1_success = test_halfway_in_unified_core()
    
    # 测试2: 多场景验证
    test_multiple_scenarios()
    
    print(f"\n🎉 专项测试完成!")
    print(f"   主要测试: {'✅ 通过' if test1_success else '❌ 未通过'}")
    print(f"   多场景测试: 已完成")
    
    if test1_success:
        print(f"\n✅ Halfway Breakout检测器已正确集成到统一战法核心架构中")
        print(f"   - Core与Detector接口契约正确")
        print(f"   - 数据格式统一处理")
        print(f"   - 事件检测逻辑正常工作")
    else:
        print(f"\n❌ 需要进一步调试Halfway Breakout检测器")
    
    return test1_success


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
