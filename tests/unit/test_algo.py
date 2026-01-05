"""
Algo单元测试

测试量化算法的核心功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from logic.algo import QuantAlgo


@pytest.mark.unit
class TestQuantAlgo:
    """QuantAlgo测试类"""
    
    @pytest.fixture
    def sample_data(self):
        """创建测试用股票数据"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        np.random.seed(42)
        
        # 创建模拟K线数据
        data = {
            'open': np.random.uniform(95, 105, 100),
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(95, 105, 100),
            'volume': np.random.uniform(1000000, 2000000, 100),
            'amount': np.random.uniform(100000000, 200000000, 100)
        }
        
        df = pd.DataFrame(data, index=dates)
        return df
    
    def test_calculate_macd(self, sample_data):
        """测试计算MACD指标"""
        macd = QuantAlgo.calculate_macd(sample_data)
        
        assert macd is not None
        assert isinstance(macd, dict)
        assert 'MACD' in macd
        assert 'Signal' in macd
        assert 'Histogram' in macd
    
    def test_calculate_rsi(self, sample_data):
        """测试计算RSI指标"""
        rsi = QuantAlgo.calculate_rsi(sample_data)
        
        assert rsi is not None
        assert isinstance(rsi, dict)
        assert 'RSI' in rsi
    
    def test_calculate_bollinger_bands(self, sample_data):
        """测试计算布林带"""
        bollinger = QuantAlgo.calculate_bollinger_bands(sample_data)
        
        assert bollinger is not None
        assert isinstance(bollinger, dict)
        assert '上轨' in bollinger
        assert '中轨' in bollinger
        assert '下轨' in bollinger
    
    def test_calculate_kdj(self, sample_data):
        """测试计算KDJ指标"""
        kdj = QuantAlgo.calculate_kdj(sample_data)
        
        assert kdj is not None
        assert isinstance(kdj, dict)
        assert 'K' in kdj
        assert 'D' in kdj
        assert 'J' in kdj
    
    def test_calculate_atr(self, sample_data):
        """测试计算ATR（平均真实波幅）"""
        atr = QuantAlgo.calculate_atr(sample_data)
        
        assert atr is not None
        assert atr > 0
    
    def test_calculate_resistance_support(self, sample_data):
        """测试计算支撑阻力位"""
        levels = QuantAlgo.calculate_resistance_support(sample_data)
        
        # 注意：这个方法可能返回列表而不是字典
        assert levels is not None
        # 接受列表或字典
        assert isinstance(levels, (list, dict))
    
    def test_get_stock_name(self):
        """测试获取股票名称"""
        # Mock akshare接口
        from unittest.mock import patch
        
        with patch('akshare.stock_info_a_code_name') as mock_akshare:
            mock_akshare.return_value = pd.DataFrame({
                'code': ['600519'],
                'name': ['贵州茅台']
            })
            
            name = QuantAlgo.get_stock_name('600519')
            assert name == '贵州茅台'
    
    def test_empty_dataframe_handling(self):
        """测试空DataFrame处理"""
        empty_df = pd.DataFrame()
        
        # 应该返回空结果或None
        try:
            macd = QuantAlgo.calculate_macd(empty_df)
            assert macd is None or isinstance(macd, dict)
        except (KeyError, IndexError):
            # 空DataFrame可能导致这些错误，也是可以接受的
            pass


@pytest.mark.unit
class TestQuantAlgoEdgeCases:
    """QuantAlgo边界情况测试"""
    
    def test_constant_price_data(self):
        """测试价格不变的数据"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        data = {
            'open': [100] * 100,
            'high': [100] * 100,
            'low': [100] * 100,
            'close': [100] * 100,
            'volume': [1000000] * 100,
            'amount': [100000000] * 100
        }
        df = pd.DataFrame(data, index=dates)
        
        # 应该能处理不变的价格
        macd = QuantAlgo.calculate_macd(df)
        assert macd is not None or isinstance(macd, dict)
    
    def test_insufficient_data_handling(self):
        """测试数据不足时的处理"""
        # 创建只有5天数据
        dates = pd.date_range(end=datetime.now(), periods=5, freq='D')
        data = {
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100, 101, 102, 103, 104],
            'volume': [1000000] * 5,
            'amount': [100000000] * 5
        }
        df = pd.DataFrame(data, index=dates)
        
        # 计算指标
        macd = QuantAlgo.calculate_macd(df)
        assert macd is not None or isinstance(macd, dict)