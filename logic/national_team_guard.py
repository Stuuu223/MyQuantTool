#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6 National Team Guard - 国家队护盘指纹识别器
专门用于识别国家队（50ETF）护盘信号
如果股票回踩时大盘正好在关键位受到国家队护盘，提升低吸信号为"全域共振"级
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from logic.logger import get_logger
from logic.data_manager import DataManager

logger = get_logger(__name__)


class NationalTeamGuard:
    """
    V18.6 国家队护盘指纹识别器（National Team Guard）
    
    核心战法：
    1. 大盘关键位监控：监控大盘（沪深300）的关键位
    2. 国家队护盘识别：识别国家队（50ETF）护盘信号
    3. 全域共振：如果股票回踩时大盘正好在关键位受到国家队护盘，提升低吸信号为"全域共振"级
    """
    
    # 大盘关键位配置（沪深300）
    CSI300_KEY_LEVELS = [
        3500.0,  # 关键支撑位1
        3400.0,  # 关键支撑位2
        3300.0,  # 关键支撑位3
        3200.0,  # 关键支撑位4
        3100.0,  # 关键支撑位5
    ]
    
    # 50ETF 护盘阈值
    ETF50_GUARD_THRESHOLD = 2.0  # 50ETF 净流入 > 2亿时认为是护盘
    
    def __init__(self):
        """初始化国家队护盘指纹识别器"""
        self.data_manager = DataManager()
        
        # 大盘数据缓存
        self._market_data_cache = {
            'csi300_data': None,
            'etf50_data': None,
            'last_update': None
        }
        self._cache_ttl = 60  # 缓存有效期（秒），1分钟
    
    def _get_csi300_data(self) -> Dict[str, Any]:
        """
        获取沪深300数据
        
        Returns:
            dict: {
                'current_price': float,    # 当前价格
                'change_pct': float,       # 涨跌幅
                'is_near_key_level': bool, # 是否接近关键位
                'key_level': float,        # 关键位
                'distance_to_key_level': float  # 距离关键位的距离
            }
        """
        result = {
            'current_price': 0.0,
            'change_pct': 0.0,
            'is_near_key_level': False,
            'key_level': 0.0,
            'distance_to_key_level': 0.0
        }
        
        try:
            # 尝试从 akshare 获取沪深300数据
            try:
                import akshare as ak
                
                # 获取沪深300实时数据
                csi300_data = ak.stock_zh_index_spot(symbol="sh000300")
                
                if csi300_data is not None and not csi300_data.empty:
                    result['current_price'] = csi300_data['current'].iloc[0]
                    result['change_pct'] = csi300_data['percent'].iloc[0]
                    
                    # 判断是否接近关键位（±0.5%）
                    for key_level in self.CSI300_KEY_LEVELS:
                        distance = (result['current_price'] - key_level) / key_level
                        if abs(distance) <= 0.005:  # ±0.5%
                            result['is_near_key_level'] = True
                            result['key_level'] = key_level
                            result['distance_to_key_level'] = distance
                            break
            except ImportError:
                logger.warning("akshare 未安装，无法获取沪深300数据")
            except Exception as e:
                logger.warning(f"获取沪深300数据失败: {e}")
        
        except Exception as e:
            logger.error(f"获取沪深300数据失败: {e}")
        
        return result
    
    def _get_etf50_data(self) -> Dict[str, Any]:
        """
        获取50ETF数据
        
        Returns:
            dict: {
                'current_price': float,    # 当前价格
                'change_pct': float,       # 涨跌幅
                'net_inflow': float,       # 净流入额（亿）
                'is_guarding': bool,       # 是否在护盘
                'guard_strength': float    # 护盘强度（0-1）
            }
        """
        result = {
            'current_price': 0.0,
            'change_pct': 0.0,
            'net_inflow': 0.0,
            'is_guarding': False,
            'guard_strength': 0.0
        }
        
        try:
            # 尝试从 akshare 获取50ETF数据
            try:
                import akshare as ak
                
                # 获取50ETF实时数据（代码：510050）
                etf50_data = ak.fund_etf_spot_em()
                
                if etf50_data is not None and not etf50_data.empty:
                    etf50_row = etf50_data[etf50_data['代码'] == '510050']
                    
                    if not etf50_row.empty:
                        result['current_price'] = etf50_row['最新价'].iloc[0]
                        result['change_pct'] = etf50_row['涨跌幅'].iloc[0]
                        
                        # 获取净流入额（单位：亿）
                        result['net_inflow'] = etf50_row['主力净流入'].iloc[0] / 100000000  # 转换为亿
                        
                        # 判断是否在护盘
                        if result['net_inflow'] > self.ETF50_GUARD_THRESHOLD:
                            result['is_guarding'] = True
                            result['guard_strength'] = min(1.0, result['net_inflow'] / 10.0)  # 最高强度为 10亿
            except ImportError:
                logger.warning("akshare 未安装，无法获取50ETF数据")
            except Exception as e:
                logger.warning(f"获取50ETF数据失败: {e}")
        
        except Exception as e:
            logger.error(f"获取50ETF数据失败: {e}")
        
        return result
    
    def check_national_team_guard(self) -> Dict[str, Any]:
        """
        检查国家队护盘信号
        
        Returns:
            dict: {
                'is_guarding': bool,        # 是否在护盘
                'csi300_data': dict,        # 沪深300数据
                'etf50_data': dict,         # 50ETF数据
                'guard_strength': float,    # 护盘强度（0-1）
                'reason': str               # 原因
            }
        """
        result = {
            'is_guarding': False,
            'csi300_data': {},
            'etf50_data': {},
            'guard_strength': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 获取沪深300数据
            csi300_data = self._get_csi300_data()
            result['csi300_data'] = csi300_data
            
            # 2. 获取50ETF数据
            etf50_data = self._get_etf50_data()
            result['etf50_data'] = etf50_data
            
            # 3. 判断是否在护盘
            # 条件1：大盘接近关键位
            is_csi300_near_key = csi300_data['is_near_key_level']
            
            # 条件2：50ETF 有净流入
            is_etf50_guarding = etf50_data['is_guarding']
            
            # 条件3：大盘下跌（护盘通常发生在下跌时）
            is_csi300_down = csi300_data['change_pct'] < 0
            
            if is_csi300_near_key and is_etf50_guarding and is_csi300_down:
                result['is_guarding'] = True
                result['guard_strength'] = etf50_data['guard_strength']
                
                key_level = csi300_data['key_level']
                distance = csi300_data['distance_to_key_level']
                net_inflow = etf50_data['net_inflow']
                
                result['reason'] = f'🛡️ [国家队护盘] 沪深300接近关键位（{key_level:.0f}，距离{distance:.2%}），50ETF净流入{net_inflow:.2f}亿，大盘下跌{csi300_data["change_pct"]:.2f}%'
                logger.info(f"✅ [国家队护盘] {result['reason']}")
            else:
                result['reason'] = '未检测到国家队护盘信号'
        
        except Exception as e:
            logger.error(f"检查国家队护盘信号失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_global_resonance(self, stock_code: str, suction_price: float = None) -> Dict[str, Any]:
        """
        检查全域共振信号
        
        逻辑：如果股票回踩时大盘正好在关键位受到国家队护盘，提升低吸信号为"全域共振"级
        
        Args:
            stock_code: 股票代码
            suction_price: 低吸价格（可选）
        
        Returns:
            dict: {
                'has_global_resonance': bool,  # 是否有全域共振
                'national_team_guard': dict,   # 国家队护盘信息
                'confidence': float,           # 置信度（0-1）
                'boost_ratio': float,          # 提升比例（1.8 表示提升 80%）
                'reason': str                  # 原因
            }
        """
        result = {
            'has_global_resonance': False,
            'national_team_guard': {},
            'confidence': 0.0,
            'boost_ratio': 1.0,
            'reason': ''
        }
        
        try:
            # 1. 检查国家队护盘信号
            national_team_guard = self.check_national_team_guard()
            result['national_team_guard'] = national_team_guard
            
            if not national_team_guard['is_guarding']:
                result['reason'] = '未检测到国家队护盘，无法判断全域共振'
                return result
            
            # 2. 判断股票是否在回踩
            if suction_price is None:
                # 如果没有提供低吸价格，使用当前价格
                realtime_data = self.data_manager.get_realtime_data(stock_code)
                if not realtime_data:
                    result['reason'] = '无法获取股票数据'
                    return result
                
                current_price = realtime_data.get('price', 0)
                prev_close = realtime_data.get('pre_close', 0)
                
                if prev_close == 0:
                    result['reason'] = '昨收价为0，无法判断是否回踩'
                    return result
                
                change_pct = (current_price - prev_close) / prev_close * 100
                
                # 判断是否在回踩（跌幅 > 1%）
                is_suction = change_pct < -1.0
            else:
                # 使用提供的低吸价格
                realtime_data = self.data_manager.get_realtime_data(stock_code)
                if not realtime_data:
                    result['reason'] = '无法获取股票数据'
                    return result
                
                prev_close = realtime_data.get('pre_close', 0)
                change_pct = (suction_price - prev_close) / prev_close * 100
                
                # 判断是否在回踩（跌幅 > 1%）
                is_suction = change_pct < -1.0
            
            # 3. 判断是否是全域共振
            if is_suction:
                result['has_global_resonance'] = True
                result['confidence'] = national_team_guard['guard_strength']
                
                # 🆕 V18.6: 提升信号确定性至 180/100
                result['boost_ratio'] = 1.8
                
                result['reason'] = f'🌟 [全域共振] 股票回踩（跌幅{change_pct:.2f}%）+ {national_team_guard["reason"]}，信号确定性提升至 180/100'
                logger.info(f"✅ [全域共振] {stock_code} {result['reason']}")
            else:
                result['reason'] = f'股票未回踩（涨幅{change_pct:.2f}%），无法形成全域共振'
        
        except Exception as e:
            logger.error(f"检查全域共振信号失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def analyze_global_resonance(self, stock_code: str, suction_price: float = None, 
                                base_score: float = 100.0) -> Dict[str, Any]:
        """
        综合分析全域共振
        
        Args:
            stock_code: 股票代码
            suction_price: 低吸价格（可选）
            base_score: 基础分数（默认 100.0）
        
        Returns:
            dict: {
                'has_global_resonance': bool,  # 是否有全域共振
                'final_score': float,          # 最终分数
                'boost_ratio': float,          # 提升比例
                'reason': str                  # 原因
            }
        """
        result = {
            'has_global_resonance': False,
            'final_score': base_score,
            'boost_ratio': 1.0,
            'reason': ''
        }
        
        try:
            # 1. 检查全域共振信号
            global_resonance = self.check_global_resonance(stock_code, suction_price)
            
            if global_resonance['has_global_resonance']:
                result['has_global_resonance'] = True
                result['boost_ratio'] = global_resonance['boost_ratio']
                result['final_score'] = base_score * global_resonance['boost_ratio']
                result['reason'] = global_resonance['reason']
            else:
                result['reason'] = global_resonance['reason']
        
        except Exception as e:
            logger.error(f"综合分析全域共振失败: {e}")
            result['reason'] = f'分析失败: {e}'
        
        return result


# 便捷函数
_ntg_instance = None

def get_national_team_guard() -> NationalTeamGuard:
    """获取国家队护盘指纹识别器单例"""
    global _ntg_instance
    if _ntg_instance is None:
        _ntg_instance = NationalTeamGuard()
    return _ntg_instance