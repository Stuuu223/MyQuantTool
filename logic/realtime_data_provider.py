#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时数据提供者
从新浪 API 获取实时行情数据
V17.1: 时区校准 - 统一使用北京时间
"""

from logic.data_provider_factory import DataProvider
from logic.logger import get_logger
from logic.utils import Utils
import config_system as config
from datetime import datetime

logger = get_logger(__name__)


class RealtimeDataProvider(DataProvider):
    """
    实时数据提供者
    
    功能：
    - 从新浪 API 获取实时行情数据
    - 支持并发请求提升性能
    - 自动处理数据清洗和格式化
    - 🆕 V16.2: 数据保质期校验
    """
    
    def __init__(self, **kwargs):
        """初始化实时数据提供者"""
        super().__init__()
        self.timeout = config.API_TIMEOUT
        self.data_freshness_threshold = 15  # V16.2: 数据保质期阈值（秒）
    
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
            
            # V16.2 新增：数据保质期校验
            current_time = datetime.now()
            current_hour = current_time.hour
            current_minute = current_time.minute
            
            # 判断是否在竞价期间（9:15-9:30）
            is_auction_period = (current_hour == 9 and 15 <= current_minute < 30)
            
            # 格式化数据
            result = []
            for code, data in market_data.items():
                if not data:
                    continue
                
                # V16.2 新增：检查数据时间戳
                data_time_str = data.get('time', '')
                if data_time_str and not is_auction_period:
                    try:
                        # 解析数据时间（格式可能是 "09:30:05" 或类似）
                        data_time = datetime.strptime(data_time_str, '%H:%M:%S')
                        data_time = data_time.replace(year=current_time.year, month=current_time.month, day=current_time.day)
                        
                        # 检查数据是否过期（超过15秒）
                        time_diff = (current_time - data_time).total_seconds()
                        if time_diff > self.data_freshness_threshold:
                            logger.warning(f"⚠️ [数据过期] {code} 数据时间 {data_time_str} 距今 {time_diff:.0f}秒，跳过交易")
                            continue
                    except Exception as e:
                        logger.warning(f"⚠️ [时间解析失败] {code} 无法解析时间戳 {data_time_str}: {e}")
                
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
                    'data_timestamp': data_time_str,  # V16.2 新增
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