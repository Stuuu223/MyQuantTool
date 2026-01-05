"""
数据库集成测试

测试数据库操作的集成功能
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from logic.data_manager import DataManager
from logic.algo import QuantAlgo


@pytest.mark.integration
class TestDatabaseIntegration:
    """数据库集成测试类"""
    
    @pytest.fixture
    def db(self, temp_db):
        """测试数据库实例"""
        return temp_db
    
    @pytest.fixture
    def sample_stock_data(self):
        """创建测试用股票数据"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        import numpy as np
        np.random.seed(42)
        
        data = {
            'open': np.random.uniform(95, 105, 100),
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(95, 105, 100),
            'volume': np.random.uniform(1000000, 2000000, 100),
            'amount': np.random.uniform(100000000, 200000000, 100)
        }
        return pd.DataFrame(data, index=dates)
    
    def test_save_and_retrieve_data(self, db, sample_stock_data):
        """测试保存和检索数据的完整流程"""
        symbol = '600519'
        
        # 保存数据
        db.save_history_data(symbol, sample_stock_data)
        
        # 检索数据
        retrieved_data = db.get_history_data(symbol)
        
        # 验证数据
        assert not retrieved_data.empty
        assert len(retrieved_data) == len(sample_stock_data)
        assert all(col in retrieved_data.columns for col in ['open', 'high', 'low', 'close', 'volume', 'amount'])
    
    def test_multiple_stocks_data(self, db, sample_stock_data):
        """测试多只股票数据的存储和检索"""
        symbols = ['600519', '000001', '600036', '000002', '600000']
        
        # 保存多只股票数据
        for symbol in symbols:
            db.save_history_data(symbol, sample_stock_data)
        
        # 批量检索
        result = db.get_multiple_stocks(symbols)
        
        # 验证结果
        assert len(result) == len(symbols)
        assert all(symbol in result for symbol in symbols)
        assert all(not df.empty for df in result.values())
    
    def test_data_persistence(self, db, sample_stock_data):
        """测试数据持久化"""
        symbol = '600519'
        
        # 保存数据
        db.save_history_data(symbol, sample_stock_data)
        
        # 创建新的数据库实例（模拟重启）
        db_path = db.db_path
        new_db = DataManager(db_path)
        
        # 检索数据
        retrieved_data = new_db.get_history_data(symbol)
        
        # 验证数据持久化成功
        assert not retrieved_data.empty
        assert len(retrieved_data) == len(sample_stock_data)
    
    def test_cache_integration(self, db, sample_stock_data):
        """测试缓存集成"""
        symbol = '600519'
        
        # 保存数据
        db.save_history_data(symbol, sample_stock_data)
        
        # 第一次检索（无缓存）
        data1 = db.get_history_data(symbol)
        
        # 第二次检索（应该使用缓存）
        data2 = db.get_history_data(symbol)
        
        # 验证数据一致性
        assert data1.equals(data2)
    
    def test_database_index_performance(self, db, sample_stock_data):
        """测试数据库索引性能"""
        import time
        
        symbols = [f'60000{i}' for i in range(50)]
        
        # 保存大量数据
        for symbol in symbols:
            db.save_history_data(symbol, sample_stock_data)
        
        # 测试查询性能
        start = time.time()
        for symbol in symbols[:10]:
            db.get_history_data(symbol)
        query_time = time.time() - start
        
        # 查询应该在合理时间内完成（< 1秒）
        assert query_time < 1.0
    
    def test_data_consistency_after_update(self, db, sample_stock_data):
        """测试更新后数据的一致性"""
        symbol = '600519'
        
        # 保存初始数据
        db.save_history_data(symbol, sample_stock_data)
        
        # 更新数据
        updated_data = sample_stock_data.copy()
        updated_data['close'] = updated_data['close'] * 1.1
        db.save_history_data(symbol, updated_data)
        
        # 检索更新后的数据
        retrieved_data = db.get_history_data(symbol)
        
        # 验证数据已更新
        assert not retrieved_data.empty
        assert abs(retrieved_data['close'].iloc[-1] - updated_data['close'].iloc[-1]) < 0.01


