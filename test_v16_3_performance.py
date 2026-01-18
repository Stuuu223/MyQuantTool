#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16.3 生态看门人性能测试
测试核心功能和性能
"""

import unittest
from unittest.mock import Mock, patch
import time
from logic.iron_rule_monitor import IronRuleMonitor
from logic.signal_generator import SignalGenerator


class TestV16_3_Performance(unittest.TestCase):
    """V16.3 性能测试"""
    
    def setUp(self):
        """初始化测试环境"""
        self.iron_monitor = IronRuleMonitor()
        self.signal_generator = SignalGenerator()
    
    def test_check_value_distortion_performance(self):
        """测试 check_value_distortion 性能"""
        print("\n测试 check_value_distortion 性能...")
        
        # 模拟实时数据
        real_time_data = {
            'turnover': 8.0,  # 8% 换手率
            'pct_chg': 7.0,   # 7% 涨幅
            'amount': 1000000000,  # 10亿成交额
            'volume': 100000000,    # 1亿成交量
            'price': 10.0
        }
        
        # 测试性能
        start_time = time.time()
        result = self.iron_monitor.check_value_distortion('600519', real_time_data)
        end_time = time.time()
        
        elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        print(f"✅ check_value_distortion 耗时: {elapsed_time:.2f}ms")
        print(f"   结果: {result}")
        
        # 性能要求：应该在 100ms 内完成
        self.assertLess(elapsed_time, 100, "check_value_distortion 性能不达标")
    
    def test_cache_performance(self):
        """测试缓存性能"""
        print("\n测试缓存性能...")
        
        # 模拟实时数据
        real_time_data = {
            'turnover': 8.0,
            'pct_chg': 7.0,
            'amount': 1000000000,
            'volume': 100000000,
            'price': 10.0
        }
        
        # 第一次调用（缓存未命中）
        start_time = time.time()
        result1 = self.iron_monitor.check_value_distortion('600519', real_time_data)
        first_call_time = (time.time() - start_time) * 1000
        
        # 第二次调用（缓存命中）
        start_time = time.time()
        result2 = self.iron_monitor.check_value_distortion('600519', real_time_data)
        second_call_time = (time.time() - start_time) * 1000
        
        print(f"✅ 第一次调用（缓存未命中）: {first_call_time:.2f}ms")
        print(f"✅ 第二次调用（缓存命中）: {second_call_time:.2f}ms")
        print(f"✅ 性能提升: {(first_call_time / second_call_time):.1f}x")
        
        # 缓存命中应该更快
        self.assertLess(second_call_time, first_call_time, "缓存性能优化失败")
    
    def test_signal_generator_integration(self):
        """测试 SignalGenerator 集成性能"""
        print("\n测试 SignalGenerator 集成性能...")
        
        # 测试性能
        start_time = time.time()
        result = self.signal_generator.calculate_final_signal(
            stock_code='600519',
            ai_score=85.0,
            capital_flow=100000000,
            trend='UP',
            current_pct_change=7.0,
            yesterday_lhb_net_buy=0,
            open_pct_change=5.0,
            circulating_market_cap=10000000000,
            market_sentiment_score=60,
            market_status='震荡'
        )
        end_time = time.time()
        
        elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        print(f"✅ calculate_final_signal 耗时: {elapsed_time:.2f}ms")
        print(f"   结果: signal={result['signal']}, score={result['score']}")
        
        # 性能要求：应该在 2000ms 内完成（包括初始化开销）
        self.assertLess(elapsed_time, 2000, "calculate_final_signal 性能不达标")
    
    def test_batch_performance(self):
        """测试批量检查性能"""
        print("\n测试批量检查性能...")
        
        # 模拟多只股票的实时数据
        stock_list = ['600519', '000001', '000002', '600036', '601318']
        
        start_time = time.time()
        for stock_code in stock_list:
            real_time_data = {
                'turnover': 8.0,
                'pct_chg': 7.0,
                'amount': 1000000000,
                'volume': 100000000,
                'price': 10.0
            }
            result = self.iron_monitor.check_value_distortion(stock_code, real_time_data)
        end_time = time.time()
        
        elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
        avg_time = elapsed_time / len(stock_list)
        
        print(f"✅ 批量检查 {len(stock_list)} 只股票总耗时: {elapsed_time:.2f}ms")
        print(f"✅ 平均每只股票耗时: {avg_time:.2f}ms")
        
        # 性能要求：平均每只股票应该在 100ms 内完成
        self.assertLess(avg_time, 100, "批量检查性能不达标")


if __name__ == '__main__':
    # 运行测试
    print("=" * 80)
    print("V16.3 生态看门人性能测试")
    print("=" * 80)
    
    unittest.main(verbosity=2)