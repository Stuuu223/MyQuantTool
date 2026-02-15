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
from logic.utils.logger import get_logger
from logic.data.data_manager import DataManager
from logic.data.money_flow_master import get_money_flow_master

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
    # 🆕 V19.0: 优化MA5阈值，强势市场中主力可能在MA5上方就承接
    MA5_TOUCH_THRESHOLD_MIN = -0.02   # 回踩 5日均线下方 -2%（深度低吸）
    MA5_TOUCH_THRESHOLD_MAX = 0.01    # 回踩 5日均线上方 1%（轻度低吸）
    
    # 🆕 V18.6: 分时均线价格缓冲区（避免因网络延迟错过机会）
    INTRADAY_MA_TOUCH_THRESHOLD_MIN = -0.025  # 回踩分时均线下方 -2.5%（缓冲区下限）
    INTRADAY_MA_TOUCH_THRESHOLD_MAX = -0.015  # 回踩分时均线下方 -1.5%（缓冲区上限）
    
    VOLUME_SHRINK_THRESHOLD = 0.7    # 缩量阈值（成交量 < 前一日的 70%）
    DDE_POSITIVE_THRESHOLD = 0.1     # DDE 净额 > 0.1亿
    
    def __init__(self):
        """初始化低吸逻辑引擎"""
        self.data_manager = DataManager()
        self.money_flow_master = get_money_flow_master()
        self._sector_analyzer = None
        
        # 🆕 V19.9: 绑定基础层（efinance）用于低吸战法
        try:
            import efinance as ef
            self.efinance = ef
            logger.info("✅ [低吸战法] 基础层（efinance）初始化成功")
        except ImportError:
            logger.warning("⚠️ [低吸战法] efinance 未安装，请运行: pip install efinance")
            self.efinance = None
        
        try:
            from logic.sector_analysis import FastSectorAnalyzer
            self._sector_analyzer = FastSectorAnalyzer(self.data_manager)
            logger.info("✅ [低吸战法] 板块共振分析器初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ [低吸战法] 初始化板块分析器失败: {e}")
    
    def check_ma5_suction(self, stock_code: str, current_price: float, prev_close: float) -> Dict[str, Any]:
        """
        检查 5日均线低吸信号

        逻辑：股价回踩 5日均线下方 -2% 处，且成交量萎缩
        🆕 V19.6 优化：引入趋势强度因子，动态调整回踩阈值

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
                'reason': str,            # 原因
                'trend_strength': float   # 🆕 趋势强度因子（0-1）
            }
        """
        result = {
            'has_suction': False,
            'suction_type': '',
            'ma5_price': 0.0,
            'touch_distance': 0.0,
            'volume_ratio': 1.0,
            'confidence': 0.0,
            'reason': '',
            'trend_strength': 0.0
        }

        try:
            # 🆕 V19.9: 优先使用基础层（efinance）获取历史K线数据
            kline_data = None
            
            if self.efinance:
                try:
                    kline_data = self.efinance.stock.get_quote_history(stock_code)
                    logger.debug(f"✅ [低吸战法-基础层] 获取K线数据成功: {stock_code}")
                except Exception as e:
                    logger.warning(f"⚠️ [低吸战法-基础层] 获取K线数据失败: {stock_code}, {e}")
            
            # 降级到DataManager
            if kline_data is None or kline_data.empty:
                kline_data = self.data_manager.get_history_data(symbol=stock_code, period='daily')
            
            if kline_data is None or kline_data.empty or len(kline_data) < 5:
                result['reason'] = 'K线数据不足'
                return result

            # 2. 计算 5日均线
            ma5 = kline_data['close'].rolling(window=5).mean().iloc[-1]
            result['ma5_price'] = ma5

            # 3. 计算触碰距离
            touch_distance = (current_price - ma5) / ma5
            result['touch_distance'] = touch_distance

            # 🆕 V19.6 新增：计算趋势强度因子
            # 10日涨幅
            if len(kline_data) >= 10:
                price_10_days_ago = kline_data['close'].iloc[-10]
                trend_strength_10d = (current_price - price_10_days_ago) / price_10_days_ago
            else:
                trend_strength_10d = 0

            # 5日涨幅
            if len(kline_data) >= 5:
                price_5_days_ago = kline_data['close'].iloc[-5]
                trend_strength_5d = (current_price - price_5_days_ago) / price_5_days_ago
            else:
                trend_strength_5d = 0

            # 综合趋势强度（10日涨幅权重更高）
            trend_strength = max(trend_strength_10d, trend_strength_5d)
            result['trend_strength'] = trend_strength

            # 🆕 V19.6 新增：根据趋势强度动态调整回踩阈值
            # 趋势越强，回踩阈值越宽松
            if trend_strength >= 0.30:  # 10日涨幅 >= 30%
                # 超强趋势：允许回踩到MA5上方1%（轻度回踩即可）
                dynamic_threshold = 0.01
                trend_desc = "超强趋势"
            elif trend_strength >= 0.20:  # 10日涨幅 >= 20%
                # 强趋势：允许回踩到MA5下方0.5%
                dynamic_threshold = -0.005
                trend_desc = "强趋势"
            elif trend_strength >= 0.10:  # 10日涨幅 >= 10%
                # 中等趋势：允许回踩到MA5下方1%
                dynamic_threshold = -0.01
                trend_desc = "中等趋势"
            else:
                # 弱趋势：使用默认阈值
                dynamic_threshold = self.MA5_TOUCH_THRESHOLD_MIN
                trend_desc = "弱趋势"

            # 4. 判断是否回踩到动态阈值
            if touch_distance <= dynamic_threshold:
                # 5. 检查成交量是否萎缩
                # 🚀 V19.7: 量能修正逻辑（更平滑的时间加权算法）
                current_volume = kline_data['volume'].iloc[-1]
                prev_volume = kline_data['volume'].iloc[-2]
                
                # 尝试获取当前时间，判断是否为盘中
                try:
                    from datetime import datetime, time
                    now = datetime.now()
                    current_time = now.time()
                    hour = now.hour
                    minute = now.minute
                    
                    # 🆕 V19.8: 9:45之前，不要用当日量推算，直接使用昨日量作为参考
                    if current_time < time(9, 45):
                        # 早盘盲信，使用昨日量作为参考
                        volume_ratio = current_volume / prev_volume if prev_volume > 0 else 1.0
                        logger.debug(f"[{stock_code}] 早盘(9:45前)量能计算(参考昨日): 当前量={current_volume:.0f}, 昨日量={prev_volume:.0f}, 量比={volume_ratio:.2f}")
                    elif hour < 9 or (hour == 9 and minute < 30):
                        # 盘前，使用昨日全天量
                        volume_ratio = current_volume / prev_volume if prev_volume > 0 else 1.0
                        logger.debug(f"[{stock_code}] 盘前量能计算: 当前量={current_volume:.0f}, 昨日量={prev_volume:.0f}, 量比={volume_ratio:.2f}")
                    elif hour < 15:
                        # 盘中（9:45之后），计算已开盘分钟数
                        market_minutes = (hour - 9) * 60 + (minute - 30)
                        trading_minutes = 330  # 全天330分钟
                        
                        # 🚀 V19.8: 使用更平滑的时间加权算法
                        if market_minutes < 60:
                            # 1小时内，随着时间推移增加权值
                            # 使用线性推演和昨日量的加权平均
                            weight = market_minutes / 60.0  # 时间权重（0-1）
                            linear_project = current_volume * (trading_minutes / market_minutes) if market_minutes > 0 else 0
                            # 加权平均：线性推演 * 权重 + 昨日量 * (1-权重)
                            predicted_vol = (linear_project * weight) + (prev_volume * (1 - weight))
                            volume_ratio = current_volume / predicted_vol if predicted_vol > 0 else 1.0
                            logger.debug(f"[{stock_code}] 盘初量能计算(加权平均): 当前量={current_volume:.0f}, 昨日量={prev_volume:.0f}, 时间={market_minutes}分钟, 权重={weight:.2f}, 量比={volume_ratio:.2f}")
                        else:
                            # 1小时后，线性推演较准
                            time_ratio = market_minutes / trading_minutes
                            adjusted_prev_volume = prev_volume * time_ratio
                            volume_ratio = current_volume / adjusted_prev_volume if adjusted_prev_volume > 0 else 1.0
                            logger.debug(f"[{stock_code}] 盘中量能计算(线性推演): 当前量={current_volume:.0f}, 昨日量={prev_volume:.0f}, 时间={market_minutes}分钟, 量比={volume_ratio:.2f}")
                    else:
                        # 收盘后，使用昨日全天量
                        volume_ratio = current_volume / prev_volume if prev_volume > 0 else 1.0
                        logger.debug(f"[{stock_code}] 收盘后量能计算: 当前量={current_volume:.0f}, 昨日量={prev_volume:.0f}, 量比={volume_ratio:.2f}")
                except Exception as e:
                    # 时间计算失败，使用简单逻辑
                    volume_ratio = current_volume / prev_volume if prev_volume > 0 else 1.0
                    logger.warning(f"[{stock_code}] 量能计算失败: {e}, 使用简单逻辑")
                
                result['volume_ratio'] = volume_ratio
                
                if volume_ratio <= self.VOLUME_SHRINK_THRESHOLD:
                    # 6. 检查 DDE 是否为正
                    realtime_data = self.data_manager.get_realtime_data(stock_code)
                    if realtime_data:
                        dde_net_flow = realtime_data.get('dde_net_flow', 0)
                        
                        # 🆕 V19.7: 板块共振分析（全维板块共振系统）
                        sector_resonance_score = 0.0
                        sector_resonance_details = []
                        is_sector_leader = False
                        
                        if self._sector_analyzer:
                            try:
                                stock_name = realtime_data.get('name', '')
                                resonance_result = self._sector_analyzer.check_stock_full_resonance(
                                    stock_code, stock_name
                                )
                                
                                sector_resonance_score = resonance_result.get('resonance_score', 0.0)
                                sector_resonance_details = resonance_result.get('resonance_details', [])
                                is_sector_leader = resonance_result.get('is_leader', False)
                                
                                logger.info(f"🚀 [板块共振] {stock_code} 共振评分: {sector_resonance_score:+.1f}, 详情: {sector_resonance_details}")
                            except Exception as e:
                                logger.warning(f"⚠️ [板块共振] 分析失败: {e}")
                        
                        # 🚀 V19.5: DDE 降级处理逻辑
                        if dde_net_flow > self.DDE_POSITIVE_THRESHOLD:
                            # 正常逻辑：资金共振
                            result['has_suction'] = True
                            result['suction_type'] = 'ma5_suction'
                            # 🆕 V19.6 优化：根据趋势强度调整置信度
                            base_confidence = min(0.8, abs(touch_distance) / 0.05)
                            trend_bonus = min(0.2, trend_strength * 0.5)  # 趋势越强，加分越多
                            # 🆕 V19.7: 添加板块共振加分
                            resonance_bonus = min(0.1, max(0, sector_resonance_score / 50.0))  # 共振评分/50，最多加0.1
                            result['confidence'] = min(1.0, base_confidence + trend_bonus + resonance_bonus)
                            
                            # 构建原因描述
                            reason_parts = [f'🔥 [5日均线低吸] {trend_desc}（10日涨幅{trend_strength*100:.1f}%），回踩5日均线{touch_distance:.2%}，缩量{volume_ratio:.2%}，DDE承接{dde_net_flow:.2f}亿']
                            if sector_resonance_details:
                                reason_parts.append(f"，板块共振加分{resonance_bonus:.2f}")
                                if is_sector_leader:
                                    reason_parts.append("（板块龙头）")
                            result['reason'] = ''.join(reason_parts)
                            logger.info(f"✅ [5日均线低吸] {stock_code} 检测到低吸信号：{result['reason']}")
                        elif dde_net_flow == 0:
                            # 降级逻辑：接口未返回 DDE，仅看技术形态
                            # 此时置信度打折，但不要直接 return
                            result['has_suction'] = True
                            result['suction_type'] = 'ma5_suction'
                            base_confidence = min(0.8, abs(touch_distance) / 0.05)
                            # 🆕 V19.7: 添加板块共振加分
                            resonance_bonus = min(0.1, max(0, sector_resonance_score / 50.0)) if sector_resonance_score > 0 else 0
                            result['confidence'] = (base_confidence * 0.7) + resonance_bonus  # 降权处理
                            
                            # 构建原因描述
                            reason_parts = [f'⚠️ [5日均线低吸] 回踩5日均线{touch_distance:.2%}，缩量{volume_ratio:.2%}，DDE数据缺失(仅技术面)']
                            if sector_resonance_score > 0:
                                reason_parts.append(f"，板块共振加分{resonance_bonus:.2f}")
                            result['reason'] = ''.join(reason_parts)
                            logger.info(f"⚠️ [5日均线低吸] {stock_code} 检测到低吸信号（DDE缺失）：{result['reason']}")
                        else:
                            # DDE 为负数，确实是主力出逃，才否决
                            result['reason'] = f'❌ [5日均线低吸] 回踩5日均线{touch_distance:.2%}，缩量{volume_ratio:.2%}，但DDE大幅流出（{dde_net_flow:.2f}亿）'
                    else:
                        # 无法获取DDE数据，同样降级处理
                        result['has_suction'] = True
                        result['suction_type'] = 'ma5_suction'
                        base_confidence = min(0.8, abs(touch_distance) / 0.05)
                        
                        # 🆕 V19.7: 板块共振分析（DDE数据缺失时）
                        sector_resonance_score = 0.0
                        sector_resonance_details = []
                        
                        if self._sector_analyzer:
                            try:
                                resonance_result = self._sector_analyzer.check_stock_full_resonance(
                                    stock_code, ''
                                )
                                sector_resonance_score = resonance_result.get('resonance_score', 0.0)
                                sector_resonance_details = resonance_result.get('resonance_details', [])
                            except Exception as e:
                                logger.warning(f"⚠️ [板块共振] 分析失败: {e}")
                        
                        # 🆕 V19.7: 添加板块共振加分
                        resonance_bonus = min(0.1, max(0, sector_resonance_score / 50.0)) if sector_resonance_score > 0 else 0
                        result['confidence'] = (base_confidence * 0.7) + resonance_bonus
                        
                        # 构建原因描述
                        reason_parts = [f'⚠️ [5日均线低吸] 回踩5日均线{touch_distance:.2%}，缩量{volume_ratio:.2%}，无法获取DDE数据(仅技术面)']
                        if sector_resonance_score > 0:
                            reason_parts.append(f"，板块共振加分{resonance_bonus:.2f}")
                        result['reason'] = ''.join(reason_parts)
                        logger.info(f"⚠️ [5日均线低吸] {stock_code} 检测到低吸信号（DDE缺失）：{result['reason']}")
                else:
                    result['reason'] = f'回踩5日均线{touch_distance:.2%}，但成交量未萎缩（{volume_ratio:.2%}）'
            else:
                result['reason'] = f'未回踩5日均线下方（{touch_distance:.2%}）'
        
        except Exception as e:
            logger.error(f"检查 5日均线低吸失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        # 🆕 V19.7: 添加板块共振信息到返回结果
        if result.get('has_suction'):
            if self._sector_analyzer:
                try:
                    resonance_result = self._sector_analyzer.check_stock_full_resonance(
                        stock_code, ''
                    )
                    result['sector_resonance_score'] = resonance_result.get('resonance_score', 0.0)
                    result['sector_resonance_details'] = resonance_result.get('resonance_details', [])
                    result['is_sector_leader'] = resonance_result.get('is_leader', False)
                except Exception as e:
                    logger.warning(f"⚠️ [板块共振] 添加共振信息失败: {e}")
        
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
                    
                    # 🚀 V19.5: DDE 降级处理逻辑
                    if dde_turn_red:
                        result['has_suction'] = True
                        result['suction_type'] = 'intraday_ma_suction'
                        # 🆕 V18.6: 根据距离计算置信度，越接近 -2% 置信度越高
                        confidence = 1.0 - abs(touch_distance + 0.02) / 0.01  # 距离 -2% 越近，置信度越高
                        result['confidence'] = min(0.9, max(0.6, confidence))
                        result['reason'] = f'🔥 [分时均线低吸] 回踩分时均线{touch_distance:.2%}（缓冲区内），DDE翻红（{dde_net_flow:.2f}亿）'
                        logger.info(f"✅ [分时均线低吸] {stock_code} 检测到低吸信号：{result['reason']}")
                    elif dde_net_flow == 0:
                        # 降级逻辑：DDE数据缺失，仅看技术形态
                        result['has_suction'] = True
                        result['suction_type'] = 'intraday_ma_suction'
                        confidence = 1.0 - abs(touch_distance + 0.02) / 0.01
                        result['confidence'] = min(0.9, max(0.6, confidence)) * 0.7  # 降权处理
                        result['reason'] = f'⚠️ [分时均线低吸] 回踩分时均线{touch_distance:.2%}（缓冲区内），DDE数据缺失(仅技术面)'
                        logger.info(f"⚠️ [分时均线低吸] {stock_code} 检测到低吸信号（DDE缺失）：{result['reason']}")
                    else:
                        # DDE为负数，否决
                        result['reason'] = f'❌ [分时均线低吸] 回踩分时均线{touch_distance:.2%}（缓冲区内），但DDE大幅流出（{dde_net_flow:.2f}亿）'
                else:
                    # 无法获取DDE数据，降级处理
                    result['has_suction'] = True
                    result['suction_type'] = 'intraday_ma_suction'
                    confidence = 1.0 - abs(touch_distance + 0.02) / 0.01
                    result['confidence'] = min(0.9, max(0.6, confidence)) * 0.7
                    result['reason'] = f'⚠️ [分时均线低吸] 回踩分时均线{touch_distance:.2%}（缓冲区内），无法获取DDE数据(仅技术面)'
                    logger.info(f"⚠️ [分时均线低吸] {stock_code} 检测到低吸信号（DDE缺失）：{result['reason']}")
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
    
    def check_divergence_to_consensus(self, stock_code: str, current_price: float, prev_close: float, 
                                     logic_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        🆕 V18.6: 检查分歧转一致（低吸战法）
        
        逻辑：主力故意在高位放手，让股价回踩均线，洗掉不坚定的筹码。
        这种确定性来自于"逻辑未死"：只要机器人/航天的大背景没变，主力回踩就是为了拿更便宜的筹码。
        你买在回踩点，比那些等回封涨停再追的人，多了 10% 的安全垫。
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            logic_keywords: 核心逻辑关键词列表（可选）
        
        Returns:
            dict: {
                'has_divergence_to_consensus': bool, # 是否有分歧转一致信号
                'high_price': float,          # 高位价格
                'pullback_pct': float,        # 回撤幅度
                'ma5_touch': bool,            # 是否回踩MA5
                'volume_shrink': bool,        # 是否缩量
                'bounce_strength': float,     # 反弹力度
                'logic_alive': bool,          # 逻辑是否未死
                'confidence': float,          # 置信度（0-1）
                'reason': str                 # 原因
            }
        """
        result = {
            'has_divergence_to_consensus': False,
            'high_price': 0.0,
            'pullback_pct': 0.0,
            'ma5_touch': False,
            'volume_shrink': False,
            'bounce_strength': 0.0,
            'logic_alive': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 获取K线数据
            kline_data = self.data_manager.get_history_data(symbol=stock_code, period='daily')
            if kline_data is None or kline_data.empty or len(kline_data) < 5:
                result['reason'] = 'K线数据不足'
                return result
            
            # 2. 识别高位价格（最近5天的最高价）
            high_price = kline_data['high'].max()
            result['high_price'] = high_price
            
            # 3. 计算回撤幅度
            if high_price > 0:
                pullback_pct = (high_price - current_price) / high_price * 100
                result['pullback_pct'] = pullback_pct
            
            # 4. 检查是否回踩MA5
            ma5 = kline_data['close'].rolling(window=5).mean().iloc[-1]
            if ma5 > 0:
                ma5_touch = current_price <= ma5 * 1.02  # 允许2%的误差
                result['ma5_touch'] = ma5_touch
            
            # 5. 检查是否缩量
            current_volume = kline_data['volume'].iloc[-1]
            prev_volume = kline_data['volume'].iloc[-2]
            volume_shrink = current_volume < prev_volume * self.VOLUME_SHRINK_THRESHOLD
            result['volume_shrink'] = volume_shrink
            
            # 6. 检查反弹力度（这里简化处理，实际应该检查分时数据）
            # 假设如果当前价格 > 开盘价，说明有反弹
            open_price = kline_data['open'].iloc[-1]
            bounce_strength = (current_price - open_price) / open_price * 100 if open_price > 0 else 0
            result['bounce_strength'] = bounce_strength
            
            # 7. 检查逻辑是否未死
            logic_alive = False
            if logic_keywords:
                stock_info = self.data_manager.get_stock_info(stock_code)
                if stock_info:
                    stock_name = stock_info.get('name', '')
                    stock_concept = stock_info.get('concept', '')
                    
                    for keyword in logic_keywords:
                        if keyword in stock_name or keyword in stock_concept:
                            logic_alive = True
                            break
            result['logic_alive'] = logic_alive
            
            # 8. 综合判断
            confidence = 0.0
            
            # 回撤幅度评分（回撤5%-15%为最佳）
            if 5.0 <= pullback_pct <= 15.0:
                confidence += 0.3
            elif 3.0 <= pullback_pct <= 20.0:
                confidence += 0.2
            
            # 回踩MA5评分
            if ma5_touch:
                confidence += 0.3
            
            # 缩量评分
            if volume_shrink:
                confidence += 0.2
            
            # 反弹力度评分
            if bounce_strength > 0:
                confidence += 0.1
            
            # 逻辑未死评分
            if logic_alive:
                confidence += 0.1
            
            result['confidence'] = min(1.0, confidence)
            
            # 9. 生成原因
            if result['confidence'] >= 0.7:
                logic_str = f"，逻辑未死（{','.join(logic_keywords)}）" if logic_alive else ""
                result['reason'] = f'🔥 [分歧转一致] 从高位回撤{pullback_pct:.1f}%，回踩MA5，缩量洗筹{logic_str}'
                result['has_divergence_to_consensus'] = True
                logger.info(f"✅ [分歧转一致] {stock_code} 检测到低吸信号：{result['reason']}")
            elif result['confidence'] >= 0.4:
                result['reason'] = f'⚠️ [分歧转一致] 有分歧转一致迹象，但强度不足'
            else:
                result['reason'] = f'📊 [分歧转一致] 暂无明显分歧转一致信号'
        
        except Exception as e:
            logger.error(f"检查分歧转一致失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_weak_to_strong(self, stock_code: str, current_price: float, prev_close: float, 
                            yesterday_limit_up: bool = False, yesterday_explosion: bool = False) -> Dict[str, Any]:
        """
        🆕 V19.0: 检查弱转强信号（情绪套利）
        
        逻辑：监控昨日炸板或烂板的股票，今日竞价是否大幅高开（超预期）。
        这是一种"情绪套利"，利用市场情绪的反转获利。
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            yesterday_limit_up: 昨日是否涨停后炸板
            yesterday_explosion: 昨日是否烂板（涨停后反复炸板）
        
        Returns:
            dict: {
                'has_weak_to_strong': bool,   # 是否有弱转强信号
                'yesterday_status': str,      # 昨日状态
                'open_gap_pct': float,        # 开盘涨幅
                'volume_surge': bool,         # 是否放量
                'dde_positive': bool,         # DDE是否为正
                'confidence': float,          # 置信度（0-1）
                'reason': str                 # 原因
            }
        """
        result = {
            'has_weak_to_strong': False,
            'yesterday_status': '',
            'open_gap_pct': 0.0,
            'volume_surge': False,
            'dde_positive': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 判断昨日状态
            if yesterday_limit_up:
                result['yesterday_status'] = '昨日炸板'
            elif yesterday_explosion:
                result['yesterday_status'] = '昨日烂板'
            else:
                result['reason'] = '昨日非炸板/烂板，不适用弱转强逻辑'
                return result
            
            # 2. 获取今日竞价数据
            realtime_data = self.data_manager.get_realtime_data(stock_code)
            if not realtime_data:
                result['reason'] = '无法获取实时数据'
                return result
            
            # 3. 计算开盘涨幅
            open_price = realtime_data.get('open', prev_close)
            open_gap_pct = (open_price - prev_close) / prev_close * 100
            result['open_gap_pct'] = open_gap_pct
            
            # 4. 判断是否超预期高开
            # 昨日炸板/烂板，今日竞价高开 > 3% 视为超预期
            if open_gap_pct > 3.0:
                confidence = 0.4
                result['reason'] = f'🔥 [弱转强] {result["yesterday_status"]}，今日竞价高开{open_gap_pct:.2f}%超预期'
            elif open_gap_pct > 0:
                confidence = 0.2
                result['reason'] = f'⚠️ [弱转强] {result["yesterday_status"]}，今日竞价小幅高开{open_gap_pct:.2f}%'
            else:
                result['reason'] = f'❌ [弱转强] {result["yesterday_status"]}，今日竞价低开{open_gap_pct:.2f}%，未转强'
                return result
            
            # 5. 检查是否放量
            current_volume = realtime_data.get('volume', 0)
            # 获取昨日成交量
            kline_data = self.data_manager.get_history_data(symbol=stock_code, period='daily')
            if kline_data is not None and len(kline_data) >= 2:
                prev_volume = kline_data['volume'].iloc[-2]
                if current_volume > prev_volume * 1.5:
                    result['volume_surge'] = True
                    confidence += 0.2
                    result['reason'] += '，放量1.5倍'
            
            # 6. 检查DDE是否为正
            dde_net_flow = realtime_data.get('dde_net_flow', 0)
            if dde_net_flow > 0:
                result['dde_positive'] = True
                confidence += 0.2
                result['reason'] += f'，DDE承接{dde_net_flow:.2f}亿'
            
            # 7. 综合判断
            result['confidence'] = min(1.0, confidence)
            
            if result['confidence'] >= 0.8:
                result['has_weak_to_strong'] = True
                logger.info(f"✅ [弱转强] {stock_code} 检测到强信号：{result['reason']}")
            elif result['confidence'] >= 0.6:
                result['has_weak_to_strong'] = True
                logger.info(f"⚠️ [弱转强] {stock_code} 检测到中等信号：{result['reason']}")
        
        except Exception as e:
            logger.error(f"检查弱转强失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def analyze_low_suction(self, stock_code: str, current_price: float, prev_close: float, 
                          intraday_data: Optional[pd.DataFrame] = None,
                          logic_keywords: Optional[List[str]] = None,
                          lhb_institutional: bool = False,
                          yesterday_limit_up: bool = False,
                          yesterday_explosion: bool = False) -> Dict[str, Any]:
        """
        🆕 V19.0: 综合分析低吸信号（含弱转强）
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            intraday_data: 分时数据（可选）
            logic_keywords: 核心逻辑关键词列表（可选）
            lhb_institutional: 龙虎榜是否有机构深度介入（默认 False）
            yesterday_limit_up: 昨日是否涨停后炸板（🆕 V19.0）
            yesterday_explosion: 昨日是否烂板（🆕 V19.0）
        
        Returns:
            dict: {
                'has_suction': bool,        # 是否有低吸信号
                'suction_signals': list,   # 低吸信号列表
                'weak_to_strong_signal': dict,  # 弱转强信号（🆕 V19.0）
                'logic_signal': dict,      # 逻辑信号
                'overall_confidence': float, # 综合置信度（0-1）
                'recommendation': str,     # 建议
                'reason': str,             # 原因
                'fail_reason': str         # 🆕 V19.3: 失败原因（调试用）
            }
        """
        result = {
            'has_suction': False,
            'suction_signals': [],
            'weak_to_strong_signal': {},
            'logic_signal': {},
            'overall_confidence': 0.0,
            'recommendation': 'HOLD',
            'reason': ''
        }
        
        try:
            # 🆕 V19.0: 1. 检查弱转强信号（情绪套利）
            if yesterday_limit_up or yesterday_explosion:
                weak_to_strong = self.check_weak_to_strong(
                    stock_code, current_price, prev_close, 
                    yesterday_limit_up, yesterday_explosion
                )
                result['weak_to_strong_signal'] = weak_to_strong
                
                if weak_to_strong['has_weak_to_strong']:
                    result['has_suction'] = True
                    result['overall_confidence'] = weak_to_strong['confidence']
                    result['recommendation'] = 'BUY'
                    result['reason'] = weak_to_strong['reason']
                    logger.info(f"✅ [弱转强] {stock_code} 检测到情绪套利机会：{result['reason']}")
                    return result
            
            # 2. 检查 5日均线低吸
            ma5_suction = self.check_ma5_suction(stock_code, current_price, prev_close)
            if ma5_suction['has_suction']:
                result['suction_signals'].append(ma5_suction)
            
            # 3. 检查分时均线低吸
            if intraday_data is not None:
                intraday_ma_suction = self.check_intraday_ma_suction(stock_code, current_price, intraday_data)
                if intraday_ma_suction['has_suction']:
                    result['suction_signals'].append(intraday_ma_suction)
            
            # 4. 检查分歧转一致
            divergence_to_consensus = self.check_divergence_to_consensus(
                stock_code, current_price, prev_close, logic_keywords
            )
            if divergence_to_consensus['has_divergence_to_consensus']:
                result['suction_signals'].append(divergence_to_consensus)
            
            # 5. 检查逻辑回踩
            if logic_keywords:
                logic_signal = self.check_logic_reversion(stock_code, logic_keywords, lhb_institutional)
                result['logic_signal'] = logic_signal
            
            # 6. 综合判断
            if result['suction_signals']:
                # 有低吸信号
                if result['logic_signal'].get('has_logic') and result['logic_signal'].get('has_institutional'):
                    # 低吸 + 逻辑 + 机构 = 强信号
                    result['has_suction'] = True
                    result['overall_confidence'] = min(0.9, sum(s['confidence'] for s in result['suction_signals']) / len(result['suction_signals']) + 0.3)
                    result['recommendation'] = 'BUY'
                    result['reason'] = f'🚀 [低吸强信号] {", ".join([s.get("suction_type", s.get("has_divergence_to_consensus", "")) for s in result["suction_signals"]])} + {result["logic_signal"]["reason"]}'
                else:
                    # 只有低吸信号，没有逻辑确认
                    result['has_suction'] = True
                    result['overall_confidence'] = sum(s['confidence'] for s in result['suction_signals']) / len(result['suction_signals'])
                    result['recommendation'] = 'HOLD'
                    result['reason'] = f'⚠️ [低吸观察] {", ".join([s.get("suction_type", s.get("has_divergence_to_consensus", "")) for s in result["suction_signals"]])}，等待逻辑确认'
            else:
                # 🆕 V19.3: 无低吸信号，返回失败原因
                fail_reasons = []
                
                # 检查MA5回踩情况
                ma5_suction = self.check_ma5_suction(stock_code, current_price, prev_close)
                if not ma5_suction['has_suction']:
                    fail_reasons.append(f"MA5未回踩({ma5_suction['reason']})")
                
                # 检查分时均线情况
                if intraday_data is not None:
                    intraday_ma_suction = self.check_intraday_ma_suction(stock_code, current_price, intraday_data)
                    if not intraday_ma_suction['has_suction']:
                        fail_reasons.append(f"分时均线未回踩({intraday_ma_suction['reason']})")
                
                # 检查分歧转一致情况
                divergence_to_consensus = self.check_divergence_to_consensus(
                    stock_code, current_price, prev_close, logic_keywords
                )
                if not divergence_to_consensus['has_divergence_to_consensus']:
                    fail_reasons.append(f"无分歧转一致({divergence_to_consensus['reason']})")
                
                # 检查逻辑确认
                if logic_keywords:
                    logic_signal = self.check_logic_reversion(stock_code, logic_keywords, lhb_institutional)
                    result['logic_signal'] = logic_signal
                    
                    if not logic_signal.get('has_logic'):
                        fail_reasons.append("不符合核心逻辑")
                    elif not logic_signal.get('has_institutional'):
                        fail_reasons.append("龙虎榜无机构深度介入")
                else:
                    fail_reasons.append("未指定逻辑关键词")
                
                result['fail_reason'] = '; '.join(fail_reasons) if fail_reasons else '未满足低吸条件'
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