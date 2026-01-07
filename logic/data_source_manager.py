"""
数据源管理器 - 实现多数据源备份和自动切换
"""

import pandas as pd
from typing import Optional, Dict, List
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "健康"
    DEGRADED = "降级"
    UNAVAILABLE = "不可用"


class DataSourceBase(ABC):
    """数据源基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.status = DataSourceStatus.HEALTHY
        self.fail_count = 0
        self.last_check_time = None
    
    @abstractmethod
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取股票数据"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass
    
    def mark_failure(self):
        """标记失败"""
        self.fail_count += 1
        if self.fail_count >= 3:
            self.status = DataSourceStatus.UNAVAILABLE
            logger.warning(f"数据源 {self.name} 连续失败 {self.fail_count} 次，标记为不可用")
    
    def mark_success(self):
        """标记成功"""
        self.fail_count = 0
        self.status = DataSourceStatus.HEALTHY


class AkShareDataSource(DataSourceBase):
    """AkShare 数据源"""
    
    def __init__(self):
        super().__init__("AkShare")
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取股票数据"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date)
            self.mark_success()
            return df
        except Exception as e:
            logger.error(f"AkShare 获取数据失败: {e}")
            self.mark_failure()
            return None
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            import akshare as ak
            # 尝试获取一个简单的数据
            df = ak.stock_zh_a_hist(symbol="600519", start_date="20240101", end_date="20240102")
            is_healthy = df is not None and not df.empty
            self.last_check_time = pd.Timestamp.now()
            return is_healthy
        except Exception as e:
            logger.error(f"AkShare 健康检查失败: {e}")
            self.last_check_time = pd.Timestamp.now()
            return False


class CacheDataSource(DataSourceBase):
    """缓存数据源"""
    
    def __init__(self, db):
        super().__init__("Cache")
        self.db = db
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从缓存获取数据"""
        try:
            df = self.db.get_stock_data(symbol, start_date, end_date)
            if df is not None and not df.empty:
                self.mark_success()
                return df
            return None
        except Exception as e:
            logger.error(f"缓存数据源失败: {e}")
            self.mark_failure()
            return None
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查数据库连接
            return self.db is not None
        except Exception as e:
            logger.error(f"缓存数据源健康检查失败: {e}")
            return False


class DataSourceManager:
    """数据源管理器"""
    
    def __init__(self, db):
        self.db = db
        self.sources: List[DataSourceBase] = []
        self._init_sources()
    
    def _init_sources(self):
        """初始化数据源"""
        # 主数据源：AkShare
        self.sources.append(AkShareDataSource())
        # 备用数据源：缓存
        self.sources.append(CacheDataSource(self.db))
        
        logger.info(f"已初始化 {len(self.sources)} 个数据源")
    
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取股票数据（自动切换数据源）
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            股票数据 DataFrame 或 None
        """
        for source in self.sources:
            if source.status == DataSourceStatus.UNAVAILABLE:
                logger.debug(f"跳过不可用的数据源: {source.name}")
                continue
            
            logger.info(f"尝试从 {source.name} 获取数据: {symbol}")
            df = source.get_stock_data(symbol, start_date, end_date)
            
            if df is not None and not df.empty:
                logger.info(f"成功从 {source.name} 获取数据")
                return df
            else:
                logger.warning(f"{source.name} 获取数据失败，尝试下一个数据源")
        
        logger.error(f"所有数据源均无法获取数据: {symbol}")
        return None
    
    def health_check(self) -> Dict[str, DataSourceStatus]:
        """
        检查所有数据源健康状态
        
        Returns:
            数据源状态字典
        """
        results = {}
        for source in self.sources:
            is_healthy = source.health_check()
            if is_healthy:
                source.status = DataSourceStatus.HEALTHY
            else:
                source.status = DataSourceStatus.UNAVAILABLE
            results[source.name] = source.status
        
        logger.info(f"数据源健康检查结果: {results}")
        return results
    
    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        return [source.name for source in self.sources if source.status == DataSourceStatus.HEALTHY]


# 全局实例
_data_source_manager = None


def get_data_source_manager(db) -> DataSourceManager:
    """获取数据源管理器实例（单例）"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager(db)
    return _data_source_manager