"""
MetricDefinitions单元测试

测试策略:
    1. 正常计算测试 - 验证公式正确性
    2. 边界条件测试 - 零值、极值处理
    3. 错误处理测试 - 异常输入的验证
    4. 类型检查测试 - 输入类型验证
    5. DataFrame操作测试 - VWAP计算
"""
import unittest
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 确保可以导入被测模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from logic.core.metric_definitions import MetricDefinitions


class TestTRUE_CHANGE(unittest.TestCase):
    """TRUE_CHANGE方法测试"""
    
    def test_normal_increase(self):
        """测试正常上涨情况"""
        result = MetricDefinitions.TRUE_CHANGE(110.0, 100.0)
        self.assertAlmostEqual(result, 10.0, places=6)
    
    def test_normal_decrease(self):
        """测试正常下跌情况"""
        result = MetricDefinitions.TRUE_CHANGE(95.0, 100.0)
        self.assertAlmostEqual(result, -5.0, places=6)
    
    def test_no_change(self):
        """测试价格不变"""
        result = MetricDefinitions.TRUE_CHANGE(100.0, 100.0)
        self.assertAlmostEqual(result, 0.0, places=6)
    
    def test_large_increase(self):
        """测试大幅上涨（涨停）"""
        result = MetricDefinitions.TRUE_CHANGE(110.0, 100.0)
        self.assertAlmostEqual(result, 10.0, places=6)
    
    def test_large_decrease(self):
        """测试大幅下跌（跌停）"""
        result = MetricDefinitions.TRUE_CHANGE(90.0, 100.0)
        self.assertAlmostEqual(result, -10.0, places=6)
    
    def test_zero_pre_close(self):
        """测试昨收为0时抛出异常"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TRUE_CHANGE(100.0, 0.0)
        self.assertIn("昨收价必须>0", str(context.exception))
    
    def test_negative_pre_close(self):
        """测试昨收为负数时抛出异常"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TRUE_CHANGE(100.0, -10.0)
        self.assertIn("昨收价必须>0", str(context.exception))
    
    def test_negative_current_price(self):
        """测试当前价格为负数时抛出异常"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TRUE_CHANGE(-100.0, 100.0)
        self.assertIn("当前价格不能为负数", str(context.exception))
    
    def test_integer_inputs(self):
        """测试整数输入"""
        result = MetricDefinitions.TRUE_CHANGE(110, 100)
        self.assertAlmostEqual(result, 10.0, places=6)
    
    def test_invalid_type_current(self):
        """测试当前价格类型错误"""
        with self.assertRaises(TypeError) as context:
            MetricDefinitions.TRUE_CHANGE("100", 100.0)
        self.assertIn("current_price必须是数字类型", str(context.exception))
    
    def test_invalid_type_pre_close(self):
        """测试昨收价类型错误"""
        with self.assertRaises(TypeError) as context:
            MetricDefinitions.TRUE_CHANGE(100.0, "100")
        self.assertIn("pre_close必须是数字类型", str(context.exception))
    
    def test_very_small_pre_close(self):
        """测试极小昨收价"""
        result = MetricDefinitions.TRUE_CHANGE(0.0002, 0.0001)
        self.assertAlmostEqual(result, 100.0, places=6)


class TestGAP_UP_PREMIUM(unittest.TestCase):
    """GAP_UP_PREMIUM方法测试"""
    
    def test_normal_gap_up(self):
        """测试正常高开"""
        result = MetricDefinitions.GAP_UP_PREMIUM(105.0, 100.0)
        self.assertAlmostEqual(result, 5.0, places=6)
    
    def test_normal_gap_down(self):
        """测试正常低开"""
        result = MetricDefinitions.GAP_UP_PREMIUM(98.0, 100.0)
        self.assertAlmostEqual(result, -2.0, places=6)
    
    def test_flat_open(self):
        """测试平开"""
        result = MetricDefinitions.GAP_UP_PREMIUM(100.0, 100.0)
        self.assertAlmostEqual(result, 0.0, places=6)
    
    def test_zero_pre_close(self):
        """测试昨收为0时抛出异常"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.GAP_UP_PREMIUM(100.0, 0.0)
        self.assertIn("昨收价必须>0", str(context.exception))
    
    def test_negative_open(self):
        """测试开盘价为负数"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.GAP_UP_PREMIUM(-10.0, 100.0)
        self.assertIn("开盘价不能为负数", str(context.exception))
    
    def test_invalid_type(self):
        """测试类型错误"""
        with self.assertRaises(TypeError):
            MetricDefinitions.GAP_UP_PREMIUM("100", 100)


class TestTRUE_AMPLITUDE(unittest.TestCase):
    """TRUE_AMPLITUDE方法测试"""
    
    def test_normal_amplitude(self):
        """测试正常振幅"""
        result = MetricDefinitions.TRUE_AMPLITUDE(110.0, 90.0, 100.0)
        self.assertAlmostEqual(result, 20.0, places=6)
    
    def test_zero_amplitude(self):
        """测试零振幅（最高价=最低价）"""
        result = MetricDefinitions.TRUE_AMPLITUDE(100.0, 100.0, 100.0)
        self.assertAlmostEqual(result, 0.0, places=6)
    
    def test_small_amplitude(self):
        """测试小振幅"""
        result = MetricDefinitions.TRUE_AMPLITUDE(101.0, 99.0, 100.0)
        self.assertAlmostEqual(result, 2.0, places=6)
    
    def test_high_equals_low(self):
        """测试最高等于最低"""
        result = MetricDefinitions.TRUE_AMPLITUDE(50.0, 50.0, 100.0)
        self.assertAlmostEqual(result, 0.0, places=6)
    
    def test_zero_pre_close(self):
        """测试昨收为0时抛出异常"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TRUE_AMPLITUDE(110.0, 90.0, 0.0)
        self.assertIn("昨收价必须>0", str(context.exception))
    
    def test_low_greater_than_high(self):
        """测试最低价大于最高价"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TRUE_AMPLITUDE(90.0, 110.0, 100.0)
        self.assertIn("最低价不能大于最高价", str(context.exception))
    
    def test_negative_high(self):
        """测试最高价为负"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TRUE_AMPLITUDE(-10.0, 90.0, 100.0)
        self.assertIn("价格不能为负数", str(context.exception))
    
    def test_negative_low(self):
        """测试最低价为负"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TRUE_AMPLITUDE(110.0, -10.0, 100.0)
        self.assertIn("价格不能为负数", str(context.exception))
    
    def test_invalid_type_high(self):
        """测试最高价类型错误"""
        with self.assertRaises(TypeError):
            MetricDefinitions.TRUE_AMPLITUDE("110", 90.0, 100.0)
    
    def test_invalid_type_low(self):
        """测试最低价类型错误"""
        with self.assertRaises(TypeError):
            MetricDefinitions.TRUE_AMPLITUDE(110.0, "90", 100.0)
    
    def test_invalid_type_pre_close(self):
        """测试昨收价类型错误"""
        with self.assertRaises(TypeError):
            MetricDefinitions.TRUE_AMPLITUDE(110.0, 90.0, "100")


class TestVWAP(unittest.TestCase):
    """VWAP方法测试"""
    
    def test_normal_vwap(self):
        """测试正常VWAP计算"""
        df = pd.DataFrame({
            'price': [100.0, 101.0, 102.0],
            'volume': [1000, 2000, 3000]
        })
        result = MetricDefinitions.VWAP(df)
        # (100*1000 + 101*2000 + 102*3000) / (1000+2000+3000) = 101.333...
        expected = (100*1000 + 101*2000 + 102*3000) / 6000
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_single_row(self):
        """测试单行数据"""
        df = pd.DataFrame({
            'price': [100.0],
            'volume': [1000]
        })
        result = MetricDefinitions.VWAP(df)
        self.assertAlmostEqual(result, 100.0, places=6)
    
    def test_custom_column_names(self):
        """测试自定义列名"""
        df = pd.DataFrame({
            'p': [100.0, 102.0],
            'v': [1000, 1000]
        })
        result = MetricDefinitions.VWAP(df, price_col='p', volume_col='v')
        self.assertAlmostEqual(result, 101.0, places=6)
    
    def test_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame({'price': [], 'volume': []})
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.VWAP(df)
        self.assertIn("DataFrame为空", str(context.exception))
    
    def test_missing_price_column(self):
        """测试缺少价格列"""
        df = pd.DataFrame({
            'other': [100.0],
            'volume': [1000]
        })
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.VWAP(df)
        self.assertIn("缺少价格列", str(context.exception))
    
    def test_missing_volume_column(self):
        """测试缺少成交量列"""
        df = pd.DataFrame({
            'price': [100.0],
            'other': [1000]
        })
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.VWAP(df)
        self.assertIn("缺少成交量列", str(context.exception))
    
    def test_zero_total_volume(self):
        """测试总成交量为0"""
        df = pd.DataFrame({
            'price': [100.0, 101.0],
            'volume': [0, 0]
        })
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.VWAP(df)
        self.assertIn("成交量总和为0", str(context.exception))
    
    def test_with_na_values(self):
        """测试包含NA值"""
        df = pd.DataFrame({
            'price': [100.0, np.nan, 102.0],
            'volume': [1000, 2000, 3000]
        })
        # 应该能处理NA值
        result = MetricDefinitions.VWAP(df)
        # 忽略nan行: (100*1000 + 102*3000) / (1000+3000) = 101.5
        expected = (100*1000 + 102*3000) / 4000
        self.assertAlmostEqual(result, expected, places=6)
    
    def test_all_na_prices(self):
        """测试价格全部为NA"""
        df = pd.DataFrame({
            'price': [np.nan, np.nan],
            'volume': [1000, 2000]
        })
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.VWAP(df)
        self.assertIn("全部为NaN", str(context.exception))
    
    def test_all_na_volumes(self):
        """测试成交量全部为NA"""
        df = pd.DataFrame({
            'price': [100.0, 101.0],
            'volume': [np.nan, np.nan]
        })
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.VWAP(df)
        self.assertIn("全部为NaN", str(context.exception))
    
    def test_not_dataframe(self):
        """测试输入不是DataFrame"""
        with self.assertRaises(TypeError) as context:
            MetricDefinitions.VWAP([1, 2, 3])
        self.assertIn("必须是pandas.DataFrame", str(context.exception))
    
    def test_result_is_float(self):
        """测试结果类型为float"""
        df = pd.DataFrame({
            'price': [100.0, 102.0],
            'volume': [1000, 1000]
        })
        result = MetricDefinitions.VWAP(df)
        self.assertIsInstance(result, float)


class TestTURNOVER_RATE(unittest.TestCase):
    """TURNOVER_RATE方法测试"""
    
    def test_normal_turnover(self):
        """测试正常换手率"""
        result = MetricDefinitions.TURNOVER_RATE(1000000, 100000000)
        self.assertAlmostEqual(result, 1.0, places=6)
    
    def test_high_turnover(self):
        """测试高换手率（超过100%）"""
        result = MetricDefinitions.TURNOVER_RATE(200000000, 100000000)
        self.assertAlmostEqual(result, 200.0, places=6)
    
    def test_zero_turnover(self):
        """测试零成交"""
        result = MetricDefinitions.TURNOVER_RATE(0, 100000000)
        self.assertAlmostEqual(result, 0.0, places=6)
    
    def test_full_turnover(self):
        """测试100%换手"""
        result = MetricDefinitions.TURNOVER_RATE(100000000, 100000000)
        self.assertAlmostEqual(result, 100.0, places=6)
    
    def test_zero_float_volume(self):
        """测试流通股本为0"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TURNOVER_RATE(1000000, 0)
        self.assertIn("流通股本必须>0", str(context.exception))
    
    def test_negative_float_volume(self):
        """测试流通股本为负"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TURNOVER_RATE(1000000, -1000000)
        self.assertIn("流通股本必须>0", str(context.exception))
    
    def test_negative_volume(self):
        """测试成交量为负"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.TURNOVER_RATE(-1000000, 100000000)
        self.assertIn("成交量不能为负数", str(context.exception))
    
    def test_invalid_type_volume(self):
        """测试成交量类型错误"""
        with self.assertRaises(TypeError):
            MetricDefinitions.TURNOVER_RATE("1000000", 100000000)
    
    def test_invalid_type_float(self):
        """测试流通股本类型错误"""
        with self.assertRaises(TypeError):
            MetricDefinitions.TURNOVER_RATE(1000000, "100000000")
    
    def test_very_small_float(self):
        """测试极小流通股本"""
        result = MetricDefinitions.TURNOVER_RATE(100, 1)
        self.assertAlmostEqual(result, 10000.0, places=6)


