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
from logic.utils.logger import get_logger
from logic.data_providers.data_provider_factory import DataProviderFactory

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

    def get_history_data(self, symbol: str, period: str = 'daily', adjust: str = 'qfq', start_date: str = None, end_date: str = None):
        """
        获取历史数据（代理方法）
        
        V17修复：统一日期格式，确保返回DateTimeIndex

        Args:
            symbol: 股票代码
            period: 周期（daily, weekly, monthly）
            adjust: 复权方式（qfq: 前复权, hfq: 后复权, none: 不复权）
            start_date: 开始日期（格式：YYYYMMDD），暂不支持
            end_date: 结束日期（格式：YYYYMMDD），暂不支持

        Returns:
            DataFrame: 历史数据，index为DateTimeIndex
        """
        import pandas as pd
        
        # 从provider获取原始数据
        df = self.provider.get_history_data(symbol, period, adjust)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # V17修复：统一处理日期格式
        # 情况1: 'date'列存在，可能是Unix毫秒时间戳或字符串日期
        if 'date' in df.columns:
            # 尝试转换为数值（Unix毫秒时间戳）
            try:
                df['date'] = pd.to_numeric(df['date'], errors='coerce')
                # 如果是Unix时间戳（数值较大，如1668700800000），用unit='ms'
                if df['date'].max() > 1e10:  # 毫秒时间戳的特征
                    df.index = pd.to_datetime(df['date'], unit='ms')
                else:
                    # 可能是秒级时间戳或已经是日期格式
                    df.index = pd.to_datetime(df['date'])
            except:
                # 如果转换失败，尝试直接作为日期字符串解析
                df.index = pd.to_datetime(df['date'], errors='coerce')
            
            # 删除原始date列（避免重复）
            df.drop(columns=['date'], inplace=True, errors='ignore')
        
        # 情况2: 索引已经是datetime类型，无需处理
        elif isinstance(df.index, pd.DatetimeIndex):
            pass
        
        # 情况3: 其他情况，尝试将索引转换为datetime
        else:
            try:
                df.index = pd.to_datetime(df.index)
            except:
                logger.warning(f"⚠️ 无法将 {symbol} 的索引转换为日期: {type(df.index)}")
        
        # 确保按日期排序
        if isinstance(df.index, pd.DatetimeIndex):
            df.sort_index(inplace=True)
        
        # 删除可能的冗余列
        for col in ['index']:
            if col in df.columns:
                df.drop(columns=[col], inplace=True, errors='ignore')
        
        return df

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

    def get_fast_price(self, stock_list: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        获取多只股票的实时数据（向后兼容）

        Args:
            stock_list: 股票代码列表

        Returns:
            dict: 股票数据字典，格式：{code: data_dict}
        """
        try:
            # 获取实时数据
            realtime_data = self.get_realtime_data(stock_list)
            
            # 转换为字典格式
            result = {}
            for stock_data in realtime_data:
                code = stock_data.get('code', '')
                if code:
                    result[code] = {
                        'name': stock_data.get('name', ''),
                        'now': stock_data.get('price', 0),  # 🆕 V19.6 修复：price -> now
                        'close': stock_data.get('pre_close', 0),  # 🆕 V19.6 修复：pre_close -> close
                        'open': stock_data.get('open', 0),
                        'high': stock_data.get('high', 0),
                        'low': stock_data.get('low', 0),
                        'volume': stock_data.get('volume', 0),
                        'turnover': stock_data.get('turnover', 0),  # 换手率
                        'amount': stock_data.get('amount', 0),  # 成交额
                        'volume_ratio': stock_data.get('volume_ratio', 0),  # 🆕 V19.6 修复：volume_ratio
                        'bid1': stock_data.get('bid1', 0),  # 🆕 V19.6 新增：买一价
                        'ask1': stock_data.get('ask1', 0),  # 🆕 V19.6 新增：卖一价
                        'bid1_volume': stock_data.get('bid1_volume', 0),  # 🆕 V19.6 新增：买一量
                        'ask1_volume': stock_data.get('ask1_volume', 0),  # 🆕 V19.6 新增：卖一量
                        'time': stock_data.get('data_timestamp', '')
                    }
            
            return result
        except Exception as e:
            logger.error(f"获取快速价格失败: {e}")
            return {}
    
    # ==================== 并发获取方法（V1.0 新增） ====================
    
    def get_fast_price_concurrent(self, stock_list: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
        """
        并发获取多只股票的实时数据（优化版）
        
        使用多线程并发获取，大幅提升速度
        
        Args:
            stock_list: 股票代码列表
            batch_size: 每批处理的股票数量
        
        Returns:
            dict: 股票数据字典，格式：{code: data_dict}
        """
        try:
            from logic.concurrent.concurrent_executor import batch_get_realtime_data_fast
            return batch_get_realtime_data_fast(self, stock_list, batch_size)
        except Exception as e:
            logger.error(f"并发获取快速价格失败: {e}")
            # 降级到同步获取
            return self.get_fast_price(stock_list)
    
    def get_history_data_concurrent(self, stock_list: List[str], **kwargs) -> Dict[str, Any]:
        """
        并发获取多只股票的历史数据（优化版）
        
        Args:
            stock_list: 股票代码列表
            **kwargs: 传递给 get_history_data 的参数
        
        Returns:
            dict: 股票历史数据字典 {code: df}
        """
        try:
            from logic.concurrent.concurrent_executor import batch_get_history_data_fast
            return batch_get_history_data_fast(self, stock_list, **kwargs)
        except Exception as e:
            logger.error(f"并发获取历史数据失败: {e}")
            # 降级到同步获取
            return {}

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

    def close(self):
        """
        关闭数据库连接（向后兼容）

        注意：
        - 在纯代理模式下，DataManager 不直接管理数据库连接
        - 数据库连接由 DataProviderFactory 管理
        - 此方法为空实现，保持向后兼容
        """
        # 🚀 V18.6.1: 纯代理模式下，DataManager 不直接管理数据库连接
        # 数据库连接由 DataProviderFactory 管理
        # 此方法为空实现，保持向后兼容
        logger.debug("DataManager.close() 调用（纯代理模式，无需关闭连接）")


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