"""
缓存管理模块
提供数据缓存功能，提升系统性能
"""

import pandas as pd
import time
from datetime import datetime, timedelta


class CacheManager:
    """缓存管理器"""

    _cache = {}
    _cache_timestamps = {}
    _default_ttl = 300  # 默认缓存5分钟

    @staticmethod
    def get(key):
        """获取缓存数据"""
        if key not in CacheManager._cache:
            return None

        # 检查是否过期
        timestamp = CacheManager._cache_timestamps.get(key, 0)
        
        # 优先检查自定义 TTL
        ttl_key = f"{key}_ttl"
        if ttl_key in CacheManager._cache_timestamps:
            ttl = CacheManager._cache_timestamps[ttl_key]
        else:
            ttl = CacheManager._default_ttl
        
        if time.time() - timestamp > ttl:
            # 缓存过期，删除
            del CacheManager._cache[key]
            del CacheManager._cache_timestamps[key]
            # 同时删除 TTL 记录
            if ttl_key in CacheManager._cache_timestamps:
                del CacheManager._cache_timestamps[ttl_key]
            return None

        return CacheManager._cache[key]

    @staticmethod
    def set(key, value, ttl=None):
        """设置缓存数据"""
        CacheManager._cache[key] = value
        CacheManager._cache_timestamps[key] = time.time()

        # 如果需要，可以设置单独的TTL
        if ttl:
            CacheManager._cache_timestamps[f"{key}_ttl"] = ttl

    @staticmethod
    def clear(key=None):
        """清除缓存"""
        if key:
            if key in CacheManager._cache:
                del CacheManager._cache[key]
                del CacheManager._cache_timestamps[key]
                # 同时删除 TTL 记录
                ttl_key = f"{key}_ttl"
                if ttl_key in CacheManager._cache_timestamps:
                    del CacheManager._cache_timestamps[ttl_key]
        else:
            CacheManager._cache.clear()
            CacheManager._cache_timestamps.clear()

    @staticmethod
    def clear_expired():
        """清除所有过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, timestamp in CacheManager._cache_timestamps.items():
            # 跳过 TTL 键本身
            if key.endswith('_ttl'):
                continue
            
            # 检查自定义 TTL
            ttl_key = f"{key}_ttl"
            if ttl_key in CacheManager._cache_timestamps:
                ttl = CacheManager._cache_timestamps[ttl_key]
            else:
                ttl = CacheManager._default_ttl
            
            if current_time - timestamp > ttl:
                expired_keys.append(key)

        for key in expired_keys:
            if key in CacheManager._cache:
                del CacheManager._cache[key]
            del CacheManager._cache_timestamps[key]
            # 同时删除 TTL 记录
            ttl_key = f"{key}_ttl"
            if ttl_key in CacheManager._cache_timestamps:
                del CacheManager._cache_timestamps[ttl_key]

    @staticmethod
    def get_cache_info():
        """获取缓存信息"""
        return {
            '缓存数量': len(CacheManager._cache),
            '缓存键列表': list(CacheManager._cache.keys())
        }


def cached(key_prefix, ttl=300):
    """
    缓存装饰器
    用于缓存函数的返回结果
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}_{str(args)}_{str(kwargs)}"

            # 尝试从缓存获取
            cached_result = CacheManager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数
            result = func(*args, **kwargs)

            # 缓存结果
            CacheManager.set(cache_key, result, ttl=ttl)

            return result
        return wrapper
    return decorator