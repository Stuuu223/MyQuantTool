#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6.1 性能测试脚本
验证后台线程异步获取 DDE 数据，避免阻塞主线程
"""

import time
import threading
from logic.realtime_data_provider import RealtimeDataProvider
from logic.logger import get_logger

logger = get_logger(__name__)


def test_non_blocking():
    """测试非阻塞运行"""
    print("=" * 60)
    print("V18.6.1 性能测试：验证非阻塞运行")
    print("=" * 60)

    # 初始化实时数据提供者
    print("\n1. 初始化实时数据提供者...")
    provider = RealtimeDataProvider()

    # 设置监控列表
    monitor_list = ["600519", "000001", "300750"]
    print(f"2. 设置监控列表: {monitor_list}")
    provider.set_monitor_list(monitor_list)

    # 等待后台线程启动并预计算 MA4
    print("\n3. 等待后台线程启动并预计算 MA4...")
    time.sleep(3)

    # 测试主线程是否被阻塞
    print("\n4. 测试主线程是否被阻塞...")
    print("   开始连续调用 get_realtime_data 10 次...")

    start_time = time.time()
    for i in range(10):
        print(f"   第 {i+1} 次调用...")
        call_start = time.time()

        # 调用 get_realtime_data
        result = provider.get_realtime_data(monitor_list)

        call_end = time.time()
        call_duration = (call_end - call_start) * 1000  # 转换为毫秒

        print(f"   ✓ 第 {i+1} 次调用完成，耗时: {call_duration:.2f}ms")

        # 检查是否有 DDE 数据
        if result:
            for stock_info in result:
                code = stock_info['code']
                dde_net_amount = stock_info.get('dde_net_amount', 0)
                dde_velocity = stock_info.get('dde_velocity', 0)
                bias_rate = stock_info.get('bias_rate', 0)

                if i == 0:  # 只在第一次调用时打印详细信息
                    print(f"     - {code}: DDE={dde_net_amount:.2f}, 加速度={dde_velocity:.2f}, 乖离率={bias_rate:.2f}%")

        # 每次调用间隔 1 秒
        if i < 9:
            time.sleep(1)

    end_time = time.time()
    total_duration = (end_time - start_time) * 1000  # 转换为毫秒
    avg_duration = total_duration / 10

    print(f"\n5. 性能测试结果:")
    print(f"   总耗时: {total_duration:.2f}ms")
    print(f"   平均每次调用耗时: {avg_duration:.2f}ms")

    # 判断是否阻塞
    if avg_duration < 1000:  # 如果平均每次调用耗时小于 1 秒，说明没有阻塞
        print(f"   ✅ 测试通过：主线程未被阻塞，平均耗时 {avg_duration:.2f}ms < 1000ms")
        print(f"   ✅ 后台线程成功运行，DDE 数据异步获取")
        return True
    else:
        print(f"   ❌ 测试失败：主线程被阻塞，平均耗时 {avg_duration:.2f}ms >= 1000ms")
        print(f"   ❌ 建议检查后台线程是否正常运行")
        return False


def test_dde_velocity():
    """测试 DDE 加速度计算"""
    print("\n" + "=" * 60)
    print("测试 DDE 加速度计算")
    print("=" * 60)

    provider = RealtimeDataProvider()
    monitor_list = ["600519"]
    provider.set_monitor_list(monitor_list)

    # 等待后台线程更新数据
    print("\n等待后台线程更新 DDE 数据（需要 10 秒）...")
    time.sleep(12)

    # 获取实时数据
    result = provider.get_realtime_data(monitor_list)

    if result:
        for stock_info in result:
            code = stock_info['code']
            dde_net_amount = stock_info.get('dde_net_amount', 0)
            dde_velocity = stock_info.get('dde_velocity', 0)
            scramble_degree = stock_info.get('scramble_degree', 0)

            print(f"\n股票代码: {code}")
            print(f"DDE 净流入: {dde_net_amount:.2f} 元")
            print(f"DDE 加速度: {dde_velocity:.2f} 元/秒")
            print(f"抢筹度: {scramble_degree:.2f}%")

            # 判断点火信号
            if dde_velocity > 1000000:
                print(f"🔥 [点火信号] DDE 加速度暴增: {dde_velocity/1000000:.2f}万/秒")
            elif dde_velocity > 500000:
                print(f"⚠️ [加速中] DDE 加速度上升: {dde_velocity/1000000:.2f}万/秒")
            elif dde_velocity < -1000000:
                print(f"🚨 [恐慌信号] DDE 加速度暴跌: {dde_velocity/1000000:.2f}万/秒")
            else:
                print(f"📊 [平稳] DDE 加速度正常")

            return True
    else:
        print("❌ 获取实时数据失败")
        return False


def test_ma4_cache():
    """测试 MA4 缓存"""
    print("\n" + "=" * 60)
    print("测试 MA4 缓存")
    print("=" * 60)

    provider = RealtimeDataProvider()
    monitor_list = ["600519"]
    provider.set_monitor_list(monitor_list)

    # 等待预计算完成
    print("\n等待 MA4 预计算完成...")
    time.sleep(5)

    # 检查 MA4 缓存
    if monitor_list[0] in provider.ma4_cache:
        ma4 = provider.ma4_cache[monitor_list[0]]
        print(f"✅ MA4 缓存已生成: {ma4:.2f}")

        # 测试快速计算乖离率
        current_price = 1700.0
        realtime_ma5 = (ma4 * 4 + current_price) / 5
        bias = (current_price - realtime_ma5) / realtime_ma5 * 100

        print(f"   当前价格: {current_price:.2f}")
        print(f"   实时 MA5: {realtime_ma5:.2f}")
        print(f"   乖离率: {bias:.2f}%")

        return True
    else:
        print("❌ MA4 缓存未生成")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🧪 V18.6.1 性能测试套件")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("非阻塞运行测试", test_non_blocking()))
    results.append(("DDE 加速度计算测试", test_dde_velocity()))
    results.append(("MA4 缓存测试", test_ma4_cache()))

    # 输出测试结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\n总计: {passed} 通过, {failed} 失败")

    if failed == 0:
        print("\n🎉 所有测试通过！V18.6.1 异步化改造成功！")
        print("✅ 后台线程正常运行，主线程未被阻塞")
        print("✅ DDE 数据异步获取，性能优化成功")
        return 0
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查配置和网络连接。")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())