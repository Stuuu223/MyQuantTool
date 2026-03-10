# -*- coding: utf-8 -*-
"""
执行模块 (Execution Module) - V66精简版

功能：
- 退出管理（止盈止损）

主要导出：
- ExitManager: 退出管理器（VWAP动态止盈止损）

注：交易执行相关代码已被移除，因为：
1. self.trader从未初始化
2. 交易接口代码永远不会被执行
3. 系统当前专注于打分和扫描
"""

from logic.execution.exit_manager import ExitManager

__all__ = [
    'ExitManager',
]

__version__ = '2.0.0'