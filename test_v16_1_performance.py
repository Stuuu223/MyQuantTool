#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16.1 Bug Hunter 性能测试
测试修复后的系统性能
"""

import time
from logic.signal_generator import get_signal_generator_v14_4
from logic.dragon_tactics import DragonTactics
from logic.predator_system import PredatorSystem
import pandas as pd
import numpy as np

# 禁用日志输出
import logging
logging.disable(logging.CRITICAL)


def test_signal_generator_performance():
    """
    性能测试 1：SignalGenerator 性能测试
    """
    print("\n" + "=" * 80)
    print("性能测试 1：SignalGenerator 性能测试")
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
            yesterday_lhb_net_buy=60000000,
            open_pct_change=4.0,
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
    
    print("\n✅ 性能测试 1 通过：SignalGenerator 性能达标")


def test_dragon_tactics_performance():
    """
    性能测试 2：DragonTactics 性能测试
    """
    print("\n" + "=" * 80)
    print("性能测试 2：DragonTactics 性能测试")
    print("=" * 80)
    
    dt = DragonTactics()
    
    stock_info = {
        'code': '603056',
        'name': '德恩精工',
        'price': 10.2,
        'open': 10.5,
        'pre_close': 10.0,
        'high': 10.6,
        'low': 10.1,
        'bid_volume': 1000,
        'ask_volume': 500,
        'volume': 100000,
        'turnover': 10.0,
        'volume_ratio': 2.0,
        'prev_pct_change': 5.0,
        'is_20cm': False
    }
    
    # 测试 1000 次计算
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        result = dt.check_dragon_criteria(stock_info)
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000
    throughput = iterations / total_time
    
    print(f"✅ 测试 {iterations} 次计算")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {throughput:.2f} 次/秒")
    
    assert avg_time < 1.0, "平均耗时应小于 1 毫秒"
    assert throughput > 1000, "吞吐量应大于 1000 次/秒"
    
    print("\n✅ 性能测试 2 通过：DragonTactics 性能达标")


def test_predator_system_performance():
    """
    性能测试 3：PredatorSystem 性能测试
    """
    print("\n" + "=" * 80)
    print("性能测试 3：PredatorSystem 性能测试")
    print("=" * 80)
    
    predator = PredatorSystem()
    
    stock_data = {
        'symbol': '603056',
        'name': '德恩精工',
        'code': '603056'
    }
    
    realtime_data = {
        'bid1_volume': 1000,
        'price': 10.0,
        'now': 10.0,
        'circulating_market_cap': 5000000000,
        'limit_up': True
    }
    
    # 测试 1000 次计算
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        score, reason = predator.check_limit_strength(
            stock_data=stock_data,
            realtime_data=realtime_data,
            score=100
        )
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000
    throughput = iterations / total_time
    
    print(f"✅ 测试 {iterations} 次计算")
    print(f"   总耗时: {total_time:.4f} 秒")
    print(f"   平均耗时: {avg_time:.4f} 毫秒/次")
    print(f"   吞吐量: {throughput:.2f} 次/秒")
    
    assert avg_time < 1.0, "平均耗时应小于 1 毫秒"
    assert throughput > 1000, "吞吐量应大于 1000 次/秒"
    
    print("\n✅ 性能测试 3 通过：PredatorSystem 性能达标")


def test_stress_test():
    """
    性能测试 4：压力测试 - 高频交易场景
    """
    print("\n" + "=" * 80)
    print("性能测试 4：压力测试 - 高频交易场景")
    print("=" * 80)
    
    sg = get_signal_generator_v14_4()
    dt = DragonTactics()
    predator = PredatorSystem()
    
    # 模拟 100 只股票，每只股票计算 100 次
    stock_codes = [f"60000{i}" for i in range(100)]
    iterations_per_stock = 100
    
    start_time = time.time()
    
    for stock_code in stock_codes:
        for _ in range(iterations_per_stock):
            # SignalGenerator
            result = sg.calculate_final_signal(
                stock_code=stock_code,
                ai_score=90,
                capital_flow=10000000,
                trend='UP',
                current_pct_change=5.0,
                yesterday_lhb_net_buy=60000000,
                open_pct_change=4.0,
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
    print("V16.1 Bug Hunter 性能测试")
    print("=" * 80)
    
    try:
        test_signal_generator_performance()
        test_dragon_tactics_performance()
        test_predator_system_performance()
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