#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.5 Low Suction Engine - 低吸逻辑引擎
专门用于监控标的回踩核心均线时的资金流
V18.5: 补齐"低吸/分时分歧"逻辑
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.money_flow_master import get_money_flow_master

logger = get_logger(__name__)


class LowSuctionEngine:
    """
    V18.5 低吸逻辑引擎（Low Suction Engine）
    
    核心战法：
    1. 回踩均线低吸：回踩 5日均线 或 分时均线下方 -2% 处
    2. 缩量回调：成交量萎缩，说明抛压减轻
    3. 资金承接：DDE 净额为正，说明主力承接
    4. 逻辑确认：符合核心逻辑（机器人/航天等）+ 龙虎榜机构深度介入
    
    🆕 V18.6: 引入价格缓冲区，避免因网络延迟错过机会
    """
    
    # 低吸阈值配置
    MA5_TOUCH_THRESHOLD = -0.02      # 回踩 5日均线下方 -2%
    
    # 🆕 V18.6: 分时均线价格缓冲区（避免因网络延迟错过机会）
    INTRADAY_MA_TOUCH_THRESHOLD_MIN = -0.025  # 回踩分时均线下方 -2.5%（缓冲区下限）
    INTRADAY_MA_TOUCH_THRESHOLD_MAX = -0.015  # 回踩分时均线下方 -1.5%（缓冲区上限）
    
    VOLUME_SHRINK_THRESHOLD = 0.7    # 缩量阈值（成交量 < 前一日的 70%）
    DDE_POSITIVE_THRESHOLD = 0.1     # DDE 净额 > 0.1亿
    
    def __init__(self):
        """初始化低吸逻辑引擎"""
        self.data_manager = DataManager()
        self.money_flow_master = get_money_flow_master()
    
    def check_ma5_suction(self, stock_code: str, current_price: float, prev_close: float) -> Dict[str, Any]:
        """
        检查 5日均线低吸信号
        
        逻辑：股价回踩 5日均线下方 -2% 处，且成交量萎缩
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
        
        Returns:
            dict: {
                'has_suction': bool,      # 是否有低吸信号
                'suction_type': str,      # 低吸类型
                'ma5_price': float,       # 5日均线价格
                'touch_distance': float,  # 触碰距离
                'volume_ratio': float,    # 成交量比率
                'confidence': float,      # 置信度（0-1）
                'reason': str             # 原因
            }
        """
        result = {
            'has_suction': False,
            'suction_type': '',
            'ma5_price': 0.0,
            'touch_distance': 0.0,
            'volume_ratio': 1.0,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 获取 K线数据
            kline_data = self.data_manager.get_kline(stock_code, period='daily', count=10)
            if not kline_data or len(kline_data) < 5:
                result['reason'] = 'K线数据不足'
                return result
            
            # 2. 计算 5日均线
            ma5 = kline_data['close'].rolling(window=5).mean().iloc[-1]
            result['ma5_price'] = ma5
            
            # 3. 计算触碰距离
            touch_distance = (current_price - ma5) / ma5
            result['touch_distance'] = touch_distance
            
            # 4. 判断是否回踩到 5日均线下方 -2%
            if touch_distance <= self.MA5_TOUCH_THRESHOLD:
                # 5. 检查成交量是否萎缩
                current_volume = kline_data['volume'].iloc[-1]
                prev_volume = kline_data['volume'].iloc[-2]
                volume_ratio = current_volume / prev_volume if prev_volume > 0 else 1.0
                result['volume_ratio'] = volume_ratio
                
                if volume_ratio <= self.VOLUME_SHRINK_THRESHOLD:
                    # 6. 检查 DDE 是否为正
                    realtime_data = self.data_manager.get_realtime_data(stock_code)
                    if realtime_data:
                        dde_net_flow = realtime_data.get('dde_net_flow', 0)
                        
                        if dde_net_flow > self.DDE_POSITIVE_THRESHOLD:
                            result['has_suction'] = True
                            result['suction_type'] = 'ma5_suction'
                            result['confidence'] = min(0.8, abs(touch_distance) / 0.05)
                            result['reason'] = f'🔥 [5日均线低吸] 回踩5日均线{touch_distance:.2%}，缩量{volume_ratio:.2%}，DDE承接{dde_net_flow:.2f}亿'
                            logger.info(f"✅ [5日均线低吸] {stock_code} 检测到低吸信号：{result['reason']}")
                        else:
                            result['reason'] = f'回踩5日均线{touch_distance:.2%}，缩量{volume_ratio:.2%}，但DDE为负（{dde_net_flow:.2f}亿）'
                    else:
                        result['reason'] = f'回踩5日均线{touch_distance:.2%}，缩量{volume_ratio:.2%}，但无法获取DDE数据'
                else:
                    result['reason'] = f'回踩5日均线{touch_distance:.2%}，但成交量未萎缩（{volume_ratio:.2%}）'
            else:
                result['reason'] = f'未回踩5日均线下方（{touch_distance:.2%}）'
        
        except Exception as e:
            logger.error(f"检查 5日均线低吸失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_intraday_ma_suction(self, stock_code: str, current_price: float, intraday_data: pd.DataFrame) -> Dict[str, Any]:
        """
        检查分时均线低吸信号
        
        🆕 V18.6: 引入价格缓冲区，避免因网络延迟错过机会
        逻辑：股价回踩分时均线（黄线）下方 -1.5% 到 -2.5% 宽幅区间，且 DDE 翻红
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            intraday_data: 分时数据
        
        Returns:
            dict: {
                'has_suction': bool,        # 是否有低吸信号
                'suction_type': str,        # 低吸类型
                'intraday_ma': float,       # 分时均线价格
                'touch_distance': float,    # 触碰距离
                'dde_turn_red': bool,       # DDE 是否翻红
                'confidence': float,        # 置信度（0-1）
                'reason': str               # 原因
            }
        """
        result = {
            'has_suction': False,
            'suction_type': '',
            'intraday_ma': 0.0,
            'touch_distance': 0.0,
            'dde_turn_red': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 检查分时数据
            if intraday_data is None or len(intraday_data) < 10:
                result['reason'] = '分时数据不足'
                return result
            
            # 2. 计算分时均线（黄线）
            intraday_ma = intraday_data['price'].mean()
            result['intraday_ma'] = intraday_ma
            
            # 3. 计算触碰距离
            touch_distance = (current_price - intraday_ma) / intraday_ma
            result['touch_distance'] = touch_distance
            
            # 🆕 V18.6: 判断是否在价格缓冲区内（-2.5% 到 -1.5%）
            if self.INTRADAY_MA_TOUCH_THRESHOLD_MIN <= touch_distance <= self.INTRADAY_MA_TOUCH_THRESHOLD_MAX:
                # 5. 检查 DDE 是否翻红
                realtime_data = self.data_manager.get_realtime_data(stock_code)
                if realtime_data:
                    dde_net_flow = realtime_data.get('dde_net_flow', 0)
                    dde_turn_red = dde_net_flow > 0
                    result['dde_turn_red'] = dde_turn_red
                    
                    if dde_turn_red:
                        result['has_suction'] = True
                        result['suction_type'] = 'intraday_ma_suction'
                        # 🆕 V18.6: 根据距离计算置信度，越接近 -2% 置信度越高
                        confidence = 1.0 - abs(touch_distance + 0.02) / 0.01  # 距离 -2% 越近，置信度越高
                        result['confidence'] = min(0.9, max(0.6, confidence))
                        result['reason'] = f'🔥 [分时均线低吸] 回踩分时均线{touch_distance:.2%}（缓冲区内），DDE翻红（{dde_net_flow:.2f}亿）'
                        logger.info(f"✅ [分时均线低吸] {stock_code} 检测到低吸信号：{result['reason']}")
                    else:
                        result['reason'] = f'回踩分时均线{touch_distance:.2%}（缓冲区内），但DDE未翻红（{dde_net_flow:.2f}亿）'
                else:
                    result['reason'] = f'回踩分时均线{touch_distance:.2%}（缓冲区内），但无法获取DDE数据'
            else:
                result['reason'] = f'未在分时均线缓冲区内（{touch_distance:.2%}，范围：{self.INTRADAY_MA_TOUCH_THRESHOLD_MIN:.2%} ~ {self.INTRADAY_MA_TOUCH_THRESHOLD_MAX:.2%}）'
        
        except Exception as e:
            logger.error(f"检查分时均线低吸失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_logic_reversion(self, stock_code: str, logic_keywords: List[str], lhb_institutional: bool) -> Dict[str, Any]:
        """
        检查逻辑回踩信号
        
        逻辑：符合核心逻辑（机器人/航天等）+ 龙虎榜机构深度介入
        
        Args:
            stock_code: 股票代码
            logic_keywords: 核心逻辑关键词列表
            lhb_institutional: 龙虎榜是否有机构深度介入
        
        Returns:
            dict: {
                'has_logic': bool,        # 是否符合核心逻辑
                'logic_type': str,        # 逻辑类型
                'has_institutional': bool, # 是否有机构深度介入
                'confidence': float,      # 置信度（0-1）
                'reason': str             # 原因
            }
        """
        result = {
            'has_logic': False,
            'logic_type': '',
            'has_institutional': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 检查核心逻辑
            stock_info = self.data_manager.get_stock_info(stock_code)
            if not stock_info:
                result['reason'] = '无法获取股票信息'
                return result
            
            stock_name = stock_info.get('name', '')
            stock_concept = stock_info.get('concept', '')
            
            # 检查是否匹配核心逻辑关键词
            matched_logic = []
            for keyword in logic_keywords:
                if keyword in stock_name or keyword in stock_concept:
                    matched_logic.append(keyword)
            
            if matched_logic:
                result['has_logic'] = True
                result['logic_type'] = ','.join(matched_logic)
                result['confidence'] = min(0.6, len(matched_logic) / len(logic_keywords))
            
            # 2. 检查龙虎榜机构深度介入
            result['has_institutional'] = lhb_institutional
            
            # 3. 综合判断
            if result['has_logic'] and result['has_institutional']:
                result['confidence'] = min(0.9, result['confidence'] + 0.3)
                result['reason'] = f'🔥 [逻辑回踩] 符合核心逻辑（{result["logic_type"]}）+ 龙虎榜机构深度介入'
                logger.info(f"✅ [逻辑回踩] {stock_code} 检测到逻辑信号：{result['reason']}")
            elif result['has_logic']:
                result['reason'] = f'符合核心逻辑（{result["logic_type"]}），但龙虎榜无机构深度介入'
            elif result['has_institutional']:
                result['reason'] = f'龙虎榜有机构深度介入，但不符合核心逻辑'
            else:
                result['reason'] = f'不符合核心逻辑，龙虎榜无机构深度介入'
        
        except Exception as e:
            logger.error(f"检查逻辑回踩失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def analyze_low_suction(self, stock_code: str, current_price: float, prev_close: float, 
                          intraday_data: Optional[pd.DataFrame] = None,
                          logic_keywords: Optional[List[str]] = None,
                          lhb_institutional: bool = False) -> Dict[str, Any]:
        """
        综合分析低吸信号
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            intraday_data: 分时数据（可选）
            logic_keywords: 核心逻辑关键词列表（可选）
            lhb_institutional: 龙虎榜是否有机构深度介入（默认 False）
        
        Returns:
            dict: {
                'has_suction': bool,        # 是否有低吸信号
                'suction_signals': list,   # 低吸信号列表
                'logic_signal': dict,      # 逻辑信号
                'overall_confidence': float, # 综合置信度（0-1）
                'recommendation': str,     # 建议
                'reason': str              # 原因
            }
        """
        result = {
            'has_suction': False,
            'suction_signals': [],
            'logic_signal': {},
            'overall_confidence': 0.0,
            'recommendation': 'HOLD',
            'reason': ''
        }
        
        try:
            # 1. 检查 5日均线低吸
            ma5_suction = self.check_ma5_suction(stock_code, current_price, prev_close)
            if ma5_suction['has_suction']:
                result['suction_signals'].append(ma5_suction)
            
            # 2. 检查分时均线低吸
            if intraday_data is not None:
                intraday_ma_suction = self.check_intraday_ma_suction(stock_code, current_price, intraday_data)
                if intraday_ma_suction['has_suction']:
                    result['suction_signals'].append(intraday_ma_suction)
            
            # 3. 检查逻辑回踩
            if logic_keywords:
                logic_signal = self.check_logic_reversion(stock_code, logic_keywords, lhb_institutional)
                result['logic_signal'] = logic_signal
            
            # 4. 综合判断
            if result['suction_signals']:
                # 有低吸信号
                if result['logic_signal'].get('has_logic') and result['logic_signal'].get('has_institutional'):
                    # 低吸 + 逻辑 + 机构 = 强信号
                    result['has_suction'] = True
                    result['overall_confidence'] = min(0.9, sum(s['confidence'] for s in result['suction_signals']) / len(result['suction_signals']) + 0.3)
                    result['recommendation'] = 'BUY'
                    result['reason'] = f'🚀 [低吸强信号] {", ".join([s["suction_type"] for s in result["suction_signals"]])} + {result["logic_signal"]["reason"]}'
                else:
                    # 只有低吸信号，没有逻辑确认
                    result['has_suction'] = True
                    result['overall_confidence'] = sum(s['confidence'] for s in result['suction_signals']) / len(result['suction_signals'])
                    result['recommendation'] = 'HOLD'
                    result['reason'] = f'⚠️ [低吸观察] {", ".join([s["suction_type"] for s in result["suction_signals"]])}，等待逻辑确认'
            else:
                # 无低吸信号
                if result['logic_signal'].get('has_logic') and result['logic_signal'].get('has_institutional'):
                    # 有逻辑，等待低吸机会
                    result['recommendation'] = 'WAIT'
                    result['reason'] = f'👀 [等待低吸] {result["logic_signal"]["reason"]}，等待回踩均线'
                else:
                    result['recommendation'] = 'HOLD'
                    result['reason'] = '无低吸信号，不符合核心逻辑'
        
        except Exception as e:
            logger.error(f"综合分析低吸失败: {e}")
            result['reason'] = f'分析失败: {e}'
        
        return result


# 便捷函数
_lse_instance = None

def get_low_suction_engine() -> LowSuctionEngine:
    """获取低吸逻辑引擎单例"""
    global _lse_instance
    if _lse_instance is None:
        _lse_instance = LowSuctionEngine()
    return _lse_instance