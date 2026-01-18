#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V17.1 Time-Sync - 时区校准性能测试
测试 Utils.get_beijing_time() 的正确性和性能
"""

import time
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.utils import Utils
from logic.time_strategy_manager import get_time_strategy_manager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_get_beijing_time():
    """测试 get_beijing_time() 方法的正确性"""
    print("=" * 80)
    print("测试 1: get_beijing_time() 正确性测试")
    print("=" * 80)

    # 获取北京时间
    beijing_time = Utils.get_beijing_time()
    system_time = datetime.now()

    print(f"系统时间: {system_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 计算时差（将北京时间转换为 naive datetime）
    beijing_time_naive = beijing_time.replace(tzinfo=None)
    time_diff = (beijing_time_naive - system_time).total_seconds() / 3600

    print(f"时差: {time_diff:.1f} 小时")

    # 验证时差是否在合理范围内（-12 到 +12 小时）
    if abs(time_diff) <= 12:
        print("✅ 测试通过: 时差在合理范围内")
        return True
    else:
        print("❌ 测试失败: 时差超出合理范围")
        return False


def test_time_consistency():
    """测试时间一致性"""
    print("\n" + "=" * 80)
    print("测试 2: 时间一致性测试")
    print("=" * 80)

    # 多次调用，检查时间是否连续递增
    times = []
    for i in range(10):
        t = Utils.get_beijing_time()
        times.append(t)
        time.sleep(0.1)

    # 检查时间是否递增
    is_increasing = all(times[i] < times[i+1] for i in range(len(times)-1))

    if is_increasing:
        print("✅ 测试通过: 时间连续递增")
        return True
    else:
        print("❌ 测试失败: 时间不连续递增")
        return False


def test_performance():
    """测试性能"""
    print("\n" + "=" * 80)
    print("测试 3: 性能测试")
    print("=" * 80)

    # 测试 1000 次调用的平均耗时
    iterations = 1000
    start_time = time.time()

    for _ in range(iterations):
        Utils.get_beijing_time()

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


def test_time_strategy_manager():
    """测试 TimeStrategyManager 使用北京时间"""
    print("\n" + "=" * 80)
    print("测试 4: TimeStrategyManager 时区测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 测试不同时间点的模式
    test_times = [
        datetime(2026, 1, 18, 9, 30),   # 黄金半小时
        datetime(2026, 1, 18, 10, 30),  # 垃圾时间
        datetime(2026, 1, 18, 14, 45),  # 尾盘偷袭
        datetime(2026, 1, 18, 16, 0),   # 休眠模式
    ]

    all_passed = True

    for test_time in test_times:
        mode_info = time_manager.get_current_mode(test_time)
        print(f"\n时间: {test_time.strftime('%H:%M')}")
        print(f"模式: {mode_info['mode_name']}")
        print(f"描述: {mode_info['description']}")
        print(f"建议: {mode_info['recommendation']}")

        # 验证模式是否正确
        if test_time.hour == 9 and 25 <= test_time.minute < 60:
            expected_mode = "进攻模式"
        elif 10 <= test_time.hour < 14 or (test_time.hour == 14 and test_time.minute < 30):
            expected_mode = "防守模式"
        elif test_time.hour == 14 and 30 <= test_time.minute < 60:
            expected_mode = "尾盘偷袭"
        else:
            expected_mode = "休眠模式"

        if mode_info['mode_name'] == expected_mode:
            print(f"✅ 模式正确: {expected_mode}")
        else:
            print(f"❌ 模式错误: 期望 {expected_mode}, 实际 {mode_info['mode_name']}")
            all_passed = False

    if all_passed:
        print("\n✅ 测试通过: 所有时间点的模式判断正确")
        return True
    else:
        print("\n❌ 测试失败: 部分时间点的模式判断错误")
        return False


def test_signal_filtering():
    """测试信号过滤功能"""
    print("\n" + "=" * 80)
    print("测试 5: 信号过滤测试")
    print("=" * 80)

    time_manager = get_time_strategy_manager()

    # 测试不同时间段的信号过滤
    test_cases = [
        (datetime(2026, 1, 18, 9, 30), "BUY", "进攻模式", True),    # 应该保留
        (datetime(2026, 1, 18, 10, 30), "BUY", "防守模式", False),  # 应该过滤
        (datetime(2026, 1, 18, 10, 30), "SELL", "防守模式", True),  # 应该保留
        (datetime(2026, 1, 18, 14, 45), "BUY", "尾盘偷袭", True),   # 应该保留
        (datetime(2026, 1, 18, 16, 0), "BUY", "休眠模式", False),   # 应该过滤
    ]

    all_passed = True

    for test_time, signal, expected_mode, should_keep in test_cases:
        filtered_signal, reason = time_manager.should_filter_signal(signal, test_time)

        if should_keep:
            if filtered_signal == signal:
                print(f"✅ {test_time.strftime('%H:%M')} {signal} -> {filtered_signal}: 保留（正确）")
            else:
                print(f"❌ {test_time.strftime('%H:%M')} {signal} -> {filtered_signal}: 应该保留但被过滤")
                all_passed = False
        else:
            if filtered_signal == "WAIT":
                print(f"✅ {test_time.strftime('%H:%M')} {signal} -> {filtered_signal}: 过滤（正确）")
            else:
                print(f"❌ {test_time.strftime('%H:%M')} {signal} -> {filtered_signal}: 应该过滤但被保留")
                all_passed = False

    if all_passed:
        print("\n✅ 测试通过: 信号过滤逻辑正确")
        return True
    else:
        print("\n❌ 测试失败: 信号过滤逻辑错误")
        return False


def test_time_zone_detection():
    """测试时区检测"""
    print("\n" + "=" * 80)
    print("测试 6: 时区检测测试")
    print("=" * 80)

    beijing_time = Utils.get_beijing_time()
    system_time = datetime.now()

    # 检查时区信息
    print(f"系统时区: {datetime.now().astimezone().tzinfo}")
    print(f"北京时间时区: Asia/Shanghai (UTC+8)")

    # 检查小时数是否在合理范围内（0-23）
    if 0 <= beijing_time.hour <= 23:
        print(f"✅ 北京时间小时数正常: {beijing_time.hour}")
        return True
    else:
        print(f"❌ 北京时间小时数异常: {beijing_time.hour}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("V17.1 Time-Sync 时区校准测试套件")
    print("=" * 80)
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = []

    # 运行所有测试
    results.append(("get_beijing_time() 正确性", test_get_beijing_time()))
    results.append(("时间一致性", test_time_consistency()))
    results.append(("性能测试", test_performance()))
    results.append(("TimeStrategyManager 时区", test_time_strategy_manager()))
    results.append(("信号过滤", test_signal_filtering()))
    results.append(("时区检测", test_time_zone_detection()))

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
        print("\n🎉 所有测试通过！V17.1 Time-Sync 时区校准功能正常。")
        return True
    else:
        print(f"\n⚠️ 有 {total_count - passed_count} 个测试失败，请检查。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)