class TestLIMIT_UP_PRICE(unittest.TestCase):
    """LIMIT_UP_PRICE方法测试"""
    
    def test_normal_limit_up(self):
        """测试正常涨停价"""
        result = MetricDefinitions.LIMIT_UP_PRICE(100.0, 10.0)
        self.assertEqual(result, 110.0)
    
    def test_st_limit_up(self):
        """测试ST股涨停价（5%）"""
        result = MetricDefinitions.LIMIT_UP_PRICE(100.0, 5.0)
        self.assertEqual(result, 105.0)
    
    def test_chinext_limit_up(self):
        """测试创业板涨停价（20%）"""
        result = MetricDefinitions.LIMIT_UP_PRICE(100.0, 20.0)
        self.assertEqual(result, 120.0)
    
    def test_rounding(self):
        """测试舍入到2位小数"""
        result = MetricDefinitions.LIMIT_UP_PRICE(10.03, 10.0)
        self.assertEqual(result, 11.03)  # 10.03 * 1.1 = 11.033 -> 11.03
    
    def test_zero_pre_close(self):
        """测试昨收为0"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.LIMIT_UP_PRICE(0.0, 10.0)
        self.assertIn("昨收价必须>0", str(context.exception))
    
    def test_zero_limit_percent(self):
        """测试涨停百分比为0"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.LIMIT_UP_PRICE(100.0, 0.0)
        self.assertIn("涨停百分比必须>0", str(context.exception))
    
    def test_invalid_type(self):
        """测试类型错误"""
        with self.assertRaises(TypeError):
            MetricDefinitions.LIMIT_UP_PRICE("100", 10)


