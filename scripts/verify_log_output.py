#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证日志配置是否生效 - 模拟实际扫描过程
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from logic.log_config import use_normal_mode

def simulate_scan_process():
    """模拟实际的扫描过程"""

    print("=" * 80)
    print("🧪 模拟实际扫描过程")
    print("=" * 80)
    print()

    # 应用日志配置
    use_normal_mode()

    # 获取各个模块的logger
    scanner_logger = logging.getLogger("logic.full_market_scanner")
    fund_logger = logging.getLogger("logic.fund_flow_analyzer")
    resonance_logger = logging.getLogger("logic.sector_resonance")
    qmt_logger = logging.getLogger("logic.qmt_health_check")
    main_logger = logging.getLogger("__main__")

    print("模拟扫描过程...")
    print("-" * 80)

    # 模拟主程序启动
    main_logger.info("🚀 事件驱动持续监控启动")
    main_logger.info("📡 [EVENT_DRIVEN] 进入事件驱动模式")

    # 模拟资金流分析（这些DEBUG/INFO日志应该被隐藏）
    fund_logger.debug("✅ 缓存命中: 002517 (T-1数据, 2026-02-10)")
    fund_logger.info("💾 缓存写入: 002517 → 2026-02-10")
    fund_logger.warning("❌ 缓存未命中: 002517，调用 AkShare API")

    # 模拟全市场扫描（这些INFO日志应该被隐藏）
    scanner_logger.debug("📊 开始Level 1筛选...")
    scanner_logger.info("🚀 [白名单短路] 600545.SH 命中主线起爆，跳过风险判定")
    scanner_logger.info("🚀 [白名单短路] 600299.SH 命中主线起爆，跳过风险判定")
    scanner_logger.info("⏸️ 降级观察池: 300364.SZ risk=0.20")
    scanner_logger.info("⏸️ 降级观察池: 600418.SH risk=0.20")
    scanner_logger.info("✅ Level 3 完成 (耗时: 0.0秒)")
    scanner_logger.warning("⚠️ [002517.SZ] 被标记为禁止场景: TRAP_PUMP_DUMP")

    # 模拟板块共振分析
    resonance_logger.info("🎯 Leaders=5, Breadth=42%")
    resonance_logger.warning("⚠️ 板块共振不足: Leaders=2, Breadth=28%")

    # 模拟QMT健康检查
    qmt_logger.info("🔌 QMT 连接状态: HEALTHY")
    qmt_logger.warning("⚠️ QMT 响应时间: 120ms（正常阈值: 100ms）")

    # 模拟扫描完成
    main_logger.info("================================================================================")
    main_logger.info("📊 扫描完成 #0 - 11:30:05")
    main_logger.info("================================================================================")
    main_logger.info("✅ 机会池（最终）: 12 只")
    main_logger.info("⚠️  观察池（含降级）: 41 只")

    print("-" * 80)
    print()
    print("📝 预期结果：")
    print("  ✅ 主程序INFO日志：显示")
    print("  ✅ 扫描模块INFO日志：隐藏")
    print("  ✅ 扫描模块WARNING日志：显示")
    print("  ✅ QMT INFO日志：隐藏")
    print("  ✅ QMT WARNING日志：显示")
    print()
    print("=" * 80)
    print("✅ 验证完成！")
    print("=" * 80)

if __name__ == "__main__":
    simulate_scan_process()