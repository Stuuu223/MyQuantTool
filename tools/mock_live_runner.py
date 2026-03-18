#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[DEPRECATED in V213] 架构脑裂产物，已废除

此文件已于 2026-03-18 被 CTO V213 大一统架构废除。
所有 Mock 逻辑已整合至主引擎 LiveTradingEngine (tasks/run_live_trading_engine.py)。

迁移路径：
  - StockStateBuffer  → logic/execution/stock_state_buffer.py
  - TickAdapter       → logic/data_providers/tick_adapters.py (MockTickAdapter)
  - 决策逻辑           → logic/execution/trade_decision_brain.py
  - 全榜追踪           → logic/execution/universal_tracker.py

使用新架构：
    # Live模式（实盘）
    python main.py live
    
    # Scan模式（沙盘回测）- 使用主引擎+MockTickAdapter
    python main.py scan --date 20260310

原功能说明（已废弃）：
    python tools/mock_live_runner.py --date 20260310  # 已失效，请使用 main.py scan

CTO签名：架构大一统，拒绝双轨制。
"""
raise DeprecationWarning(
    "[V213] mock_live_runner.py 已废除！\n"
    "请使用新架构：\n"
    "  python main.py scan --date YYYYMMDD\n"
    "详见：docs/architecture/RADAR_STATE_MACHINE_DESIGN.md"
)