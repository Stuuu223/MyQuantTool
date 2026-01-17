#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据提供者工厂
支持实时数据和历史回放数据两种模式
"""

from logic.logger import get_logger

logger = get_logger(__name__)


class DataProviderFactory:
    """
    数据提供者工厂
    
    功能：
    - 根据模式返回实时数据提供者或历史回放数据提供者
    - 支持无缝切换，无需修改核心算法代码
    """
    
    @staticmethod
    def get_provider(mode='live', **kwargs):
        """
        获取数据提供者
        
        Args:
            mode: 数据模式
                - 'live': 实时数据模式（默认）
                - 'replay': 历史回放模式
            **kwargs: 额外参数
                - date: 历史日期（仅 replay 模式需要，格式：'20260116'）
                - stock_list: 股票列表（可选）
        
        Returns:
            DataProvider: 数据提供者实例
        """
        if mode == 'live':
            from logic.realtime_data_provider import RealtimeDataProvider
            return RealtimeDataProvider(**kwargs)
        elif mode == 'replay':
            from logic.historical_replay_provider import HistoricalReplayProvider
            return HistoricalReplayProvider(**kwargs)
        else:
            raise ValueError(f"不支持的 data mode: {mode}")


class DataProvider:
    """
    数据提供者基类
    定义统一的数据接口
    """
    
    def get_realtime_data(self, stock_list):
        """
        获取实时数据
        
        Args:
            stock_list: 股票代码列表或包含股票信息的字典列表
        
        Returns:
            list: 股票数据列表，每只股票包含：
                - code: 股票代码
                - name: 股票名称
                - price: 当前价格
                - change_pct: 涨跌幅
                - volume: 成交量
                - amount: 成交额
                - ... 其他字段
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def get_market_data(self):
        """
        获取市场整体数据
        
        Returns:
            dict: 市场数据，包含：
                - limit_up_count: 涨停家数
                - limit_down_count: 跌停家数
                - market_heat: 市场热度
                - ... 其他字段
        """
        raise NotImplementedError("子类必须实现此方法")