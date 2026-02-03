#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
盘中实时分析器
专门处理交易时间内的实时决策问题

功能：
1. 自动判断是否交易时间
2. 获取盘中实时快照（价格、成交量、买卖盘）
3. 计算买卖盘压力
4. 评估盘中强度
5. 生成盘中信号
6. 对比昨天数据

Author: iFlow CLI
Version: 1.0
Date: 2026-02-03
"""

from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class IntraDayAnalyzer:
    """盘中实时分析器"""
    
    def __init__(self):
        """初始化盘中分析器"""
        self.xtdata = None
        self.converter = None
        self.trading_hours = {
            'morning_start': time(9, 30),
            'morning_end': time(11, 30),
            'afternoon_start': time(13, 0),
            'afternoon_end': time(15, 0)
        }
        self._init_qmt()
    
    def _init_qmt(self):
        """初始化 QMT 连接"""
        try:
            from xtquant import xtdata
            from logic.code_converter import CodeConverter
            self.xtdata = xtdata
            self.converter = CodeConverter()
            logger.info("✅ [盘中分析器] QMT 初始化成功")
        except ImportError as e:
            logger.warning(f"⚠️ [盘中分析器] 无法导入 QMT 模块: {e}")
    
    def is_available(self) -> bool:
        """检查 QMT 是否可用"""
        return self.xtdata is not None
    
    def is_trading_time(self) -> bool:
        """
        判断当前是否交易时间
        
        Returns:
            bool: True 表示在交易时间内
        """
        now = datetime.now().time()
        morning = (self.trading_hours['morning_start'] <= now <= 
                   self.trading_hours['morning_end'])
        afternoon = (self.trading_hours['afternoon_start'] <= now <= 
                     self.trading_hours['afternoon_end'])
        return morning or afternoon
    
    def get_trading_time_info(self) -> Dict[str, Any]:
        """
        获取交易时间信息
        
        Returns:
            Dict: 包含当前时间、是否交易时间、距离收盘时间等
        """
        now = datetime.now()
        now_time = now.time()
        
        is_trading = self.is_trading_time()
        
        # 计算距离收盘时间
        morning_end = datetime.combine(now.date(), self.trading_hours['morning_end'])
        afternoon_end = datetime.combine(now.date(), self.trading_hours['afternoon_end'])
        
        if is_trading:
            if now_time <= self.trading_hours['morning_end']:
                # 上午交易时间
                minutes_to_close = int((morning_end - now).total_seconds() / 60)
                next_close = self.trading_hours['morning_end']
            else:
                # 下午交易时间
                minutes_to_close = int((afternoon_end - now).total_seconds() / 60)
                next_close = self.trading_hours['afternoon_end']
        else:
            minutes_to_close = None
            next_close = None
        
        return {
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'is_trading': is_trading,
            'trading_period': self._get_trading_period(now_time),
            'minutes_to_close': minutes_to_close,
            'next_close_time': next_close.strftime('%H:%M') if next_close else None
        }
    
    def _get_trading_period(self, now_time: time) -> str:
        """获取当前交易时段"""
        if self.trading_hours['morning_start'] <= now_time <= self.trading_hours['morning_end']:
            return '上午交易时段'
        elif self.trading_hours['afternoon_start'] <= now_time <= self.trading_hours['afternoon_end']:
            return '下午交易时段'
        elif now_time < self.trading_hours['morning_start']:
            return '交易前'
        elif now_time > self.trading_hours['afternoon_end']:
            return '交易后'
        else:
            return '午休时间'
    
    def get_intraday_snapshot(self, stock_code: str) -> Dict[str, Any]:
        """
        获取盘中实时快照（只在交易时间调用）
        
        Args:
            stock_code: 股票代码（如 '300997'）
        
        Returns:
            Dict: 盘中快照数据
            {
                'time': '2026-02-03 14:30:00',
                'price': 24.63,
                'open': 23.81,
                'high': 24.85,
                'low': 23.80,
                'volume': 1500000,  # 成交量（股）
                'amount': 36500000,  # 成交额（元）
                'pct_chg': 3.45,  # 涨跌幅（%）
                'bid_ask_pressure': -0.81,  # 买卖盘压力
                'strength': 'WEAK',  # 强度评估
                'signal': '卖盘压力大，游资出货'
            }
        """
        if not self.is_available():
            return {'error': 'QMT 不可用，无法获取盘中数据'}
        
        if not self.is_trading_time():
            time_info = self.get_trading_time_info()
            return {
                'error': '非交易时间，无法获取盘中数据',
                'time_info': time_info
            }
        
        try:
            # 转换为 QMT 代码格式
            qmt_code = self.converter.to_qmt(stock_code)
            
            # 获取全市场 Tick 数据
            tick_data = self.xtdata.get_full_tick([qmt_code])
            
            if tick_data is None or len(tick_data) == 0 or qmt_code not in tick_data:
                return {'error': '未找到 Tick 数据'}
            
            tick = tick_data[qmt_code]
            
            # 提取基础数据
            price = float(tick.get('lastPrice', 0))
            open_price = float(tick.get('open', 0))
            high_price = float(tick.get('high', 0))
            low_price = float(tick.get('low', 0))
            volume = float(tick.get('volume', 0))  # 股
            amount = float(tick.get('amount', 0))  # 元
            
            # 计算涨跌幅
            last_close = float(tick.get('lastClose', 0))
            if last_close > 0:
                pct_chg = (price - last_close) / last_close * 100
            else:
                pct_chg = 0.0
            
            # 提取买卖盘
            bid_prices = tick.get('bidPrice', [])
            ask_prices = tick.get('askPrice', [])
            bid_vols = tick.get('bidVol', [])
            ask_vols = tick.get('askVol', [])
            
            bid = []
            ask = []
            for i in range(min(5, len(bid_prices))):
                if bid_prices[i] > 0:
                    bid.append({
                        "price": round(bid_prices[i], 2),
                        "volume": round(bid_vols[i], 2) if i < len(bid_vols) else 0
                    })
            
            for i in range(min(5, len(ask_prices))):
                if ask_prices[i] > 0:
                    ask.append({
                        "price": round(ask_prices[i], 2),
                        "volume": round(ask_vols[i], 2) if i < len(ask_vols) else 0
                    })
            
            # 计算买卖盘压力
            bid_total = sum([b['volume'] for b in bid])
            ask_total = sum([a['volume'] for a in ask])
            bid_ask_pressure = (bid_total - ask_total) / (bid_total + ask_total) if (bid_total + ask_total) > 0 else 0.0
            
            # 评估强度
            strength = self._evaluate_strength(price, open_price, high_price, low_price, pct_chg)
            
            # 生成信号
            signal = self._generate_signal(bid_ask_pressure, strength, pct_chg)
            
            result = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stock_code': stock_code,
                'price': round(price, 2),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'last_close': round(last_close, 2),
                'volume': int(volume),  # 股
                'volume_hands': int(volume / 100),  # 手
                'amount': round(amount, 2),  # 元
                'amount_wan': round(amount / 10000, 2),  # 万元
                'pct_chg': round(pct_chg, 2),
                
                # 买卖盘数据
                'bid': bid,
                'ask': ask,
                'bid_total': round(bid_total, 2),
                'ask_total': round(ask_total, 2),
                'bid_ask_pressure': round(bid_ask_pressure, 2),
                
                # 强度和信号
                'strength': strength,
                'signal': signal
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [盘中分析器] 获取盘中快照失败: {e}")
            return {'error': f'获取盘中数据失败: {str(e)}'}
    
    def _evaluate_strength(self, price: float, open_price: float, 
                           high_price: float, low_price: float, 
                           pct_chg: float) -> str:
        """
        评估盘中强度
        
        Args:
            price: 当前价格
            open_price: 开盘价
            high_price: 最高价
            low_price: 最低价
            pct_chg: 涨跌幅（%）
        
        Returns:
            str: STRONG | MODERATE | WEAK | VOLATILE | NEUTRAL
        """
        # 计算振幅
        if low_price > 0:
            amplitude = (high_price - low_price) / low_price * 100
        else:
            amplitude = 0.0
        
        # 判断强度
        if pct_chg > 3 and amplitude < 5:
            return 'STRONG'  # 强势上涨，波动小
        elif pct_chg > 1 and amplitude < 7:
            return 'MODERATE'  # 温和上涨
        elif pct_chg < -3:
            return 'WEAK'  # 弱势下跌
        elif amplitude > 10:
            return 'VOLATILE'  # 剧烈波动
        else:
            return 'NEUTRAL'  # 震荡
    
    def _generate_signal(self, bid_ask_pressure: float, strength: str, 
                         pct_chg: float) -> str:
        """
        生成盘中信号
        
        Args:
            bid_ask_pressure: 买卖盘压力（-1到+1）
            strength: 强度评估
            pct_chg: 涨跌幅（%）
        
        Returns:
            str: 信号描述
        """
        # 信号生成逻辑
        if bid_ask_pressure < -0.6 and strength == 'WEAK':
            return '🔴 卖盘压力大，游资出货，建议减亏'
        elif bid_ask_pressure > 0.5 and strength == 'STRONG':
            return '🟢 买盘强势，机构吸筹，可继续持有'
        elif strength == 'VOLATILE':
            return '⚠️ 剧烈波动，可能是对倒，观察不动'
        elif pct_chg > 5 and bid_ask_pressure < 0:
            return '🔴 涨幅大但卖压增加，可能是诱多'
        elif pct_chg < -3 and bid_ask_pressure > 0:
            return '🟢 跌幅大但买盘承接，可能是洗盘'
        else:
            return '⚪ 盘面平稳，继续观察'
    
    def compare_with_yesterday(self, stock_code: str, 
                               yesterday_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        对比昨天的数据（关键！）
        
        Args:
            stock_code: 股票代码
            yesterday_data: 昨天的分析结果（从 enhanced JSON 获取）
        
        Returns:
            Dict: 对比结果
        """
        today = self.get_intraday_snapshot(stock_code)
        
        if 'error' in today:
            return today
        
        # 获取昨天的收盘价
        yesterday_close = yesterday_data.get('qmt', {}).get('latest', {}).get('close', 0)
        if yesterday_close == 0:
            yesterday_close = yesterday_data.get('qmt', {}).get('data', {})[-1].get('close', 0) if yesterday_data.get('qmt', {}).get('data') else 0
        
        # 获取昨天的买卖盘压力（如果有）
        yesterday_pressure = 0.0
        if 'order_book' in yesterday_data.get('qmt', {}):
            yesterday_pressure = yesterday_data['qmt']['order_book'].get('bid_ask_imbalance', 0.0)
        
        # 对比分析
        price_change_pct = (today['price'] - yesterday_close) / yesterday_close * 100 if yesterday_close > 0 else 0.0
        
        comparison = {
            'price_change_pct': round(price_change_pct, 2),
            'yesterday_close': round(yesterday_close, 2),
            'today_price': today['price'],
            'pressure_change': {
                'today': today['bid_ask_pressure'],
                'yesterday': round(yesterday_pressure, 2),
                'delta': round(today['bid_ask_pressure'] - yesterday_pressure, 2)
            },
            'signal': self._generate_comparison_signal(today['bid_ask_pressure'], 
                                                       yesterday_pressure, 
                                                       price_change_pct)
        }
        
        return {
            'today': today,
            'yesterday': {
                'close': round(yesterday_close, 2),
                'bid_ask_pressure': round(yesterday_pressure, 2)
            },
            'comparison': comparison
        }
    
    def _generate_comparison_signal(self, today_pressure: float, 
                                   yesterday_pressure: float,
                                   price_change_pct: float) -> str:
        """
        生成对比信号
        
        Args:
            today_pressure: 今天的买卖盘压力
            yesterday_pressure: 昨天的买卖盘压力
            price_change_pct: 价格变化（%）
        
        Returns:
            str: 信号描述
        """
        pressure_delta = today_pressure - yesterday_pressure
        
        if pressure_delta < -0.5:
            return '🔴 今天卖压明显增大，昨天的反弹可能是诱多'
        elif pressure_delta > 0.5:
            return '🟢 今天买盘明显增强，昨天的弱势可能反转'
        elif price_change_pct > 3 and pressure_delta < 0:
            return '🔴 涨幅大但卖压增大，注意风险'
        elif price_change_pct < -3 and pressure_delta > 0:
            return '🟢 跌幅大但买盘承接，可能是机会'
        else:
            return '⚪ 今天延续昨天的走势，无明显变化'


# 便捷函数
def get_intraday_snapshot(stock_code: str) -> Dict[str, Any]:
    """
    获取盘中快照（便捷函数）
    
    Args:
        stock_code: 股票代码
    
    Returns:
        Dict: 盘中快照数据
    """
    analyzer = IntraDayAnalyzer()
    return analyzer.get_intraday_snapshot(stock_code)


def is_trading_time() -> bool:
    """
    判断是否交易时间（便捷函数）
    
    Returns:
        bool: True 表示在交易时间内
    """
    analyzer = IntraDayAnalyzer()
    return analyzer.is_trading_time()