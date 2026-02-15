#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富T-1资金流数据提供者

封装现有的 FundFlowAnalyzer，提供统一接口

Author: MyQuantTool Team
Date: 2026-02-12
"""

from datetime import datetime
from typing import Optional

from logic.data_providers.fund_flow_analyzer import FundFlowAnalyzer
from .base import (
    ICapitalFlowProvider,
    CapitalFlowSignal,
    DataNotAvailableError
)
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class DongCaiT1Provider(ICapitalFlowProvider):
    """
    东方财富T-1数据提供者

    特点：
    - 数据延迟：T-1（次日凌晨更新）
    - 数据精度：官方统计，高可信度
    - 使用场景：盘前选股、历史分析
    - 置信度：0.8（历史数据可信，但盘中过期）
    """

    def __init__(self):
        self.fund_flow = FundFlowAnalyzer()
        self._cache = {}  # 简单缓存（避免重复请求）
        self._cache_ttl = 3600  # 缓存1小时

    def get_realtime_flow(self, code: str) -> CapitalFlowSignal:
        """
        获取T-1资金流数据

        Args:
            code: 股票代码（6位）

        Returns:
            CapitalFlowSignal: 昨日资金流数据
        """
        try:
            # 检查缓存
            if code in self._cache:
                cached_signal, cache_time = self._cache[code]
                age = (datetime.now() - cache_time).total_seconds()
                if age < self._cache_ttl:
                    logger.debug(f"✅ {code} 使用缓存数据（年龄: {age:.0f}秒）")
                    return cached_signal

            # 获取30天数据（用于后续诱多检测）
            flow_data = self.fund_flow.get_fund_flow(code, days=30)

            if not flow_data or 'error' in flow_data:
                raise DataNotAvailableError(f"东方财富API返回错误: {flow_data.get('error', '未知')}")

            # 提取最新一天数据
            latest = flow_data.get('latest', {})
            if not latest:
                raise DataNotAvailableError("最新数据为空")

            # 转换为统一格式
            signal = CapitalFlowSignal(
                code=code,
                main_net_inflow=latest.get('main_net_inflow', 0),
                super_large_inflow=latest.get('super_large_net', 0),
                large_inflow=latest.get('large_net', 0),
                timestamp=datetime.now().timestamp(),
                confidence=0.8,  # T-1数据可信度高
                source='DongCai'
            )

            # 更新缓存
            self._cache[code] = (signal, datetime.now())

            return signal

        except Exception as e:
            logger.warning(f"⚠️ {code} 东方财富数据获取失败: {e}")
            # 返回空信号（注意：用户提供的代码中没有_create_empty_signal方法）
            # 我需要创建一个默认的空信号
            return CapitalFlowSignal(
                code=code,
                timestamp=datetime.now().timestamp(),
                main_net_inflow=0.0,
                super_large_inflow=0.0,
                large_inflow=0.0,
                confidence=0.0,
                source='DongCai'
            )

    def get_data_freshness(self, code: str) -> int:
        """
        获取数据新鲜度

        东方财富数据是T-1，新鲜度通常是1-2天（86400-172800秒）
        """
        signal = self.get_realtime_flow(code)
        # T-1数据，假设是昨天收盘后15:00，计算到现在的时间
        yesterday = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        yesterday = yesterday - timedelta(days=1)
        age_seconds = (datetime.now() - yesterday).total_seconds()
        return int(age_seconds)

    def get_full_tick(self, code_list):
        """东方财富不支持Tick数据，返回空"""
        return {}

    def get_kline_data(self, code_list, period='1d', start_time='', end_time='', count=-1):
        """东方财富不支持K线数据，返回空"""
        return {}

    def get_stock_list_in_sector(self, sector_name):
        """东方财富不支持板块数据，返回空"""
        return []

    def get_historical_flow(self, code: str, days: int = 30):
        """
        获取历史资金流

        Args:
            code: 股票代码
            days: 获取最近几天的数据

        Returns:
            Dict: 历史资金流数据
        """
        return self.fund_flow.get_fund_flow(code, days=days)

    def is_available(self) -> bool:
        """检查东方财富API是否可用"""
        try:
            # 测试获取一个常见股票（平安银行）
            test_data = self.fund_flow.get_fund_flow('000001', days=1)
            return test_data is not None and 'error' not in test_data
        except Exception as e:
            logger.error(f"❌ 东方财富API不可用: {e}")
            return False

    def download_history_data(self, code: str, period: str = '1m',
                              count: int = -1, incrementally: bool = False):
        """东方财富不支持历史数据下载，返回空"""
        return {'success': False, 'error': 'DongCai does not support download_history_data'}

    def get_instrument_detail(self, code: str):
        """东方财富不支持合约详情，返回空"""
        return {}

    def get_market_data(self, field_list, stock_list, period='1d', start_time='', end_time='', dividend_type='none', fill_data=False):
        """东方财富不支持市场数据，返回空"""
        return {}

    def get_provider_name(self) -> str:
        return "DongCaiT1"