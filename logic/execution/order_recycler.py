#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废单回收机 - Order Recycler

功能: 定时检查未成交订单,超时自动撤单释放资金
CTO规范: 小资金效率极致化,资金必须时刻保持"可击发"状态

Author: AI总监 (CTO排雷版)
Date: 2026-02-24
Version: 1.0.0
"""

import time
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class PendingOrder:
    """待处理订单"""
    order_id: str
    stock_code: str
    order_type: str  # 'buy' or 'sell'
    price: float
    quantity: int
    submit_time: datetime
    status: str = 'pending'  # pending, filled, cancelled, expired
    
    def age_seconds(self) -> float:
        """订单已存在秒数"""
        return (datetime.now() - self.submit_time).total_seconds()


class OrderRecycler:
    """
    废单回收机
    
    职责:
    1. 跟踪所有未成交订单
    2. 定时检查订单状态
    3. 超时限订单自动撤单
    4. 释放资金,保持流动性
    
    使用方式:
    - 实盘主循环中每3秒调用一次check_and_recycle()
    - 或启动独立后台线程持续监控
    """
    
    def __init__(self, timeout_seconds: int = 5, check_interval: float = 3.0):
        """
        初始化废单回收机
        
        Args:
            timeout_seconds: 订单超时时间(秒),默认5秒
            check_interval: 检查间隔(秒),默认3秒
        """
        self.timeout_seconds = timeout_seconds
        self.check_interval = check_interval
        
        # 订单跟踪字典
        self._pending_orders: Dict[str, PendingOrder] = {}
        
        # 统计数据
        self._stats = {
            'total_submitted': 0,
            'total_filled': 0,
            'total_cancelled': 0,
            'total_expired': 0,
            'freed_capital': 0.0
        }
        
        # 后台线程控制
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        logger.info(f"✅ [OrderRecycler] 初始化完成,超时={timeout_seconds}s,检查间隔={check_interval}s")
    
    def submit_order(self, order_id: str, stock_code: str, order_type: str, 
                     price: float, quantity: int) -> None:
        """
        提交新订单到监控队列
        
        Args:
            order_id: 订单ID
            stock_code: 股票代码
            order_type: 'buy' or 'sell'
            price: 价格
            quantity: 数量
        """
        order = PendingOrder(
            order_id=order_id,
            stock_code=stock_code,
            order_type=order_type,
            price=price,
            quantity=quantity,
            submit_time=datetime.now()
        )
        
        self._pending_orders[order_id] = order
        self._stats['total_submitted'] += 1
        
        logger.info(f"📤 [OrderRecycler] 新订单加入监控: {order_id} {stock_code} "
                   f"{order_type} {quantity}股 @ {price}")
    
    def mark_filled(self, order_id: str) -> None:
        """标记订单已成交"""
        if order_id in self._pending_orders:
            order = self._pending_orders[order_id]
            order.status = 'filled'
            self._stats['total_filled'] += 1
            
            # 从监控队列移除
            del self._pending_orders[order_id]
            
            logger.info(f"✅ [OrderRecycler] 订单成交: {order_id} {order.stock_code}")
    
    def check_and_recycle(self) -> List[PendingOrder]:
        """
        检查并回收废单
        
        Returns:
            List[PendingOrder]: 被回收的订单列表
        """
        now = datetime.now()
        recycled_orders = []
        
        for order_id, order in list(self._pending_orders.items()):
            if order.status != 'pending':
                continue
            
            age = order.age_seconds()
            
            if age > self.timeout_seconds:
                # 订单超时,执行撤单
                logger.warning(f"🚨 [OrderRecycler] 订单超时 {age:.1f}s > {self.timeout_seconds}s: "
                              f"{order_id} {order.stock_code}")
                
                # 调用撤单接口
                if self._cancel_order(order):
                    order.status = 'cancelled'
                    recycled_orders.append(order)
                    self._stats['total_cancelled'] += 1
                    self._stats['freed_capital'] += order.price * order.quantity
                    
                    # 从监控队列移除
                    del self._pending_orders[order_id]
                    
                    logger.info(f"♻️ [OrderRecycler] 废单回收成功: {order_id}, "
                               f"释放资金 {order.price * order.quantity:.2f}")
                else:
                    # 撤单失败,标记为过期
                    order.status = 'expired'
                    self._stats['total_expired'] += 1
                    logger.error(f"❌ [OrderRecycler] 撤单失败: {order_id}")
        
        if recycled_orders:
            logger.info(f"📊 [OrderRecycler] 本次回收 {len(recycled_orders)} 单, "
                       f"累计释放资金 {self._stats['freed_capital']:.2f}")
        
        return recycled_orders
    
    def _cancel_order(self, order: PendingOrder) -> bool:
        """
        执行撤单操作
        
        Args:
            order: 待撤订单
            
        Returns:
            bool: 撤单是否成功
        """
        try:
            # TODO: 接入真实QMT撤单接口
            # from xtquant import xttrader
            # xttrader.cancel_order(order.order_id)
            
            # 当前为模拟实现
            logger.debug(f"调用撤单接口: {order.order_id}")
            return True
            
        except Exception as e:
            logger.error(f"撤单异常: {e}")
            return False
    
    def get_pending_count(self) -> int:
        """获取当前待处理订单数量"""
        return len([o for o in self._pending_orders.values() if o.status == 'pending'])
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'pending_count': self.get_pending_count(),
            'total_submitted': self._stats['total_submitted'],
            'total_filled': self._stats['total_filled'],
            'total_cancelled': self._stats['total_cancelled'],
            'total_expired': self._stats['total_expired'],
            'freed_capital': self._stats['freed_capital'],
            'timeout_seconds': self.timeout_seconds,
            'check_interval': self.check_interval
        }
    
    def start_monitor(self):
        """启动后台监控线程"""
        if self._running:
            logger.warning("[OrderRecycler] 监控线程已在运行")
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("🚀 [OrderRecycler] 后台监控线程已启动")
    
    def stop_monitor(self):
        """停止后台监控线程"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("🛑 [OrderRecycler] 后台监控线程已停止")
    
    def _monitor_loop(self):
        """后台监控循环"""
        while self._running:
            try:
                self.check_and_recycle()
            except Exception as e:
                logger.error(f"[OrderRecycler] 监控异常: {e}")
            
            time.sleep(self.check_interval)


