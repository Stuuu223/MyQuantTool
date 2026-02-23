#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
metrics_utils 模块单元测试

测试 calc_vwap, calc_sustain_factor 等核心指标计算函数

Author: iFlow CLI
Date: 2026-02-23
"""

import unittest
import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.core.metrics_utils import (
    calc_vwap,
    calc_sustain_factor,
    calc_sustain_linear,
    calc_intraday_vwap_from_ticks,
    batch_calc_sustain,
    MetricsCalculationError,
    InsufficientDataError
)


class TestCalcVWAP(unittest.TestCase):
    """测试VWAP计算"""

    def setUp(self):
        """准备测试数据"""
        # 标准测试数据
        self.test_df = pd.DataFrame({
            'price': [10.0, 10.5, 11.0, 10.8, 11.2],
            'volume': [100, 200, 150, 120, 180]
        })

    def test_basic_calculation(self):
        """测试基本计算"""
        # VWAP = (10*100 + 10.5*200 + 11*150 + 10.8*120 + 11.2*180) / (100+200+150+120+180)
        # = (1000 + 2100 + 1650 + 1296 + 2016) / 750
        # = 8062 / 750 = 10.7493...
        result = calc_vwap(self.test_df, min_records=3)
        expected = 10.7493
        self.assertAlmostEqual(result, expected, places=3)

    def test_single_column_custom_names(self):
        """测试自定义列名"""
        df = pd.DataFrame({
            'p': [10.0, 11.0],
            'v': [100, 200]
        })
        result = calc_vwap(df, price_col='p', volume_col='v', min_records=2)
        # (10*100 + 11*200) / 300 = 3200/300 = 10.667
        self.assertAlmostEqual(result, 10.6667, places=3)

    def test_custom_min_records(self):
        """测试自定义最小记录数"""
        df = pd.DataFrame({
            'price': [10.0, 11.0],
            'volume': [100, 200]
        })
        # 默认需要10条，这里只有2条
        with self.assertRaises(InsufficientDataError):
            calc_vwap(df, min_records=10)
        
        # 降低要求后可以计算
        result = calc_vwap(df, min_records=2)
        self.assertIsNotNone(result)

    def test_empty_dataframe(self):
        """测试空DataFrame"""
        empty_df = pd.DataFrame({'price': [], 'volume': []})
        with self.assertRaises(ValueError):
            calc_vwap(empty_df)

    def test_none_input(self):
        """测试None输入"""
        with self.assertRaises(ValueError):
            calc_vwap(None)

    def test_missing_columns(self):
        """测试缺少列"""
        df = pd.DataFrame({'price': [10.0, 11.0]})
        with self.assertRaises(ValueError):
            calc_vwap(df)

    def test_with_nan_values(self):
        """测试包含NaN值"""
        df = pd.DataFrame({
            'price': [10.0, np.nan, 11.0, 10.5],
            'volume': [100, 200, 150, 120]
        })
        result = calc_vwap(df, min_records=2)
        # NaN被过滤，剩下3条记录
        self.assertIsNotNone(result)

    def test_with_zero_volume(self):
        """测试包含零成交量"""
        df = pd.DataFrame({
            'price': [10.0, 11.0, 12.0],
            'volume': [100, 0, 200]
        })
        result = calc_vwap(df, min_records=2)
        # 零成交量记录会被过滤（价格>0且成交量>=0）
        # 实际是 (10*100 + 0*11 + 12*200) / 300 = 3400/300 = 11.333
        # 但11这行volume=0，会被保留因为volume >= 0
        # 结果应该是 (10*100 + 11*0 + 12*200) / 300 = 3400/300 = 11.333
        self.assertAlmostEqual(result, 11.3333, places=3)

    def test_all_zero_volume(self):
        """测试全部零成交量"""
        df = pd.DataFrame({
            'price': [10.0, 11.0],
            'volume': [0, 0]
        })
        with self.assertRaises(MetricsCalculationError):
            calc_vwap(df, min_records=2)

    def test_negative_price(self):
        """测试负价格"""
        df = pd.DataFrame({
            'price': [10.0, -5.0, 11.0],
            'volume': [100, 200, 150]
        })
        # 负价格应该被过滤
        result = calc_vwap(df, min_records=1)
        # 只有正价格记录被使用
        self.assertIsNotNone(result)

    def test_negative_volume(self):
        """测试负成交量"""
        df = pd.DataFrame({
            'price': [10.0, 11.0],
            'volume': [100, -50]
        })
        result = calc_vwap(df, min_records=1)
        # 负成交量应该被过滤
        self.assertIsNotNone(result)


class TestCalcSustainFactor(unittest.TestCase):
    """测试承接力度计算"""

    def test_price_equal_vwap(self):
        """测试价格等于VWAP"""
        # price = vwap, factor = 0.5
        result = calc_sustain_factor(10.0, 10.0)
        self.assertAlmostEqual(result, 0.5, places=2)

    def test_price_above_vwap(self):
        """测试价格高于VWAP"""
        # price = 11, vwap = 10, price > vwap -> factor > 0.5
        result = calc_sustain_factor(11.0, 10.0)
        self.assertGreater(result, 0.5)
        self.assertLessEqual(result, 1.0)

    def test_price_below_vwap(self):
        """测试价格低于VWAP"""
        # price = 9, vwap = 10, price < vwap -> factor < 0.5
        result = calc_sustain_factor(9.0, 10.0)
        self.assertLess(result, 0.5)
        self.assertGreaterEqual(result, 0.0)

    def test_strong_sustain(self):
        """测试强承接（价格远高于VWAP）"""
        # price = 12, vwap = 10, 上涨20%
        result = calc_sustain_factor(12.0, 10.0)
        self.assertGreater(result, 0.6)  # sigmoid(0.8) ≈ 0.69
        self.assertLessEqual(result, 1.0)

    def test_weak_sustain(self):
        """测试弱承接（价格远低于VWAP）"""
        # price = 8, vwap = 10, 下跌20%
        result = calc_sustain_factor(8.0, 10.0)
        self.assertLess(result, 0.4)  # sigmoid(-0.8) ≈ 0.31
        self.assertGreaterEqual(result, 0.0)

    def test_invalid_input(self):
        """测试无效输入"""
        with self.assertRaises(ValueError):
            calc_sustain_factor(None, 10.0)
        with self.assertRaises(ValueError):
            calc_sustain_factor(10.0, None)
        with self.assertRaises(ValueError):
            calc_sustain_factor(-5.0, 10.0)
        with self.assertRaises(ValueError):
            calc_sustain_factor(10.0, 0)
        with self.assertRaises(ValueError):
            calc_sustain_factor(10.0, -5.0)

    def test_boundary_values(self):
        """测试边界值"""
        # 极高价格
        result = calc_sustain_factor(100.0, 10.0)
        self.assertAlmostEqual(result, 1.0, places=2)
        
        # 极低价格（接近0）
        result = calc_sustain_factor(0.01, 10.0)
        self.assertLess(result, 0.1)  # 应该接近0


class TestCalcSustainLinear(unittest.TestCase):
    """测试承接力度线性计算"""

    def test_price_equal_vwap(self):
        """测试价格等于VWAP"""
        result = calc_sustain_linear(10.0, 10.0)
        self.assertEqual(result, 0.5)

    def test_price_above_vwap(self):
        """测试价格高于VWAP"""
        # deviation = 0.1 (10%), max_deviation = 0.1
        # sustain = (0.1 / 0.2) + 0.5 = 1.0
        result = calc_sustain_linear(11.0, 10.0, max_deviation=0.1)
        self.assertEqual(result, 1.0)

    def test_price_below_vwap(self):
        """测试价格低于VWAP"""
        # deviation = -0.1 (10%), max_deviation = 0.1
        # sustain = (-0.1 / 0.2) + 0.5 = 0.0
        result = calc_sustain_linear(9.0, 10.0, max_deviation=0.1)
        self.assertEqual(result, 0.0)

    def test_half_deviation(self):
        """测试半偏离"""
        # deviation = 0.05 (5%), max_deviation = 0.1
        # sustain = (0.05 / 0.2) + 0.5 = 0.75
        result = calc_sustain_linear(10.5, 10.0, max_deviation=0.1)
        self.assertEqual(result, 0.75)


class TestCalcIntradayVWAPFromTicks(unittest.TestCase):
    """测试从Tick数据计算VWAP"""

    def setUp(self):
        """准备测试数据"""
        self.tick_df = pd.DataFrame({
            'time': ['09:30:00', '09:31:00', '09:32:00'],
            'price': [10.0, 10.5, 11.0],
            'volume': [100, 200, 150]
        })

    def test_basic_calculation(self):
        """测试基本计算"""
        result = calc_intraday_vwap_from_ticks(self.tick_df, min_records=2)
        
        self.assertIn('vwap', result)
        self.assertIn('total_volume', result)
        self.assertIn('avg_price', result)
        self.assertIn('price_std', result)
        self.assertIn('record_count', result)
        
        self.assertEqual(result['record_count'], 3)
        self.assertEqual(result['total_volume'], 450)

    def test_insufficient_data(self):
        """测试数据不足"""
        df = pd.DataFrame({
            'time': ['09:30:00'],
            'price': [10.0],
            'volume': [100]
        })
        with self.assertRaises(InsufficientDataError):
            calc_intraday_vwap_from_ticks(df)

    def test_missing_columns(self):
        """测试缺少列"""
        df = pd.DataFrame({'time': ['09:30:00'], 'price': [10.0]})
        with self.assertRaises(ValueError):
            calc_intraday_vwap_from_ticks(df)


class TestBatchCalcSustain(unittest.TestCase):
    """测试批量计算承接力度"""

    def test_basic_batch(self):
        """测试基本批量计算"""
        prices = [11.0, 10.0, 9.0]  # 高于、等于、低于VWAP
        vwaps = [10.0, 10.0, 10.0]
        
        results = batch_calc_sustain(prices, vwaps)
        
        self.assertEqual(len(results), 3)
        self.assertGreater(results[0], 0.5)  # 价格高于VWAP
        self.assertAlmostEqual(results[1], 0.5, places=2)  # 价格等于VWAP
        self.assertLess(results[2], 0.5)  # 价格低于VWAP

    def test_length_mismatch(self):
        """测试长度不匹配"""
        with self.assertRaises(ValueError):
            batch_calc_sustain([10.0, 11.0], [10.0])

    def test_empty_lists(self):
        """测试空列表"""
        results = batch_calc_sustain([], [])
        self.assertEqual(results, [])

    def test_single_element(self):
        """测试单元素"""
        results = batch_calc_sustain([11.0], [10.0])
        self.assertEqual(len(results), 1)
        self.assertGreater(results[0], 0.5)


class TestMetricsCalculationError(unittest.TestCase):
    """测试指标计算异常"""

    def test_error_message(self):
        """测试异常消息"""
        error = MetricsCalculationError("测试计算错误")
        self.assertEqual(str(error), "测试计算错误")


class TestInsufficientDataError(unittest.TestCase):
    """测试数据不足异常"""

    def test_error_message(self):
        """测试异常消息"""
        error = InsufficientDataError("测试数据不足")
        self.assertEqual(str(error), "测试数据不足")


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_vwap_and_sustain_workflow(self):
        """测试VWAP和承接力度计算完整流程"""
        # 1. 创建模拟Tick数据
        tick_data = pd.DataFrame({
            'price': [10.0, 10.2, 10.5, 10.3, 10.8, 11.0],
            'volume': [100, 150, 200, 120, 180, 220]
        })
        
        # 2. 计算VWAP
        vwap = calc_vwap(tick_data, min_records=3)
        self.assertIsNotNone(vwap)
        
        # 3. 计算当前价格相对于VWAP的承接力度
        current_price = 11.0
        sustain = calc_sustain_factor(current_price, vwap)
        
        # 4. 验证结果合理性
        self.assertGreaterEqual(sustain, 0.0)
        self.assertLessEqual(sustain, 1.0)
        
        # 当前价格11.0应该高于VWAP，承接力度应该大于0.5
        self.assertGreater(sustain, 0.5)

    def test_edge_cases(self):
        """测试边界情况"""
        # 极端价格差异
        sustain = calc_sustain_factor(100.0, 1.0)
        self.assertAlmostEqual(sustain, 1.0, places=2)
        
        sustain = calc_sustain_factor(0.01, 100.0)
        self.assertLess(sustain, 0.05)  # 极接近0


if __name__ == '__main__':
    unittest.main(verbosity=2)
