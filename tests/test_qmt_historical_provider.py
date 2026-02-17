#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QMTHistoricalProvider 单元测试

测试 QMTHistoricalProvider 的基本功能
"""

import unittest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider


class TestQMTHistoricalProvider(unittest.TestCase):
    """QMTHistoricalProvider 测试类"""

    def setUp(self):
        """测试前准备"""
        # 使用300997.SZ和一个已知的历史日期
        self.provider = QMTHistoricalProvider(
            stock_code="300997.SZ",
            start_time="20251114093000",
            end_time="20251114150000",
            period="tick"
        )

    def test_tick_count(self):
        """测试Tick数据数量"""
        count = self.provider.get_tick_count()
        # 验证行数 > 0
        self.assertGreater(count, 0, "Tick数据数量应该大于0")
        print(f"✅ Tick数据数量测试通过: {count}")

    def test_time_range(self):
        """测试时间范围"""
        first_time, last_time = self.provider.get_time_range()
        # 验证时间范围存在
        self.assertIsNotNone(first_time, "开始时间不应该为None")
        self.assertIsNotNone(last_time, "结束时间不应该为None")
        self.assertLessEqual(first_time, last_time, "开始时间应该小于等于结束时间")
        print(f"✅ 时间范围测试通过: {first_time} ~ {last_time}")

    def test_iter_ticks(self):
        """测试Tick迭代器"""
        tick_count = 0
        required_fields = ['time', 'last_price', 'volume', 'amount']
        
        for tick in self.provider.iter_ticks():
            # 验证字段齐全
            for field in required_fields:
                self.assertIn(field, tick, f"Tick数据中应该包含字段: {field}")
            
            tick_count += 1
            if tick_count >= 5:  # 只检查前5条
                break
        
        # 确保至少迭代了一条
        self.assertGreater(tick_count, 0, "应该能够迭代至少一条Tick数据")
        print(f"✅ Tick迭代器测试通过: 检查了{tick_count}条数据，字段齐全")

    def test_estimate_main_flow_from_ticks(self):
        """测试资金流推断"""
        flow_data = self.provider.estimate_main_flow_from_ticks()
        
        # 验证返回的数据结构
        expected_keys = [
            'main_net_inflow', 'main_buy', 'main_sell', 
            'retail_net_inflow', 'bid_pressure', 'price_strength', 'base_flow'
        ]
        
        for key in expected_keys:
            self.assertIn(key, flow_data, f"资金流数据应该包含字段: {key}")
        
        # 验证数据类型
        for key in expected_keys:
            self.assertIsInstance(flow_data[key], (int, float), f"{key} 应该是数值类型")
        
        print(f"✅ 资金流推断测试通过: {flow_data}")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 QMTHistoricalProvider 单元测试")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestQMTHistoricalProvider)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败！")
        for failure in result.failures:
            print(f"失败: {failure[0]}")
            print(failure[1])
        for error in result.errors:
            print(f"错误: {error[0]}")
            print(error[1])
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
