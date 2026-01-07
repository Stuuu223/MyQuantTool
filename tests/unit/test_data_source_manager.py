"""
DataSourceManager 单元测试
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from logic.data_source_manager import (
    DataSourceBase,
    DataSourceStatus,
    AkShareDataSource,
    CacheDataSource,
    DataSourceManager
)


class MockDataSource(DataSourceBase):
    """模拟数据源"""
    
    def __init__(self, name: str, should_succeed: bool = True):
        super().__init__(name)
        self.should_succeed = should_succeed
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str):
        if self.should_succeed:
            return pd.DataFrame({"close": [100, 101, 102]})
        return None
    
    def health_check(self):
        return self.should_succeed


class TestDataSourceBase:
    """数据源基类测试"""
    
    def test_mark_failure(self):
        """测试标记失败"""
        source = MockDataSource("Test", should_succeed=True)
        assert source.status == DataSourceStatus.HEALTHY
        assert source.fail_count == 0
        
        source.mark_failure()
        assert source.fail_count == 1
        assert source.status == DataSourceStatus.HEALTHY
        
        # 连续失败3次后标记为不可用
        for _ in range(3):
            source.mark_failure()
        assert source.status == DataSourceStatus.UNAVAILABLE
    
    def test_mark_success(self):
        """测试标记成功"""
        source = MockDataSource("Test", should_succeed=False)
        source.fail_count = 5
        source.status = DataSourceStatus.UNAVAILABLE
        
        source.mark_success()
        assert source.fail_count == 0
        assert source.status == DataSourceStatus.HEALTHY


class TestDataSourceManager:
    """数据源管理器测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库"""
        return Mock()
    
    @pytest.fixture
    def manager(self, mock_db):
        """创建数据源管理器"""
        return DataSourceManager(mock_db)
    
    def test_init_sources(self, manager):
        """测试初始化数据源"""
        assert len(manager.sources) == 2
        assert isinstance(manager.sources[0], AkShareDataSource)
        assert isinstance(manager.sources[1], CacheDataSource)
    
    def test_get_stock_data_success(self, manager):
        """测试成功获取数据"""
        # 替换为模拟数据源
        manager.sources = [MockDataSource("Mock1", should_succeed=True)]
        
        df = manager.get_stock_data("600519", "20240101", "20240131")
        assert df is not None
        assert not df.empty
    
    def test_get_stock_data_failover(self, manager):
        """测试数据源切换"""
        # 第一个数据源失败，第二个成功
        manager.sources = [
            MockDataSource("Mock1", should_succeed=False),
            MockDataSource("Mock2", should_succeed=True)
        ]
        
        df = manager.get_stock_data("600519", "20240101", "20240131")
        assert df is not None
        assert not df.empty
    
    def test_get_stock_data_all_fail(self, manager):
        """测试所有数据源失败"""
        manager.sources = [
            MockDataSource("Mock1", should_succeed=False),
            MockDataSource("Mock2", should_succeed=False)
        ]
        
        df = manager.get_stock_data("600519", "20240101", "20240131")
        assert df is None
    
    def test_get_stock_data_skip_unavailable(self, manager):
        """测试跳过不可用的数据源"""
        source1 = MockDataSource("Mock1", should_succeed=False)
        source1.status = DataSourceStatus.UNAVAILABLE
        source2 = MockDataSource("Mock2", should_succeed=True)
        
        manager.sources = [source1, source2]
        
        df = manager.get_stock_data("600519", "20240101", "20240131")
        assert df is not None
    
    def test_health_check(self, manager):
        """测试健康检查"""
        manager.sources = [
            MockDataSource("Mock1", should_succeed=True),
            MockDataSource("Mock2", should_succeed=False)
        ]
        
        results = manager.health_check()
        assert results["Mock1"] == DataSourceStatus.HEALTHY
        assert results["Mock2"] == DataSourceStatus.UNAVAILABLE
    
    def test_get_available_sources(self, manager):
        """测试获取可用数据源"""
        manager.sources = [
            MockDataSource("Mock1", should_succeed=True),
            MockDataSource("Mock2", should_succeed=False)
        ]
        manager.health_check()
        
        available = manager.get_available_sources()
        assert "Mock1" in available
        assert "Mock2" not in available