#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
市场情绪分析器 - V19.8

功能：
- 获取全市场涨跌比
- 统计涨停/跌停家数
- 计算市场情绪指数
- 为龙头战法提供市场情绪判断

Author: iFlow CLI
Version: V19.8
"""

import pandas as pd
from typing import Dict, Any, Optional
from logic.logger import get_logger
from logic.api_robust import robust_api_call

logger = get_logger(__name__)


class MarketSentiment:
    """
    市场情绪分析器
    
    功能：
    1. 获取全市场涨跌比
    2. 统计涨停/跌停家数
    3. 计算市场情绪指数
    4. 为龙头战法提供市场情绪判断
    """
    
    def __init__(self, db=None):
        """初始化市场情绪分析器
        
        Args:
            db: DataManager 实例（可选）
        """
        self.db = db
        logger.info("✅ [市场情绪分析器] 初始化完成")
    
    @robust_api_call(max_retries=3, delay=2, return_empty_df=True)
    def get_market_sentiment(self) -> Optional[Dict[str, Any]]:
        """
        获取市场情绪数据
        
        Returns:
            Dict: 市场情绪数据
                - total_count: 总股票数
                - up_count: 上涨家数
                - down_count: 下跌家数
                - flat_count: 平盘家数
                - limit_up_count: 涨停家数
                - limit_down_count: 跌停家数
                - sentiment_index: 市场情绪指数（0-100）
                - sentiment_level: 市场情绪等级（极差/差/中性/好/极好）
        """
        try:
            # 获取全市场数据
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            
            if df.empty:
                logger.warning("⚠️ [市场情绪分析器] 获取全市场数据失败")
                return None
            
            # 统计涨跌家数
            total_count = len(df)
            up_count = len(df[df['涨跌幅'] > 0])
            down_count = len(df[df['涨跌幅'] < 0])
            flat_count = len(df[df['涨跌幅'] == 0])
            
            # 统计涨停/跌停家数
            # 主板10cm涨停：涨幅 >= 9.9%
            # 创业板/科创板20cm涨停：涨幅 >= 19.9%
            limit_up_count = len(df[
                ((df['代码'].str.startswith(('600', '000', '001', '002', '003')) & (df['涨跌幅'] >= 9.9))) |
                ((df['代码'].str.startswith(('300', '688')) & (df['涨跌幅'] >= 19.9)))
            ])
            
            # 主板10cm跌停：涨幅 <= -9.9%
            # 创业板/科创板20cm跌停：涨幅 <= -19.9%
            limit_down_count = len(df[
                ((df['代码'].str.startswith(('600', '000', '001', '002', '003')) & (df['涨跌幅'] <= -9.9))) |
                ((df['代码'].str.startswith(('300', '688')) & (df['涨跌幅'] <= -19.9)))
            ])
            
            # 计算市场情绪指数
            # 情绪指数 = (上涨家数 - 下跌家数) / 总股票数 * 100
            # 范围：-100到100
            sentiment_index = ((up_count - down_count) / total_count) * 100
            
            # 标准化到0-100范围
            normalized_sentiment_index = (sentiment_index + 100) / 2
            
            # 判断市场情绪等级
            if normalized_sentiment_index < 20:
                sentiment_level = "极差"
            elif normalized_sentiment_index < 40:
                sentiment_level = "差"
            elif normalized_sentiment_index < 60:
                sentiment_level = "中性"
            elif normalized_sentiment_index < 80:
                sentiment_level = "好"
            else:
                sentiment_level = "极好"
            
            result = {
                'total_count': total_count,
                'up_count': up_count,
                'down_count': down_count,
                'flat_count': flat_count,
                'limit_up_count': limit_up_count,
                'limit_down_count': limit_down_count,
                'sentiment_index': sentiment_index,
                'normalized_sentiment_index': normalized_sentiment_index,
                'sentiment_level': sentiment_level,
                'up_ratio': up_count / total_count * 100,
                'down_ratio': down_count / total_count * 100
            }
            
            logger.info(f"✅ [市场情绪分析器] 获取完成: 上涨{up_count}家, 下跌{down_count}家, 涨停{limit_up_count}家, 跌停{limit_down_count}家, 情绪等级: {sentiment_level}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [市场情绪分析器] 获取失败: {e}")
            return None
    
    def is_market_sentiment_good(self) -> bool:
        """
        判断市场情绪是否良好
        
        Returns:
            bool: 市场情绪是否良好
        """
        sentiment_data = self.get_market_sentiment()
        
        if not sentiment_data:
            return False
        
        # 市场情绪良好的条件：
        # 1. 情绪等级为"好"或"极好"
        # 2. 跌停家数 <= 10
        # 3. 涨停家数 >= 30
        
        sentiment_level = sentiment_data.get('sentiment_level', '')
        limit_down_count = sentiment_data.get('limit_down_count', 0)
        limit_up_count = sentiment_data.get('limit_up_count', 0)
        
        is_good = (
            sentiment_level in ['好', '极好'] and
            limit_down_count <= 10 and
            limit_up_count >= 30
        )
        
        return is_good
    
    def is_market_sentiment_bad(self) -> bool:
        """
        判断市场情绪是否恶劣
        
        Returns:
            bool: 市场情绪是否恶劣
        """
        sentiment_data = self.get_market_sentiment()
        
        if not sentiment_data:
            return False
        
        # 市场情绪恶劣的条件：
        # 1. 跌停家数 > 20
        # 2. 下跌家数占比 > 70%
        
        limit_down_count = sentiment_data.get('limit_down_count', 0)
        down_ratio = sentiment_data.get('down_ratio', 0)
        
        is_bad = (
            limit_down_count > 20 or
            down_ratio > 70
        )
        
        return is_bad