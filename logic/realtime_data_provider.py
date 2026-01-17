#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时数据提供者
从新浪 API 获取实时行情数据
"""

from logic.data_provider_factory import DataProvider
from logic.logger import get_logger
import config_system as config

logger = get_logger(__name__)


class RealtimeDataProvider(DataProvider):
    """
    实时数据提供者
    
    功能：
    - 从新浪 API 获取实时行情数据
    - 支持并发请求提升性能
    - 自动处理数据清洗和格式化
    """
    
    def __init__(self, **kwargs):
        """初始化实时数据提供者"""
        super().__init__()
        self.timeout = config.API_TIMEOUT
    
    def get_realtime_data(self, stock_list):
        """
        获取实时数据
        
        Args:
            stock_list: 股票代码列表或包含股票信息的字典列表
        
        Returns:
            list: 股票数据列表
        """
        try:
            import easyquotation as eq
            
            # 初始化行情接口
            quotation = eq.use('sina')
            
            # 提取股票代码
            if isinstance(stock_list[0], dict):
                codes = [stock['code'] for stock in stock_list]
            else:
                codes = stock_list
            
            # 获取实时数据
            market_data = quotation.stocks(codes)
            
            # 格式化数据
            result = []
            for code, data in market_data.items():
                if not data:
                    continue
                
                stock_info = {
                    'code': code,
                    'name': data.get('name', ''),
                    'price': data.get('now', 0),
                    'change_pct': data.get('percent', 0) / 100,  # 转换为小数
                    'volume': data.get('volume', 0),
                    'amount': data.get('amount', 0),
                    'open': data.get('open', 0),
                    'high': data.get('high', 0),
                    'low': data.get('low', 0),
                    'pre_close': data.get('close', 0),
                }
                result.append(stock_info)
            
            return result
            
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            return []
    
    def get_market_data(self):
        """
        获取市场整体数据
        
        Returns:
            dict: 市场数据
        """
        try:
            from logic.data_manager import DataManager
            
            dm = DataManager()
            
            # 获取今日涨停股票
            limit_up_stocks = dm.get_limit_up_stocks()
            
            # 获取市场情绪
            from logic.market_sentiment import MarketSentiment
            ms = MarketSentiment()
            sentiment_data = ms.get_market_sentiment()
            
            return {
                'limit_up_count': len(limit_up_stocks),
                'market_heat': sentiment_data.get('score', 50),
                'mal_rate': sentiment_data.get('mal_rate', 0.3),
                'regime': sentiment_data.get('regime', 'CHAOS'),
            }
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return {
                'limit_up_count': 0,
                'market_heat': 50,
                'mal_rate': 0.3,
                'regime': 'CHAOS',
            }