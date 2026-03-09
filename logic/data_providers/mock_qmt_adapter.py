# -*- coding: utf-8 -*-
"""
MockQmtAdapter - 历史Tick伪装实时流适配器

【CTO V52战役三 - 灵魂统一架构核心组件】
让Scan模式复用LiveTradingEngine，实现绝对同质同源！

设计原理：
- 实现与QMTEventAdapter相同的接口
- 从本地历史Tick文件读取数据
- 按时间线伪装成实时Tick推送

Author: CTO架构组
Date: 2026-03-09
Version: 1.0.0
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class MockQmtAdapter:
    """
    Mock QMT适配器 - 从历史Tick文件读取，伪装成实时流
    
    用途：
    - Scan模式复用LiveTradingEngine
    - 回测时使用真实引擎逻辑
    - 开发调试无需连接QMT
    """
    
    def __init__(self, target_date: str = None, event_bus=None):
        """
        初始化Mock适配器
        
        Args:
            target_date: 目标日期 (格式: 'YYYYMMDD')
            event_bus: 事件总线实例
        """
        self.target_date = target_date or datetime.now().strftime('%Y%m%d')
        self.event_bus = event_bus
        self._subscribed_stocks = set()
        self._tick_data_cache = {}  # {stock_code: DataFrame}
        self._current_time_index = {}  # {stock_code: current_row_index}
        self._is_initialized = False
        self._xtdata = None
        
    def initialize(self) -> bool:
        """
        初始化 - 连接QMT读取历史数据
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            from xtquant import xtdata
            xtdata.enable_hello = False
            self._xtdata = xtdata
            self._is_initialized = True
            logger.info(f"✅ [MockQmtAdapter] 初始化成功，目标日期: {self.target_date}")
            return True
        except ImportError:
            logger.error("❌ [MockQmtAdapter] 无法导入xtquant模块")
            return False
        except Exception as e:
            logger.error(f"❌ [MockQmtAdapter] 初始化失败: {e}")
            return False
    
    def subscribe_ticks(self, stock_list: List[str]) -> int:
        """
        订阅股票Tick数据 - 预加载历史Tick
        
        Args:
            stock_list: 股票代码列表
            
        Returns:
            int: 成功订阅数量
        """
        if not self._is_initialized:
            logger.error("[MockQmtAdapter] 未初始化，无法订阅")
            return 0
        
        success_count = 0
        for stock in stock_list:
            try:
                # 加载历史Tick数据
                local_data = self._xtdata.get_local_data(
                    field_list=[],
                    stock_list=[stock],
                    period='tick',
                    start_time=self.target_date,
                    end_time=self.target_date
                )
                
                if local_data and stock in local_data:
                    df = local_data[stock]
                    if df is not None and not df.empty:
                        self._tick_data_cache[stock] = df
                        self._current_time_index[stock] = 0
                        self._subscribed_stocks.add(stock)
                        success_count += 1
            except Exception as e:
                logger.debug(f"[MockQmtAdapter] {stock} 加载失败: {e}")
                continue
        
        logger.info(f"✅ [MockQmtAdapter] 预加载 {success_count}/{len(stock_list)} 只股票历史Tick")
        return success_count
    
    def get_all_a_shares(self) -> List[str]:
        """
        获取全A股列表
        
        Returns:
            List[str]: 股票代码列表
        """
        if not self._is_initialized:
            return []
        
        try:
            sz = self._xtdata.get_stock_list_in_sector('SZ')
            sh = self._xtdata.get_stock_list_in_sector('SH')
            all_stocks = sz + sh
            # 过滤ST、退市等
            valid_stocks = [s for s in all_stocks if not any(x in s for x in ['ST', '退', 'PT'])]
            return valid_stocks
        except Exception as e:
            logger.error(f"[MockQmtAdapter] 获取股票列表失败: {e}")
            return []
    
    def get_full_tick_snapshot(self, stock_list: List[str]) -> Dict[str, Dict]:
        """
        获取Tick快照 - 从历史数据提取最新状态
        
        Args:
            stock_list: 股票代码列表
            
        Returns:
            Dict[str, Dict]: {stock_code: tick_dict}
        """
        snapshot = {}
        
        for stock in stock_list:
            if stock in self._tick_data_cache:
                df = self._tick_data_cache[stock]
                if df is not None and not df.empty:
                    # 取最后一行作为当前快照
                    last_row = df.iloc[-1]
                    snapshot[stock] = self._row_to_tick_dict(last_row, stock)
            else:
                # 尝试实时加载（懒加载）
                try:
                    local_data = self._xtdata.get_local_data(
                        field_list=[],
                        stock_list=[stock],
                        period='tick',
                        start_time=self.target_date,
                        end_time=self.target_date
                    )
                    if local_data and stock in local_data:
                        df = local_data[stock]
                        if df is not None and not df.empty:
                            self._tick_data_cache[stock] = df
                            last_row = df.iloc[-1]
                            snapshot[stock] = self._row_to_tick_dict(last_row, stock)
                except:
                    pass
        
        return snapshot
    
    def get_tick_at_time(self, stock: str, time_str: str) -> Optional[Dict]:
        """
        获取指定时间的Tick数据 - 用于时间线回放
        
        Args:
            stock: 股票代码
            time_str: 时间字符串 (格式: 'HH:MM:SS' 或 'HHMMSS')
            
        Returns:
            Optional[Dict]: Tick字典或None
        """
        if stock not in self._tick_data_cache:
            return None
        
        df = self._tick_data_cache[stock]
        if df is None or df.empty:
            return None
        
        # 标准化时间格式
        if ':' in time_str:
            target_time = time_str.replace(':', '')
        else:
            target_time = time_str
        
        # 查找匹配时间的行
        for idx, row in df.iterrows():
            tick_time = str(row.get('time', ''))
            # tick_time格式可能是 'HHMMSS' 或时间戳
            if target_time in str(tick_time):
                return self._row_to_tick_dict(row, stock)
        
        return None
    
    def get_timeline_ticks(self, stock_list: List[str], interval_seconds: int = 3) -> List[Dict]:
        """
        获取时间线Tick序列 - 用于回放模式
        
        Args:
            stock_list: 股票代码列表
            interval_seconds: 时间间隔（秒）
            
        Returns:
            List[Dict]: 时间线Tick列表，每个元素包含 {time, ticks: {stock: tick_dict}}
        """
        timeline = []
        
        # 构建时间线（09:30 - 15:00）
        start_time = datetime.strptime("093000", "%H%M%S")
        end_time = datetime.strptime("150000", "%H%M%S")
        
        current_time = start_time
        while current_time <= end_time:
            time_str = current_time.strftime("%H%M%S")
            
            ticks_at_time = {}
            for stock in stock_list:
                tick = self.get_tick_at_time(stock, time_str)
                if tick:
                    ticks_at_time[stock] = tick
            
            if ticks_at_time:
                timeline.append({
                    'time': time_str,
                    'datetime': current_time,
                    'ticks': ticks_at_time
                })
            
            current_time += timedelta(seconds=interval_seconds)
        
        return timeline
    
    def _row_to_tick_dict(self, row, stock_code: str) -> Dict:
        """
        将DataFrame行转换为Tick字典
        
        Args:
            row: DataFrame行
            stock_code: 股票代码
            
        Returns:
            Dict: 标准Tick字典
        """
        return {
            'stock_code': stock_code,
            'lastPrice': float(row.get('lastPrice', 0)),
            'open': float(row.get('open', 0)),
            'high': float(row.get('high', 0)),
            'low': float(row.get('low', 0)),
            'lastClose': float(row.get('lastClose', 0)),
            'amount': float(row.get('amount', 0)),
            'volume': float(row.get('volume', 0)),
            'bidPrice1': float(row.get('bidPrice1', 0)),
            'bidVol1': float(row.get('bidVol1', 0)),
            'askPrice1': float(row.get('askPrice1', 0)),
            'askVol1': float(row.get('askVol1', 0)),
            'time': row.get('time', 0),
        }
    
    def push_tick_to_event_bus(self, stock: str, tick_dict: Dict) -> bool:
        """
        将Tick推送到事件总线 - 模拟实时推送
        
        Args:
            stock: 股票代码
            tick_dict: Tick数据字典
            
        Returns:
            bool: 是否推送成功
        """
        if self.event_bus is None:
            return False
        
        try:
            # 创建Tick事件
            from dataclasses import dataclass
            from typing import Any
            
            @dataclass
            class TickEvent:
                stock_code: str
                data: Dict[str, Any]
            
            event = TickEvent(stock_code=stock, data=tick_dict)
            self.event_bus.publish('tick', event)
            return True
        except Exception as e:
            logger.debug(f"[MockQmtAdapter] 推送事件失败: {e}")
            return False
