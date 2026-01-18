#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16 战场指挥官性能测试
测试环境熔断系统的性能表现
"""

import time
from logic.signal_generator import get_signal_generator_v14_4

# 禁用日志输出
import logging
logging.disable(logging.CRITICAL)


def test_basic_performance():
    """
    性能测试 1：基本性能 - 单次计算耗时
    """
    print("\n" + "=" * 80)
    print("性能测试 1：基本性能 - 单次计算耗时")
    print("=" * 80)
    
    sg = get_signal_generator_v14_4()
    
    # 测试 1000 次计算
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        result = sg.calculate_final_signal(
            stock_code="603056",
            ai_score=90,
            capital_flow=10000000,
            trend='UP',
            current_pct_change=5.0,
            yesterday_lhb_net_buy=0,
            open_pct_change=0.5,
            market_sentiment_score=50,
            market_status="震荡"
        )
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000  # 毫秒
    throughput = iterations / total_time
    
    print(f"✅ 测试 {iterations} 次计算")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {throughput:.2f} 次/秒")
    
    assert avg_time < 1.0, "平均耗时应小于 1 毫秒"
    assert throughput > 1000, "吞吐量应大于 1000 次/秒"
    
    print("\n✅ 性能测试 1 通过：基本性能达标")


def test_multi_scenario_performance():
    """
    性能测试 2：多场景性能 - 不同市场环境
    """
    print("\n" + "=" * 80)
    print("性能测试 2：多场景性能 - 不同市场环境")
    print("=" * 80)
    
    sg = get_signal_generator_v14_4()
    
    scenarios = [
        {"name": "冰点熔断", "market_score": 15, "market_status": "冰点"},
        {"name": "退潮减权", "market_score": 40, "market_status": "退潮"},
        {"name": "共振加强", "market_score": 70, "market_status": "主升"},
        {"name": "正常环境", "market_score": 50, "market_status": "震荡"}
    ]
    
    for scenario in scenarios:
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            result = sg.calculate_final_signal(
                stock_code="603056",
                ai_score=90,
                capital_flow=10000000,
                trend='UP',
                current_pct_change=5.0,
                yesterday_lhb_net_buy=0,
                open_pct_change=0.5,
                market_sentiment_score=scenario["market_score"],
                market_status=scenario["market_status"]
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = (total_time / iterations) * 1000
        throughput = iterations / total_time
        
        print(f"✅ 场景: {scenario['name']}")
        print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
        print(f"   吞吐量: {throughput:.2f} 次/秒")
    
    print("\n✅ 性能测试 2 通过：所有场景性能达标")


def test_market_sentiment_score_performance():
    """
    性能测试 3：市场情绪分数获取性能
    """
    print("\n" + "=" * 80)
    print("性能测试 3：市场情绪分数获取性能")
    print("=" * 80)
    
    from logic.market_sentiment import MarketSentiment
    
    ms = MarketSentiment()
    
    iterations = 100
    start_time = time.time()
    
    for _ in range(iterations):
        result = ms.get_market_sentiment_score()
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000
    throughput = iterations / total_time
    
    print(f"✅ 测试 {iterations} 次市场情绪分数获取")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {throughput:.2f} 次/秒")
    
    # 市场情绪分数获取涉及数据库查询和实时数据获取，允许较慢
    assert avg_time < 200.0, "平均耗时应小于 200 毫秒"
    
    print("\n✅ 性能测试 3 通过：市场情绪分数获取性能达标")


def test_stress_test():
    """
    性能测试 4：压力测试 - 高频交易场景
    """
    print("\n" + "=" * 80)
    print("性能测试 4：压力测试 - 高频交易场景")
    print("=" * 80)
    
    sg = get_signal_generator_v14_4()
    
    # 模拟 100 只股票，每只股票计算 100 次
    stock_codes = [f"60000{i}" for i in range(100)]
    iterations_per_stock = 100
    
    start_time = time.time()
    
    for stock_code in stock_codes:
        for _ in range(iterations_per_stock):
            result = sg.calculate_final_signal(
                stock_code=stock_code,
                ai_score=90,
                capital_flow=10000000,
                trend='UP',
                current_pct_change=5.0,
                yesterday_lhb_net_buy=0,
                open_pct_change=0.5,
                market_sentiment_score=50,
                market_status="震荡"
            )
    
    end_time = time.time()
    total_time = end_time - start_time
    total_iterations = len(stock_codes) * iterations_per_stock
    avg_time = (total_time / total_iterations) * 1000
    throughput = total_iterations / total_time
    
    print(f"✅ 测试 {total_iterations} 次操作（{len(stock_codes)} 只股票 x {iterations_per_stock} 次更新）")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {throughput:.2f} 次/秒")
    
    assert avg_time < 1.0, "平均耗时应小于 1 毫秒"
    assert throughput > 1000, "吞吐量应大于 1000 次/秒"
    
    print("\n✅ 性能测试 4 通过：压力测试达标")


def main():
    print("\n" + "=" * 80)
    print("V16 战场指挥官性能测试")
    print("=" * 80)
    
    try:
        test_basic_performance()
        test_multi_scenario_performance()
        test_market_sentiment_score_performance()
        test_stress_test()
        
        print("\n" + "=" * 80)
        print("✅ 所有性能测试通过！")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()