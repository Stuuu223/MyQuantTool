#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实际的日志输出
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from logic.logger import get_logger
from logic.log_config import use_normal_mode

def test_actual_output():
    """测试实际的日志输出"""

    print("=" * 80)
    print("🧪 测试实际日志输出")
    print("=" * 80)
    print()

    # 应用日志配置
    use_normal_mode()

    # 使用实际的get_logger
    monitor_logger = get_logger("tasks.run_event_driven_monitor")
    scanner_logger = get_logger("logic.full_market_scanner")
    fund_logger = get_logger("logic.fund_flow_analyzer")

    print("测试日志输出:")
    print("-" * 80)

    # 模拟监控器启动
    monitor_logger.info("🚀 事件驱动持续监控启动")
    monitor_logger.info("📡 [EVENT_DRIVEN] 进入事件驱动模式")

    # 模拟扫描过程
    scanner_logger.info("📊 Level 1 筛选: 100 只")
    scanner_logger.info("🚀 [白名单短路] 600545.SH 命中主线起爆")
    scanner_logger.warning("⚠️ [002517.SZ] 被标记为禁止场景: TRAP_PUMP_DUMP")

    # 模拟资金流分析
    fund_logger.info("💾 缓存写入: 002517 → 2026-02-10")
    fund_logger.warning("❌ 缓存未命中: 002517，调用 AkShare API")

    # 模拟扫描完成
    monitor_logger.info("=" * 80)
    monitor_logger.info("📊 扫描完成 #0 - 11:30:05")
    monitor_logger.info("=" * 80)
    monitor_logger.info("✅ 机会池（最终）: 12 只")
    monitor_logger.info("⚠️  观察池（含降级）: 41 只")

    print("-" * 80)
    print()
    print("✅ 测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    test_actual_output()