# 全局实例
_recycler_instance: Optional[OrderRecycler] = None


def get_order_recycler(timeout_seconds: int = 5) -> OrderRecycler:
    """获取废单回收机单例"""
    global _recycler_instance
    if _recycler_instance is None:
        _recycler_instance = OrderRecycler(timeout_seconds=timeout_seconds)
    return _recycler_instance


if __name__ == "__main__":
    # 测试废单回收机
    print("🧪 废单回收机测试")
    print("=" * 50)
    
    recycler = OrderRecycler(timeout_seconds=3, check_interval=1)
    
    # 提交测试订单
    recycler.submit_order("ORDER001", "000001.SZ", "buy", 10.5, 1000)
    recycler.submit_order("ORDER002", "000002.SZ", "buy", 20.0, 2000)
    
    print(f"\n待处理订单: {recycler.get_pending_count()}")
    
    # 模拟订单成交
    recycler.mark_filled("ORDER001")
    print(f"成交后待处理: {recycler.get_pending_count()}")
    
    # 等待ORDER002超时
    print("\n等待ORDER002超时...")
    import time
    time.sleep(4)
    
    # 手动触发检查
    recycled = recycler.check_and_recycle()
    print(f"\n回收订单数: {len(recycled)}")
    
    # 统计
    stats = recycler.get_stats()
    print(f"\n统计: {stats}")
    
    print("\n✅ 测试完成")
