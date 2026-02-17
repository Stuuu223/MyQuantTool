#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略接口定义
用于定义可以运行在Tick数据上的策略
"""

from typing import Protocol, List, Dict, Any, Optional
from datetime import datetime


class TickData:
    """Tick数据结构"""
    def __init__(self, time: int, last_price: float, volume: int, amount: float,
                 bid_price: float, ask_price: float, bid_vol: int, ask_vol: int):
        self.time = time  # 毫秒时间戳
        self.last_price = last_price  # 最新价格
        self.volume = volume  # 总成交量
        self.amount = amount  # 总成交额
        self.bid_price = bid_price  # 买一价
        self.ask_price = ask_price  # 卖一价
        self.bid_vol = bid_vol  # 买一量
        self.ask_vol = ask_vol  # 卖一量


class Signal:
    """信号结构"""
    def __init__(self, time: int, price: float, signal_type: str, 
                 params: Dict, strength: float = 1.0, extra_info: Dict = None):
        self.time = time  # 信号时间戳
        self.price = price  # 信号价格
        self.signal_type = signal_type  # 信号类型
        self.params = params  # 参数
        self.strength = strength  # 信号强度
        self.extra_info = extra_info or {}  # 额外信息


class ITickStrategy(Protocol):
    """Tick策略接口"""
    
    def on_tick(self, tick: TickData) -> List[Signal]:
        """
        处理单个Tick数据
        
        Args:
            tick: Tick数据
            
        Returns:
            List[Signal]: 产生的信号列表
        """
        ...
    
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        ...
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前策略状态（用于调试）"""
        ...


class StrategyContext:
    """策略运行上下文"""
    def __init__(self):
        self.current_price = 0.0
        self.current_time = 0
        self.price_history = []  # [(time, price), ...]
        self.volume_history = []  # [(time, volume), ...]
        self.signals = []


if __name__ == "__main__":
    print("✅ 策略接口定义完成")