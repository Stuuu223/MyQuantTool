#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18 板块共振识别器
拒绝独狼式诱多，只有"个股强 + 板块止跌"的共振才是真龙
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
from logic.utils.logger import get_logger
from logic.data_providers.data_manager import DataManager
from logic.data_providers.cache_manager import CacheManager

logger = get_logger(__name__)


class SectorResonanceDetector:
    """
    板块共振识别器
    
    功能：
    1. 检测个股所属板块的整体走势
    2. 识别板块止跌或上涨信号
    3. 判断个股与板块是否共振
    4. 拒绝独狼式诱多
    """
    
    # 共振阈值
    SECTOR_STOP_LOSS_THRESHOLD = -0.5  # 板块跌幅 > -0.5% 认为止跌
    SECTOR_RISE_THRESHOLD = 0.5  # 板块涨幅 > 0.5% 认为上涨
    MIN_STOCKS_IN_SECTOR = 5  # 板块至少有 5 只股票才判断
    
    def __init__(self):
        """初始化板块共振识别器"""
        self.data_manager = DataManager()
        self.cache = CacheManager()
    
    def get_stock_sector(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票所属板块
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {
                'industry': str,  # 行业
                'concept': str,  # 概念
                'sector_type': str  # 板块类型（industry/concept）
            }
        """
        try:
            stock_info = self.data_manager.get_stock_info(stock_code)
            if stock_info:
                industry = stock_info.get('industry', '')
                concept = stock_info.get('concept', '')
                
                # 优先使用行业板块
                if industry:
                    return {
                        'industry': industry,
                        'concept': concept,
                        'sector_type': 'industry'
                    }
                elif concept:
                    return {
                        'industry': '',
                        'concept': concept,
                        'sector_type': 'concept'
                    }
            
            return None
        except Exception as e:
            logger.error(f"❌ [板块共振] 获取股票板块失败: {e}")
            return None
    
    def get_sector_performance(self, sector_name: str, sector_type: str = 'industry') -> Dict:
        """
        获取板块整体表现
        
        Args:
            sector_name: 板块名称
            sector_type: 板块类型（industry/concept）
        
        Returns:
            dict: {
                'avg_change_pct': float,  # 平均涨跌幅
                'total_stocks': int,  # 总股票数
                'rise_count': int,  # 上涨股票数
                'fall_count': int,  # 下跌股票数
                'status': str  # 板块状态（上涨/止跌/下跌）
            }
        """
        try:
            # 尝试从缓存获取
            cache_key = f"sector_performance_{sector_type}_{sector_name}"
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # 获取板块股票列表
            if sector_type == 'industry':
                sector_stocks = self.data_manager.get_industry_stocks(sector_name)
            else:
                # 概念板块暂时不支持
                logger.warning(f"⚠️ [板块共振] 概念板块暂不支持: {sector_name}")
                return {
                    'avg_change_pct': 0.0,
                    'total_stocks': 0,
                    'rise_count': 0,
                    'fall_count': 0,
                    'status': 'unknown'
                }
            
            if not sector_stocks or len(sector_stocks) < self.MIN_STOCKS_IN_SECTOR:
                return {
                    'avg_change_pct': 0.0,
                    'total_stocks': 0,
                    'rise_count': 0,
                    'fall_count': 0,
                    'status': 'unknown'
                }
            
            # 获取板块股票的实时数据
            total_change = 0.0
            rise_count = 0
            fall_count = 0
            valid_count = 0
            
            for stock_code in sector_stocks[:50]:  # 限制前 50 只股票
                try:
                    realtime_data = self.data_manager.get_realtime_data(stock_code)
                    if realtime_data:
                        change_pct = realtime_data.get('change_pct', 0.0)
                        total_change += change_pct
                        valid_count += 1
                        
                        if change_pct > 0:
                            rise_count += 1
                        elif change_pct < 0:
                            fall_count += 1
                except Exception as e:
                    continue
            
            if valid_count == 0:
                return {
                    'avg_change_pct': 0.0,
                    'total_stocks': 0,
                    'rise_count': 0,
                    'fall_count': 0,
                    'status': 'unknown'
                }
            
            # 计算平均涨跌幅
            avg_change_pct = total_change / valid_count
            
            # 判断板块状态
            if avg_change_pct >= self.SECTOR_RISE_THRESHOLD:
                status = '上涨'
            elif avg_change_pct >= self.SECTOR_STOP_LOSS_THRESHOLD:
                status = '止跌'
            else:
                status = '下跌'
            
            result = {
                'avg_change_pct': avg_change_pct,
                'total_stocks': valid_count,
                'rise_count': rise_count,
                'fall_count': fall_count,
                'status': status
            }
            
            # 缓存结果（30秒）
            self.cache.set(cache_key, result, ttl=30)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [板块共振] 获取板块表现失败: {e}")
            return {
                'avg_change_pct': 0.0,
                'total_stocks': 0,
                'rise_count': 0,
                'fall_count': 0,
                'status': 'unknown'
            }
    
    def check_sector_resonance(self, stock_code: str, stock_change_pct: float) -> Dict:
        """
        检查个股与板块是否共振
        
        Args:
            stock_code: 股票代码
            stock_change_pct: 个股涨跌幅
        
        Returns:
            dict: {
                'has_resonance': bool,  # 是否共振
                'resonance_type': str,  # 共振类型（真龙/独狼）
                'sector_name': str,  # 板块名称
                'sector_status': str,  # 板块状态
                'sector_avg_change': float,  # 板块平均涨跌幅
                'stock_change': float,  # 个股涨跌幅
                'reason': str  # 原因
            }
        """
        try:
            # 获取股票所属板块
            sector_info = self.get_stock_sector(stock_code)
            if not sector_info:
                return {
                    'has_resonance': False,
                    'resonance_type': 'unknown',
                    'sector_name': '',
                    'sector_status': 'unknown',
                    'sector_avg_change': 0.0,
                    'stock_change': stock_change_pct,
                    'reason': '无法获取板块信息'
                }
            
            sector_name = sector_info['industry'] if sector_info['sector_type'] == 'industry' else sector_info['concept']
            sector_type = sector_info['sector_type']
            
            # 获取板块表现
            sector_performance = self.get_sector_performance(sector_name, sector_type)
            
            # 判断共振
            has_resonance = False
            resonance_type = '独狼'
            reason = ''
            
            # 个股强（涨幅 > 2%）
            if stock_change_pct > 2.0:
                # 板块止跌或上涨
                if sector_performance['status'] in ['止跌', '上涨']:
                    has_resonance = True
                    resonance_type = '真龙'
                    reason = f"个股强({stock_change_pct:.2f}%) + 板块{sector_performance['status']}({sector_performance['avg_change_pct']:.2f}%)，共振确认"
                else:
                    # 板块下跌，个股独强
                    has_resonance = False
                    resonance_type = '独狼'
                    reason = f"个股强({stock_change_pct:.2f}%) 但板块下跌({sector_performance['avg_change_pct']:.2f}%)，独狼式诱多，谨慎"
            else:
                # 个股不强，不判断共振
                has_resonance = False
                resonance_type = 'unknown'
                reason = f"个股不强({stock_change_pct:.2f}%)，不判断共振"
            
            result = {
                'has_resonance': has_resonance,
                'resonance_type': resonance_type,
                'sector_name': sector_name,
                'sector_status': sector_performance['status'],
                'sector_avg_change': sector_performance['avg_change_pct'],
                'stock_change': stock_change_pct,
                'reason': reason
            }
            
            if resonance_type == '独狼':
                logger.warning(f"🚨 [板块共振] {stock_code} {sector_name} {reason}")
            elif has_resonance:
                logger.info(f"✅ [板块共振] {stock_code} {sector_name} {reason}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [板块共振] 检查板块共振失败: {e}")
            return {
                'has_resonance': False,
                'resonance_type': 'unknown',
                'sector_name': '',
                'sector_status': 'unknown',
                'sector_avg_change': 0.0,
                'stock_change': stock_change_pct,
                'reason': f'检查失败: {e}'
            }


# 全局实例
_sector_resonance_detector: Optional[SectorResonanceDetector] = None


def get_sector_resonance_detector() -> SectorResonanceDetector:
    """获取板块共振识别器单例"""
    global _sector_resonance_detector
    if _sector_resonance_detector is None:
        _sector_resonance_detector = SectorResonanceDetector()
    return _sector_resonance_detector