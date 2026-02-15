#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API稳健调用工具 - V19.8

功能：
- 给数据源加装"防弹衣"（Retry & Backoff装饰器）
- 自动重试机制，避免网络波动导致的数据获取失败
- 递增等待时间，避免被封IP

Author: iFlow CLI
Version: V19.8
"""

import time
import functools
import pandas as pd
from typing import Callable, Any, Optional
from requests.exceptions import RequestException, ConnectionError
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def robust_api_call(max_retries: int = 3, delay: int = 2, 
                    return_empty_df: bool = False, 
                    return_none_on_failure: bool = False) -> Callable:
    """
    稳健的API调用装饰器
    
    功能：
    1. 遇到网络错误自动重试
    2. 每次重试前休息几秒（避免被封）
    3. 捕获所有异常，防止程序崩溃
    4. 支持返回空DataFrame或None
    
    Args:
        max_retries: 最大重试次数（默认3次）
        delay: 初始延迟时间（秒，默认2秒）
        return_empty_df: 失败时返回空DataFrame（默认False）
        return_none_on_failure: 失败时返回None（默认False）
    
    Returns:
        装饰器函数
    
    使用方法：
        @robust_api_call()
        def get_realtime_data(code):
            return ak.stock_zh_a_spot_em()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for i in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    
                    # 检查返回结果是否为空
                    if result is None:
                        if i < max_retries - 1:
                            logger.warning(f"⚠️ [{func.__name__}] 返回值为None，第{i+1}次重试...")
                            time.sleep(delay * (i + 1))
                            continue
                        else:
                            logger.error(f"💀 [{func.__name__}] 最终失败，返回值为None")
                            return pd.DataFrame() if return_empty_df else None
                    
                    # 检查DataFrame是否为空
                    if isinstance(result, pd.DataFrame) and result.empty:
                        if i < max_retries - 1:
                            logger.warning(f"⚠️ [{func.__name__}] 返回空DataFrame，第{i+1}次重试...")
                            time.sleep(delay * (i + 1))
                            continue
                        else:
                            logger.error(f"💀 [{func.__name__}] 最终失败，返回空DataFrame")
                            return pd.DataFrame() if return_empty_df else None
                    
                    # 成功获取数据
                    return result
                    
                except (RequestException, ConnectionError) as e:
                    if i < max_retries - 1:
                        logger.warning(f"⚠️ [网络波动] {func.__name__} 第{i+1}次重试... ({e})")
                        time.sleep(delay * (i + 1))  # 递增等待：2s, 4s, 6s
                    else:
                        logger.error(f"💀 [网络失败] {func.__name__} 无法获取数据: {e}")
                        return pd.DataFrame() if return_empty_df else None
                        
                except Exception as e:
                    logger.error(f"❌ [数据源严重错误] {func.__name__}: {e}")
                    return pd.DataFrame() if return_empty_df else None
            
            # 所有重试都失败
            logger.error(f"💀 [最终失败] {func.__name__} 无法获取数据，返回空值")
            return pd.DataFrame() if return_empty_df else None
        
        return wrapper
    return decorator


def rate_limit_decorator(calls_per_second: int = 5) -> Callable:
    """
    速率限制装饰器
    
    功能：
    - 限制函数调用频率，避免被封IP
    - 适用于高频API调用场景
    
    Args:
        calls_per_second: 每秒最大调用次数（默认5次）
    
    Returns:
        装饰器函数
    
    使用方法：
        @rate_limit_decorator(calls_per_second=3)
        def get_stock_data(code):
            return ak.stock_zh_a_spot_em()
    """
    def decorator(func: Callable) -> Callable:
        last_call_time = [0]  # 使用列表避免闭包问题
        min_interval = 1.0 / calls_per_second
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_time = time.time()
            elapsed = current_time - last_call_time[0]
            
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                logger.debug(f"⏱️ [{func.__name__}] 速率限制，等待{sleep_time:.2f}秒")
                time.sleep(sleep_time)
            
            last_call_time[0] = time.time()
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def fallback_decorator(primary_func: Callable, fallback_func: Callable) -> Callable:
    """
    降级策略装饰器
    
    功能：
    - 如果主函数失败，自动切换到备用函数
    - 适用于多数据源场景
    
    Args:
        primary_func: 主函数
        fallback_func: 备用函数
    
    Returns:
        装饰器函数
    
    使用方法：
        def get_stock_data_backup(code):
            return ef.stock.get_quote_history(code)
        
        @fallback_decorator(get_stock_data_primary, get_stock_data_backup)
        def get_stock_data(code):
            return ak.stock_zh_a_hist(symbol=code, period="daily")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                # 尝试调用主函数
                result = primary_func(*args, **kwargs)
                
                # 检查结果是否有效
                if result is None:
                    raise ValueError("主函数返回None")
                
                if isinstance(result, pd.DataFrame) and result.empty:
                    raise ValueError("主函数返回空DataFrame")
                
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ [{func.__name__}] 主函数失败，切换备用源: {e}")
                
                try:
                    # 切换到备用函数
                    result = fallback_func(*args, **kwargs)
                    
                    if result is None or (isinstance(result, pd.DataFrame) and result.empty):
                        logger.error(f"💀 [{func.__name__}] 备用函数也失败")
                        return None
                    
                    logger.info(f"✅ [{func.__name__}] 备用函数成功")
                    return result
                    
                except Exception as fallback_error:
                    logger.error(f"❌ [{func.__name__}] 备用函数失败: {fallback_error}")
                    return None
        
        return wrapper
    return decorator