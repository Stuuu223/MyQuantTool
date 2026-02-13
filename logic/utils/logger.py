"""
日志系统配置模块

提供统一的日志记录功能，支持文件和控制台输出
"""

import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
from contextlib import contextmanager


class Logger:
    """日志管理器（单例模式）
    
    提供统一的日志记录功能，支持文件和控制台双输出。
    日志文件按日期分割，每天一个文件。
    
    Attributes:
        log_dir: 日志文件存储目录
        _instance: 单例实例
        _initialized: 是否已初始化
        
    Example:
        >>> logger = Logger()
        >>> print(logger.log_dir)
    """
    
    _instance: Optional['Logger'] = None
    _initialized: bool = False
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._initialized = True
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 配置日志系统
        # FileHandler: 保持 INFO 级别（用于事后排查）
        file_handler = logging.FileHandler(
            self.log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # StreamHandler: 降级为 WARNING 级别（仅显示严重错误）
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.WARNING)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            handlers=[file_handler, stream_handler]
        )
        
        # 性能日志单独文件
        self.performance_logger = logging.getLogger('performance')
        self.performance_logger.setLevel(logging.INFO)
        performance_handler = logging.FileHandler(
            self.log_dir / f'performance_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        performance_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s')
        )
        self.performance_logger.addHandler(performance_handler)
    
    @staticmethod
    def get_logger(name: Optional[str] = None) -> logging.Logger:
        """获取日志记录器
        
        如果不提供名称，会自动使用调用者的模块名。
        
        Args:
            name: 日志记录器名称，默认使用调用者的模块名
            
        Returns:
            配置好的日志记录器实例
            
        Example:
            >>> logger = get_logger(__name__)
            >>> logger.info("应用启动")
            >>> logger.error("发生错误", exc_info=True)
        """
        logger_instance = Logger()
        if name is None:
            import inspect
            # 获取调用者的模块名
            frame = inspect.currentframe().f_back
            module = inspect.getmodule(frame)
            name = module.__name__ if module else __name__
        
        return logging.getLogger(name)
    
    @staticmethod
    def log_performance(func_name: str, duration: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """记录性能日志
        
        Args:
            func_name: 函数名称
            duration: 执行时长（秒）
            metadata: 额外的元数据
        """
        logger_instance = Logger()
        msg = f"[PERF] {func_name} - {duration:.3f}s"
        if metadata:
            msg += f" - {metadata}"
        logger_instance.performance_logger.info(msg)
    
    @staticmethod
    def log_error(func_name: str, error: Exception, metadata: Optional[Dict[str, Any]] = None) -> None:
        """记录错误日志
        
        Args:
            func_name: 函数名称
            error: 异常对象
            metadata: 额外的元数据
        """
        logger_instance = Logger()
        logger = logger_instance.get_logger(func_name)
        msg = f"[ERROR] {func_name} - {type(error).__name__}: {str(error)}"
        if metadata:
            msg += f" - {metadata}"
        logger.error(msg, exc_info=True)


def log_execution_time(func):
    """装饰器：记录函数执行时间
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
        
    Example:
        >>> @log_execution_time
        >>> def my_function():
        >>>     time.sleep(1)
        >>>     return "done"
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            Logger.log_performance(func.__name__, duration, {'status': 'success'})
            return result
        except Exception as e:
            duration = time.time() - start_time
            Logger.log_error(func.__name__, e, {'duration': f'{duration:.3f}s'})
            raise
    return wrapper


@contextmanager
def performance_context(name: str):
    """上下文管理器：记录代码块执行时间
    
    Args:
        name: 代码块名称
        
    Example:
        >>> with performance_context("data_processing"):
        >>>     # 执行一些操作
        >>>     process_data()
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        Logger.log_performance(name, duration)


# 便捷函数
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return Logger.get_logger(name)


# 导出常用的日志记录器
logger = get_logger(__name__)