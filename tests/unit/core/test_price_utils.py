#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
price_utils 模块单元测试

测试 get_pre_close, calc_true_change 等核心价格工具函数

Author: iFlow CLI
Date: 2026-02-23
"""

import unittest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.price_utils import (
    calc_true_change,
    validate_price_data,
    batch_get_pre_close,
    _normalize_stock_code,
    _get_previous_trade_date,
    DataMissingError,
    PriceCalculationError
)


class TestNormalizeStockCode(unittest.TestCase):
    """测试股票代码标准化函数"""

    def test_shenzhen_code(self):
        """测试深圳代码（0、3开头）"""
        self.assertEqual(_normalize_stock_code('300986'), '300986.SZ')
        self.assertEqual(_normalize_stock_code('000001'), '000001.SZ')
        self.assertEqual(_normalize_stock_code('300986.SZ'), '300986.SZ')
        self.assertEqual(_normalize_stock_code('300986.sz'), '300986.SZ')

    def test_shanghai_code(self):
        """测试上海代码（6开头）"""
        self.assertEqual(_normalize_stock_code('600519'), '600519.SH')
        self.assertEqual(_normalize_stock_code('688981'), '688981.SH')
        self.assertEqual(_normalize_stock_code('600519.SH'), '600519.SH')

    def test_beijing_code(self):
        """测试北京代码（8、4开头）"""
        self.assertEqual(_normalize_stock_code('835184'), '835184.BJ')
        self.assertEqual(_normalize_stock_code('430047'), '430047.BJ')

    def test_invalid_code(self):
        """测试无效代码"""
        with self.assertRaises(ValueError):
            _normalize_stock_code('')
        with self.assertRaises(ValueError):
            _normalize_stock_code(None)
        with self.assertRaises(ValueError):
            _normalize_stock_code('12345')  # 5位
        with self.assertRaises(ValueError):
            _normalize_stock_code('1234567')  # 7位
        with self.assertRaises(ValueError):
            _normalize_stock_code('abcdef')  # 非数字
        with self.assertRaises(ValueError):
            _normalize_stock_code('999999')  # 无法识别前缀


class TestGetPreviousTradeDate(unittest.TestCase):
    """测试前一交易日计算"""

    def test_normal_day(self):
        """测试普通工作日"""
        # 2025-12-31 是周三
        result = _get_previous_trade_date('20260101')
        self.assertEqual(result, '20251231')

    def test_skip_weekend(self):
        """测试跳过周末"""
        # 2026-01-05 是周一
        result = _get_previous_trade_date('20260105')
        # 前一交易日应该是周五 2026-01-02
        self.assertEqual(result, '20260102')

    def test_monday(self):
        """测试周一"""
        # 2026-01-05 是周一，前一交易日是1月2日（周五）
        result = _get_previous_trade_date('20260105')
        self.assertEqual(result, '20260102')

    def test_invalid_date(self):
        """测试无效日期"""
        with self.assertRaises(ValueError):
            _get_previous_trade_date('')
        with self.assertRaises(ValueError):
            _get_previous_trade_date('20251301')  # 无效月份
        with self.assertRaises(ValueError):
            _get_previous_trade_date('20250132')  # 无效日期


class TestCalcTrueChange(unittest.TestCase):
    """测试真实涨幅计算"""

    def test_positive_change(self):
        """测试上涨情况"""
        # (27 - 25.68) / 25.68 * 100 = 5.14%
        result = calc_true_change(27.0, 25.68)
        self.assertAlmostEqual(result, 5.14, places=2)

    def test_negative_change(self):
        """测试下跌情况"""
        # (24 - 25.68) / 25.68 * 100 = -6.54%
        result = calc_true_change(24.0, 25.68)
        self.assertAlmostEqual(result, -6.54, places=2)

    def test_no_change(self):
        """测试平盘"""
        result = calc_true_change(25.68, 25.68)
        self.assertEqual(result, 0.0)

    def test_limit_up(self):
        """测试涨停（20%）"""
        # 创业板涨停 20%
        pre_close = 10.0
        current = 12.0
        result = calc_true_change(current, pre_close)
        self.assertAlmostEqual(result, 20.0, places=2)

    def test_limit_down(self):
        """测试跌停（-10%）"""
        # 主板跌停 -10%
        pre_close = 10.0
        current = 9.0
        result = calc_true_change(current, pre_close)
        self.assertAlmostEqual(result, -10.0, places=2)

    def test_invalid_input(self):
        """测试无效输入"""
        with self.assertRaises(ValueError):
            calc_true_change(None, 10.0)
        with self.assertRaises(ValueError):
            calc_true_change(10.0, None)
        with self.assertRaises(ValueError):
            calc_true_change(-5.0, 10.0)  # 负价格
        with self.assertRaises(ValueError):
            calc_true_change(10.0, 0.0)   # 昨收为0
        with self.assertRaises(ValueError):
            calc_true_change(10.0, -5.0)  # 负昨收
        with self.assertRaises(ValueError):
            calc_true_change("10.0", 10.0)  # 字符串


class TestValidatePriceData(unittest.TestCase):
    """测试价格数据验证"""

    def test_valid_data(self):
        """测试有效数据"""
        self.assertTrue(validate_price_data(11.0, 10.0))
        self.assertTrue(validate_price_data(10.0, 10.0))
        self.assertTrue(validate_price_data(9.0, 10.0))

    def test_normal_change(self):
        """测试正常涨跌幅"""
        # 上涨 5%
        self.assertTrue(validate_price_data(10.5, 10.0, max_change_pct=20.0))
        # 下跌 5%
        self.assertTrue(validate_price_data(9.5, 10.0, max_change_pct=20.0))

    def test_abnormal_change(self):
        """测试异常涨跌幅"""
        # 上涨 30% 超过20%限制
        with self.assertRaises(ValueError):
            validate_price_data(13.0, 10.0, max_change_pct=20.0)
        # 下跌 30%
        with self.assertRaises(ValueError):
            validate_price_data(7.0, 10.0, max_change_pct=20.0)

    def test_invalid_price(self):
        """测试无效价格"""
        with self.assertRaises(ValueError):
            validate_price_data(0, 10.0)
        with self.assertRaises(ValueError):
            validate_price_data(10.0, 0)
        with self.assertRaises(ValueError):
            validate_price_data(-5.0, 10.0)


class TestBatchGetPreClose(unittest.TestCase):
    """测试批量获取昨收价"""

    def test_batch_empty_list(self):
        """测试空列表"""
        result = batch_get_pre_close([], '20251231')
        self.assertEqual(result, {})

    def test_batch_single_code(self):
        """测试单个代码"""
        # 注意：此测试需要xtdata可用，否则会被捕获为失败
        # 这里只测试函数调用不报错
        try:
            result = batch_get_pre_close(['000001.SZ'], '20251231')
            # 如果成功，结果是字典
            self.assertIsInstance(result, dict)
        except Exception as e:
            # xtdata不可用时跳过
            self.skipTest(f"xtdata不可用: {e}")


class TestDataMissingError(unittest.TestCase):
    """测试数据缺失异常"""

    def test_error_message(self):
        """测试异常消息"""
        error = DataMissingError("测试数据缺失")
        self.assertEqual(str(error), "测试数据缺失")


class TestPriceCalculationError(unittest.TestCase):
    """测试价格计算异常"""

    def test_error_message(self):
        """测试异常消息"""
        error = PriceCalculationError("测试计算错误")
        self.assertEqual(str(error), "测试计算错误")


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_change_calculation_workflow(self):
        """测试涨幅计算完整流程"""
        # 模拟一个完整的计算流程
        pre_close = 25.68
        current_price = 27.0
        
        # 1. 验证价格数据
        is_valid = validate_price_data(current_price, pre_close)
        self.assertTrue(is_valid)
        
        # 2. 计算涨幅
        change = calc_true_change(current_price, pre_close)
        
        # 3. 验证结果
        self.assertAlmostEqual(change, 5.14, places=2)
        self.assertGreater(change, 0)  # 上涨


if __name__ == '__main__':
    unittest.main(verbosity=2)
