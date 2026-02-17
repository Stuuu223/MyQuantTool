#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时Tick事件处理器 (Real-time Tick Event Handler)

根据CTO指导意见，将统一战法核心集成到实时EventDriven监控系统中。
该处理器订阅实时Tick数据，使用UnifiedWarfareCore检测多战法事件。

核心功能：
1. 订阅实时Tick数据
2. 使用UnifiedWarfareCore处理多战法检测
3. 实时发布检测到的事件
4. 与现有EventDriven架构对齐

设计原则：
1. 保持与QMT的兼容性
2. 使用统一的事件处理流程
3. 遵循V12.1.0规范

验收标准：
- 能够实时处理Tick数据
- 与UnifiedWarfareCore集成
- 性能满足实时处理要求
- 代码符合项目规范

Author: iFlow CLI
Version: V12.1.0
Date: 2026-02-17
"""

import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import threading
import queue

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

from logic.strategies.unified_warfare_core import get_unified_warfare_core
from logic.strategies.event_driven_warfare_adapter import get_event_driven_adapter
from logic.strategies.event_detector import EventType, TradingEvent
from logic.utils.logger import get_logger
from logic.data_providers.qmt_manager import get_qmt_manager

logger = get_logger(__name__)


class RealTimeTickEventHandler:
    """
    实时Tick事件处理器
    
    功能：
    1. 订阅实时Tick数据
    2. 使用统一战法核心处理Tick
    3. 实时发布战法事件
    4. 管理订阅的股票列表
    """

    def __init__(self):
        """初始化实时Tick事件处理器"""
        # 获取QMT管理器
        self.qmt_manager = get_qmt_manager()
        
        # 获取统一战法核心
        self.warfare_core = get_unified_warfare_core()
        
        # 获取EventDriven适配器
        self.adapter = get_event_driven_adapter()
        
        # 订阅的股票列表
        self.subscribed_stocks = set()
        
        # 事件队列
        self.event_queue = queue.Queue()
        
        # 控制标志
        self.running = False
        self.processing_thread = None
        
        # 性能统计
        self._total_ticks_processed = 0
        self._total_events_detected = 0
        self._start_time = None
        
        logger.info("✅ [实时Tick事件处理器] 初始化完成")
        logger.info(f"   - QMT状态: {'可用' if self.qmt_manager.is_available() else '不可用'}")
        logger.info(f"   - 支持战法: {len(self.warfare_core.get_active_detectors())} 种")
    
    def subscribe_stocks(self, stock_list: List[str]):
        """
        订阅股票列表
        
        Args:
            stock_list: 股票代码列表
        """
        if not self.qmt_manager.is_available():
            logger.error("❌ QMT不可用，无法订阅股票")
            return
        
        try:
            # 标准化股票代码
            normalized_stocks = [self.qmt_manager.normalize_code(code) for code in stock_list]
            
            # 订阅行情数据
            xtdata.subscribe_quote(normalized_stocks)
            
            # 更新内部订阅列表
            self.subscribed_stocks.update(normalized_stocks)
            
            logger.info(f"✅ 订阅 {len(normalized_stocks)} 只股票: {normalized_stocks[:5]}{'...' if len(normalized_stocks) > 5 else ''}")
            
        except Exception as e:
            logger.error(f"❌ 订阅股票失败: {e}")
    
    def unsubscribe_stocks(self, stock_list: List[str]):
        """
        取消订阅股票列表
        
        Args:
            stock_list: 股票代码列表
        """
        if not self.qmt_manager.is_available():
            logger.error("❌ QMT不可用，无法取消订阅股票")
            return
        
        try:
            # 标准化股票代码
            normalized_stocks = [self.qmt_manager.normalize_code(code) for code in stock_list]
            
            # 取消订阅行情数据
            xtdata.unsubscribe_quote(normalized_stocks)
            
            # 更新内部订阅列表
            for stock in normalized_stocks:
                self.subscribed_stocks.discard(stock)
            
            logger.info(f"✅ 取消订阅 {len(normalized_stocks)} 只股票")
            
        except Exception as e:
            logger.error(f"❌ 取消订阅股票失败: {e}")
    
    def start_processing(self):
        """开始处理实时Tick数据"""
        if self.running:
            logger.warning("⚠️ Tick处理器已在运行中")
            return
        
        if not self.qmt_manager.is_available():
            logger.error("❌ QMT不可用，无法开始处理")
            return
        
        self.running = True
        self._start_time = datetime.now()
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        logger.info("🚀 [实时Tick事件处理器] 开始处理")
    
    def stop_processing(self):
        """停止处理实时Tick数据"""
        self.running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)  # 等待最多2秒
        
        logger.info("🛑 [实时Tick事件处理器] 停止处理")
    
    def _processing_loop(self):
        """处理循环 - 运行在独立线程中"""
        logger.info("🧵 [Tick处理线程] 启动")
        
        while self.running:
            try:
                # 获取当前订阅的所有股票的Tick数据
                if self.subscribed_stocks:
                    tick_data = self.qmt_manager.get_full_tick(list(self.subscribed_stocks))
                    
                    if tick_data:
                        # 处理每个股票的Tick数据
                        for stock_code, stock_tick_data in tick_data.items():
                            if self.running:  # 检查是否需要停止
                                self._process_single_tick(stock_code, stock_tick_data)
                
                # 控制处理频率（避免过于频繁的API调用）
                time.sleep(0.1)  # 100ms间隔
                
            except Exception as e:
                logger.error(f"❌ [Tick处理循环] 发生错误: {e}")
                time.sleep(1.0)  # 出错时稍作延迟
        
        logger.info("🧵 [Tick处理线程] 退出")
    
    def _process_single_tick(self, stock_code: str, tick_data: Dict[str, Any]):
        """
        处理单个股票的Tick数据
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
        """
        try:
            # 更新处理计数
            self._total_ticks_processed += 1
            
            # 格式化Tick数据以适配UnifiedWarfareCore
            formatted_tick_data = self._format_tick_data(stock_code, tick_data)
            
            # 使用适配器处理Tick数据
            detected_events = self.adapter.process_tick(formatted_tick_data)
            
            # 更新事件计数
            self._total_events_detected += len(detected_events)
            
            # 如果检测到事件，放入事件队列（供外部消费）
            for event in detected_events:
                self.event_queue.put(event)
            
            # 记录处理统计（每1000次记录一次）
            if self._total_ticks_processed % 1000 == 0:
                logger.info(
                    f"📊 [Tick处理器] 处理统计 - "
                    f"Ticks: {self._total_ticks_processed}, "
                    f"Events: {self._total_events_detected}, "
                    f"Rate: {self._total_events_detected/max(1, self._total_ticks_processed)*1000:.2f}/1000"
                )
                
        except Exception as e:
            logger.error(f"❌ [Tick处理器] 处理 {stock_code} Tick数据失败: {e}")
    
    def _format_tick_data(self, stock_code: str, raw_tick_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化原始Tick数据以适配UnifiedWarfareCore
        
        Args:
            stock_code: 股票代码
            raw_tick_data: 原始Tick数据
            
        Returns:
            格式化后的Tick数据
        """
        try:
            # 提取基本tick信息
            current_time = datetime.now()
            price = raw_tick_data.get('lastPrice', 0)
            open_price = raw_tick_data.get('open', 0)
            high_price = raw_tick_data.get('high', 0)
            low_price = raw_tick_data.get('low', 0)
            prev_close = raw_tick_data.get('preClose', 0)
            volume = raw_tick_data.get('volume', 0)
            amount = raw_tick_data.get('amount', 0)
            ask_price = raw_tick_data.get('askPrice1', 0)
            bid_price = raw_tick_data.get('bidPrice1', 0)
            
            # 涨跌幅
            if prev_close > 0:
                change_pct = (price - prev_close) / prev_close * 100
            else:
                change_pct = 0
            
            # 构建格式化的tick数据
            formatted_data = {
                'stock_code': stock_code,
                'datetime': current_time,
                'price': price,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'prev_close': prev_close,
                'volume': volume,
                'amount': amount,
                'ask_price': ask_price,
                'bid_price': bid_price,
                'change_pct': change_pct,
                'is_limit_up': raw_tick_data.get('isST', False) or (change_pct >= 9.8),  # 涨停判断
                
                # 上下文信息（需要从其他地方获取或计算）
                'price_history': [],  # 从历史数据获取
                'volume_history': [],  # 从历史数据获取
                'ma5': 0,  # 从计算获取
                'ma20': 0,  # 从计算获取
                'rsi': 50,  # 从计算获取
                'avg_volume_5d': 0,  # 从历史数据获取
                'auction_volume_ratio': 0,  # 竞价量比
                'sector_data': {}  # 板块数据
            }
            
            # 为竞价时间的股票添加特殊处理
            current_hour = current_time.hour
            current_minute = current_time.minute
            
            # 如果是竞价时间，添加竞价相关数据
            if (current_hour == 9 and 25 <= current_minute <= 30) or (current_hour == 14 and current_minute == 57):
                # 计算竞价量比（简化的计算）
                if formatted_data['prev_close'] > 0:
                    formatted_data['auction_volume_ratio'] = volume / 1000000  # 简化计算
        
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ [Tick处理器] 格式化Tick数据失败: {e}")
            # 返回最小化的tick数据结构
            return {
                'stock_code': stock_code,
                'datetime': datetime.now(),
                'price': raw_tick_data.get('lastPrice', 0),
                'prev_close': raw_tick_data.get('preClose', 0),
                'volume': raw_tick_data.get('volume', 0),
                'amount': raw_tick_data.get('amount', 0)
            }
    
    def get_events(self, max_events: int = 100) -> List[Dict[str, Any]]:
        """
        获取积压的事件
        
        Args:
            max_events: 最大获取事件数
            
        Returns:
            事件列表
        """
        events = []
        count = 0
        
        while not self.event_queue.empty() and count < max_events:
            try:
                event = self.event_queue.get_nowait()
                events.append(event)
                count += 1
            except queue.Empty:
                break
        
        return events
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        if self._start_time:
            elapsed_time = (datetime.now() - self._start_time).total_seconds()
            ticks_per_second = self._total_ticks_processed / elapsed_time if elapsed_time > 0 else 0
        else:
            elapsed_time = 0
            ticks_per_second = 0
        
        warfare_stats = self.warfare_core.get_warfare_stats()
        
        stats = {
            '总处理Tick数': self._total_ticks_processed,
            '总检测事件数': self._total_events_detected,
            '事件检测率': f"{self._total_events_detected/max(1, self._total_ticks_processed)*100:.4f}%",
            '运行时长': f"{elapsed_time:.1f}秒",
            'Tick处理速度': f"{ticks_per_second:.2f} TPS",
            '待处理事件数': self.event_queue.qsize(),
            '订阅股票数': len(self.subscribed_stocks),
            '战法检测统计': warfare_stats
        }
        
        return stats
    
    def is_running(self) -> bool:
        """检查处理器是否正在运行"""
        return self.running


