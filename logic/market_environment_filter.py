#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
市场环境过滤器 (MarketEnvironmentFilter) - V18.6.1

功能：独立的市场环境判断模块，解耦板块共振逻辑
- 判断当前市场环境是否支持做多
- 板块共振分析
- 资金热度评估
- 龙头溯源

Author: iFlow CLI
Version: V18.6.1
"""

from typing import Dict, List, Optional, Tuple
from logic.utils.logger import get_logger
from logic.data_manager import DataManager
from logic.sector_analysis import FastSectorAnalyzer

logger = get_logger(__name__)


class MarketEnvironmentFilter:
    """
    市场环境过滤器
    
    功能：
    - 判断当前市场环境是否支持做多
    - 板块共振分析
    - 资金热度评估
    - 龙头溯源
    
    设计理念：
    - 将板块共振逻辑从信号生成器中抽离
    - 信号生成器只询问过滤器："当前环境是否支持做多？"
    - 过滤器负责所有市场环境相关的判断
    """
    
    def __init__(self, db: DataManager):
        """
        初始化市场环境过滤器
        
        Args:
            db: DataManager 实例
        """
        self.db = db
        self.sector_analyzer = FastSectorAnalyzer(db)
        self._environment_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 60  # 缓存60秒
        
        logger.info("✅ 市场环境过滤器初始化完成")
    
    def check_market_environment(self, stock_code: str) -> Dict:
        """
        检查市场环境是否支持做多
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: 市场环境信息，包含：
                - is_supportive: 是否支持做多
                - resonance_score: 共振分数
                - resonance_details: 共振详情
                - sector_info: 板块信息
        """
        # 检查缓存
        if stock_code in self._environment_cache:
            return self._environment_cache[stock_code]
        
        try:
            # 执行全维板块共振分析
            resonance_result = self.sector_analyzer.analyze_full_resonance(stock_code)
            
            # 判断是否支持做多
            is_supportive = resonance_result.get('resonance_score', 0) > 0
            
            # 构建返回结果
            result = {
                'is_supportive': is_supportive,
                'resonance_score': resonance_result.get('resonance_score', 0),
                'resonance_details': resonance_result.get('reason', ''),
                'sector_info': resonance_result.get('sector_info', {})
            }
            
            # 缓存结果
            self._environment_cache[stock_code] = result
            
            return result
            
        except Exception as e:
            logger.error(f"检查市场环境失败 {stock_code}: {e}")
            return {
                'is_supportive': False,
                'resonance_score': 0,
                'resonance_details': f'环境检查失败: {e}',
                'sector_info': {}
            }
    
    def get_market_themes(self) -> List[str]:
        """
        获取当前市场主线题材
        
        Returns:
            list: 主线题材列表
        """
        try:
            # 获取市场快照
            market_snapshot = self.sector_analyzer.get_market_snapshot()
            
            # 获取主线题材
            main_themes = market_snapshot.get('main_themes', [])
            
            return main_themes
            
        except Exception as e:
            logger.error(f"获取市场主线失败: {e}")
            return []
    
    def get_leading_stocks(self, theme: str, limit: int = 5) -> List[Dict]:
        """
        获取指定题材的龙头股票
        
        Args:
            theme: 题材名称
            limit: 返回数量限制
        
        Returns:
            list: 龙头股票列表
        """
        try:
            # 获取市场快照
            market_snapshot = self.sector_analyzer.get_market_snapshot()
            
            # 筛选指定题材的股票
            theme_stocks = market_snapshot[market_snapshot['main_themes'].apply(lambda x: theme in x)]
            
            # 按涨幅排序，取前N只
            leading_stocks = theme_stocks.nlargest(limit, 'pct_chg')
            
            return leading_stocks.to_dict('records')
            
        except Exception as e:
            logger.error(f"获取龙头股票失败 {theme}: {e}")
            return []
    
    def clear_cache(self):
        """清空缓存"""
        self._environment_cache.clear()
        self._cache_timestamp = None
        logger.info("✅ 市场环境过滤器缓存已清空")


# 单例模式
_instance = None

def get_market_environment_filter(db: DataManager = None) -> MarketEnvironmentFilter:
    """
    获取市场环境过滤器单例
    
    Args:
        db: DataManager 实例
    
    Returns:
        MarketEnvironmentFilter: 市场环境过滤器实例
    """
    global _instance
    
    if _instance is None:
        if db is None:
            from logic.data_manager import DataManager
            db = DataManager()
        _instance = MarketEnvironmentFilter(db)
    
    return _instance