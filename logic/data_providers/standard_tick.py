# -*- coding: utf-8 -*-
"""
StandardTick - 全系统法定Tick结构

【CTO V213 大一统引擎核心组件】
数据防腐层(Anti-Corruption Layer) - 所有数据源必须转换为StandardTick

设计原则：
1. 统一量纲：volume统一为股，amount统一为元
2. 防御性编程：缺失字段用默认值填充，不抛异常
3. 类型安全：使用dataclass定义，IDE友好

Author: CTO架构组
Date: 2026-03-18
Version: 1.0.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class StandardTick:
    """
    全系统法定Tick结构 - 所有引擎只消费此结构
    
    字段说明：
    - code: 股票代码 (如 '000001.SZ')
    - time: 时间戳 (datetime对象或YYYYMMDDHHMMSS字符串)
    - last_price: 最新价 (元)
    - volume_shares: 成交量 (股，强制换算)
    - amount_yuan: 成交额 (元)
    - bid_prices: 五档买价 [bid1, bid2, bid3, bid4, bid5]
    - ask_prices: 五档卖价 [ask1, ask2, ask3, ask4, ask5]
    - bid_vols: 五档买量 [vol1, vol2, vol3, vol4, vol5] (股)
    - ask_vols: 五档卖量 [vol1, vol2, vol3, vol4, vol5] (股)
    - open_price: 今开价
    - high_price: 最高价
    - low_price: 最低价
    - prev_close: 昨收价
    - limit_up: 涨停价
    - limit_down: 跌停价
    """
    
    code: str
    time: Any  # datetime或字符串
    last_price: float = 0.0
    volume_shares: int = 0  # 单位：股
    amount_yuan: float = 0.0  # 单位：元
    
    # 五档盘口
    bid_prices: List[float] = field(default_factory=lambda: [0.0] * 5)
    ask_prices: List[float] = field(default_factory=lambda: [0.0] * 5)
    bid_vols: List[int] = field(default_factory=lambda: [0] * 5)  # 单位：股
    ask_vols: List[int] = field(default_factory=lambda: [0] * 5)  # 单位：股
    
    # 日内价格区间
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    prev_close: float = 0.0
    
    # 涨跌停价
    limit_up: float = 0.0
    limit_down: float = 0.0
    
    # 扩展字段 (用于传递原始数据)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（snake_case字段名）"""
        return {
            'code': self.code,
            'time': self.time,
            'last_price': self.last_price,
            'volume_shares': self.volume_shares,
            'amount_yuan': self.amount_yuan,
            'bid_prices': self.bid_prices,
            'ask_prices': self.ask_prices,
            'bid_vols': self.bid_vols,
            'ask_vols': self.ask_vols,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'prev_close': self.prev_close,
            'limit_up': self.limit_up,
            'limit_down': self.limit_down,
            'extra': self.extra
        }
    
    def to_qmt_dict(self) -> Dict[str, Any]:
        """
        【CTO V214】转换为QMT原生格式字典（camelCase字段名）
        
        返回与xtdata.get_full_tick()完全兼容的字典格式，
        用于主引擎无感知替换。
        
        量纲转换：
        - volume_shares(股) → volume(手)，除以100
        - bid_vols/ask_vols(股) → bidVol/askVol(手)，除以100
        """
        return {
            'lastPrice': self.last_price,
            'volume': self.volume_shares // 100,  # 股→手
            'amount': self.amount_yuan,
            'lastClose': self.prev_close,
            'preClose': self.prev_close,  # 兼容两种字段名
            'open': self.open_price,
            'high': self.high_price,
            'low': self.low_price,
            'limitUp': self.limit_up,
            'limitDown': self.limit_down,
            # 完整五档买价
            'bidPrice1': self.bid_prices[0] if len(self.bid_prices) > 0 else 0.0,
            'bidPrice2': self.bid_prices[1] if len(self.bid_prices) > 1 else 0.0,
            'bidPrice3': self.bid_prices[2] if len(self.bid_prices) > 2 else 0.0,
            'bidPrice4': self.bid_prices[3] if len(self.bid_prices) > 3 else 0.0,
            'bidPrice5': self.bid_prices[4] if len(self.bid_prices) > 4 else 0.0,
            # 完整五档卖价
            'askPrice1': self.ask_prices[0] if len(self.ask_prices) > 0 else 0.0,
            'askPrice2': self.ask_prices[1] if len(self.ask_prices) > 1 else 0.0,
            'askPrice3': self.ask_prices[2] if len(self.ask_prices) > 2 else 0.0,
            'askPrice4': self.ask_prices[3] if len(self.ask_prices) > 3 else 0.0,
            'askPrice5': self.ask_prices[4] if len(self.ask_prices) > 4 else 0.0,
            # 完整五档买量（手）
            'bidVol1': self.bid_vols[0] // 100 if len(self.bid_vols) > 0 and self.bid_vols[0] else 0,
            'bidVol2': self.bid_vols[1] // 100 if len(self.bid_vols) > 1 and self.bid_vols[1] else 0,
            'bidVol3': self.bid_vols[2] // 100 if len(self.bid_vols) > 2 and self.bid_vols[2] else 0,
            'bidVol4': self.bid_vols[3] // 100 if len(self.bid_vols) > 3 and self.bid_vols[3] else 0,
            'bidVol5': self.bid_vols[4] // 100 if len(self.bid_vols) > 4 and self.bid_vols[4] else 0,
            # 完整五档卖量（手）
            'askVol1': self.ask_vols[0] // 100 if len(self.ask_vols) > 0 and self.ask_vols[0] else 0,
            'askVol2': self.ask_vols[1] // 100 if len(self.ask_vols) > 1 and self.ask_vols[1] else 0,
            'askVol3': self.ask_vols[2] // 100 if len(self.ask_vols) > 2 and self.ask_vols[2] else 0,
            'askVol4': self.ask_vols[3] // 100 if len(self.ask_vols) > 3 and self.ask_vols[3] else 0,
            'askVol5': self.ask_vols[4] // 100 if len(self.ask_vols) > 4 and self.ask_vols[4] else 0,
        }
    
    @classmethod
    def from_qmt_tick(cls, code: str, tick: Dict[str, Any]) -> 'StandardTick':
        """
        从QMT原始Tick转换为StandardTick
        
        Args:
            code: 股票代码
            tick: QMT get_full_tick返回的字典
            
        Returns:
            StandardTick实例
            
        量纲转换规则(V185量纲铁律)：
        - QMT volume单位是手(100股)，需要×100转股
        - QMT amount单位是元，无需转换
        """
        # 提取价格
        last_price = tick.get('lastPrice', 0) or 0.0
        prev_close = tick.get('lastClose', 0) or tick.get('preClose', 0) or 0.0
        open_price = tick.get('open', 0) or 0.0
        high_price = tick.get('high', 0) or 0.0
        low_price = tick.get('low', 0) or 0.0
        
        # 【V185量纲铁律】QMT volume是手，×100转股
        volume_shares = int((tick.get('volume', 0) or 0) * 100)
        amount_yuan = float(tick.get('amount', 0) or 0.0)
        
        # 五档盘口
        bid_prices = [
            tick.get('bidPrice1', 0) or 0.0,
            tick.get('bidPrice2', 0) or 0.0,
            tick.get('bidPrice3', 0) or 0.0,
            tick.get('bidPrice4', 0) or 0.0,
            tick.get('bidPrice5', 0) or 0.0,
        ]
        ask_prices = [
            tick.get('askPrice1', 0) or 0.0,
            tick.get('askPrice2', 0) or 0.0,
            tick.get('askPrice3', 0) or 0.0,
            tick.get('askPrice4', 0) or 0.0,
            tick.get('askPrice5', 0) or 0.0,
        ]
        # 【V185量纲铁律】盘口量也是手，×100转股
        bid_vols = [
            int((tick.get('bidVol1', 0) or 0) * 100),
            int((tick.get('bidVol2', 0) or 0) * 100),
            int((tick.get('bidVol3', 0) or 0) * 100),
            int((tick.get('bidVol4', 0) or 0) * 100),
            int((tick.get('bidVol5', 0) or 0) * 100),
        ]
        ask_vols = [
            int((tick.get('askVol1', 0) or 0) * 100),
            int((tick.get('askVol2', 0) or 0) * 100),
            int((tick.get('askVol3', 0) or 0) * 100),
            int((tick.get('askVol4', 0) or 0) * 100),
            int((tick.get('askVol5', 0) or 0) * 100),
        ]
        
        return cls(
            code=code,
            time=datetime.now(),  # 实时Tick用当前时间
            last_price=float(last_price),
            volume_shares=volume_shares,
            amount_yuan=float(amount_yuan),
            bid_prices=bid_prices,
            ask_prices=ask_prices,
            bid_vols=bid_vols,
            ask_vols=ask_vols,
            open_price=float(open_price),
            high_price=float(high_price),
            low_price=float(low_price),
            prev_close=float(prev_close),
            limit_up=float(tick.get('limitUp', 0) or 0.0),
            limit_down=float(tick.get('limitDown', 0) or 0.0),
            extra={'raw_tick': tick}  # 保留原始数据
        )
    
    @classmethod
    def from_local_tick(cls, code: str, tick_row: Dict[str, Any], time_str: str = None) -> 'StandardTick':
        """
        从本地历史Tick DataFrame行转换为StandardTick
        
        Args:
            code: 股票代码
            tick_row: DataFrame行转字典
            time_str: 时间字符串
            
        Returns:
            StandardTick实例
        """
        last_price = tick_row.get('price', tick_row.get('lastPrice', 0)) or 0.0
        prev_close = tick_row.get('prev_close', tick_row.get('lastClose', 0)) or 0.0
        
        # 本地Tick数据volume可能是股也可能是手，需要根据实际情况判断
        # 这里假设本地数据volume已经是股
        volume_shares = int(tick_row.get('volume', tick_row.get('vol', 0)) or 0)
        amount_yuan = float(tick_row.get('amount', tick_row.get('amt', 0)) or 0.0)
        
        return cls(
            code=code,
            time=time_str or tick_row.get('time', ''),
            last_price=float(last_price),
            volume_shares=volume_shares,
            amount_yuan=float(amount_yuan),
            prev_close=float(prev_close),
            open_price=float(tick_row.get('open', 0) or 0.0),
            high_price=float(tick_row.get('high', 0) or 0.0),
            low_price=float(tick_row.get('low', 0) or 0.0),
            extra={'raw_row': tick_row}
        )


class TickAdapterBase:
    """
    Tick适配器基类 - 定义统一接口
    
    所有适配器必须实现：
    - get_ticks(): 获取Tick数据
    - get_full_tick_snapshot(): 获取全市场快照
    """
    
    def get_ticks(self, stock_codes: List[str]) -> Dict[str, StandardTick]:
        """
        获取多只股票的Tick数据
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            {stock_code: StandardTick}
        """
        raise NotImplementedError
    
    def get_full_tick_snapshot(self, stock_codes: List[str]) -> Dict[str, StandardTick]:
        """
        获取全市场快照
        
        Args:
            stock_codes: 股票代码列表
            
        Returns:
            {stock_code: StandardTick}
        """
        raise NotImplementedError
