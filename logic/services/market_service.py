# -*- coding: utf-8 -*-
"""
行情服务 - 统一行情数据门面 (Market Service)

整合所有行情数据源：
- Tick数据 (TickProvider)
- K线数据 (各个provider)
- 实时行情 (RealtimeDataProvider)

禁止直接访问logic.data_providers.*，必须通过此服务。
"""

from typing import List, Dict, Optional, Union
from datetime import datetime
import pandas as pd

from logic.data_providers.tick_provider import TickProvider
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class MarketService:
    """
    行情服务 - 统一门面
    
    使用示例:
        service = MarketService()
        ticks = service.get_tick_series('300017.SZ', '20250101', '20250131')
        minute_bars = service.get_minute_bars('300017.SZ', '1m', '20250101', '20250131')
    """
    
    def __init__(self):
        self._tick_provider = None
    
    def _get_tick_provider(self) -> TickProvider:
        """懒加载TickProvider"""
        if self._tick_provider is None:
            self._tick_provider = TickProvider()
        return self._tick_provider
    
    def get_tick_series(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        获取Tick数据序列
        
        Args:
            stock_code: 股票代码 (如 '300017.SZ')
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            Tick数据DataFrame，若数据不存在返回None
        """
        try:
            provider = self._get_tick_provider()
            # 使用download_ticks获取数据
            result = provider.download_ticks([stock_code], start_date, end_date)
            
            if result.get('success_count', 0) > 0:
                # 从datadir读取实际数据
                return provider.load_ticks(stock_code, start_date, end_date)
            else:
                logger.warning(f"未找到{stock_code}的Tick数据")
                return None
        
        except Exception as e:
            logger.error(f"获取Tick数据失败: {e}")
            return None
    
    def get_minute_bars(
        self,
        stock_code: str,
        period: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        获取分钟K线数据
        
        Args:
            stock_code: 股票代码
            period: 周期 ('1m', '5m')
            start_date: 开始日期
            end_date: 结束日期
        """
        try:
            provider = self._get_tick_provider()
            result = provider.download_minute_data([stock_code], start_date, end_date, period)
            
            if result.get('success_count', 0) > 0:
                logger.info(f"成功获取{stock_code}的{period}数据")
                # TODO: 实现实际的K线数据读取
                return pd.DataFrame()
            else:
                logger.warning(f"未找到{stock_code}的{period}数据")
                return None
        
        except Exception as e:
            logger.error(f"获取分钟数据失败: {e}")
            return None
    
    def check_data_coverage(
        self,
        stock_codes: List[str],
        date: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        检查数据覆盖情况
        
        Args:
            stock_codes: 股票代码列表
            date: 日期，默认为今天
        
        Returns:
            覆盖情况字典
        """
        try:
            provider = self._get_tick_provider()
            return provider.check_coverage(stock_codes, date)
        
        except Exception as e:
            logger.error(f"检查数据覆盖失败: {e}")
            return {}
