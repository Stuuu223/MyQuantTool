"""
数据源健康监控器 - 定期检查数据源健康状态
"""

import logging
import pandas as pd
from typing import Dict
from logic.data_source_manager import get_data_source_manager, DataSourceStatus

logger = logging.getLogger(__name__)


class DataHealthMonitor:
    """数据源健康监控器"""
    
    def __init__(self, db, check_interval_minutes: int = 30):
        """
        初始化健康监控器
        
        Args:
            db: 数据库实例
            check_interval_minutes: 检查间隔（分钟）
        """
        self.db = db
        self.check_interval_minutes = check_interval_minutes
        self.last_check_time = None
        self.health_history = {}
    
    def should_check(self) -> bool:
        """判断是否应该执行健康检查"""
        if self.last_check_time is None:
            return True
        
        elapsed = (pd.Timestamp.now() - self.last_check_time).total_seconds() / 60
        return elapsed >= self.check_interval_minutes
    
    def check_health(self) -> Dict[str, DataSourceStatus]:
        """
        执行健康检查
        
        Returns:
            数据源健康状态字典
        """
        if not self.should_check():
            logger.debug("距离上次检查时间不足，跳过健康检查")
            return {}
        
        logger.info("开始执行数据源健康检查...")
        manager = get_data_source_manager(self.db)
        results = manager.health_check()
        
        # 记录历史
        self.last_check_time = pd.Timestamp.now()
        self.health_history[self.last_check_time] = results
        
        # 记录告警
        unhealthy_sources = [name for name, status in results.items() 
                          if status != DataSourceStatus.HEALTHY]
        if unhealthy_sources:
            logger.warning(f"⚠️ 发现不健康的数据源: {unhealthy_sources}")
        else:
            logger.info("✅ 所有数据源健康")
        
        return results
    
    def get_health_summary(self) -> Dict:
        """
        获取健康状态摘要
        
        Returns:
            健康状态摘要
        """
        manager = get_data_source_manager(self.db)
        available_sources = manager.get_available_sources()
        
        return {
            "total_sources": len(manager.sources),
            "available_sources": len(available_sources),
            "unavailable_sources": len(manager.sources) - len(available_sources),
            "last_check_time": self.last_check_time,
            "available_sources_list": available_sources,
        }


# 全局实例
_health_monitor = None


def get_health_monitor(db, check_interval_minutes: int = 30) -> DataHealthMonitor:
    """获取健康监控器实例（单例）"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = DataHealthMonitor(db, check_interval_minutes)
    return _health_monitor