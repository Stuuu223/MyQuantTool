# -*- coding: utf-8 -*-
import asyncio
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import time

# 获取logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging as log_mod
    logger = log_mod.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = log_mod.StreamHandler()
    handler.setFormatter(log_mod.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)


@dataclass
class TickEvent:
    """
    Tick事件数据类
    
    Attributes:
        stock_code: 股票代码
        price: 价格
        volume: 成交量
        amount: 成交额
        timestamp: 时间戳
        open: 开盘价
        high: 最高价
        low: 最低价
        prev_close: 昨收价
        data: 原始Tick字典（向后兼容）
    """
    stock_code: str
    price: float
    volume: int
    amount: float
    timestamp: str
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    prev_close: float = 0.0
    data: Dict = None  # 原始Tick字典，向后兼容


class AsyncEventBus:
    """
    异步事件总线 - 实现真正的事件驱动 (CTO加固版)
    
    CTO加固要点:
    - 内存爆炸防护: maxsize限制队列大小
    - 非阻塞投递: 使用put_nowait避免阻塞
    - 异常隔离: 单个处理器异常不影响其他处理器
    - 多线程消费: 使用线程池并发处理事件
    """
    
    def __init__(self, max_queue_size: int = 10000, max_workers: int = 10):
        """
        初始化事件总线
        
        Args:
            max_queue_size: 队列最大容量，防止内存爆炸
            max_workers: 最大工作线程数
        """
        self._tick_queue = queue.Queue(maxsize=max_queue_size)
        self._handlers: Dict[str, list] = {}
        self._running = False
        self._consumer_thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='EventBusWorker')
        
        # 统计信息
        self._stats = {
            'published': 0,
            'dropped': 0,
            'processed': 0,
            'start_time': time.time()
        }
        
        logger.info(f"[OK] [AsyncEventBus] 初始化完成 (max_queue_size: {max_queue_size}, workers: {max_workers})")
    
    def subscribe(self, event_type: str, handler: Callable):
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"[TARGET] 订阅事件: {event_type}, 处理器数: {len(self._handlers[event_type])}")
    
    def publish(self, event_type: str, data: Any) -> bool:
        """
        发布事件 (非阻塞)
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            bool: 是否成功发布 (False表示队列已满，事件被丢弃)
        """
        try:
            # 非阻塞添加到队列
            self._tick_queue.put_nowait((event_type, data))
            self._stats['published'] += 1
            return True
        except queue.Full:
            # 队列已满，丢弃事件 (CTO强制：不能阻塞)
            self._stats['dropped'] += 1
            logger.warning(f"[WARN] 队列满，事件丢弃: {event_type} (已丢弃: {self._stats['dropped']})")
            return False
    
    def start_consumer(self):
        """
        启动消费者线程 (CTO加固: 使用线程池并发处理)
        """
        if self._running:
            logger.warning("[WARN] 事件总线消费者已在运行")
            return
        
        def consumer():
            logger.info("🚀 事件总线消费者线程启动")
            self._running = True
            last_stats_time = time.time()
            
            while self._running:
                try:
                    # 非阻塞获取事件，超时避免死循环
                    event_type, data = self._tick_queue.get(timeout=0.1)
                    self._stats['processed'] += 1
                    
                    # 调用所有处理器 (CTO加固: 使用线程池并发执行)
                    if event_type in self._handlers:
                        for handler in self._handlers[event_type]:
                            # 提交到线程池并发执行，避免阻塞
                            self._executor.submit(self._safe_handler_call, handler, data)
                    
                    # 定期输出统计信息
                    current_time = time.time()
                    if current_time - last_stats_time > 10:  # 每10秒
                        self._print_stats()
                        last_stats_time = current_time
                        
                except queue.Empty:
                    # 队列为空，继续循环
                    continue
                except Exception as e:
                    logger.error(f"[X] 消费者线程异常: {e}")
                    time.sleep(0.1)  # 防止异常导致的死循环
            
            logger.info("[STOP] 事件总线消费者线程停止")
        
        self._consumer_thread = threading.Thread(target=consumer, daemon=True)
        self._consumer_thread.start()
        logger.info("[OK] 事件总线消费者已启动")
    
    def _safe_handler_call(self, handler: Callable, data: Any):
        """
        安全调用处理器 (异常隔离)
        
        Args:
            handler: 事件处理器
            data: 事件数据
        """
        try:
            handler(data)
        except Exception as e:
            logger.error(f"[X] 处理事件失败: {e}")
    
    def stop(self):
        """停止事件总线"""
        logger.info("[STOP] 停止事件总线...")
        self._running = False
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=2.0)  # 最多等待2秒
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
        
        logger.info("[OK] 事件总线已停止")
    
    def _print_stats(self):
        """打印统计信息"""
        elapsed = time.time() - self._stats['start_time']
        rate = self._stats['processed'] / elapsed if elapsed > 0 else 0
        logger.info(
            f"[STATS] 事件总线统计: 发布{self._stats['published']} | "
            f"处理{self._stats['processed']} | "
            f"丢弃{self._stats['dropped']} | "
            f"速率{rate:.1f}/s"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        current_time = time.time()
        elapsed = current_time - self._stats['start_time']
        return {
            **self._stats,
            'uptime': elapsed,
            'processing_rate': self._stats['processed'] / elapsed if elapsed > 0 else 0,
            'drop_rate': self._stats['dropped'] / self._stats['published'] if self._stats['published'] > 0 else 0
        }


# 便捷函数
def create_event_bus(max_queue_size: int = 10000, max_workers: int = 10) -> AsyncEventBus:
    """
    创建事件总线实例
    
    Args:
        max_queue_size: 队列最大容量
        max_workers: 最大工作线程数
        
    Returns:
        AsyncEventBus: 事件总线实例
    """
    return AsyncEventBus(max_queue_size=max_queue_size, max_workers=max_workers)


if __name__ == "__main__":
    # 测试异步事件总线
    print("[TEST] 异步事件总线测试 (CTO加固版)")
    print("=" * 50)
    
    # 创建事件总线
    event_bus = create_event_bus(max_queue_size=100, max_workers=5)
    
    # 定义处理器
    def price_handler(data):
        time.sleep(0.01)  # 模拟耗时操作
        if isinstance(data, TickEvent):
            print(f"[TRADE-BUY] 价格更新: {data.stock_code} -> {data.price}")
    
    def volume_handler(data):
        time.sleep(0.01)  # 模拟耗时操作
        if isinstance(data, TickEvent):
            if data.volume > 100000:
                print(f"[STATS] 大单监控: {data.stock_code} 量 {data.volume}")
    
    # 订阅事件
    event_bus.subscribe('tick', price_handler)
    event_bus.subscribe('tick', volume_handler)
    
    # 启动消费者
    event_bus.start_consumer()
    
    # 模拟发布事件
    import random
    test_stocks = ['300986.SZ', '002969.SZ', '603278.SH']
    
    print("🚀 开始发布测试事件...")
    for i in range(20):
        stock = random.choice(test_stocks)
        tick = TickEvent(
            stock_code=stock,
            price=10.0 + random.random() * 5,
            volume=random.randint(50000, 200000),
            amount=0,
            timestamp=datetime.now().strftime('%H:%M:%S')
        )
        
        success = event_bus.publish('tick', tick)
        if not success:
            print(f"[X] 事件发布失败: {tick.stock_code}")
        
        time.sleep(0.005)  # 快速发布事件
    
    # 等待处理完成
    time.sleep(3)
    
    # 打印统计
    stats = event_bus.get_stats()
    print(f"\n[TREND] 最终统计: {stats}")
    
    # 停止事件总线
    event_bus.stop()
    print("\n[OK] 测试完成")