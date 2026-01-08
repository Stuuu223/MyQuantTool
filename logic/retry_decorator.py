# logic/retry_decorator.py
"""
重试机制装饰器 - 为API调用添加指数退避重试
功能：提升网络不稳定场景下的成功率
"""

import time
import logging
from functools import wraps
from typing import Callable, Any, Tuple

logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 2, 
                       initial_wait: float = 1):
    """
    指数退避重试装饰器
    
    参数:
        max_retries: 最多重试次数 (默认3次)
        backoff_factor: 退避因子 (等待时间 = initial_wait * (backoff_factor ** attempt))
        initial_wait: 初始等待时间（秒，默认1秒）
    
    示例:
        @retry_with_backoff(max_retries=3, backoff_factor=2)
        def fetch_data():
            return ak.stock_lhb_detail_em(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        wait_time = initial_wait * (backoff_factor ** attempt)
                        logger.warning(
                            f"🔄 {func.__name__} 执行失败 ({attempt + 1}/{max_retries}), "
                            f"等待 {wait_time:.1f}秒后重试... 错误: {str(e)}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"[ERROR] {func.__name__} 在{max_retries}次重试后仍然失败: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_with_jitter(max_retries: int = 3, base_wait: float = 1):
    """
    带抖动的重试装饰器 - 用于高并发场景防止雷群效应
    
    参数:
        max_retries: 最多重试次数
        base_wait: 基础等待时间（秒）
    
    示例:
        @retry_with_jitter(max_retries=3, base_wait=1)
        def fetch_data():
            return ak.stock_lhb_detail_em(...)
    """
    import random
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        # 计算等待时间：base_wait * (2^attempt) + 随机抖动
                        exponential_wait = base_wait * (2 ** attempt)
                        jitter = random.uniform(0, exponential_wait * 0.1)
                        wait_time = exponential_wait + jitter
                        
                        logger.warning(
                            f"🔄 {func.__name__} 执行失败 ({attempt + 1}/{max_retries}), "
                            f"等待 {wait_time:.2f}秒后重试（含抖动）..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"[ERROR] {func.__name__} 在{max_retries}次重试后仍然失败"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


class RetryManager:
    """重试管理器 - 用于手动控制重试流程"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.attempt = 0
        self.last_exception = None
    
    def execute(self, func: Callable, *args, **kwargs) -> Tuple[Any, bool]:
        """
        执行函数并处理重试
        返回: (结果, 是否成功)
        
        示例:
            manager = RetryManager(max_retries=3)
            result, success = manager.execute(ak.stock_lhb_detail_em, 
                                               start_date='20260106',
                                               end_date='20260106')
        """
        for attempt in range(self.max_retries):
            self.attempt = attempt
            
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ {func.__name__} 执行成功 (第 {attempt + 1} 次尝试)")
                return result, True
            
            except Exception as e:
                self.last_exception = e
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"⚠️  {func.__name__} 执行失败 ({attempt + 1}/{self.max_retries}), "
                        f"等待{wait_time}秒后重试..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"[ERROR] {func.__name__} 在{self.max_retries}次重试后仍然失败: {str(e)}"
                    )
        
        return None, False
    
    def get_retry_stats(self) -> dict:
        """获取重试统计"""
        return {
            'total_retries': self.max_retries,
            'last_attempt': self.attempt,
            'last_exception': str(self.last_exception) if self.last_exception else None,
        }


# 使用示例
if __name__ == '__main__':
    import akshare as ak
    
    # 方式 1: 使用装饰器
    @retry_with_backoff(max_retries=3, backoff_factor=2)
    def fetch_lhb_data(date_str):
        return ak.stock_lhb_detail_em(start_date=date_str, end_date=date_str)
    
    # 调用
    data = fetch_lhb_data('20260106')
    print(f"获取到 {len(data)} 条龙虎榜记录")
    
    # 方式 2: 使用 RetryManager
    manager = RetryManager(max_retries=3)
    data, success = manager.execute(
        ak.stock_lhb_detail_em,
        start_date='20260106',
        end_date='20260106'
    )
    
    if success:
        print(f"[SUCCESS] 成功获取数据: {len(data)} 条")
    else:
        print(f"[ERROR] 失败: {manager.get_retry_stats()}")
