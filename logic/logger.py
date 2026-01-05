"""
日志系统配置模块

提供统一的日志记录功能，支持文件和控制台输出
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    """日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 配置日志系统
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(
                    self.log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log',
                    encoding='utf-8'
                ),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    @staticmethod
    def get_logger(name: str = None) -> logging.Logger:
        """获取日志记录器
        
        Args:
            name: 日志记录器名称，默认使用调用者的模块名
            
        Returns:
            日志记录器实例
        """
        logger_instance = Logger()
        if name is None:
            import inspect
            # 获取调用者的模块名
            frame = inspect.currentframe().f_back
            module = inspect.getmodule(frame)
            name = module.__name__ if module else __name__
        
        return logging.getLogger(name)


# 便捷函数
def get_logger(name: str = None) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return Logger.get_logger(name)


# 导出常用的日志记录器
logger = get_logger(__name__)