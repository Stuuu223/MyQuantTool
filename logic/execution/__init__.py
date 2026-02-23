# -*- coding: utf-8 -*-
"""
执行模块 (Execution Module)

功能：
- 交易接口抽象层（模拟盘/实盘）
- 交易看门狗（风控检查）

主要导出：
- TradeInterface: 交易接口抽象基类
- SimulatedTrading: 模拟盘实现
- QMTTrading: QMT实盘实现（预留）
- TradeOrder: 交易订单数据类
- TradeResult: 交易结果数据类
- create_trader: 工厂函数

使用示例:
    >>> from logic.execution import create_trader, TradeOrder
    >>> 
    >>> # 创建模拟盘
    >>> trader = create_trader('simulated', initial_cash=20000.0)
    >>> trader.connect()
    >>> 
    >>> # 下单
    >>> order = TradeOrder('300986.SZ', 'BUY', 100, 13.42)
    >>> result = trader.buy(order)
"""

from logic.execution.trade_interface import (
    TradeInterface,
    SimulatedTrading,
    QMTTrading,
    TradeOrder,
    TradeResult,
    OrderValidator,
    OrderDirection,
    OrderType,
    OrderStatus,
    create_trader,
    quick_sim_trade,
)

from logic.execution.trade_gatekeeper import (
    TradeGatekeeper,
    check_buy_order,
    check_sell_order,
)

__all__ = [
    # 交易接口
    'TradeInterface',
    'SimulatedTrading',
    'QMTTrading',
    # 数据类
    'TradeOrder',
    'TradeResult',
    'OrderValidator',
    # 枚举
    'OrderDirection',
    'OrderType',
    'OrderStatus',
    # 函数
    'create_trader',
    'quick_sim_trade',
    'TradeGatekeeper',
    'check_buy_order',
    'check_sell_order',
]

__version__ = '1.0.0'
