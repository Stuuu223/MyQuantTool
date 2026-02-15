#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票名称查询工具（本地 JSON 映射）

Usage:
    from logic.utils.stock_name_fetcher import get_stock_name
    name = get_stock_name('000001.SZ')  # 返回 '平安银行'

    from logic.utils.stock_name_fetcher import get_stock_names
    names = get_stock_names(['000001.SZ', '600000.SH'])
    # 返回 {'000001.SZ': '平安银行', '600000.SH': '浦发银行'}
"""

import json
from pathlib import Path
from functools import lru_cache

class StockNameFetcher:
    """
    股票名称获取器（本地缓存）

    特性：
    - 单例模式，全局唯一实例
    - LRU 缓存，最近查询的股票名称缓存在内存中
    - 本地 JSON 查询，无需网络请求
    - 毫秒级响应速度
    """

    _instance = None
    _stock_names = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """加载股票名称映射表"""
        if self._stock_names is None:
            self._load_stock_names()

    def _load_stock_names(self):
        """从本地 JSON 加载股票名称"""
        json_path = Path(__file__).parent.parent / 'data' / 'stock_names.json'

        if not json_path.exists():
            raise FileNotFoundError(
                f"❌ 股票名称映射文件不存在: {json_path}\n"
                f"请先运行: python scripts/download_stock_names.py"
            )

        with open(json_path, 'r', encoding='utf-8') as f:
            self._stock_names = json.load(f)

        print(f"✅ [StockNameFetcher] 加载 {len(self._stock_names)} 只股票名称")

    @lru_cache(maxsize=10000)
    def get_name(self, stock_code: str) -> str:
        """
        获取股票名称（带缓存）

        Args:
            stock_code: 股票代码（如 '000001.SZ'）

        Returns:
            股票名称，未找到则返回股票代码本身
        """
        return self._stock_names.get(stock_code, stock_code)

    def get_names(self, stock_codes: list) -> dict:
        """
        批量获取股票名称

        Args:
            stock_codes: 股票代码列表

        Returns:
            {stock_code: name} 映射字典
        """
        return {code: self.get_name(code) for code in stock_codes}

    def reload(self):
        """重新加载股票名称（更新后调用）"""
        self._stock_names = None
        self._load_stock_names()
        self.get_name.cache_clear()  # 清空缓存
        print("✅ [StockNameFetcher] 股票名称已重新加载")

    def get_all_names(self) -> dict:
        """获取所有股票名称（不使用缓存）"""
        return self._stock_names.copy()

    def search_by_name(self, keyword: str) -> dict:
        """
        根据股票名称搜索股票代码

        Args:
            keyword: 搜索关键词

        Returns:
            {stock_code: name} 匹配的股票列表
        """
        keyword = keyword.lower()
        return {
            code: name
            for code, name in self._stock_names.items()
            if keyword in name.lower()
        }


# 全局单例
_fetcher = StockNameFetcher()

def get_stock_name(stock_code: str) -> str:
    """
    快捷函数：获取股票名称

    Usage:
        >>> from logic.utils.stock_name_fetcher import get_stock_name
        >>> get_stock_name('000001.SZ')
        '平安银行'
        >>> get_stock_name('600000.SH')
        '浦发银行'
    """
    return _fetcher.get_name(stock_code)


def get_stock_names(stock_codes: list) -> dict:
    """
    快捷函数：批量获取股票名称

    Usage:
        >>> from logic.utils.stock_name_fetcher import get_stock_names
        >>> get_stock_names(['000001.SZ', '600000.SH'])
        {'000001.SZ': '平安银行', '600000.SH': '浦发银行'}
    """
    return _fetcher.get_names(stock_codes)


def reload_stock_names():
    """
    快捷函数：重新加载股票名称
    用于每月更新后刷新缓存
    """
    _fetcher.reload()


def get_all_stock_names() -> dict:
    """
    快捷函数：获取所有股票名称
    """
    return _fetcher.get_all_names()


def search_stock_by_name(keyword: str) -> dict:
    """
    快捷函数：根据股票名称搜索股票代码

    Usage:
        >>> search_stock_by_name('银行')
        {'600000.SH': '浦发银行', '601166.SH': '兴业银行', ...}
    """
    return _fetcher.search_by_name(keyword)


def get_fetcher() -> StockNameFetcher:
    """
    快捷函数：获取 StockNameFetcher 实例

    Usage:
        >>> from logic.utils.stock_name_fetcher import get_fetcher
        >>> fetcher = get_fetcher()
        >>> fetcher.get_name('000001.SZ')
        '平安银行'
    """
    return _fetcher