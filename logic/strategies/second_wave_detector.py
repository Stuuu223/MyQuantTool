#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6 Second Wave Detector - 二波预期识别器
专门用于识别"二波预期"信号
联动龙虎榜数据，识别顶级游资或机构专用的持仓成本区
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from logic.utils.logger import get_logger
from logic.data_manager import DataManager

logger = get_logger(__name__)


class SecondWaveDetector:
    """
    V18.6 二波预期识别器（Second Wave Detector）
    
    核心战法：
    1. 龙虎榜成本区识别：识别顶级游资（如陈小群）或机构专用的持仓成本区
    2. 二波预期信号：如果低吸位恰好是这些成本区，提升信号确定性至 150/100
    3. 博弈主力预期：这才是真正的"博弈主力预期"
    """
    
    # 顶级游资名单（持续更新）
    TOP_TRADERS = [
        '陈小群',
        '章盟主',
        '方新侠',
        '作手新一',
        '桑田路',
        '湖里大道',
        '劳动路',
        '金开大道',
        '宁波桑田路',
        '宁波解放南',
        '上海溧阳路',
        '苏州中心广场',
        '拉萨团结路',
        '拉萨东环路',
        '拉萨东财'
    ]
    
    # 机构专用席位
    INSTITUTIONAL_SEATS = [
        '机构专用',
        '机构',
        '机构投资者'
    ]
    
    def __init__(self):
        """初始化二波预期识别器"""
        self.data_manager = DataManager()
    
    def get_lhb_cost_zone(self, stock_code: str, lookback_days: int = 30) -> Dict[str, Any]:
        """
        获取龙虎榜成本区
        
        逻辑：识别顶级游资或机构专用的持仓成本区
        
        Args:
            stock_code: 股票代码
            lookback_days: 回看天数
        
        Returns:
            dict: {
                'has_cost_zone': bool,    # 是否有成本区
                'traders': list,          # 游资名单
                'institutions': bool,     # 是否有机构
                'avg_cost': float,        # 平均成本价
                'cost_range': tuple,      # 成本范围 (min, max)
                'confidence': float,      # 置信度（0-1）
                'reason': str             # 原因
            }
        """
        result = {
            'has_cost_zone': False,
            'traders': [],
            'institutions': False,
            'avg_cost': 0.0,
            'cost_range': (0.0, 0.0),
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 从数据库获取龙虎榜历史数据
            conn = self.data_manager.get_db_connection()
            cursor = conn.cursor()
            
            # 获取最近 30 天的龙虎榜数据
            from_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT sell_date, sell_seat, sell_amount, sell_price
                FROM stock_lhb_seller
                WHERE stock_code = ? AND sell_date >= ?
                ORDER BY sell_date DESC
            """, (stock_code, from_date))
            
            seller_data = cursor.fetchall()
            
            if not seller_data:
                result['reason'] = '无龙虎榜数据'
                conn.close()
                return result
            
            # 2. 识别顶级游资和机构
            traders = []
            institutions = []
            costs = []
            
            for sell_date, sell_seat, sell_amount, sell_price in seller_data:
                # 检查是否是顶级游资
                for trader in self.TOP_TRADERS:
                    if trader in sell_seat:
                        traders.append(trader)
                        if sell_price > 0:
                            costs.append(sell_price)
                        break
                
                # 检查是否是机构
                for institution in self.INSTITUTIONAL_SEATS:
                    if institution in sell_seat:
                        institutions.append(institution)
                        if sell_price > 0:
                            costs.append(sell_price)
                        break
            
            # 3. 计算成本区
            if costs:
                avg_cost = np.mean(costs)
                cost_range = (min(costs), max(costs))
                result['avg_cost'] = avg_cost
                result['cost_range'] = cost_range
            
            # 4. 综合判断
            if traders or institutions:
                result['has_cost_zone'] = True
                result['traders'] = list(set(traders))  # 去重
                result['institutions'] = len(institutions) > 0
                
                # 计算置信度
                trader_count = len(result['traders'])
                institution_count = len(institutions)
                
                # 游资越多，置信度越高
                confidence = min(0.8, trader_count * 0.3)
                # 机构介入，置信度提升
                if result['institutions']:
                    confidence = min(0.9, confidence + 0.3)
                
                result['confidence'] = confidence
                
                # 构建原因
                trader_str = ', '.join(result['traders']) if result['traders'] else '无'
                institution_str = '有' if result['institutions'] else '无'
                result['reason'] = f'🔥 [龙虎榜成本区] 游资：{trader_str}，机构：{institution_str}，平均成本：{avg_cost:.2f}元'
                logger.info(f"✅ [龙虎榜成本区] {stock_code} {result['reason']}")
            else:
                result['reason'] = '龙虎榜数据中无顶级游资或机构'
            
            conn.close()
        
        except Exception as e:
            logger.error(f"获取龙虎榜成本区失败: {e}")
            result['reason'] = f'获取失败: {e}'
        
        return result
    
    def check_second_wave_signal(self, stock_code: str, current_price: float, 
                                suction_price: float = None) -> Dict[str, Any]:
        """
        检查二波预期信号
        
        逻辑：如果低吸位恰好是龙虎榜中顶级游资或机构专用的持仓成本区，提升信号确定性至 150/100
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            suction_price: 低吸价格（可选）
        
        Returns:
            dict: {
                'has_second_wave': bool,    # 是否有二波预期
                'cost_zone': dict,          # 成本区信息
                'is_in_cost_zone': bool,    # 是否在成本区内
                'distance_to_cost': float,  # 距离成本区的距离
                'confidence': float,        # 置信度（0-1）
                'boost_ratio': float,       # 提升比例（1.5 表示提升 50%）
                'reason': str               # 原因
            }
        """
        result = {
            'has_second_wave': False,
            'cost_zone': {},
            'is_in_cost_zone': False,
            'distance_to_cost': 0.0,
            'confidence': 0.0,
            'boost_ratio': 1.0,
            'reason': ''
        }
        
        try:
            # 1. 获取龙虎榜成本区
            cost_zone = self.get_lhb_cost_zone(stock_code)
            result['cost_zone'] = cost_zone
            
            if not cost_zone['has_cost_zone']:
                result['reason'] = '无龙虎榜成本区，无法判断二波预期'
                return result
            
            # 2. 判断是否在成本区内
            avg_cost = cost_zone['avg_cost']
            cost_min, cost_max = cost_zone['cost_range']
            
            if avg_cost == 0:
                result['reason'] = '成本区数据无效'
                return result
            
            # 使用低吸价格或当前价格
            check_price = suction_price if suction_price else current_price
            
            # 判断是否在成本区 ±5% 范围内
            distance_to_cost = (check_price - avg_cost) / avg_cost
            result['distance_to_cost'] = distance_to_cost
            
            if -0.05 <= distance_to_cost <= 0.05:
                result['is_in_cost_zone'] = True
                result['has_second_wave'] = True
                result['confidence'] = cost_zone['confidence']
                
                # 🆕 V18.6: 提升信号确定性至 150/100
                result['boost_ratio'] = 1.5
                
                result['reason'] = f'🚀 [二波预期] 低吸位（{check_price:.2f}元）恰好是龙虎榜成本区（{avg_cost:.2f}元，距离{distance_to_cost:.2%}），信号确定性提升至 150/100'
                logger.info(f"✅ [二波预期] {stock_code} {result['reason']}")
            else:
                result['reason'] = f'低吸位（{check_price:.2f}元）不在龙虎榜成本区（{avg_cost:.2f}元，距离{distance_to_cost:.2%}）'
        
        except Exception as e:
            logger.error(f"检查二波预期信号失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def analyze_second_wave(self, stock_code: str, current_price: float, 
                           suction_price: float = None, base_score: float = 100.0) -> Dict[str, Any]:
        """
        综合分析二波预期
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            suction_price: 低吸价格（可选）
            base_score: 基础分数（默认 100.0）
        
        Returns:
            dict: {
                'has_second_wave': bool,    # 是否有二波预期
                'final_score': float,       # 最终分数
                'boost_ratio': float,       # 提升比例
                'reason': str               # 原因
            }
        """
        result = {
            'has_second_wave': False,
            'final_score': base_score,
            'boost_ratio': 1.0,
            'reason': ''
        }
        
        try:
            # 1. 检查二波预期信号
            second_wave = self.check_second_wave_signal(stock_code, current_price, suction_price)
            
            if second_wave['has_second_wave']:
                result['has_second_wave'] = True
                result['boost_ratio'] = second_wave['boost_ratio']
                result['final_score'] = base_score * second_wave['boost_ratio']
                result['reason'] = second_wave['reason']
            else:
                result['reason'] = second_wave['reason']
        
        except Exception as e:
            logger.error(f"综合分析二波预期失败: {e}")
            result['reason'] = f'分析失败: {e}'
        
        return result


# 便捷函数
_swd_instance = None

def get_second_wave_detector() -> SecondWaveDetector:
    """获取二波预期识别器单例"""
    global _swd_instance
    if _swd_instance is None:
        _swd_instance = SecondWaveDetector()
    return _swd_instance