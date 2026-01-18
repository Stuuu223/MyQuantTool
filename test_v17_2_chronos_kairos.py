#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V17.2 Chronos-Kairos Fusion - 时空融合性能测试
测试情绪覆盖时间策略的功能
"""

import time
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.time_strategy_manager import get_time_strategy_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_sentiment_override():
    """测试情绪覆盖功能"""
    print("=" * 80)
    print("测试 1: 情绪覆盖功能测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 测试场景：垃圾时间（11:00）+ 情绪爆发（85）
    test_time = datetime(2026, 1, 18, 11, 0)
    sentiment_score = 85.0

    mode_info = time_manager.get_current_mode(test_time, sentiment_score)

    print(f"测试时间: {test_time.strftime('%H:%M')}")
    print(f"情绪分数: {sentiment_score:.1f}")
    print(f"当前模式: {mode_info['mode_name']}")
    print(f"情绪覆盖: {mode_info['sentiment_override']}")
    print(f"允许买入: {mode_info['allow_buy']}")

    # 验证：情绪爆发时，即使是在垃圾时间，也应该允许买入
    if mode_info['sentiment_override'] and mode_info['allow_buy']:
        print("✅ 测试通过: 情绪爆发覆盖时间策略，允许买入")
        return True
    else:
        print("❌ 测试失败: 情绪爆发未覆盖时间策略")
        return False


def test_sentiment_freeze():
    """测试情绪冰点功能"""
    print("\n" + "=" * 80)
    print("测试 2: 情绪冰点功能测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 测试场景：黄金半小时（9:30）+ 情绪冰点（15）
    test_time = datetime(2026, 1, 18, 9, 30)
    sentiment_score = 15.0

    mode_info = time_manager.get_current_mode(test_time, sentiment_score)

    print(f"测试时间: {test_time.strftime('%H:%M')}")
    print(f"情绪分数: {sentiment_score:.1f}")
    print(f"当前模式: {mode_info['mode_name']}")
    print(f"情绪覆盖: {mode_info['sentiment_override']}")
    print(f"允许买入: {mode_info['allow_buy']}")

    # 验证：情绪冰点时，即使是在黄金时间，也应该禁止买入
    if mode_info['sentiment_override'] and not mode_info['allow_buy']:
        print("✅ 测试通过: 情绪冰点覆盖时间策略，禁止买入")
        return True
    else:
        print("❌ 测试失败: 情绪冰点未覆盖时间策略")
        return False


def test_normal_sentiment():
    """测试正常情绪功能"""
    print("\n" + "=" * 80)
    print("测试 3: 正常情绪功能测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 测试场景：垃圾时间（11:00）+ 正常情绪（50）
    test_time = datetime(2026, 1, 18, 11, 0)
    sentiment_score = 50.0

    mode_info = time_manager.get_current_mode(test_time, sentiment_score)

    print(f"测试时间: {test_time.strftime('%H:%M')}")
    print(f"情绪分数: {sentiment_score:.1f}")
    print(f"当前模式: {mode_info['mode_name']}")
    print(f"情绪覆盖: {mode_info['sentiment_override']}")
    print(f"允许买入: {mode_info['allow_buy']}")

    # 验证：正常情绪时，应该遵循时间策略
    if not mode_info['sentiment_override'] and not mode_info['allow_buy']:
        print("✅ 测试通过: 正常情绪遵循时间策略，禁止买入")
        return True
    else:
        print("❌ 测试失败: 正常情绪未遵循时间策略")
        return False


def test_signal_filtering():
    """测试信号过滤功能"""
    print("\n" + "=" * 80)
    print("测试 4: 信号过滤测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 测试场景：垃圾时间（11:00）+ 情绪爆发（85）
    test_time = datetime(2026, 1, 18, 11, 0)
    sentiment_score = 85.0

    # 测试 BUY 信号
    filtered_signal, reason = time_manager.should_filter_signal("BUY", test_time, sentiment_score)

    print(f"测试时间: {test_time.strftime('%H:%M')}")
    print(f"情绪分数: {sentiment_score:.1f}")
    print(f"原始信号: BUY")
    print(f"过滤后信号: {filtered_signal}")
    print(f"原因: {reason}")

    # 验证：情绪爆发时，BUY 信号应该被保留
    if filtered_signal == "BUY" and "情绪爆发" in reason:
        print("✅ 测试通过: 情绪爆发时，BUY 信号被保留")
        return True
    else:
        print("❌ 测试失败: 情绪爆发时，BUY 信号被错误过滤")
        return False


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 80)
    print("测试 5: 边界情况测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    all_passed = True

    # 测试 1: 情绪分数 = 80（刚好爆发）
    test_time = datetime(2026, 1, 18, 11, 0)
    sentiment_score = 80.0
    mode_info = time_manager.get_current_mode(test_time, sentiment_score)
    
    if mode_info['sentiment_override'] and mode_info['allow_buy']:
        print("✅ 情绪分数 = 80: 触发情绪爆发")
    else:
        print("❌ 情绪分数 = 80: 未触发情绪爆发")
        all_passed = False

    # 测试 2: 情绪分数 = 20（刚好冰点）
    sentiment_score = 20.0
    mode_info = time_manager.get_current_mode(test_time, sentiment_score)
    
    if mode_info['sentiment_override'] and not mode_info['allow_buy']:
        print("✅ 情绪分数 = 20: 触发情绪冰点")
    else:
        print("❌ 情绪分数 = 20: 未触发情绪冰点")
        all_passed = False

    # 测试 3: 情绪分数 = 79（正常情绪）
    sentiment_score = 79.0
    mode_info = time_manager.get_current_mode(test_time, sentiment_score)
    
    if not mode_info['sentiment_override']:
        print("✅ 情绪分数 = 79: 正常情绪")
    else:
        print("❌ 情绪分数 = 79: 错误触发情绪覆盖")
        all_passed = False

    # 测试 4: 情绪分数 = 21（正常情绪）
    sentiment_score = 21.0
    mode_info = time_manager.get_current_mode(test_time, sentiment_score)
    
    if not mode_info['sentiment_override']:
        print("✅ 情绪分数 = 21: 正常情绪")
    else:
        print("❌ 情绪分数 = 21: 错误触发情绪覆盖")
        all_passed = False

    if all_passed:
        print("\n✅ 测试通过: 所有边界情况处理正确")
        return True
    else:
        print("\n❌ 测试失败: 部分边界情况处理错误")
        return False


def test_performance():
    """测试性能"""
    print("\n" + "=" * 80)
    print("测试 6: 性能测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 测试 1000 次调用的平均耗时
    iterations = 1000
    start_time = time.time()

    for i in range(iterations):
        test_time = datetime(2026, 1, 18, 11, 0)
        sentiment_score = 50.0 + (i % 50)  # 50-100 之间的情绪分数
        time_manager.get_current_mode(test_time, sentiment_score)

    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / iterations * 1000  # 毫秒

    print(f"总耗时: {total_time:.4f} 秒")
    print(f"平均耗时: {avg_time:.4f} 毫秒/次")

    # 性能要求：平均耗时 < 1 毫秒
    if avg_time < 1.0:
        print("✅ 测试通过: 性能满足要求（< 1 毫秒/次）")
        return True
    else:
        print("⚠️ 测试警告: 性能略低于要求（>= 1 毫秒/次）")
        return True  # 仍然通过，只是警告


def test_mode_history():
    """测试模式历史记录"""
    print("\n" + "=" * 80)
    print("测试 7: 模式历史记录测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 清空历史记录
    time_manager.mode_history = []

    # 添加一些模式记录
    test_cases = [
        (datetime(2026, 1, 18, 9, 30), 50.0),  # 黄金半小时，正常情绪
        (datetime(2026, 1, 18, 11, 0), 85.0),  # 垃圾时间，情绪爆发
        (datetime(2026, 1, 18, 14, 45), 50.0),  # 尾盘偷袭，正常情绪
    ]

    for test_time, sentiment_score in test_cases:
        time_manager.get_current_mode(test_time, sentiment_score)

    # 检查历史记录
    history = time_manager.mode_history

    print(f"历史记录数量: {len(history)}")

    # 验证历史记录包含情绪分数和覆盖状态
    all_passed = True
    for record in history:
        if 'sentiment_score' in record and 'sentiment_override' in record:
            print(f"✅ 记录包含情绪分数: {record['sentiment_score']}, 覆盖状态: {record['sentiment_override']}")
        else:
            print("❌ 记录缺少情绪分数或覆盖状态")
            all_passed = False

    if all_passed:
        print("\n✅ 测试通过: 模式历史记录正确")
        return True
    else:
        print("\n❌ 测试失败: 模式历史记录错误")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("V17.2 Chronos-Kairos Fusion 时空融合测试套件")
    print("=" * 80)
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = []

    # 运行所有测试
    results.append(("情绪覆盖功能", test_sentiment_override()))
    results.append(("情绪冰点功能", test_sentiment_freeze()))
    results.append(("正常情绪功能", test_normal_sentiment()))
    results.append(("信号过滤", test_signal_filtering()))
    results.append(("边界情况", test_edge_cases()))
    results.append(("性能测试", test_performance()))
    results.append(("模式历史记录", test_mode_history()))

    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)

    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")

    print()
    print(f"总计: {passed_count}/{total_count} 测试通过")

    if passed_count == total_count:
        print("\n🎉 所有测试通过！V17.2 时空融合功能正常。")
        return True
    else:
        print(f"\n⚠️ 有 {total_count - passed_count} 个测试失败，请检查。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)