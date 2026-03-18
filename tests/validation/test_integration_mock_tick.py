#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[DEPRECATED in V213] 集成测试已废弃

此测试文件依赖已废除的 mock_live_runner.py。
V213 大一统架构后，Mock 测试应使用主引擎 + MockTickAdapter。

新架构测试方法：
    # 使用主引擎进行沙盘测试
    python main.py scan --date 20260310

    # 或直接测试 LiveTradingEngine
    from tasks.run_live_trading_engine import LiveTradingEngine
    engine = LiveTradingEngine(mode='scan', target_date='20260310')

迁移说明：
    - MockLiveRunner 已被 LiveTradingEngine(mode='scan') 替代
    - StockStateBuffer 已迁移至 logic/execution/stock_state_buffer.py
    - TickAdapter 架构见 logic/data_providers/tick_adapters.py

CTO签名：V213 大一统，拒绝双轨制测试。
"""

def run_integration_test():
    """已废弃 - 请使用 main.py scan 模式"""
    print("[DEPRECATED] 此测试已废弃")
    print("请使用: python main.py scan --date YYYYMMDD")
    raise DeprecationWarning(
        "test_integration_mock_tick.py 已废弃\n"
        "请使用 main.py scan 模式进行沙盘测试"
    )


if __name__ == '__main__':
    run_integration_test()