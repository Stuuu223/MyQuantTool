#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.6 Fake Order Detector - 假单识别器
专门用于识别"托单套路"和"虚假繁荣"
监控买一到买五的撤单率，识别假单
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from logic.logger import get_logger
from logic.data_manager import DataManager

logger = get_logger(__name__)


class FakeOrderDetector:
    """
    V18.6 假单识别器（Fake Order Detector）
    
    核心战法：
    1. 撤单率监控：监控买一到买五的撤单率
    2. 虚假繁荣识别：如果 DDE 巨量流入，但买一到买五出现频繁撤单，判定为"虚假繁荣"
    3. 取消 BUY 信号：识别到假单时，取消 BUY 信号
    """
    
    # 撤单率阈值配置
    HIGH_CANCELLATION_RATE_THRESHOLD = 0.3  # 撤单率 > 30% 为高撤单
    DDE_FAKE_THRESHOLD = 1.0  # DDE > 1.0亿时才检查撤单率
    
    def __init__(self):
        """初始化假单识别器"""
        self.data_manager = DataManager()
        
        # 撤单历史数据缓存
        self._cancellation_history_cache = {}  # {stock_code: {'cancellations': [], 'last_update': datetime}}
        self._cache_ttl = 300  # 缓存有效期（秒），5分钟
    
    def _get_order_book_snapshot(self, stock_code: str) -> Dict[str, Any]:
        """
        获取盘口快照数据
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {
                'bid_prices': list,      # 买一到买五价格
                'bid_volumes': list,     # 买一到买五量
                'ask_prices': list,      # 卖一到卖五价格
                'ask_volumes': list,     # 卖一到卖五量
                'timestamp': datetime    # 时间戳
            }
        """
        result = {
            'bid_prices': [],
            'bid_volumes': [],
            'ask_prices': [],
            'ask_volumes': [],
            'timestamp': datetime.now()
        }
        
        try:
            # 从实时数据获取盘口数据
            realtime_data = self.data_manager.get_realtime_data(stock_code)
            
            if realtime_data:
                # 获取买一到买五
                for i in range(1, 6):
                    bid_price_key = f'bid{i}_price'
                    bid_volume_key = f'bid{i}_volume'
                    ask_price_key = f'ask{i}_price'
                    ask_volume_key = f'ask{i}_volume'
                    
                    result['bid_prices'].append(realtime_data.get(bid_price_key, 0.0))
                    result['bid_volumes'].append(realtime_data.get(bid_volume_key, 0))
                    result['ask_prices'].append(realtime_data.get(ask_price_key, 0.0))
                    result['ask_volumes'].append(realtime_data.get(ask_volume_key, 0))
        
        except Exception as e:
            logger.error(f"获取盘口快照失败: {e}")
        
        return result
    
    def _calculate_cancellation_rate(self, stock_code: str, lookback_seconds: int = 60) -> float:
        """
        计算撤单率
        
        逻辑：比较前后两个时间点的盘口数据，计算撤单率
        
        Args:
            stock_code: 股票代码
            lookback_seconds: 回看时间（秒）
        
        Returns:
            float: 撤单率（0-1）
        """
        try:
            # 检查缓存
            cache_key = stock_code
            if cache_key in self._cancellation_history_cache:
                cache_data = self._cancellation_history_cache[cache_key]
                cache_age = (datetime.now() - cache_data['last_update']).total_seconds()
                if cache_age < self._cache_ttl:
                    # 从缓存中获取历史数据
                    history = cache_data['cancellations']
                    if len(history) >= 2:
                        # 计算最近两次的撤单率
                        latest = history[-1]
                        previous = history[-2]
                        
                        # 计算买一到买五的总撤单量
                        total_cancellation = 0
                        total_previous_volume = 0
                        
                        for i in range(5):
                            bid_volume_latest = latest['bid_volumes'][i] if i < len(latest['bid_volumes']) else 0
                            bid_volume_previous = previous['bid_volumes'][i] if i < len(previous['bid_volumes']) else 0
                            
                            # 如果最新量比前一次少，说明有撤单
                            if bid_volume_latest < bid_volume_previous:
                                total_cancellation += (bid_volume_previous - bid_volume_latest)
                                total_previous_volume += bid_volume_previous
                        
                        if total_previous_volume > 0:
                            return total_cancellation / total_previous_volume
            
            # 获取当前盘口快照
            current_snapshot = self._get_order_book_snapshot(stock_code)
            
            # 更新缓存
            if cache_key not in self._cancellation_history_cache:
                self._cancellation_history_cache[cache_key] = {
                    'cancellations': [],
                    'last_update': datetime.now()
                }
            
            self._cancellation_history_cache[cache_key]['cancellations'].append(current_snapshot)
            self._cancellation_history_cache[cache_key]['last_update'] = datetime.now()
            
            # 如果缓存数据不足，返回 0
            if len(self._cancellation_history_cache[cache_key]['cancellations']) < 2:
                return 0.0
            
            return 0.0
        
        except Exception as e:
            logger.error(f"计算撤单率失败: {e}")
            return 0.0
    
    def check_fake_order_signal(self, stock_code: str, signal: str) -> Dict[str, Any]:
        """
        检查假单信号
        
        逻辑：如果 DDE 巨量流入，但买一到买五出现频繁撤单，判定为"虚假繁荣"
        
        Args:
            stock_code: 股票代码
            signal: 原始信号（BUY/SELL/HOLD）
        
        Returns:
            dict: {
                'has_fake_order': bool,    # 是否有假单
                'cancellation_rate': float, # 撤单率
                'dde_net_flow': float,     # DDE 净额
                'is_fake_prosperity': bool, # 是否是虚假繁荣
                'confidence': float,       # 置信度（0-1）
                'reason': str              # 原因
            }
        """
        result = {
            'has_fake_order': False,
            'cancellation_rate': 0.0,
            'dde_net_flow': 0.0,
            'is_fake_prosperity': False,
            'confidence': 0.0,
            'reason': ''
        }
        
        try:
            # 只有 BUY 信号才需要检查假单
            if signal != 'BUY':
                result['reason'] = '非 BUY 信号，跳过假单检查'
                return result
            
            # 1. 获取 DDE 数据
            realtime_data = self.data_manager.get_realtime_data(stock_code)
            if not realtime_data:
                result['reason'] = '无法获取实时数据'
                return result
            
            dde_net_flow = realtime_data.get('dde_net_flow', 0)
            result['dde_net_flow'] = dde_net_flow
            
            # 2. 只有 DDE 巨量流入时才检查撤单率
            if dde_net_flow < self.DDE_FAKE_THRESHOLD:
                result['reason'] = f'DDE 净额（{dde_net_flow:.2f}亿）未达到阈值（{self.DDE_FAKE_THRESHOLD}亿），跳过假单检查'
                return result
            
            # 3. 计算撤单率
            cancellation_rate = self._calculate_cancellation_rate(stock_code)
            result['cancellation_rate'] = cancellation_rate
            
            # 4. 判断是否是虚假繁荣
            if cancellation_rate > self.HIGH_CANCELLATION_RATE_THRESHOLD:
                result['has_fake_order'] = True
                result['is_fake_prosperity'] = True
                result['confidence'] = min(0.9, cancellation_rate)
                result['reason'] = f'🚨 [虚假繁荣] DDE 巨量流入（{dde_net_flow:.2f}亿），但买一到买五撤单率高（{cancellation_rate:.2%}），判定为假单'
                logger.warning(f"❌ [虚假繁荣] {stock_code} {result['reason']}")
            else:
                result['reason'] = f'DDE 巨量流入（{dde_net_flow:.2f}亿），撤单率正常（{cancellation_rate:.2%}），未发现假单'
        
        except Exception as e:
            logger.error(f"检查假单信号失败: {e}")
            result['reason'] = f'检查失败: {e}'
        
        return result
    
    def should_cancel_buy_signal(self, stock_code: str, signal: str) -> Tuple[bool, str]:
        """
        判断是否应该取消 BUY 信号
        
        Args:
            stock_code: 股票代码
            signal: 原始信号（BUY/SELL/HOLD）
        
        Returns:
            tuple: (是否取消, 取消原因)
        """
        try:
            # 检查假单信号
            fake_order = self.check_fake_order_signal(stock_code, signal)
            
            if fake_order['is_fake_prosperity']:
                cancel_reason = f'🛑 [取消 BUY 信号] {fake_order["reason"]}'
                logger.warning(f"❌ {stock_code} {cancel_reason}")
                return True, cancel_reason
            
            return False, ''
        
        except Exception as e:
            logger.error(f"判断是否取消 BUY 信号失败: {e}")
            return False, f'判断失败: {e}'


# 便捷函数
_fod_instance = None

def get_fake_order_detector() -> FakeOrderDetector:
    """获取假单识别器单例"""
    global _fod_instance
    if _fod_instance is None:
        _fod_instance = FakeOrderDetector()
    return _fod_instance