@pytest.mark.integration
class TestAlgoIntegration:
    """算法集成测试类"""
    
    @pytest.fixture
    def sample_stock_data(self):
        """创建测试用股票数据"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        import numpy as np
        np.random.seed(42)
        
        data = {
            'open': np.random.uniform(95, 105, 100),
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(95, 105, 100),
            'volume': np.random.uniform(1000000, 2000000, 100),
            'amount': np.random.uniform(100000000, 200000000, 100)
        }
        return pd.DataFrame(data, index=dates)
    
    def test_complete_analysis_workflow(self, sample_stock_data):
        """测试完整的分析工作流"""
        # 计算各种指标
        ma5 = QuantAlgo.calculate_ma(sample_stock_data, 5)
        ma10 = QuantAlgo.calculate_ma(sample_stock_data, 10)
        macd = QuantAlgo.calculate_macd(sample_stock_data)
        rsi = QuantAlgo.calculate_rsi(sample_stock_data)
        bollinger = QuantAlgo.calculate_bollinger_bands(sample_stock_data)
        kdj = QuantAlgo.calculate_kdj(sample_stock_data)
        atr = QuantAlgo.calculate_atr(sample_stock_data)
        volume_analysis = QuantAlgo.analyze_volume(sample_stock_data)
        
        # 验证所有指标都计算成功
        assert ma5 is not None
        assert ma10 is not None
        assert macd is not None
        assert rsi is not None
        assert bollinger is not None
        assert kdj is not None
        assert atr is not None
        assert volume_analysis is not None
    
    def test_indicator_correlation(self, sample_stock_data):
        """测试指标之间的相关性"""
        macd = QuantAlgo.calculate_macd(sample_stock_data)
        rsi = QuantAlgo.calculate_rsi(sample_stock_data)
        
        # 验证指标长度一致
        assert len(macd['MACD']) == len(rsi['RSI'])
    
    def test_multi_indicator_analysis(self, sample_stock_data):
        """测试多指标综合分析"""
        # 计算多个指标
        ma5 = QuantAlgo.calculate_ma(sample_stock_data, 5)
        ma10 = QuantAlgo.calculate_ma(sample_stock_data, 10)
        macd = QuantAlgo.calculate_macd(sample_stock_data)
        rsi = QuantAlgo.calculate_rsi(sample_stock_data)
        
        # 检测信号
        golden_cross = QuantAlgo.detect_golden_cross(ma5, ma10)
        
        # 验证信号检测
        if golden_cross is not None:
            assert 'date' in golden_cross
            assert 'price' in golden_cross


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """错误处理集成测试类"""
    
    @pytest.fixture
    def db(self, temp_db):
        """测试数据库实例"""
        return temp_db
    
    def test_invalid_symbol_handling(self, db):
        """测试无效股票代码的处理"""
        # 应该返回空DataFrame或抛出异常
        result = db.get_history_data('')
        assert result is not None
    
    def test_network_error_handling(self, db):
        """测试网络错误的处理"""
        # Mock网络错误
        from unittest.mock import patch
        import akshare
        
        with patch.object(akshare, 'stock_zh_a_hist_min_em', side_effect=Exception("Network error")):
            result = db.get_realtime_data('600519')
            # 应该返回None或处理错误
            assert result is None or 'error' in str(result).lower()
    
    def test_database_connection_error(self):
        """测试数据库连接错误的处理"""
        # 尝试连接到不存在的数据库
        with pytest.raises(Exception):
            DataManager('/nonexistent/path/to/database.db')
    
    def test_corrupted_data_handling(self, db):
        """测试损坏数据的处理"""
        # 创建损坏的数据
        corrupted_data = pd.DataFrame({
            'open': [None, None, None],
            'high': [None, None, None],
            'low': [None, None, None],
            'close': [None, None, None],
            'volume': [None, None, None],
            'amount': [None, None, None]
        })
        
        # 应该能处理损坏的数据
        db.save_history_data('TEST', corrupted_data)
        result = db.get_history_data('TEST')
        
        # 结果可能为空或包含NaN
        assert result is not None