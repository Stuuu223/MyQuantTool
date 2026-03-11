# -*- coding: utf-8 -*-
"""
执行模块 (Execution Module) - V70执行层重建版

功能：
- 微观盘口防线（TradeGatekeeper）
- L1虚拟交易所（MockExecutionManager）
- 退出管理（ExitManager）

主要导出：
- TradeGatekeeper: 微观盘口防线（涨跌停/盘口稀疏拦截）
- MockExecutionManager: L1虚拟交易所（资金状态机+摩擦力模型）
- ExitManager: 退出管理器（VWAP动态止盈止损）
"""

from logic.execution.trade_gatekeeper import TradeGatekeeper
from logic.execution.mock_execution_manager import MockExecutionManager
from logic.execution.exit_manager import ExitManager

__all__ = [
    'TradeGatekeeper',
    'MockExecutionManager',
    'ExitManager',
]

__version__ = '3.0.0'