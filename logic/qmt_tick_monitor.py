#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT Tick订阅和状态维护模块

功能：
1. 使用QMT API订阅指定股票的Tick数据
2. 维护每只股票的"上一刻状态"
3. 提供回调机制，当有新Tick数据到达时，调用事件检测器

Author: iFlow CLI
Version: V2.0
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StockState:
    """
    股票状态
    
    维护每只股票的"上一刻状态"和"当前状态"
    """
    stock_code: str
    last_price: float = 0.0
    last_volume: int = 0
    last_time: Optional[datetime] = None
    day_high: float = 0.0
    day_low: float = 0.0
    day_open: float = 0.0
    day_volume: int = 0
    
    # 扩展状态
    bid1_volume: int = 0
    ask1_volume: int = 0
    auction_volume: int = 0
    prev_close: float = 0.0
    
    def update(self, tick_data: Dict[str, Any]):
        """
        更新股票状态
        
        Args:
            tick_data: Tick数据字典
        """
        self.last_price = tick_data.get('now', self.last_price)
        self.last_volume = tick_data.get('volume', self.last_volume)
        self.last_time = datetime.now()
        
        # 更新当日最高价和最低价
        if self.day_high == 0 or self.last_price > self.day_high:
            self.day_high = self.last_price
        if self.day_low == 0 or self.last_price < self.day_low:
            self.day_low = self.last_price
        
        # 更新开盘价
        if self.day_open == 0:
            self.day_open = tick_data.get('open', 0)
        
        # 更新当日成交量
        self.day_volume = tick_data.get('volume', self.day_volume)
        
        # 更新扩展状态
        self.bid1_volume = tick_data.get('bid1_volume', self.bid1_volume)
        self.ask1_volume = tick_data.get('ask1_volume', self.ask1_volume)
        self.auction_volume = tick_data.get('auction_volume', self.auction_volume)
        self.prev_close = tick_data.get('close', self.prev_close)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'last_price': self.last_price,
            'last_volume': self.last_volume,
            'last_time': self.last_time.isoformat() if self.last_time else None,
            'day_high': self.day_high,
            'day_low': self.day_low,
            'day_open': self.day_open,
            'day_volume': self.day_volume,
            'bid1_volume': self.bid1_volume,
            'ask1_volume': self.ask1_volume,
            'auction_volume': self.auction_volume,
            'prev_close': self.prev_close
        }


