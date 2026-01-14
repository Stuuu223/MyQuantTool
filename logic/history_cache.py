"""
历史数据缓存管理器
用于缓存股票的历史数据，避免重复从数据库读取
"""
import time
from typing import Dict, Optional
import pandas as pd
from logic.logger import get_logger

logger = get_logger(__name__)


class HistoryCache:
    """历史数据缓存类"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        初始化缓存

        Args:
            max_size: 最大缓存数量
            ttl: 缓存过期时间（秒），默认 1 小时
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict] = {}
        self.access_order = []  # 用于 LRU 淘汰

    def get(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        从缓存获取历史数据

        Args:
            symbol: 股票代码

        Returns:
            历史数据 DataFrame，如果不存在或已过期则返回 None
        """
        if symbol not in self.cache:
            return None

        cache_item = self.cache[symbol]

        # 检查是否过期
        if time.time() - cache_item['timestamp'] > self.ttl:
            logger.debug(f"缓存已过期: {symbol}")
            del self.cache[symbol]
            self.access_order.remove(symbol)
            return None

        # 更新访问顺序（LRU）
        self.access_order.remove(symbol)
        self.access_order.append(symbol)

        logger.debug(f"缓存命中: {symbol}")
        return cache_item['data']

    def set(self, symbol: str, data: pd.DataFrame) -> None:
        """
        将历史数据存入缓存

        Args:
            symbol: 股票代码
            data: 历史数据 DataFrame
        """
        # 如果缓存已满，淘汰最久未使用的数据
        if len(self.cache) >= self.max_size and symbol not in self.cache:
            oldest_symbol = self.access_order.pop(0)
            del self.cache[oldest_symbol]
            logger.debug(f"缓存淘汰: {oldest_symbol}")

        # 存入缓存
        self.cache[symbol] = {
            'data': data,
            'timestamp': time.time()
        }

        # 更新访问顺序
        if symbol in self.access_order:
            self.access_order.remove(symbol)
        self.access_order.append(symbol)

        logger.debug(f"缓存存入: {symbol}")

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.access_order.clear()
        logger.info("缓存已清空")

    def get_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        return {
            '缓存数量': len(self.cache),
            '最大容量': self.max_size,
            '使用率': f"{len(self.cache) / self.max_size * 100:.1f}%",
            '过期时间': f"{self.ttl}秒"
        }


# 全局缓存实例
_global_cache = HistoryCache(max_size=2000, ttl=3600)  # 缓存 2000 只股票，1 小时过期


def get_history_cache() -> HistoryCache:
    """获取全局历史数据缓存实例"""
    return _global_cache