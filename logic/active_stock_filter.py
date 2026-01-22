#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.1 Active Stock Filter - 活跃股筛选器
专门用于筛选活跃股票，避免扫描"僵尸股"
按成交额或涨幅排序，优先扫描主力战场

Author: iFlow CLI
Version: V19.1
"""

import easyquotation as eq
from typing import List, Dict, Any, Optional
from logic.logger import get_logger

logger = get_logger(__name__)


class ActiveStockFilter:
    """
    V19.1 活跃股筛选器（Active Stock Filter）
    
    核心功能：
    1. 获取全市场实时行情
    2. 过滤停牌、无量、ST、退市股
    3. 按成交额或涨幅排序
    4. 返回前N只活跃股
    """
    
    def __init__(self, quotation_source: str = 'tencent'):
        """
        初始化活跃股筛选器
        
        Args:
            quotation_source: 行情源，默认 'tencent'
        """
        self.quotation_source = quotation_source
        self.quotation = eq.use(quotation_source)
    
    def get_active_stocks(
        self,
        limit: int = 100,
        sort_by: str = 'amount',
        min_change_pct: Optional[float] = None,
        max_change_pct: Optional[float] = None,
        exclude_st: bool = True,
        exclude_delisting: bool = True,
        min_volume: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取活跃股票列表
        
        Args:
            limit: 返回股票数量
            sort_by: 排序方式，'amount'（成交额）或 'change_pct'（涨幅）
            min_change_pct: 最小涨幅（可选）
            max_change_pct: 最大涨幅（可选）
            exclude_st: 是否排除ST股
            exclude_delisting: 是否排除退市股
            min_volume: 最小成交量（手）
        
        Returns:
            list: 活跃股票列表
        """
        active_list = []
        
        try:
            logger.info(f"开始获取全市场行情，行情源: {self.quotation_source}")
            
            # 获取全市场数据
            data = self.quotation.market_snapshot(prefix=True)
            
            logger.info(f"获取到 {len(data)} 只股票的行情数据")
            
            for code, info in data.items():
                # 过滤掉停牌和无量股
                if info.get('turnover') is None or info.get('volume', 0) == 0:
                    continue
                
                try:
                    # 提取关键指标
                    stock = {
                        'code': code[2:] if code.startswith(('sh', 'sz')) else code,  # 去掉前缀
                        'name': info.get('name', ''),
                        'price': info.get('now', 0),
                        'close': info.get('close', 0),
                        'high': info.get('high', 0),
                        'low': info.get('low', 0),
                        'open': info.get('open', 0),
                        'volume': info.get('volume', 0),  # 成交量（手）
                        'amount': info.get('turnover', 0),  # 成交额（元）
                        'change_pct': 0.0
                    }
                    
                    # 计算涨跌幅
                    if stock['close'] > 0:
                        stock['change_pct'] = (stock['price'] - stock['close']) / stock['close'] * 100
                    
                    # 过滤无效数据
                    if stock['price'] == 0 or stock['close'] == 0:
                        continue
                    
                    # 过滤ST股
                    if exclude_st and ('ST' in stock['name'] or '*ST' in stock['name']):
                        continue
                    
                    # 过滤退市股
                    if exclude_delisting and '退' in stock['name']:
                        continue
                    
                    # 过滤成交量不足的股票
                    if min_volume > 0 and stock['volume'] < min_volume:
                        continue
                    
                    # 过滤涨幅范围
                    if min_change_pct is not None and stock['change_pct'] < min_change_pct:
                        continue
                    
                    if max_change_pct is not None and stock['change_pct'] > max_change_pct:
                        continue
                    
                    active_list.append(stock)
                
                except Exception as e:
                    logger.warning(f"处理股票 {code} 数据失败: {e}")
                    continue
            
            # 按指定字段排序
            if sort_by == 'amount':
                # 按成交额排序（主力战场）
                active_list.sort(key=lambda x: x['amount'], reverse=True)
                logger.info(f"按成交额排序，前10只成交额: {[s['amount'] for s in active_list[:10]]}")
            elif sort_by == 'change_pct':
                # 按涨幅排序
                active_list.sort(key=lambda x: x['change_pct'], reverse=True)
                logger.info(f"按涨幅排序，前10只涨幅: {[s['change_pct'] for s in active_list[:10]]}")
            else:
                logger.warning(f"未知的排序方式: {sort_by}，默认按成交额排序")
                active_list.sort(key=lambda x: x['amount'], reverse=True)
            
            # 限制返回数量
            result = active_list[:limit]
            
            logger.info(f"✅ 筛选完成，返回 {len(result)} 只活跃股（原始: {len(active_list)}）")
            
            return result
        
        except Exception as e:
            logger.error(f"获取活跃股票失败: {e}")
            return []
    
    def get_stock_name_dict(self, stocks: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        从股票列表中提取代码到名称的映射
        
        Args:
            stocks: 股票列表
        
        Returns:
            dict: {code: name}
        """
        return {s['code']: s['name'] for s in stocks}


# 便捷函数
_asf_instance = None

def get_active_stock_filter(quotation_source: str = 'tencent') -> ActiveStockFilter:
    """获取活跃股筛选器单例"""
    global _asf_instance
    if _asf_instance is None or _asf_instance.quotation_source != quotation_source:
        _asf_instance = ActiveStockFilter(quotation_source)
    return _asf_instance


def get_active_stocks(
    limit: int = 100,
    sort_by: str = 'amount',
    min_change_pct: Optional[float] = None,
    max_change_pct: Optional[float] = None,
    exclude_st: bool = True,
    exclude_delisting: bool = True,
    min_volume: int = 0
) -> List[Dict[str, Any]]:
    """
    便捷函数：获取活跃股票列表
    
    Args:
        limit: 返回股票数量
        sort_by: 排序方式，'amount'（成交额）或 'change_pct'（涨幅）
        min_change_pct: 最小涨幅（可选）
        max_change_pct: 最大涨幅（可选）
        exclude_st: 是否排除ST股
        exclude_delisting: 是否排除退市股
        min_volume: 最小成交量（手）
    
    Returns:
        list: 活跃股票列表
    """
    filter_obj = get_active_stock_filter()
    return filter_obj.get_active_stocks(
        limit=limit,
        sort_by=sort_by,
        min_change_pct=min_change_pct,
        max_change_pct=max_change_pct,
        exclude_st=exclude_st,
        exclude_delisting=exclude_delisting,
        min_volume=min_volume
    )