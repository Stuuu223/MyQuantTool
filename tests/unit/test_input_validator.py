"""
InputValidator 单元测试
"""

import pytest
from main import InputValidator


class TestInputValidator:
    """输入验证器测试类"""
    
    def test_validate_stock_code_valid(self):
        """测试有效的股票代码"""
        assert InputValidator.validate_stock_code("600519") == True
        assert InputValidator.validate_stock_code("000001") == True
        assert InputValidator.validate_stock_code("300001") == True
    
    def test_validate_stock_code_invalid_length(self):
        """测试无效长度的股票代码"""
        assert InputValidator.validate_stock_code("60051") == False  # 5位
        assert InputValidator.validate_stock_code("6005190") == False  # 7位
    
    def test_validate_stock_code_invalid_format(self):
        """测试无效格式的股票代码"""
        assert InputValidator.validate_stock_code("ABC123") == False  # 包含字母
        assert InputValidator.validate_stock_code("600 519") == False  # 包含空格
        assert InputValidator.validate_stock_code("600-519") == False  # 包含特殊字符
    
    def test_validate_stock_code_none(self):
        """测试 None 输入"""
        assert InputValidator.validate_stock_code(None) == False
        assert InputValidator.validate_stock_code("") == False
    
    def test_validate_percentage_valid(self):
        """测试有效的百分比"""
        assert InputValidator.validate_percentage(0) == True
        assert InputValidator.validate_percentage(50) == True
        assert InputValidator.validate_percentage(100) == True
    
    def test_validate_percentage_invalid(self):
        """测试无效的百分比"""
        assert InputValidator.validate_percentage(-1) == False
        assert InputValidator.validate_percentage(101) == False
        assert InputValidator.validate_percentage(150) == False
    
    def test_validate_positive_valid(self):
        """测试有效的正数"""
        assert InputValidator.validate_positive(1) == True
        assert InputValidator.validate_positive(0.5) == True
        assert InputValidator.validate_positive(1000) == True
    
    def test_validate_positive_invalid(self):
        """测试无效的正数"""
        assert InputValidator.validate_positive(0) == False
        assert InputValidator.validate_positive(-1) == False
        assert InputValidator.validate_positive(-0.5) == False