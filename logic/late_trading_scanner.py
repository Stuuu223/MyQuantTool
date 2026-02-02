#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.0 Late Trading Scanner - 尾盘选股扫描器
专门用于扫描尾盘（14:30-15:00）的选股机会
实现三种尾盘模式：高位横盘、尾盘抢筹、首板回封

Author: iFlow CLI
Version: V19.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, time
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.market_status import MarketStatusChecker

logger = get_logger(__name__)


class LateTradingScanner:
    """
    V19.0 尾盘选股扫描器（Late Trading Scanner）
    
    核心战法：
    1. 高位横盘 (STABLE_HOLD): 全天在均线上方，3%-7%涨幅，窄幅震荡
    2. 尾盘抢筹 (SNEAK_ATTACK): 14:30后突然放量拉升
    3. 首板回封 (RESEAL): 早盘涨停后炸板，尾盘再次回封
    
    时间窗口：14:30 - 15:00
    """
    
    # 尾盘选股阈值配置
    STABLE_HOLD_CHANGE_MIN = 0.03    # 最小涨幅 3%
    STABLE_HOLD_CHANGE_MAX = 0.07    # 最大涨幅 7%
    STABLE_HOLD_VOLATILITY = 0.02    # 近1小时振幅 < 2%
    
    SNEAK_ATTACK_TIME_START = time(14, 30)  # 尾盘抢筹开始时间
    SNEAK_ATTACK_VOLUME_RATIO = 1.5         # 尾盘量比 > 1.5
    SNEAK_ATTACK_PRICE_GAIN = 0.02          # 价格拉升 > 2%
    
    RESEAL_TIME_START = time(14, 30)        # 回封开始时间
    RESEAL_LIMIT_UP_THRESHOLD = 0.095       # 涨停阈值
    
    def __init__(self):
        """初始化尾盘选股扫描器"""
        self.data_manager = DataManager()
        self.market_checker = MarketStatusChecker()
    
    def is_late_trading_time(self) -> bool:
        """
        判断当前是否在尾盘时段（14:30 - 15:00）
        
        🆕 V19.6: 支持DEBUG_MODE，允许在非交易时间测试战法
        
        Returns:
            bool: 是否在尾盘时段（或DEBUG_MODE开启）
        """
        # 🆕 V19.6: 检查是否开启调试模式
        try:
            import config.config_system as config
            if getattr(config, 'DEBUG_MODE', False):
                logger.debug("🚀 [DEBUG_MODE] 已启用，忽略时间限制")
                return True
        except Exception as e:
            logger.warning(f"检查DEBUG_MODE失败: {e}")
        
        # 正常模式：检查时间
        current_time = self.market_checker.get_current_time()
        return time(14, 30) <= current_time <= time(15, 0)
    
    def check_stable_hold(self, stock_code: str, current_price: float, prev_close: float,
                         intraday_data: pd.DataFrame, kline_data: pd.DataFrame) -> Dict[str, Any]:
        """
        检查高位横盘模式（STABLE_HOLD）
        
        逻辑：全天股价在均价线（VWAP）上方运行，且在 3%~7% 之间窄幅震荡
        说明主力控盘极好，大概率在酝酿明天的突破
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            intraday_data: 分时数据
            kline_data: K线数据
        
        Returns:
            dict: {
                'has_signal': bool,         # 是否有信号
                'signal_type': str,         # 信号类型
                'change_pct': float,        # 涨跌幅
                'vwap': float,              # 分时均价
                'price_above_vwap': bool,   # 价格是否在均线上方
                'volatility': float,        # 波动率
                'ma_alignment': bool,       # 均线是否多头排列
                'confidence': float,        # 置信度（0-1）
                'reason': str               # 原因
            }
        """
        result = {
            'has_signal': False,
            'signal_type': 'STABLE_HOLD',
            'change_pct': 0.0,
            'vwap': 0.0,
            'price_above_vwap': False,
            'volatility': 0.0,
            'ma_alignment': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 计算涨跌幅
            change_pct = (current_price - prev_close) / prev_close
            result['change_pct'] = change_pct
            
            # 2. 判断涨幅是否在 3%-7% 范围内
            if not (self.STABLE_HOLD_CHANGE_MIN <= change_pct <= self.STABLE_HOLD_CHANGE_MAX):
                result['reason'] = f'涨幅{change_pct:.2%}不在3%-7%范围内'
                return result
            
            # 3. 检查分时数据
            if intraday_data is None or len(intraday_data) < 30:
                result['reason'] = '分时数据不足'
                return result
            
            # 4. 计算分时均价（VWAP）
            vwap = intraday_data['price'].mean()
            result['vwap'] = vwap
            
            # 5. 判断价格是否稳稳站上均线（> 1%）
            price_above_vwap = current_price > vwap * 1.01
            result['price_above_vwap'] = price_above_vwap
            
            if not price_above_vwap:
                result['reason'] = f'价格{current_price:.2f}未站稳均线{vwap:.2f}'
                return result
            
            # 6. 计算尾盘波动率（近30分钟）
            recent_prices = intraday_data['price'].tail(30)
            volatility = recent_prices.std() / recent_prices.mean()
            result['volatility'] = volatility
            
            if volatility > self.STABLE_HOLD_VOLATILITY:
                result['reason'] = f'尾盘波动率{volatility:.2%}过大，非横盘'
                return result
            
            # 7. 检查均线是否多头排列
            if kline_data is not None and len(kline_data) >= 20:
                ma5 = kline_data['close'].rolling(window=5).mean().iloc[-1]
                ma10 = kline_data['close'].rolling(window=10).mean().iloc[-1]
                ma20 = kline_data['close'].rolling(window=20).mean().iloc[-1]
                
                ma_alignment = ma5 > ma10 > ma20
                result['ma_alignment'] = ma_alignment
                
                if not ma_alignment:
                    result['reason'] = '均线未多头排列'
                    return result
            else:
                result['reason'] = 'K线数据不足，无法判断均线排列'
                return result
            
            # 8. 综合判断
            confidence = 0.0
            confidence += 0.3  # 涨幅合适
            confidence += 0.3  # 站稳均线
            confidence += 0.2  # 波动率小
            confidence += 0.2  # 均线多头排列
            
            result['confidence'] = min(1.0, confidence)
            result['has_signal'] = True
            result['reason'] = f'🔥 [高位横盘] 涨幅{change_pct:.2%}，站稳均线，波动率{volatility:.2%}，均线多头排列'
            logger.info(f"✅ [高位横盘] {stock_code} 检测到尾盘机会：{result['reason']}")
        
        except Exception as e:
            logger.error(f"检查高位横盘失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_sneak_attack(self, stock_code: str, current_price: float, prev_close: float,
                          intraday_data: pd.DataFrame, realtime_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查尾盘抢筹模式（SNEAK_ATTACK）
        
        逻辑：14:30 之前表现平平，突然有大单密集买入，股价快速拉升
        这通常是主力为了第二天做盘，或者利用尾盘抛压小，"偷袭"拉升做图形
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            prev_close: 昨收价
            intraday_data: 分时数据
            realtime_data: 实时数据
        
        Returns:
            dict: {
                'has_signal': bool,         # 是否有信号
                'signal_type': str,         # 信号类型
                'change_pct': float,        # 涨跌幅
                'volume_ratio': float,      # 量比
                'price_gain': float,        # 价格拉升幅度
                'dde_surge': bool,          # DDE是否异动
                'confidence': float,        # 置信度（0-1）
                'reason': str               # 原因
            }
        """
        result = {
            'has_signal': False,
            'signal_type': 'SNEAK_ATTACK',
            'change_pct': 0.0,
            'volume_ratio': 0.0,
            'price_gain': 0.0,
            'dde_surge': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 计算涨跌幅
            change_pct = (current_price - prev_close) / prev_close
            result['change_pct'] = change_pct
            
            # 2. 检查分时数据
            if intraday_data is None or len(intraday_data) < 60:
                result['reason'] = '分时数据不足'
                return result
            
            # 3. 计算尾盘量比（最后30分钟 vs 前30分钟）
            last_30_min_volume = intraday_data['volume'].tail(30).sum()
            prev_30_min_volume = intraday_data['volume'].iloc[-60:-30].sum()
            
            volume_ratio = last_30_min_volume / prev_30_min_volume if prev_30_min_volume > 0 else 1.0
            result['volume_ratio'] = volume_ratio
            
            # 4. 判断是否放量
            if volume_ratio < self.SNEAK_ATTACK_VOLUME_RATIO:
                result['reason'] = f'尾盘量比{volume_ratio:.2f}未达到1.5倍'
                return result
            
            # 5. 计算价格拉升幅度
            price_30_min_ago = intraday_data['price'].iloc[-30]
            price_gain = (current_price - price_30_min_ago) / price_30_min_ago
            result['price_gain'] = price_gain
            
            if price_gain < self.SNEAK_ATTACK_PRICE_GAIN:
                result['reason'] = f'价格拉升{price_gain:.2%}未达到2%'
                return result
            
            # 6. 检查DDE是否异动
            if realtime_data:
                dde_net_flow = realtime_data.get('dde_net_flow', 0)
                dde_surge = dde_net_flow > 0.1  # DDE净流入 > 0.1亿
                result['dde_surge'] = dde_surge
                
                if dde_surge:
                    result['reason'] += f'，DDE异动{dde_net_flow:.2f}亿'
            
            # 7. 综合判断
            confidence = 0.0
            confidence += 0.3  # 放量
            confidence += 0.4  # 价格拉升
            if result['dde_surge']:
                confidence += 0.3  # DDE异动
            
            result['confidence'] = min(1.0, confidence)
            result['has_signal'] = True
            result['reason'] = f'🔥 [尾盘抢筹] 尾盘量比{volume_ratio:.2f}倍，价格拉升{price_gain:.2%}{result.get("reason", "")}'
            logger.info(f"✅ [尾盘抢筹] {stock_code} 检测到尾盘机会：{result['reason']}")
        
        except Exception as e:
            logger.error(f"检查尾盘抢筹失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def check_reseal(self, stock_code: str, current_price: float, prev_close: float,
                    realtime_data: Dict[str, Any], kline_data: pd.DataFrame) -> Dict[str, Any]:
        """
        检查首板回封模式（RESEAL）
        
        逻辑：早盘涨停，盘中炸板，经过长时间换手，尾盘（14:30 后）再次封死涨停
        这是典型的"弱转强"前兆，次日溢价极高
        
        Args:
            stock_code: 股票代码
            current_price: prev_close: 昨收价
            realtime_data: 实时数据
            kline_data: K线数据
        
        Returns:
            dict: {
                'has_signal': bool,         # 是否有信号
                'signal_type': str,         # 信号类型
                'is_limit_up': bool,        # 是否涨停
                'change_pct': float,        # 涨跌幅
                'explosion_count': int,     # 炸板次数
                'reseal_time': str,         # 回封时间
                'confidence': float,        # 置信度（0-1）
                'reason': str               # 原因
            }
        """
        result = {
            'has_signal': False,
            'signal_type': 'RESEAL',
            'is_limit_up': False,
            'change_pct': 0.0,
            'explosion_count': 0,
            'reseal_time': '',
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 1. 计算涨跌幅
            change_pct = (current_price - prev_close) / prev_close
            result['change_pct'] = change_pct
            
            # 2. 判断是否涨停
            is_limit_up = change_pct >= self.RESEAL_LIMIT_UP_THRESHOLD
            result['is_limit_up'] = is_limit_up
            
            if not is_limit_up:
                result['reason'] = f'当前涨幅{change_pct:.2%}未达涨停'
                return result
            
            # 3. 检查是否有过炸板（这里简化处理，实际应该从分时数据中检测）
            # 如果当前是涨停，但今日最高价 > 当前价格，说明有过炸板
            if kline_data is not None and len(kline_data) >= 1:
                today_high = kline_data['high'].iloc[-1]
                if today_high > current_price:
                    result['explosion_count'] = 1
                    result['reason'] = f'今日有过炸板（最高{today_high:.2f}）'
            
            # 4. 判断回封时间（14:30后）
            current_time = self.market_checker.get_current_time()
            if current_time < time(14, 30):
                result['reason'] = f'当前时间{current_time}未到14:30'
                return result
            
            result['reseal_time'] = current_time.strftime('%H:%M:%S')
            
            # 5. 综合判断
            confidence = 0.0
            confidence += 0.4  # 当前涨停
            if result['explosion_count'] > 0:
                confidence += 0.4  # 有过炸板
            confidence += 0.2  # 尾盘回封
            
            result['confidence'] = min(1.0, confidence)
            result['has_signal'] = True
            explosion_str = f"，炸板{result['explosion_count']}次" if result['explosion_count'] > 0 else ""
            result['reason'] = f'🔥 [首板回封] 涨停{change_pct:.2%}{explosion_str}，{result["reseal_time"]}回封'
            logger.info(f"✅ [首板回封] {stock_code} 检测到尾盘机会：{result['reason']}")
        
        except Exception as e:
            logger.error(f"检查首板回封失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def scan_late_trading_opportunities(self, stock_list: List[str], 
                                       stock_name_dict: Optional[Dict[str, str]] = None,
                                       max_stocks: int = 50) -> Dict[str, Any]:
        """
        扫描尾盘选股机会
        
        Args:
            stock_list: 股票代码列表
            stock_name_dict: 股票代码到名称的映射（可选）
            max_stocks: 最大返回股票数
        
        Returns:
            dict: {
                'is_late_trading_time': bool,  # 是否在尾盘时段
                'total_scanned': int,          # 扫描总数
                'opportunities': list,         # 机会列表
                'summary': dict                # 汇总信息
            }
        """
        result = {
            'is_late_trading_time': self.is_late_trading_time(),
            'total_scanned': 0,
            'opportunities': [],
            'summary': {
                'stable_hold': 0,
                'sneak_attack': 0,
                'reseal': 0
            }
        }
        
        try:
            # 如果不在尾盘时段，返回空结果
            if not result['is_late_trading_time']:
                result['reason'] = '当前不在尾盘时段（14:30-15:00）'
                return result
            
            logger.info(f"开始扫描尾盘选股机会，目标股票数：{len(stock_list)}")
            
            # 获取实时数据
            realtime_data_dict = self.data_manager.get_fast_price(stock_list)
            
            for stock_code in stock_list:
                try:
                    result['total_scanned'] += 1
                    
                    # 获取实时数据
                    realtime_data = realtime_data_dict.get(stock_code)
                    if not realtime_data:
                        continue
                    
                    current_price = realtime_data.get('now', 0)
                    prev_close = realtime_data.get('close', 0)
                    
                    if current_price == 0 or prev_close == 0:
                        continue
                    
                    # 获取K线数据
                    kline_data = self.data_manager.get_history_data(stock_code, period='daily')
                    
                    # 获取分时数据（暂时设为None，因为DataManager没有此方法）
                    intraday_data = None
                    
                    # 检查三种模式
                    opportunities = []
                    
                    # 1. 高位横盘
                    stable_hold = self.check_stable_hold(
                        stock_code, current_price, prev_close, intraday_data, kline_data
                    )
                    if stable_hold['has_signal']:
                        opportunities.append(stable_hold)
                        result['summary']['stable_hold'] += 1
                    
                    # 2. 尾盘抢筹
                    sneak_attack = self.check_sneak_attack(
                        stock_code, current_price, prev_close, intraday_data, realtime_data
                    )
                    if sneak_attack['has_signal']:
                        opportunities.append(sneak_attack)
                        result['summary']['sneak_attack'] += 1
                    
                    # 3. 首板回封
                    reseal = self.check_reseal(
                        stock_code, current_price, prev_close, realtime_data, kline_data
                    )
                    if reseal['has_signal']:
                        opportunities.append(reseal)
                        result['summary']['reseal'] += 1
                    
                    # 如果有信号，添加到结果列表
                    if opportunities:
                        # 获取股票名称
                        stock_name = stock_name_dict.get(stock_code, '') if stock_name_dict else ''
                        
                        # 选择置信度最高的信号
                        best_signal = max(opportunities, key=lambda x: x['confidence'])
                        
                        result['opportunities'].append({
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'current_price': current_price,
                            'prev_close': prev_close,
                            'change_pct': change_pct,
                            'signal': best_signal
                        })
                
                except Exception as e:
                    logger.warning(f"扫描股票 {stock_code} 失败: {e}")
                    continue
            
            # 按置信度排序
            result['opportunities'].sort(key=lambda x: x['signal']['confidence'], reverse=True)
            
            # 限制返回数量
            result['opportunities'] = result['opportunities'][:max_stocks]
            
            logger.info(f"✅ 尾盘选股扫描完成，扫描{result['total_scanned']}只股票，找到{len(result['opportunities'])}个机会")
        
        except Exception as e:
            logger.error(f"扫描尾盘选股机会失败: {e}")
            result['reason'] = f'扫描失败: {e}'
        
        return result


# 便捷函数
_lts_instance = None

def get_late_trading_scanner() -> LateTradingScanner:
    """获取尾盘选股扫描器单例"""
    global _lts_instance
    if _lts_instance is None:
        _lts_instance = LateTradingScanner()
    return _lts_instance