# ==================== 全局实例 ====================

_real_time_handler: Optional[RealTimeTickEventHandler] = None


def get_real_time_tick_handler() -> RealTimeTickEventHandler:
    """获取实时Tick事件处理器单例"""
    global _real_time_handler
    if _real_time_handler is None:
        _real_time_handler = RealTimeTickEventHandler()
    return _real_time_handler


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试RealTimeTickEventHandler
    print("=" * 80)
    print("实时Tick事件处理器测试")
    print("=" * 80)
    
    handler = get_real_time_tick_handler()
    
    print(f"\nQMT状态: {'✅ 可用' if handler.qmt_manager.is_available() else '❌ 不可用'}")
    print(f"支持战法数: {len(handler.warfare_core.get_active_detectors())}")
    
    if handler.qmt_manager.is_available():
        # 订阅一些测试股票
        test_stocks = ['000001.SZ', '600519.SH', '300750.SZ']  # 平安银行, 贵州茅台, 宁德时代
        
        print(f"\n准备订阅测试股票: {test_stocks}")
        handler.subscribe_stocks(test_stocks)
        
        print(f"\n开始处理Tick数据（5秒）...")
        handler.start_processing()
        
        # 运行5秒钟
        time.sleep(5)
        
        # 停止处理
        handler.stop_processing()
        
        # 获取统计信息
        stats = handler.get_processing_stats()
        print(f"\n处理统计:")
        for key, value in stats.items():
            if key != '战法检测统计':
                print(f"  {key}: {value}")
        
        # 获取检测到的事件
        events = handler.get_events()
        print(f"\n检测到 {len(events)} 个事件:")
        for i, event in enumerate(events, 1):
            print(f"  事件 {i}: {event['event_type']} - {event['stock_code']} - {event['description']}")
    
    else:
        print("\n⚠️ QMT不可用，跳过实时测试")
        print("但可以测试战法核心功能...")
        
        # 测试战法核心功能
        warfare_core = get_unified_warfare_core()
        
        # 模拟tick数据
        test_tick_data = {
            'stock_code': '300750',
            'datetime': datetime.now(),
            'price': 205.0,
            'prev_close': 200.0,
            'open': 201.0,
            'high': 206.0,
            'low': 200.5,
            'volume': 1200000,
            'amount': 246000000,
            'is_limit_up': False,
        }
        
        test_context = {
            'price_history': [200.1, 200.5, 201.0, 202.5, 203.0, 204.0, 205.0],
            'volume_history': [800000, 850000, 900000, 950000, 1000000, 1100000, 1200000],
            'ma5': 202.5,
            'ma20': 201.0,
            'rsi': 25,
            'avg_volume_5d': 900000,
            'auction_volume_ratio': 2.5,
            'sector_data': {
                'stocks': [
                    {'code': '300750', 'change_pct': 2.5},
                    {'code': '300015', 'change_pct': 1.8},
                ]
            }
        }
        
        events = warfare_core.process_tick(test_tick_data, test_context)
        
        print(f"\n战法核心测试 - 检测到 {len(events)} 个事件:")
        for event in events:
            print(f"  - {event['event_type']}: {event['description']} (置信度: {event['confidence']:.2f})")
    
    print("\n✅ 测试完成")
    print("=" * 80)
