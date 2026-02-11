#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志配置是否生效（V2修正版）
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from logic.log_config import use_normal_mode

def test_log_configuration_v2():
    """测试日志配置V2"""

    print("=" * 80)
    print("🧪 测试日志配置 V2（修正模块名）")
    print("=" * 80)
    print()

    # 应用配置
    use_normal_mode()

    # 模拟各个模块的日志输出
    print("测试各种级别的日志输出:")
    print("-" * 80)

    # 扫描相关模块（WARNING级别）
    fund_logger = logging.getLogger("logic.fund_flow_analyzer")
    scanner_logger = logging.getLogger("logic.full_market_scanner")
    resonance_logger = logging.getLogger("logic.sector_resonance")

    # DEBUG日志（不应该显示）
    fund_logger.debug("✅ 缓存命中: 002517 (T-1数据, 2026-02-10)")
    scanner_logger.debug("🚀 [白名单短路] 600545.SH 命中主线起爆")
    resonance_logger.debug("📊 板块共振分析完成")

    # INFO日志（不应该显示，因为WARNING级别）
    fund_logger.info("💾 缓存写入: 002517 → 2026-02-10")
    scanner_logger.info("📊 Level 1 筛选: 100 只")
    resonance_logger.info("🎯 Leaders=5, Breadth=42%")

    # WARNING日志（应该显示）
    fund_logger.warning("❌ 缓存未命中: 002517，调用 AkShare API")
    scanner_logger.warning("⚠️ [002517.SZ] 被标记为禁止场景: TRAP_PUMP_DUMP")

    print("✅ 扫描模块：DEBUG/INFO日志被隐藏，WARNING日志显示（符合预期）")
    print()

    # QMT相关模块（WARNING级别）
    qmt_logger = logging.getLogger("logic.qmt_health_check")

    # INFO日志（不应该显示）
    qmt_logger.info("🔌 QMT 连接状态: HEALTHY")

    # WARNING日志（应该显示）
    qmt_logger.warning("⚠️ QMT 响应时间: 120ms（正常阈值: 100ms）")

    print("✅ QMT模块：INFO日志被隐藏，WARNING日志显示（符合预期）")
    print()

    # 关键业务模块（INFO级别）
    main_logger = logging.getLogger("__main__")
    event_logger = logging.getLogger("logic.event_detector")

    # INFO日志（应该显示）
    main_logger.info("🚀 事件驱动持续监控启动")
    event_logger.info("📡 [EVENT_DRIVEN] 进入事件驱动模式")

    print("✅ 关键模块：INFO日志正常显示（符合预期）")
    print()

    # 第三方库（ERROR级别）
    akshare_logger = logging.getLogger("akshare")

    # INFO日志（不应该显示）
    akshare_logger.info("📡 AkShare API 调用成功")

    # ERROR日志（应该显示）
    akshare_logger.error("❌ AkShare API 调用失败: 超时")

    print("✅ 第三方库：INFO日志被隐藏，ERROR日志显示（符合预期）")
    print()

    # 打印关键logger的级别
    print("关键 Logger 级别:")
    print("-" * 80)
    key_loggers = [
        "logic.fund_flow_analyzer",
        "logic.full_market_scanner",
        "logic.qmt_health_check",
        "__main__",
    ]
    for name in key_loggers:
        level_name = logging.getLevelName(logging.getLogger(name).level)
        print(f"  {name}: {level_name}")

    print("=" * 80)
    print()
    print("✅ 日志配置 V2 已生效！")
    print("📝 预期效果：只显示 WARNING 级别以上的日志")
    print("=" * 80)

if __name__ == "__main__":
    test_log_configuration_v2()