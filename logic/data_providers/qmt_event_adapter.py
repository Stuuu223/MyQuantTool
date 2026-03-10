#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT事件适配器 - 底层通讯层剥离

【架构解耦核心组件】
将主引擎(run_live_trading_engine.py)中的QMT脏活剥离至此：
- QMT Tick订阅与回调管理
- 原始数据格式转换(TickEvent标准化)
- 批量订阅性能优化

【设计原则】
1. 单一职责: 只处理QMT通讯，不做业务决策
2. 适配器模式: 将QMT原生数据转为系统标准事件
3. 依赖注入: 通过event_bus发布事件，不直接调用引擎

Author: 架构解耦工程
Date: 2026-02-26
Version: 1.0.0
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class QMTEventAdapter:
    """
    QMT事件适配器 - 封装所有与QMT的交互细节
    
    职责:
    1. 管理QMT Tick订阅/取消订阅
    2. 将QMT原始数据转换为标准TickEvent字典
    3. 通过event_bus发布标准化事件
    """
    
    def __init__(self, event_bus=None):
        """
        初始化适配器
        
        Args:
            event_bus: 事件总线实例，用于发布标准化事件
        """
        self.event_bus = event_bus
        self._subscribed_stocks = set()
        self._tick_count = 0
        self._is_initialized = False
        self._xtdata = None
        
    def initialize(self) -> bool:
        """
        初始化QMT连接
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            from xtquant import xtdata
            self._xtdata = xtdata
            self._is_initialized = True
            logger.info("✅ [QMTEventAdapter] QMT连接初始化成功")
            return True
        except ImportError:
            logger.error("❌ [QMTEventAdapter] 无法导入xtquant模块")
            return False
        except Exception as e:
            logger.error(f"❌ [QMTEventAdapter] QMT初始化失败: {e}")
            return False
    
    def subscribe_ticks(self, stock_list: List[str]) -> int:
        """
        订阅股票Tick数据
        
        【CTO强制规范】
        - 必须逐一订阅，不能批量
        - 记录成功/失败数量
        - 失败不中断，继续订阅其他
        
        Args:
            stock_list: 股票代码列表
            
        Returns:
            int: 成功订阅的数量
        """
        if not self._is_initialized:
            logger.error("❌ [QMTEventAdapter] 未初始化，无法订阅")
            return 0
            
        if not stock_list:
            logger.warning("⚠️ [QMTEventAdapter] 股票列表为空，跳过订阅")
            return 0
            
        # 过滤已订阅的股票
        new_stocks = [s for s in stock_list if s not in self._subscribed_stocks]
        if not new_stocks:
            logger.info("📊 [QMTEventAdapter] 所有股票已订阅，无需重复")
            return 0
            
        logger.info(f"📊 [QMTEventAdapter] 开始订阅 {len(new_stocks)} 只股票Tick数据...")
        
        subscribed_count = 0
        for code in new_stocks:
            try:
                self._xtdata.subscribe_quote(
                    stock_code=code,
                    period='tick',
                    count=-1,
                    callback=self._qmt_tick_callback
                )
                self._subscribed_stocks.add(code)
                subscribed_count += 1
            except Exception as e:
                logger.warning(f"⚠️ [QMTEventAdapter] 订阅 {code} 失败: {e}")
                
        logger.info(f"✅ [QMTEventAdapter] Tick订阅完成: {subscribed_count}/{len(new_stocks)} 只")
        return subscribed_count
    
    def unsubscribe_all(self):
        """取消所有订阅"""
        # 注意: xtdata没有直接的取消订阅API，此处作为占位
        logger.info(f"📊 [QMTEventAdapter] 已订阅股票数: {len(self._subscribed_stocks)}")
        self._subscribed_stocks.clear()
    
    def _qmt_tick_callback(self, datas: Dict):
        """
        QMT Tick回调函数 - 核心转换逻辑
        
        将QMT推送的原始数据转换为标准TickEvent字典，
        并通过event_bus发布
        
        Args:
            datas: QMT原始数据字典 {stock_code: tick_list}
        """
        if not datas:
            return
            
        try:
            for stock_code, tick_list in datas.items():
                if not tick_list:
                    continue
                    
                # tick_list是列表，取最新的tick
                latest_tick = tick_list[-1] if isinstance(tick_list, list) else tick_list
                
                # 【标准化转换】将QMT原始字段转为系统标准字段
                tick_event = self._convert_to_standard_tick(stock_code, latest_tick)
                
                # 发布到事件总线
                if self.event_bus:
                    self._publish_tick_event(tick_event)
                    
                # 计数日志(每100次输出一次)
                self._tick_count += 1
                if self._tick_count % 100 == 0:
                    logger.info(f"📊 [QMTEventAdapter] 累计处理Tick: {self._tick_count} 条")
                    
        except Exception as e:
            logger.error(f"❌ [QMTEventAdapter] Tick回调处理失败: {e}")
    
    def _convert_to_standard_tick(self, stock_code: str, raw_tick: Dict) -> Dict[str, Any]:
        """
        将QMT原始Tick数据转换为标准格式
        
        【字段映射表】
        QMT字段 -> 标准字段
        - lastPrice -> price
        - volume -> volume
        - amount -> amount
        - open -> open
        - high -> high
        - low -> low
        - lastClose -> prev_close
        - time -> timestamp
        
        Args:
            stock_code: 股票代码
            raw_tick: QMT原始tick数据
            
        Returns:
            Dict: 标准化的tick事件字典
        """
        return {
            'stock_code': stock_code,
            'price': float(raw_tick.get('lastPrice', 0)),
            'volume': int(raw_tick.get('volume', 0)),
            'amount': float(raw_tick.get('amount', 0)),
            'open': float(raw_tick.get('open', 0)),
            'high': float(raw_tick.get('high', 0)),
            'low': float(raw_tick.get('low', 0)),
            'prev_close': float(raw_tick.get('lastClose', 0)),  # 修复：lastClose而非preClose
            'timestamp': str(raw_tick.get('time', '')),
            'data': raw_tick  # 【CTO修复】保留原始数据字典，向后兼容
        }
    
    def _publish_tick_event(self, tick_event: Dict):
        """
        发布Tick事件到事件总线
        
        Args:
            tick_event: 标准化的tick事件字典
        """
        try:
            from logic.data_providers.event_bus import TickEvent
            
            # 创建TickEvent对象并发布
            event_obj = TickEvent(**tick_event)
            self.event_bus.publish('tick', event_obj)
            
        except TypeError as te:
            logger.error(f"❌ [QMTEventAdapter] TickEvent字段不匹配: {te}")
            logger.debug(f"   传入字段: {list(tick_event.keys())}")
        except Exception as e:
            logger.error(f"❌ [QMTEventAdapter] TickEvent创建失败: {e}")
    
    def get_full_tick_snapshot(self, stock_list: List[str]) -> Dict[str, Dict]:
        """
        获取全量Tick快照
        
        【性能优化】
        分批获取避免超时，每批最多500只
        
        Args:
            stock_list: 股票代码列表
            
        Returns:
            Dict: {stock_code: tick_data}
        """
        if not self._is_initialized:
            logger.error("❌ [QMTEventAdapter] 未初始化，无法获取快照")
            return {}
            
        if not stock_list:
            return {}
            
        result = {}
        batch_size = 500
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            try:
                snapshot = self._xtdata.get_full_tick(batch)
                if snapshot:
                    result.update(snapshot)
            except Exception as e:
                logger.warning(f"⚠️ [QMTEventAdapter] 获取快照批次失败({i}-{i+batch_size}): {e}")
                
        logger.info(f"✅ [QMTEventAdapter] 获取快照完成: {len(result)}/{len(stock_list)} 只")
        return result
    
    def get_all_a_shares(self) -> List[str]:
        """
        获取全市场A股列表
        
        Returns:
            List[str]: 沪深A股代码列表
        """
        if not self._is_initialized:
            logger.error("❌ [QMTEventAdapter] 未初始化，无法获取股票列表")
            return []
            
        try:
            stocks = self._xtdata.get_stock_list_in_sector('沪深A股')
            logger.info(f"✅ [QMTEventAdapter] 获取全市场股票: {len(stocks)} 只")
            return stocks
        except Exception as e:
            logger.error(f"❌ [QMTEventAdapter] 获取股票列表失败: {e}")
            return []


# =============================================================================
# 快捷函数 - 供主引擎直接调用
# =============================================================================

def create_qmt_adapter(event_bus=None) -> QMTEventAdapter:
    """
    工厂函数: 创建并初始化QMT适配器
    
    Args:
        event_bus: 事件总线实例
        
    Returns:
        QMTEventAdapter: 初始化好的适配器实例
    """
    adapter = QMTEventAdapter(event_bus)
    if adapter.initialize():
        return adapter
    else:
        raise RuntimeError("QMTEventAdapter初始化失败，无法继续")
