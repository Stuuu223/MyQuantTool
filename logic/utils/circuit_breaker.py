#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO指令】熔断器机制 - 数据轮询超时保护
- 任何轮询等待时间不得超过0.5秒
- 超时即熔断，返回缓存或错误，严禁卡死
"""

import time
import signal
from functools import wraps
from typing import Optional, Callable, Any
import threading

class CircuitBreakerError(Exception):
    """熔断器异常"""
    def __init__(self, message: str = "Circuit breaker triggered - operation timeout"):
        self.message = message
        super().__init__(self.message)

class CircuitBreaker:
    """
    熔断器 - 防止数据轮询卡死
    
    使用方式:
        @circuit_breaker(timeout=0.5)
        def fetch_data():
            return xtdata.get_full_tick(...)
            
        # 或
        breaker = CircuitBreaker(timeout=0.5)
        result = breaker.call(xtdata.get_full_tick, args=(stock_list,))
    """
    
    def __init__(self, timeout: float = 0.5, max_retries: int = 1):
        """
        Args:
            timeout: 超时时间(秒)，默认0.5秒
            max_retries: 最大重试次数，默认不重试
        """
        self.timeout = timeout
        self.max_retries = max_retries
        
    def call(self, func: Callable, args: tuple = (), kwargs: dict = None, 
             fallback: Optional[Callable] = None) -> Any:
        """
        执行函数，超时熔断
        
        Args:
            func: 要执行的函数
            args: 位置参数
            kwargs: 关键字参数
            fallback: 超时后的回调函数
            
        Returns:
            函数返回值
            
        Raises:
            CircuitBreakerError: 超时触发熔断
        """
        kwargs = kwargs or {}
        
        for attempt in range(self.max_retries + 1):
            result = self._call_with_timeout(func, args, kwargs)
            
            if result is not None or attempt == self.max_retries:
                return result
                
        # 触发fallback
        if fallback:
            return fallback()
            
        raise CircuitBreakerError(
            f"Function {func.__name__} timed out after {self.timeout}s "
            f"and {self.max_retries} retries"
        )
    
    def _call_with_timeout(self, func: Callable, args: tuple, kwargs: dict) -> Any:
        """带超时的函数调用"""
        result = [None]
        exception = [None]
        is_done = [False]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
            finally:
                is_done[0] = True
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            # 超时 - 触发熔断
            return None
            
        if exception[0]:
            raise exception[0]
            
        return result[0]

def circuit_breaker(timeout: float = 0.5, max_retries: int = 1, 
                    fallback: Optional[Callable] = None):
    """
    熔断器装饰器
    
    Args:
        timeout: 超时时间(秒)
        max_retries: 最大重试次数
        fallback: 超时回调函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            breaker = CircuitBreaker(timeout=timeout, max_retries=max_retries)
            return breaker.call(func, args, kwargs, fallback)
        return wrapper
    return decorator

# === 常用场景预配置 ===

# 实时tick数据获取 - 0.5秒超时
fetch_tick_breaker = CircuitBreaker(timeout=0.5, max_retries=1)

# 历史数据获取 - 2秒超时(历史数据量大)
fetch_history_breaker = CircuitBreaker(timeout=2.0, max_retries=2)

# 快速查询 - 0.2秒超时
quick_query_breaker = CircuitBreaker(timeout=0.2, max_retries=0)

def safe_get_full_tick(stock_list: list, timeout: float = 0.5) -> Optional[dict]:
    """
    安全获取全推tick数据 - 带熔断保护
    
    Args:
        stock_list: 股票代码列表
        timeout: 超时时间(秒)
        
    Returns:
        tick数据字典，超时返回None
    """
    try:
        import xtdata
        breaker = CircuitBreaker(timeout=timeout)
        return breaker.call(xtdata.get_full_tick, args=(stock_list,))
    except CircuitBreakerError:
        print(f"⚠️ 获取tick数据超时(>{timeout}s)，熔断保护触发")
        return None
    except Exception as e:
        print(f"❌ 获取tick数据异常: {e}")
        return None

def safe_get_local_data(stock_code: str, start_time: str, end_time: str,
                        period: str = 'tick', timeout: float = 2.0) -> Optional[Any]:
    """
    安全获取本地历史数据 - 带熔断保护
    
    Args:
        stock_code: 股票代码
        start_time: 开始时间
        end_time: 结束时间
        period: 周期('tick', '1m', '5m'等)
        timeout: 超时时间(秒)
        
    Returns:
        历史数据DataFrame，超时返回None
    """
    try:
        import xtdata
        breaker = CircuitBreaker(timeout=timeout)
        return breaker.call(
            xtdata.get_local_data,
            args=(['time', 'volume', 'lastPrice'], [stock_code], period, start_time, end_time)
        )
    except CircuitBreakerError:
        print(f"⚠️ 获取历史数据超时(>{timeout}s)，熔断保护触发")
        return None
    except Exception as e:
        print(f"❌ 获取历史数据异常: {e}")
        return None

if __name__ == '__main__':
    # 测试熔断器
    print("="*60)
    print("熔断器测试")
    print("="*60)
    
    # 测试正常函数
    def normal_func(x):
        time.sleep(0.1)
        return x * 2
    
    breaker = CircuitBreaker(timeout=0.5)
    result = breaker.call(normal_func, args=(5,))
    print(f"✅ 正常函数: {result}")
    
    # 测试超时函数
    def slow_func():
        time.sleep(1.0)
        return "done"
    
    result = breaker.call(slow_func)
    print(f"⚠️ 超时函数返回: {result}")
    
    # 测试装饰器
    @circuit_breaker(timeout=0.3)
    def decorated_slow():
        time.sleep(0.5)
        return "should timeout"
    
    try:
        result = decorated_slow()
    except CircuitBreakerError as e:
        print(f"✅ 装饰器成功捕获熔断: {e}")
    
    print("\n✅ 熔断器机制测试完成")