class QMTTickMonitor:
    """
    QMT Tick监控器
    
    负责订阅QMT的Tick数据，并维护股票状态
    """
    
    def __init__(self):
        """初始化QMT Tick监控器"""
        if not QMT_AVAILABLE:
            raise ImportError("请先安装 xtquant 库")
        
        self.subscribed_stocks: List[str] = []
        self.stock_states: Dict[str, StockState] = {}
        self.event_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info("✅ QMT Tick监控器初始化成功")
    
    def subscribe(self, stock_codes: List[str]):
        """
        订阅股票Tick数据
        
        Args:
            stock_codes: 股票代码列表
        """
        if not stock_codes:
            return
        
        # 过滤已订阅的股票
        new_stocks = [code for code in stock_codes if code not in self.subscribed_stocks]
        
        if not new_stocks:
            logger.info("⏭️  所有股票已订阅，无需重复订阅")
            return
        
        try:
            # 使用QMT API订阅Tick数据
            xtdata.subscribe_quote(new_stocks, period='tick')
            
            self.subscribed_stocks.extend(new_stocks)
            
            # 初始化股票状态
            for code in new_stocks:
                if code not in self.stock_states:
                    self.stock_states[code] = StockState(stock_code=code)
            
            logger.info(f"✅ 订阅成功: {len(new_stocks)} 只股票")
            logger.info(f"   总订阅数: {len(self.subscribed_stocks)} 只")
            
        except Exception as e:
            logger.error(f"❌ 订阅失败: {e}")
            raise
    
    def unsubscribe(self, stock_codes: List[str]):
        """
        取消订阅股票Tick数据
        
        Args:
            stock_codes: 股票代码列表
        """
        if not stock_codes:
            return
        
        try:
            # 使用QMT API取消订阅
            xtdata.unsubscribe_quote(stock_codes)
            
            # 从订阅列表中移除
            for code in stock_codes:
                if code in self.subscribed_stocks:
                    self.subscribed_stocks.remove(code)
                if code in self.stock_states:
                    del self.stock_states[code]
            
            logger.info(f"✅ 取消订阅: {len(stock_codes)} 只股票")
            logger.info(f"   剩余订阅数: {len(self.subscribed_stocks)} 只")
            
        except Exception as e:
            logger.error(f"❌ 取消订阅失败: {e}")
    
    def add_event_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        添加事件回调函数
        
        Args:
            callback: 回调函数，接收股票代码和Tick数据
        """
        self.event_callbacks.append(callback)
        logger.info(f"📝 添加事件回调，当前回调数: {len(self.event_callbacks)}")
    
    def _process_tick(self, stock_code: str, tick_data: Dict[str, Any]):
        """
        处理Tick数据
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
        """
        try:
            # 更新股票状态
            if stock_code in self.stock_states:
                self.stock_states[stock_code].update(tick_data)
            
            # 调用所有回调函数
            for callback in self.event_callbacks:
                try:
                    callback(stock_code, tick_data)
                except Exception as e:
                    logger.error(f"❌ 回调函数执行失败: {e}")
        
        except Exception as e:
            logger.error(f"❌ 处理Tick数据失败: {e}")
    
    def _monitor_loop(self):
        """监控循环"""
        logger.info("🚀 Tick监控循环启动")
        
        while not self._stop_event.is_set():
            try:
                # 获取所有订阅股票的Tick数据
                for stock_code in self.subscribed_stocks:
                    try:
                        # 获取Tick数据
                        tick_data = xtdata.get_market_data(
                            stock_list=[stock_code],
                            period='tick',
                            count=1
                        )
                        
                        if tick_data and stock_code in tick_data:
                            # 转换为字典格式
                            tick_dict = tick_data[stock_code].to_dict('records')[0] if hasattr(tick_data[stock_code], 'to_dict') else {}
                            
                            # 添加股票代码
                            tick_dict['code'] = stock_code
                            
                            # 处理Tick数据
                            self._process_tick(stock_code, tick_dict)
                    
                    except Exception as e:
                        logger.warning(f"⚠️  获取 {stock_code} Tick数据失败: {e}")
                
                # 等待下一次轮询
                self._stop_event.wait(1.0)
            
            except Exception as e:
                logger.error(f"❌ 监控循环异常: {e}")
                time.sleep(1.0)
        
        logger.info("🛑 Tick监控循环已停止")
    
    def start(self):
        """启动监控"""
        if self.is_running:
            logger.warning("⚠️  监控器已在运行中")
            return
        
        if not self.subscribed_stocks:
            logger.warning("⚠️  没有订阅任何股票，无法启动监控")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        # 启动监控线程
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        logger.info("✅ QMT Tick监控器已启动")
    
    def stop(self):
        """停止监控"""
        if not self.is_running:
            return
        
        self._stop_event.set()
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("✅ QMT Tick监控器已停止")
    
    def get_stock_state(self, stock_code: str) -> Optional[StockState]:
        """
        获取股票状态
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票状态对象，如果不存在则返回None
        """
        return self.stock_states.get(stock_code)
    
    def get_all_states(self) -> Dict[str, StockState]:
        """获取所有股票状态"""
        return self.stock_states.copy()


# 创建全局实例（单例）
_tick_monitor_instance = None


def get_tick_monitor() -> QMTTickMonitor:
    """
    获取QMT Tick监控器单例
    
    Returns:
        QMTTickMonitor实例
    """
    global _tick_monitor_instance
    
    if _tick_monitor_instance is None:
        _tick_monitor_instance = QMTTickMonitor()
    
    return _tick_monitor_instance


if __name__ == "__main__":
    # 快速测试
    print("✅ QMT Tick监控器测试")
    print(f"   QMT可用: {QMT_AVAILABLE}")
    
    if QMT_AVAILABLE:
        monitor = QMTTickMonitor()
        print(f"   订阅数: {len(monitor.subscribed_stocks)}")
        print(f"   股票状态数: {len(monitor.stock_states)}")
    else:
        print("⚠️  QMT不可用，请安装 xtquant 库")