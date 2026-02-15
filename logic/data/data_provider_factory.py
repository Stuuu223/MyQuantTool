#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据提供者工厂
支持实时数据和历史回放数据两种模式
"""

from logic.utils.logger import get_logger

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
                - 'replay': 历史回放模式（AkShare 日线数据）
                - 'qmt_replay': QMT 历史复盘模式（支持时间点快照）
            **kwargs: 额外参数
                - date: 历史日期（仅 replay/qmt_replay 模式需要，格式：'20260116'）
                - time_point: 时间点（仅 qmt_replay 模式需要，格式：'145600'，即 14:56:00）
                - period: 数据周期（仅 qmt_replay 模式，默认 '1m'）
                - stock_list: 股票列表（可选）
        
        Returns:
            DataProvider: 数据提供者实例
        """
        if mode == 'live':
            from logic.data.realtime_data_provider import RealtimeDataProvider
            return RealtimeDataProvider(**kwargs)
        elif mode == 'replay':
            from logic.historical_replay_provider import HistoricalReplayProvider
            return HistoricalReplayProvider(**kwargs)
        elif mode == 'qmt_replay':
            # 🔥 V19.17: 新增 QMT 历史复盘模式
            from logic.qmt_historical_provider import QMTHistoricalProvider
            return QMTHistoricalProvider(**kwargs)
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
    
    def get_history_data(self, symbol: str, period: str = 'daily', adjust: str = 'qfq'):
        """
        获取历史数据
        
        Args:
            symbol: 股票代码
            period: 周期（daily, weekly, monthly）
            adjust: 复权方式（qfq: 前复权, hfq: 后复权, none: 不复权）
        
        Returns:
            DataFrame: 历史数据
        """
        raise NotImplementedError("子类必须实现此方法")