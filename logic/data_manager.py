#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据管理器 (DataManager) - V18.6.1 纯代理模式

功能：
- 作为数据访问的统一入口
- 代理所有数据请求到 DataProviderFactory
- 支持实时数据和历史回放数据两种模式
- 提供向后兼容的接口

架构：
- 纯代理模式（Proxy Pattern）
- 强制使用 DataProviderFactory
- 移除所有旧逻辑

Author: iFlow CLI
Version: V18.6.1
"""

import os
from typing import Optional, Dict, Any, List
from logic.logger import get_logger
from logic.data_provider_factory import DataProviderFactory

logger = get_logger(__name__)


class DataManager:
    """
    数据管理器 - 纯代理模式

    功能：
    - 作为数据访问的统一入口
    - 代理所有数据请求到 DataProviderFactory
    - 支持实时数据和历史回放数据两种模式
    - 提供向后兼容的接口

    架构：
    - 纯代理模式（Proxy Pattern）
    - 强制使用 DataProviderFactory
    - 移除所有旧逻辑
    """

    _instance = None
    _initialized = False

    def __new__(cls, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, mode='live', **kwargs):
        """
        初始化数据管理器

        Args:
            mode: 数据模式
                - 'live': 实时数据模式（默认）
                - 'replay': 历史回放模式
            **kwargs: 额外参数
                - date: 历史日期（仅 replay 模式需要，格式：'20260116'）
                - stock_list: 股票列表（可选）
        """
        # 避免重复初始化
        if DataManager._initialized:
            return

        logger.info(f"初始化 DataManager，模式: {mode}")

        # 🚀 V18.6.1: 强制使用 DataProviderFactory
        self.mode = mode
        self.kwargs = kwargs
        self.provider = None

        # 初始化数据提供者
        self._init_provider()

        DataManager._initialized = True
        logger.info("DataManager 初始化完成")

    def _init_provider(self):
        """初始化数据提供者"""
        try:
            self.provider = DataProviderFactory.get_provider(mode=self.mode, **self.kwargs)
            logger.info(f"✅ 数据提供者初始化成功: {self.mode}")
        except Exception as e:
            logger.error(f"❌ 数据提供者初始化失败: {e}")
            raise

    # ==================== 代理方法：转发所有请求到 Provider ====================

    def get_realtime_data(self, stock_list):
        """
        获取实时数据（代理方法）

        Args:
            stock_list: 股票代码列表或包含股票信息的字典列表

        Returns:
            list: 股票数据列表
        """
        return self.provider.get_realtime_data(stock_list)

    def get_market_data(self):
        """
        获取市场整体数据（代理方法）

        Returns:
            dict: 市场数据
        """
        return self.provider.get_market_data()

    def get_history_data(self, symbol: str, period: str = 'daily', adjust: str = 'qfq'):
        """
        获取历史数据（代理方法）

        Args:
            symbol: 股票代码
            period: 周期（daily, weekly, monthly）
            adjust: 复权方式（qfq: 前复权, hfq: 后复权, none: 不复权）

        Returns:
            DataFrame: 历史数据
        """
        return self.provider.get_history_data(symbol, period, adjust)

    # ==================== 向后兼容的接口 ====================

    def get_realtime_data_dict(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票的实时数据（向后兼容）

        Args:
            stock_code: 股票代码

        Returns:
            dict: 股票数据字典
        """
        result = self.get_realtime_data([stock_code])
        if result and len(result) > 0:
            return result[0]
        return None

    def get_limit_up_stocks(self, date: str = None) -> List[str]:
        """
        获取涨停板股票列表（向后兼容）

        Args:
            date: 日期字符串，格式YYYYMMDD

        Returns:
            list: 股票代码列表
        """
        try:
            import akshare as ak

            if date is None:
                from datetime import datetime
                date = datetime.now().strftime("%Y%m%d")

            # 获取涨停板数据
            df = ak.stock_zt_pool_em(date=date)

            if df is not None and not df.empty:
                return df['代码'].tolist()

            return []

        except Exception as e:
            logger.error(f"获取涨停板数据失败: {e}")
            return []

    # ==================== 数据库相关方法（保留向后兼容）====================

    def sqlite_execute(self, sql: str, params: tuple = None):
        """
        执行 SQL 语句（向后兼容）

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            cursor
        """
        # 🚀 V18.6.1: 代理到 provider
        if hasattr(self.provider, 'sqlite_execute'):
            return self.provider.sqlite_execute(sql, params)
        else:
            logger.warning("⚠️ 当前 provider 不支持 sqlite_execute")
            return None

    def sqlite_query(self, sql: str, params: tuple = None):
        """
        查询 SQL 语句（向后兼容）

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            list: 查询结果
        """
        # 🚀 V18.6.1: 代理到 provider
        if hasattr(self.provider, 'sqlite_query'):
            return self.provider.sqlite_query(sql, params)
        else:
            logger.warning("⚠️ 当前 provider 不支持 sqlite_query")
            return []

    # ==================== 工厂方法 ====================

    @staticmethod
    def get_instance(mode='live', **kwargs):
        """
        获取 DataManager 实例（工厂方法）

        Args:
            mode: 数据模式
            **kwargs: 额外参数

        Returns:
            DataManager: 数据管理器实例
        """
        return DataManager(mode=mode, **kwargs)

    @staticmethod
    def reset():
        """重置单例（用于测试）"""
        DataManager._instance = None
        DataManager._initialized = False
        logger.info("DataManager 单例已重置")


# 单例测试
if __name__ == "__main__":
    # 测试实时数据模式
    dm = DataManager(mode='live')
    print("DataManager 初始化成功")

    # 测试获取实时数据
    data = dm.get_realtime_data(['600519'])
    print(f"获取到 {len(data)} 只股票的数据")

    # 测试获取市场数据
    market_data = dm.get_market_data()
    print(f"市场数据: {market_data}")