class TestLIMIT_DOWN_PRICE(unittest.TestCase):
    """LIMIT_DOWN_PRICE方法测试"""
    
    def test_normal_limit_down(self):
        """测试正常跌停价"""
        result = MetricDefinitions.LIMIT_DOWN_PRICE(100.0, 10.0)
        self.assertEqual(result, 90.0)
    
    def test_st_limit_down(self):
        """测试ST股跌停价（5%）"""
        result = MetricDefinitions.LIMIT_DOWN_PRICE(100.0, 5.0)
        self.assertEqual(result, 95.0)
    
    def test_rounding(self):
        """测试舍入到2位小数"""
        result = MetricDefinitions.LIMIT_DOWN_PRICE(10.03, 10.0)
        self.assertEqual(result, 9.03)  # 10.03 * 0.9 = 9.027 -> 9.03
    
    def test_zero_pre_close(self):
        """测试昨收为0"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.LIMIT_DOWN_PRICE(0.0, 10.0)
        self.assertIn("昨收价必须>0", str(context.exception))
    
    def test_negative_limit_percent(self):
        """测试跌停百分比为负"""
        with self.assertRaises(ValueError) as context:
            MetricDefinitions.LIMIT_DOWN_PRICE(100.0, -10.0)
        self.assertIn("跌停百分比必须>0", str(context.exception))


class TestPRICE_CHANGE_RANGE(unittest.TestCase):
    """PRICE_CHANGE_RANGE方法测试"""
    
    def test_limit_up(self):
        """测试涨停判断"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(110.0, 100.0)
        self.assertEqual(result, 'limit_up')
    
    def test_up_strong(self):
        """测试强势上涨"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(107.0, 100.0)
        self.assertEqual(result, 'up_strong')
    
    def test_up_normal(self):
        """测试正常上涨"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(103.0, 100.0)
        self.assertEqual(result, 'up_normal')
    
    def test_flat_up(self):
        """测试平盘（微涨）"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(100.3, 100.0)
        self.assertEqual(result, 'flat')
    
    def test_flat_exact(self):
        """测试平盘（精确）"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(100.0, 100.0)
        self.assertEqual(result, 'flat')
    
    def test_flat_down(self):
        """测试平盘（微跌）"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(99.7, 100.0)
        self.assertEqual(result, 'flat')
    
    def test_down_normal(self):
        """测试正常下跌"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(97.0, 100.0)
        self.assertEqual(result, 'down_normal')
    
    def test_down_strong(self):
        """测试强势下跌"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(93.0, 100.0)
        self.assertEqual(result, 'down_strong')
    
    def test_limit_down(self):
        """测试跌停判断"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(90.0, 100.0)
        self.assertEqual(result, 'limit_down')
    
    def test_boundary_limit_up(self):
        """测试涨停边界（9.9%）"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(109.9, 100.0)
        self.assertEqual(result, 'up_strong')  # 刚好9.9不算涨停
    
    def test_boundary_up_strong(self):
        """测试强势上涨边界（5%）"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(105.0, 100.0)
        self.assertEqual(result, 'up_strong')
    
    def test_boundary_down_strong(self):
        """测试强势下跌边界（-5%）"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(95.0, 100.0)
        self.assertEqual(result, 'down_strong')
    
    def test_boundary_limit_down(self):
        """测试跌停边界（-9.9%）"""
        result = MetricDefinitions.PRICE_CHANGE_RANGE(90.1, 100.0)
        self.assertEqual(result, 'down_strong')  # -9.9%以上不算跌停


class TestMetricDefinitionsIntegration(unittest.TestCase):
    """集成测试 - 真实场景测试"""
    
    def test_stock_daily_change_scenario(self):
        """测试股票日涨跌场景"""
        pre_close = 100.0
        open_price = 102.0
        high = 105.0
        low = 101.0
        close = 103.0
        
        # 计算各项指标
        gap = MetricDefinitions.GAP_UP_PREMIUM(open_price, pre_close)
        change = MetricDefinitions.TRUE_CHANGE(close, pre_close)
        amplitude = MetricDefinitions.TRUE_AMPLITUDE(high, low, pre_close)
        price_range = MetricDefinitions.PRICE_CHANGE_RANGE(close, pre_close)
        
        self.assertAlmostEqual(gap, 2.0, places=6)
        self.assertAlmostEqual(change, 3.0, places=6)
        self.assertAlmostEqual(amplitude, 4.0, places=6)
        self.assertEqual(price_range, 'up_normal')
    
    def test_intraday_vwap_scenario(self):
        """测试日内VWAP场景"""
        # 模拟日内tick数据
        np.random.seed(42)
        n_ticks = 100
        df = pd.DataFrame({
            'price': 100 + np.random.randn(n_ticks).cumsum() * 0.5,
            'volume': np.random.randint(1000, 10000, n_ticks)
        })
        
        vwap = MetricDefinitions.VWAP(df)
        
        # VWAP应该在价格范围内
        self.assertGreaterEqual(vwap, df['price'].min())
        self.assertLessEqual(vwap, df['price'].max())
    
    def test_turnover_calculation_scenario(self):
        """测试换手率计算场景"""
        float_volume = 100000000  # 1亿股
        daily_volume = 25000000   # 2500万股成交
        
        turnover = MetricDefinitions.TURNOVER_RATE(daily_volume, float_volume)
        
        self.assertAlmostEqual(turnover, 25.0, places=6)
    
    def test_limit_price_calculation_scenario(self):
        """测试涨跌停价计算场景"""
        pre_close = 10.0
        
        limit_up = MetricDefinitions.LIMIT_UP_PRICE(pre_close, 10.0)
        limit_down = MetricDefinitions.LIMIT_DOWN_PRICE(pre_close, 10.0)
        
        self.assertEqual(limit_up, 11.0)
        self.assertEqual(limit_down, 9.0)
        
        # 验证涨跌幅计算
        up_change = MetricDefinitions.TRUE_CHANGE(limit_up, pre_close)
        down_change = MetricDefinitions.TRUE_CHANGE(limit_down, pre_close)
        
        self.assertAlmostEqual(up_change, 10.0, places=6)
        self.assertAlmostEqual(down_change, -10.0, places=6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
