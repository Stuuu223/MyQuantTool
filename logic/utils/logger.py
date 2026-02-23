# -*- coding: utf-8 -*-
"""
日志工具模块 - Phase 9.2 统一日志接口
"""

import logging
import functools
import time
from typing import Callable, Any


def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例
    
    Args:
        name: logger名称
        
    Returns:
        logging.Logger实例
    """
    return logging.getLogger(name)


def log_execution_time(func: Callable = None, *, level: str = "DEBUG") -> Callable:
    """
    装饰器：记录函数执行时间
    
    Args:
        func: 被装饰的函数
        level: 日志级别
        
    Returns:
        装饰器函数
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(f.__module__)
            start = time.time()
            try:
                result = f(*args, **kwargs)
                elapsed = time.time() - start
                getattr(logger, level.lower(), logger.debug)(
                    f"⏱️ {f.__name__} 执行完成，耗时: {elapsed:.3f}s"
                )
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"⏱️ {f.__name__} 执行失败，耗时: {elapsed:.3f}s，错误: {e}")
                raise
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)


class performance_context:
    """
    上下文管理器：记录代码块执行时间
    
    用法:
        with performance_context("数据处理"):
            process_data()
    """
    
    def __init__(self, name: str, level: str = "DEBUG"):
        self.name = name
        self.level = level
        self.logger = get_logger(__name__)
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type is None:
            getattr(self.logger, self.level.lower(), self.logger.debug)(
                f"⏱️ {self.name} 完成，耗时: {elapsed:.3f}s"
            )
        else:
            self.logger.error(
                f"⏱️ {self.name} 失败，耗时: {elapsed:.3f}s，错误: {exc_val}"
            )
