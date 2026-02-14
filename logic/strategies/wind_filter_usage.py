#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
板块共振过滤器使用示例

演示如何在项目中使用 WindFilter 模块
"""

import sys
sys.path.insert(0, '.')

from logic.strategies.wind_filter import get_wind_filter

def example_basic_usage():
    """基础使用示例"""
    print("=" * 80)
    print("示例1: 基础使用")
    print("=" * 80)

    # 获取单例
    wind_filter = get_wind_filter()

    # 检查单只股票
    result = wind_filter.check_sector_resonance('000001')

    print(f"股票: 000001")
    print(f"行业: {result['industry']}")
    print(f"是否共振: {result['is_resonance']}")
    print(f"共振分数: {result['resonance_score']:.2f}")
    print(f"通过条件: {', '.join(result['passed_conditions'])}")

    # 根据结果决定是否通过
    if result['is_resonance']:
        print("✅ 通过板块共振检查，可以继续")
    else:
        print("❌ 未通过板块共振检查，拒绝交易")


def example_batch_check():
    """批量检查示例"""
    print("\n" + "=" * 80)
    print("示例2: 批量检查")
    print("=" * 80)

    wind_filter = get_wind_filter()

    # 观察池股票
    watchlist = ['000001', '000002', '600519', '000858', '601318']

    # 批量检查
    results = wind_filter.batch_check_resonance(watchlist)

    # 筛选通过共振检查的股票
    passed_stocks = [
        code for code, result in results.items()
        if result['is_resonance']
    ]

    print(f"观察池股票: {len(watchlist)} 只")
    print(f"通过共振检查: {len(passed_stocks)} 只")

    for code in passed_stocks:
        result = results[code]
        print(f"  ✅ {code} ({result['industry']}) 分数:{result['resonance_score']:.2f}")


def example_integration_with_triple_funnel():
    """与三漏斗扫描器集成示例"""
    print("\n" + "=" * 80)
    print("示例3: 与三漏斗扫描器集成")
    print("=" * 80)

    wind_filter = get_wind_filter()

    # 模拟三漏斗扫描器的Level 2筛选结果
    level2_passed_stocks = ['000001', '000002', '600519']

    print(f"Level 2 通过股票: {len(level2_passed_stocks)} 只")

    # 在Level 2之后添加板块共振检查
    level3_candidates = []
    for code in level2_passed_stocks:
        result = wind_filter.check_sector_resonance(code)

        if result['is_resonance']:
            level3_candidates.append(code)
            print(f"  ✅ {code} 通过共振检查，进入Level 3")
        else:
            print(f"  ❌ {code} 未通过共振检查，被过滤")

    print(f"\nLevel 3 候选股票: {len(level3_candidates)} 只")


def example_custom_thresholds():
    """自定义阈值示例"""
    print("\n" + "=" * 80)
    print("示例4: 自定义阈值")
    print("=" * 80)

    wind_filter = get_wind_filter()

    # 获取原始结果
    result = wind_filter.check_sector_resonance('000001')

    # 自定义判断逻辑（更严格）
    custom_passed = (
        result['limit_up_count'] >= 5 and  # 至少5只涨停
        result['breadth'] >= 0.5 and       # 至少50%上涨
        result['resonance_score'] >= 0.8   # 共振分数至少0.8
    )

    print(f"标准判断: {'✅ 通过' if result['is_resonance'] else '❌ 未通过'}")
    print(f"自定义判断: {'✅ 通过' if custom_passed else '❌ 未通过'} (更严格)")
    print(f"\n当前参数:")
    print(f"  - 涨停股数: {result['limit_up_count']} / {wind_filter.MIN_LIMIT_UP_COUNT}")
    print(f"  - 上涨占比: {result['breadth']*100:.1f}% / {wind_filter.MIN_RISE_RATIO*100:.0f}%")
    print(f"  - 共振分数: {result['resonance_score']:.2f}")


def example_performance_monitoring():
    """性能监控示例"""
    print("\n" + "=" * 80)
    print("示例5: 性能监控")
    print("=" * 80)

    import time

    wind_filter = get_wind_filter()

    # 测试性能
    test_codes = ['000001', '000002', '600519', '000858', '601318']

    start_time = time.time()
    for code in test_codes:
        wind_filter.check_sector_resonance(code)
    elapsed = (time.time() - start_time) * 1000

    avg_time = elapsed / len(test_codes)

    print(f"测试股票数: {len(test_codes)}")
    print(f"总耗时: {elapsed:.1f}ms")
    print(f"平均耗时: {avg_time:.1f}ms")

    # 查看缓存信息
    cache_info = wind_filter.get_cache_info()
    print(f"\n缓存统计:")
    print(f"  总缓存数: {cache_info['总缓存数']}")
    print(f"  板块相关缓存数: {cache_info['板块相关缓存数']}")


def main():
    """运行所有示例"""
    print("\n" + "🎯 板块共振过滤器使用示例".center(80, "="))
    print()

    example_basic_usage()
    example_batch_check()
    example_integration_with_triple_funnel()
    example_custom_thresholds()
    example_performance_monitoring()

    print("\n" + "=" * 80)
    print("✅ 所有示例运行完成")
    print("=" * 80)


if __name__ == "__main__":
    main()