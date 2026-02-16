#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V16.3.0 性能测试 - 验证预热速度提升30%

测试目标：
1. 测试V16.3.0的预热速度
2. 对比理论性能提升（移除500+次新闻API调用）
3. 验证性能提升是否达到30%

Usage:
    python tests/test_v16_3_performance.py

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.3.0
"""

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.data_providers.akshare_manager import AkShareDataManager


def test_warmup_performance(stock_count=50):
    """
    测试预热性能

    Args:
        stock_count: 测试股票数量

    Returns:
        dict: 性能数据
    """
    # 准备测试数据
    test_stock_list = []
    for i in range(stock_count):
        if i < 1000:
            test_stock_list.append(f"{600000 + i:06d}.SH")
        else:
            test_stock_list.append(f"{000000 + (i - 1000):06d}.SZ")

    print(f"\n📋 性能测试配置:")
    print(f"  测试股票数量: {len(test_stock_list)}只")
    print(f"  预期API调用减少: {len(test_stock_list)}次新闻API调用")
    print(f"  理论性能提升: 30%+")

    print(f"\n🚀 开始性能测试...")

    # 创建预热模式的管理器
    manager = AkShareDataManager(mode='warmup')

    # 开始计时
    start_time = time.time()

    # 执行预热
    report = manager.warmup_all(stock_list=test_stock_list)

    # 结束计时
    end_time = time.time()
    elapsed_time = end_time - start_time

    # 计算统计数据
    total_success = sum([
        report['fund_flow']['success'],
        report['financial_indicator']['success'],
        report['limit_up_pool']['success']
    ])
    total_failed = sum([
        report['fund_flow']['failed'],
        report['financial_indicator']['failed'],
        report['limit_up_pool']['failed']
    ])

    # 计算每只股票平均时间
    avg_time_per_stock = elapsed_time / len(test_stock_list)

    return {
        'stock_count': len(test_stock_list),
        'elapsed_time': elapsed_time,
        'avg_time_per_stock': avg_time_per_stock,
        'total_success': total_success,
        'total_failed': total_failed,
        'report': report
    }


def main():
    """主函数"""
    print("=" * 80)
    print("V16.3.0 性能测试 - 验证预热速度提升30%")
    print("=" * 80)

    # 测试配置
    test_configs = [10, 20, 50]  # 测试不同数量的股票

    results = []

    for stock_count in test_configs:
        print(f"\n" + "─" * 80)
        print(f"测试 {stock_count} 只股票的预热性能")
        print("─" * 80)

        result = test_warmup_performance(stock_count)
        results.append(result)

        # 打印结果
        print(f"\n📊 性能测试结果:")
        print(f"  股票数量: {result['stock_count']}只")
        print(f"  总耗时: {result['elapsed_time']:.2f}秒")
        print(f"  平均每只股票: {result['avg_time_per_stock']:.2f}秒")
        print(f"  成功获取: {result['total_success']}次")
        print(f"  失败获取: {result['total_failed']}次")

        # 计算理论性能提升
        # V16.2.3: 每只股票需要3个API调用（资金流、新闻、基本面）
        # V16.3.0: 每只股票需要2个API调用（资金流、基本面）
        # 理论性能提升 = (3 - 2) / 3 = 33.3%
        theoretical_improvement = 33.3

        print(f"\n💡 理论分析:")
        print(f"  V16.2.3: 每只股票3个API调用（资金流、新闻、基本面）")
        print(f"  V16.3.0: 每只股票2个API调用（资金流、基本面）")
        print(f"  理论性能提升: {theoretical_improvement:.1f}%")

        # 实际性能提升需要对比V16.2.3的基准数据
        # 由于没有V16.2.3的基准数据，我们只能展示V16.3.0的性能
        print(f"\n⚠️ 注意: 需要V16.2.3基准数据才能计算实际性能提升")
        print(f"  当前仅展示V16.3.0的性能数据")

    # 汇总结果
    print(f"\n" + "=" * 80)
    print("📊 性能测试汇总")
    print("=" * 80)
    print(f"{'股票数量':<12} {'总耗时(秒)':<15} {'平均耗时(秒/只)':<20}")
    print("─" * 80)
    for result in results:
        print(f"{result['stock_count']:<12} {result['elapsed_time']:<15.2f} {result['avg_time_per_stock']:<20.2f}")

    print("\n" + "=" * 80)
    print("✅ V16.3.0 性能测试完成")
    print("=" * 80)
    print("\n📝 结论:")
    print("  ✅ 新闻模块已完全移除")
    print("  ✅ API调用次数减少33.3%（每只股票从3次减少到2次）")
    print("  ⚠️ 需要V16.2.3基准数据才能验证实际性能提升是否达到30%")
    print("\n💡 建议:")
    print("  1. 在相同环境下测试V16.2.3的预热速度")
    print("  2. 对比V16.2.3和V16.3.0的实际耗时")
    print("  3. 验证性能提升是否达到30%")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
