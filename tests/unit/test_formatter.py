"""
Formatter单元测试

测试数据格式化功能
"""

import pytest
import pandas as pd
from datetime import datetime
from logic.formatter import Formatter


@pytest.mark.unit
class TestFormatter:
    """Formatter测试类"""
    
    def test_format_price(self):
        """测试价格格式化"""
        assert Formatter.format_price(100.5) == "¥100.50"
        assert Formatter.format_price(1000.123) == "¥1000.12"
        assert Formatter.format_price(None) == "-"
    
    def test_format_amount(self):
        """测试金额格式化"""
        assert Formatter.format_amount(100) == "¥100"
        assert Formatter.format_amount(10000) == "¥1.00万"
        assert Formatter.format_amount(100000000) == "¥1.00亿"
        assert Formatter.format_amount(-10000) == "¥-1.00万"
        assert Formatter.format_amount(None) == "-"
    
    def test_format_amount_no_symbol(self):
        """测试不带货币符号的金额格式化"""
        assert Formatter.format_amount_no_symbol(100) == "100"
        assert Formatter.format_amount_no_symbol(10000) == "1.00万"
        assert Formatter.format_amount_no_symbol(100000000) == "1.00亿"
        assert Formatter.format_amount_no_symbol(None) == "-"
    
    def test_format_percentage(self):
        """测试百分比格式化"""
        assert Formatter.format_percentage(0.1) == "10.00%"
        assert Formatter.format_percentage(0.5) == "50.00%"
        assert Formatter.format_percentage(1.0) == "100.00%"
        assert Formatter.format_percentage(-0.1) == "-10.00%"
        assert Formatter.format_percentage(None) == "-"
    
    def test_format_change(self):
        """测试涨跌幅格式化"""
        assert Formatter.format_change(0.1) == "+10.00%"
        assert Formatter.format_change(-0.1) == "-10.00%"
        assert Formatter.format_change(0.0) == "0.00%"  # 修正：零值不加符号
        assert Formatter.format_change(None) == "-"
    
    def test_format_volume(self):
        """测试成交量格式化"""
        assert Formatter.format_volume(1000) == "1000手"
        assert Formatter.format_volume(10000) == "1.00万手"
        assert Formatter.format_volume(100000000) == "1.00亿手"
        assert Formatter.format_volume(None) == "-"
    
    def test_format_number(self):
        """测试数字格式化"""
        assert Formatter.format_number(100) == "100.00"
        assert Formatter.format_number(1000) == "1,000.00"
        assert Formatter.format_number(1000000) == "1,000,000.00"
        assert Formatter.format_number(None) == "-"
    
    def test_format_ratio(self):
        """测试比例格式化"""
        assert Formatter.format_ratio(0.1) == "10.00%"
        assert Formatter.format_ratio(0.5) == "50.00%"
        assert Formatter.format_ratio(None) == "-"
    
    def test_format_date(self):
        """测试日期格式化"""
        date = datetime(2026, 1, 5)
        assert Formatter.format_date(date) == "2026-01-05"
        
        date_str = "2026-01-05"
        assert Formatter.format_date(date_str) == "2026-01-05"
        assert Formatter.format_date(None) == "-"
    
    def test_format_datetime(self):
        """测试日期时间格式化"""
        dt = datetime(2026, 1, 5, 15, 30, 45)
        result = Formatter.format_datetime(dt)
        assert result == "2026-01-05 15:30:45"
        assert Formatter.format_datetime(None) == "-"
    
    def test_format_rank(self):
        """测试排名格式化"""
        assert Formatter.format_rank(1) == "第1名"
        assert Formatter.format_rank(1, 10) == "1/10"
        assert Formatter.format_rank(None) == "-"
    
    def test_format_score(self):
        """测试评分格式化"""
        assert Formatter.format_score(85) == "85/100 (85%)"
        assert Formatter.format_score(85, 100) == "85/100 (85%)"
        assert Formatter.format_score(None) == "-"
    
    def test_format_duration(self):
        """测试持续时间格式化"""
        assert Formatter.format_duration(30) == "30秒"
        assert Formatter.format_duration(60) == "1分钟"
        assert Formatter.format_duration(3600) == "1.0小时"
        assert Formatter.format_duration(90061) == "25.0小时"
        assert Formatter.format_duration(None) == "-"
    
    def test_format_distance(self):
        """测试距离格式化"""
        assert Formatter.format_distance(0.1) == "+10.00%"
        assert Formatter.format_distance(-0.1) == "-10.00%"
        assert Formatter.format_distance(0.1, "km") == "+10.00%km"
        assert Formatter.format_distance(None) == "-"
    
    def test_get_color_class(self):
        """测试颜色类名获取"""
        assert Formatter.get_color_class(10) == "text-red"
        assert Formatter.get_color_class(-10) == "text-green"
        assert Formatter.get_color_class(0) == "text-gray"
        assert Formatter.get_color_class(None) == "text-gray"
    
    def test_format_with_color(self):
        """测试带颜色标记的格式化"""
        assert Formatter.format_with_color(10) == "🔺 10"
        assert Formatter.format_with_color(-10) == "🔻 -10"
        assert Formatter.format_with_color(0) == "➖ 0"
        assert Formatter.format_with_color(None) == "-"
        
        # 测试自定义格式化函数
        result = Formatter.format_with_color(0.1, Formatter.format_percentage)
        assert "🔺" in result
        assert "10.00%" in result


@pytest.mark.unit
class TestFormatterEdgeCases:
    """Formatter边界情况测试"""
    
    def test_format_price_zero(self):
        """测试零价格的格式化"""
        assert Formatter.format_price(0) == "¥0.00"
    
    def test_format_amount_zero(self):
        """测试零金额的格式化"""
        assert Formatter.format_amount(0) == "¥0"
    
    def test_format_percentage_zero(self):
        """测试零百分比的格式化"""
        assert Formatter.format_percentage(0) == "0.00%"
    
    def test_format_number_zero(self):
        """测试零数字的格式化"""
        assert Formatter.format_number(0) == "0.00"
    
    def test_format_duration_zero(self):
        """测试零时长的格式化"""
        assert Formatter.format_duration(0) == "0秒"
    
    def test_format_very_large_amount(self):
        """测试极大金额的格式化"""
        large_amount = 10**12  # 1万亿
        result = Formatter.format_amount(large_amount)
        assert "亿" in result
    
    def test_format_very_small_amount(self):
        """测试极小金额的格式化"""
        small_amount = 0.01
        result = Formatter.format_amount(small_amount)
        assert result == "¥0"
    
    def test_format_negative_volume(self):
        """测试负成交量的格式化"""
        result = Formatter.format_volume(-10000)
        assert "-" in result
        assert "万手" in result
    
    def test_format_with_custom_decimal_places(self):
        """测试自定义小数位数"""
        assert Formatter.format_percentage(0.12345, 4) == "12.3450%"
        assert Formatter.format_number(100.12345, 4) == "100.1235"