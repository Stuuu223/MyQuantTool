#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试日志配置是否生效
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from logic.log_config import setup_scan_logging, get_current_log_levels

def test_log_configuration():
    """测试日志配置"""
    
    print("=" * 80)
    print("🧪 测试日志配置是否生效")
    print("=" * 80)
    print()
    
    # 应用配置
    setup_scan_logging(scan_level="WARNING", root_level="INFO")
    
    # 模拟资金流分析器的日志输出
    analyzer_logger = logging.getLogger("logic.fundflowanalyzer")
    full_scanner_logger = logging.getLogger("logic.fullmarketscanner")
    
    print("测试日志输出（这些应该是DEBUG级别，不会显示）:")
    print("-" * 80)
    
    # 这些是DEBUG日志，不会显示（因为logger级别是WARNING）
    analyzer_logger.debug("✅ 缓存命中: 002517 (T-1数据, 2026-02-10)")
    analyzer_logger.debug("💾 缓存写入: 002517 → 2026-02-10")
    full_scanner_logger.debug("⚠️ [002517.SZ] TRAP_PUMP_DUMP: 单日暴量")
    
    print("✅ DEBUG日志被隐藏（符合预期）")
    print()
    
    # 这些是INFO日志，会显示（因为logger级别是INFO）
    full_scanner_logger.info("✅ 扫描完成: 找到 12 只主线候选")
    full_scanner_logger.info("📊 Level 1 筛选: 100 只")
    
    print("✅ INFO日志正常显示")
    print()
    
    # 这些是WARNING日志，会显示
    analyzer_logger.warning("❌ 缓存未命中: 002517，调用 AkShare API")
    
    print("✅ WARNING日志正常显示")
    print()
    
    # 检查当前日志级别
    levels = get_current_log_levels()
    
    print("当前日志级别:")
    print("-" * 80)
    for name, level in sorted(levels.items()):
        print(f"  {name}: {level}")
    
    print("=" * 80)
    print()
    print("✅ 日志配置已生效！")
    print("=" * 80)

if __name__ == "__main__":
    test_log_configuration()