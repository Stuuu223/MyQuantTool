#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史回放数据提供者
从 AkShare 获取历史数据并伪装成实时数据
"""

from logic.data_provider_factory import DataProvider
from logic.utils.logger import get_logger
import config.config_system as config
import akshare as ak
import pandas as pd
from datetime import datetime

logger = get_logger(__name__)


class HistoricalReplayProvider(DataProvider):
    """
    历史回放数据提供者
    
    功能：
    - 从 AkShare 获取指定日期的历史数据
    - 伪装成实时数据格式返回
    - 支持多只股票并发获取
    - 用于周末历史重演测试
    """
    
    def __init__(self, date=None, stock_list=None, **kwargs):
        """
        初始化历史回放数据提供者
        
        Args:
            date: 历史日期（格式：'20260116'），默认为上周五
            stock_list: 股票列表（可选）
        """
        super().__init__()
        
        # 默认日期：上周五
        if date is None:
            today = datetime.now()
            if today.weekday() == 6:  # 周日
                date = (today - pd.Timedelta(days=2)).strftime('%Y%m%d')
            elif today.weekday() == 0:  # 周一
                date = (today - pd.Timedelta(days=3)).strftime('%Y%m%d')
            else:
                date = (today - pd.Timedelta(days=1)).strftime('%Y%m%d')
        
        self.date = date
        self.stock_list = stock_list or []
        self.cache = {}  # 缓存已获取的数据
        
        logger.info(f"📅 历史回放模式：日期={self.date}")
    
    def get_realtime_data(self, stock_list):
        """
        获取历史数据并伪装成实时数据
        
        Args:
            stock_list: 股票代码列表或包含股票信息的字典列表
        
        Returns:
            list: 股票数据列表（格式与实时数据一致）
        """
        try:
            # 提取股票代码
            if isinstance(stock_list[0], dict):
                codes = [stock.get('code') for stock in stock_list]
            else:
                codes = stock_list
            
            result = []
            
            for code in codes:
                try:
                    # 清洗代码
                    clean_code = code.replace("sh", "").replace("sz", "")
                    
                    # 从缓存获取
                    if code in self.cache:
                        result.append(self.cache[code])
                        continue
                    
                    # 获取历史数据
                    df = ak.stock_zh_a_hist(
                        symbol=clean_code,
                        period="daily",
                        start_date=self.date,
                        end_date=self.date,
                        adjust="qfq"
                    )
                    
                    if df.empty:
                        logger.warning(f"⚠️ 未找到股票 {code} 在 {self.date} 的数据")
                        continue
                    
                    # 获取当日数据
                    row = df.iloc[0]
                    
                    # 🔧 字段名映射表（兼容不同版本的 AkShare）
                    field_mapping = {
                        'name': ['股票名称', '名称', 'name'],
                        'open': ['开盘', 'open'],
                        'close': ['收盘', 'close'],
                        'high': ['最高', 'high'],
                        'low': ['最低', 'low'],
                        'volume': ['成交量', 'volume'],
                        'amount': ['成交额', 'amount'],
                        'change_pct': ['涨跌幅', 'percent'],
                        'change_amount': ['涨跌额', 'change'],
                        'turnover': ['换手率', 'turnover'],
                    }
                    
                    # 🔧 辅助函数：获取字段值（支持多个字段名）
                    def get_field_value(row, possible_names, default=0):
                        for name in possible_names:
                            if name in row and pd.notna(row[name]):
                                return row[name]
                        return default
                    
                    # 获取字段值
                    name = get_field_value(row, field_mapping['name'], '')
                    open_price = get_field_value(row, field_mapping['open'], 0)
                    close_price = get_field_value(row, field_mapping['close'], 0)
                    high_price = get_field_value(row, field_mapping['high'], 0)
                    low_price = get_field_value(row, field_mapping['low'], 0)
                    volume = get_field_value(row, field_mapping['volume'], 0)
                    amount = get_field_value(row, field_mapping['amount'], 0)
                    change_pct = get_field_value(row, field_mapping['change_pct'], 0)
                    
                    # 计算昨收价
                    if change_pct != 0:
                        pre_close = close_price / (1 + change_pct / 100)
                    else:
                        pre_close = close_price
                    
                    # 构造股票信息（伪装成实时数据格式）
                    stock_info = {
                        'code': code,
                        'name': name,
                        'price': close_price,
                        'change_pct': change_pct / 100,  # 转换为小数
                        'volume': volume,
                        'amount': amount,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'pre_close': pre_close,
                        # 添加历史数据特有的字段
                        'replay_date': self.date,
                        'replay_mode': True,
                    }
                    
                    # 缓存
                    self.cache[code] = stock_info
                    result.append(stock_info)
                    
                except Exception as e:
                    logger.error(f"获取股票 {code} 历史数据失败: {e}")
                    continue
            
            logger.info(f"✅ 历史回放：成功获取 {len(result)} 只股票的数据")
            return result
            
        except Exception as e:
            logger.error(f"历史回放获取数据失败: {e}")
            return []
    
    def get_market_data(self):
        """
        获取历史市场数据
        
        Returns:
            dict: 市场数据
        """
        try:
            # 获取当日所有A股数据
            df = ak.stock_zh_a_spot_em()
            
            # 筛选涨停股票
            limit_up_stocks = df[df['涨跌幅'] >= 9.5]  # 近似涨停
            
            # 计算市场热度
            total_stocks = len(df)
            limit_up_count = len(limit_up_stocks)
            market_heat = min(100, limit_up_count * 2)  # 简单计算
            
            # 计算炸板率（近似）
            # 这里无法获取真实的炸板率，使用默认值
            mal_rate = 0.3
            
            # 判断市场状态
            if market_heat > 70:
                regime = 'BULL_ATTACK'
            elif market_heat < 30:
                regime = 'BEAR_DEFENSE'
            else:
                regime = 'CHAOS'
            
            return {
                'limit_up_count': limit_up_count,
                'market_heat': market_heat,
                'mal_rate': mal_rate,
                'regime': regime,
                'replay_date': self.date,
                'replay_mode': True,
            }
            
        except Exception as e:
            logger.error(f"获取历史市场数据失败: {e}")
            return {
                'limit_up_count': 0,
                'market_heat': 50,
                'mal_rate': 0.3,
                'regime': 'CHAOS',
                'replay_date': self.date,
                'replay_mode': True,
            }
    
    def get_historical_kline(self, code, days=60):
        """
        获取历史K线数据（用于技术分析）
        
        Args:
            code: 股票代码
            days: 获取天数
        
        Returns:
            DataFrame: K线数据
        """
        try:
            clean_code = code.replace("sh", "").replace("sz", "")
            
            # 计算起始日期
            end_date = datetime.strptime(self.date, '%Y%m%d')
            start_date = (end_date - pd.Timedelta(days=days*2)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(
                symbol=clean_code,
                period="daily",
                start_date=start_date,
                end_date=self.date,
                adjust="qfq"
            )
            
            # 只返回最近 days 天的数据
            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"获取股票 {code} 历史K线数据失败: {e}")
            return pd.DataFrame()