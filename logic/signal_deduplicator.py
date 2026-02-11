#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号去重器

功能：
1. 时间窗口去重（30分钟内相同股票+相同信号只保留一次）
2. LRU缓存机制（最多保留100个信号）
3. 自动过期清理（超过30分钟自动删除）
4. 线程安全设计

Author: MyQuantTool Team
Date: 2026-02-11
"""

import time
import threading
from typing import Dict, Tuple, Optional
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta

from logic.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SignalRecord:
    """信号记录"""
    stock_code: str
    signal_type: str
    timestamp: float
    confidence: float
    details: dict


class SignalDeduplicator:
    """
    信号去重器
    
    使用场景：
    - 实时监控中，避免重复预警
    - 全市场扫描，去除重复记录
    
    去重策略：
    - 相同股票 + 相同信号类型 + 30分钟内 → 视为重复
    - 超过30分钟自动过期
    
    示例：
    ```python
    dedup = SignalDeduplicator(window_minutes=30, max_cache_size=100)
    
    if dedup.is_duplicate('600000.SH', 'TRAP_WARNING'):
        logger.info("重复信号，忽略")
    else:
        dedup.add_signal('600000.SH', 'TRAP_WARNING', confidence=0.85)
        logger.info("新信号，发送预警")
    ```
    """
    
    def __init__(self, window_minutes: int = 30, max_cache_size: int = 100):
        """
        初始化去重器
        
        Args:
            window_minutes: 时间窗口（分钟）
            max_cache_size: 最大缓存大小
        """
        self.window_seconds = window_minutes * 60
        self.max_cache_size = max_cache_size
        
        # 使用OrderedDict实现LRU缓存
        self._cache: OrderedDict[Tuple[str, str], SignalRecord] = OrderedDict()
        self._lock = threading.Lock()  # 线程安全
        
        logger.info(f"SignalDeduplicator 初始化: window={window_minutes}min, max_size={max_cache_size}")
    
    def is_duplicate(self, stock_code: str, signal_type: str) -> bool:
        """
        检查是否为重复信号
        
        Args:
            stock_code: 股票代码
            signal_type: 信号类型
        
        Returns:
            True: 重复信号
            False: 新信号
        """
        key = (stock_code, signal_type)
        current_time = time.time()
        
        with self._lock:
            # 清理过期信号
            self._cleanup_expired(current_time)
            
            if key in self._cache:
                record = self._cache[key]
                time_diff = current_time - record.timestamp
                
                if time_diff < self.window_seconds:
                    logger.debug(f"重复信号: {stock_code} {signal_type} (距上次 {time_diff:.0f}秒)")
                    return True
                else:
                    # 过期，删除旧记录
                    del self._cache[key]
            
            return False
    
    def add_signal(
        self,
        stock_code: str,
        signal_type: str,
        confidence: float = 0.0,
        details: Optional[dict] = None
    ):
        """
        添加新信号
        
        Args:
            stock_code: 股票代码
            signal_type: 信号类型
            confidence: 置信度
            details: 额外详情
        """
        key = (stock_code, signal_type)
        current_time = time.time()
        
        record = SignalRecord(
            stock_code=stock_code,
            signal_type=signal_type,
            timestamp=current_time,
            confidence=confidence,
            details=details or {}
        )
        
        with self._lock:
            # LRU策略：如果已存在，移除旧记录
            if key in self._cache:
                del self._cache[key]
            
            # 添加新记录
            self._cache[key] = record
            
            # 检查缓存大小，删除最旧记录
            if len(self._cache) > self.max_cache_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"缓存满，删除最旧记录: {oldest_key}")
            
            logger.debug(f"添加信号: {stock_code} {signal_type} (confidence={confidence:.2f})")
    
    def _cleanup_expired(self, current_time: float):
        """
        清理过期信号（内部方法，已加锁）
        """
        expired_keys = [
            key for key, record in self._cache.items()
            if current_time - record.timestamp > self.window_seconds
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"清理过期信号: {len(expired_keys)} 个")
    
    def get_recent_signals(self, minutes: int = 30) -> list[SignalRecord]:
        """
        获取最近N分钟的信号
        
        Args:
            minutes: 时间范围（分钟）
        
        Returns:
            信号记录列表
        """
        cutoff_time = time.time() - (minutes * 60)
        
        with self._lock:
            return [
                record for record in self._cache.values()
                if record.timestamp >= cutoff_time
            ]
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            {
                'total_signals': 总信号数,
                'cache_size': 缓存大小,
                'oldest_signal_age': 最旧信号年龄（秒）
            }
        """
        with self._lock:
            if not self._cache:
                return {
                    'total_signals': 0,
                    'cache_size': 0,
                    'oldest_signal_age': 0
                }
            
            oldest_record = next(iter(self._cache.values()))
            oldest_age = time.time() - oldest_record.timestamp
            
            return {
                'total_signals': len(self._cache),
                'cache_size': len(self._cache),
                'oldest_signal_age': oldest_age
            }
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("SignalDeduplicator 缓存已清空")


# 全局单例
_global_deduplicator: Optional[SignalDeduplicator] = None


def get_signal_deduplicator(window_minutes: int = 30, max_cache_size: int = 100) -> SignalDeduplicator:
    """
    获取全局去重器单例
    
    Args:
        window_minutes: 时间窗口（分钟）
        max_cache_size: 最大缓存大小
    
    Returns:
        SignalDeduplicator 实例
    """
    global _global_deduplicator
    
    if _global_deduplicator is None:
        _global_deduplicator = SignalDeduplicator(
            window_minutes=window_minutes,
            max_cache_size=max_cache_size
        )
    
    return _global_deduplicator
