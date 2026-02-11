#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证日志配置是否生效 - 使用实际的模块名
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from logic.log_config import use_normal_mode

def simulate_actual_monitor():
    """模拟实际的监控器"""

    print("=" * 80)
    print("🧪 模拟实际监控器（使用实际的模块名）")
    print("=" * 80)
    print()

    # 应用日志配置
    use_normal_mode()

    # 使用实际的模块名
    monitor_logger = logging.getLogger("tasks.run_event_driven_monitor")
    scanner_logger = logging.getLogger("logic.full_market_scanner")
    fund_logger = logging.getLogger("logic.fund_flow_analyzer")
    qmt_logger = logging.getLogger("logic.qmt_health_check")

    print("模拟监控过程...")
    print("-" * 80)

    # 模拟监控器启动（这些INFO日志应该显示）
    monitor_logger.info("🚀 事件驱动持续监控启动")
    monitor_logger.info("📅 启动时间: 2026-02-11 11:30:00")
    monitor_logger.info("🎯 运行模式: 自动策略切换")
    monitor_logger.info("🔌 QMT 状态: HEALTHY")
    monitor_logger.info("")
    monitor_logger.info("📡 [EVENT_DRIVEN] 进入事件驱动模式")
    monitor_logger.info("   候选池: 100 只")
    monitor_logger.info("   开始深度扫描...")

    # 模拟扫描过程（这些INFO日志应该被隐藏）
    scanner_logger.info("📊 Level 1 筛选: 100 只")
    scanner_logger.info("🚀 [白名单短路] 600545.SH 命中主线起爆")
    scanner_logger.info("⏸️ 降级观察池: 300364.SZ risk=0.20")
    scanner_logger.warning("⚠️ [002517.SZ] 被标记为禁止场景: TRAP_PUMP_DUMP")

    # 模拟资金流分析（这些INFO日志应该被隐藏）
    fund_logger.info("💾 缓存写入: 002517 → 2026-02-10")
    fund_logger.warning("❌ 缓存未命中: 002517，调用 AkShare API")

    # 模拟QMT健康检查（这些INFO日志应该被隐藏）
    qmt_logger.info("🔌 QMT 连接状态: HEALTHY")
    qmt_logger.warning("⚠️ QMT 响应时间: 120ms（正常阈值: 100ms）")

    # 模拟扫描完成（这些INFO日志应该显示）
    monitor_logger.info("")
    monitor_logger.info("=" * 80)
    monitor_logger.info("📊 扫描完成 #0 - 11:30:05")
    monitor_logger.info("=" * 80)
    monitor_logger.info("✅ 机会池（最终）: 12 只")
    monitor_logger.info("⚠️  观察池（含降级）: 41 只")
    monitor_logger.info("")
    monitor_logger.info("【低风险机会池】（风险≤0.2，12 只）")
    monitor_logger.info("==================================================")
    monitor_logger.info("代码       名称        价格   涨跌幅   ...")
    monitor_logger.info("002517.SZ  恺英网络    10.52   5.20    ...")
    monitor_logger.info("600482.SH  中国动力    15.83   4.37    ...")
    monitor_logger.info("")
    monitor_logger.info("   等待 30 秒后重新检测...")

    print("-" * 80)
    print()
    print("📝 预期结果：")
    print("  ✅ 监控器INFO日志：显示")
    print("  ✅ 扫描模块INFO日志：隐藏")
    print("  ✅ 扫描模块WARNING日志：显示")
    print("  ✅ QMT INFO日志：隐藏")
    print("  ✅ QMT WARNING日志：显示")
    print()
    print("=" * 80)
    print("✅ 验证完成！")
    print("=" * 80)

if __name__ == "__main__":
    simulate_actual_monitor()