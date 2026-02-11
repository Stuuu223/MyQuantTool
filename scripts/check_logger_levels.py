#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查logger级别
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from logic.log_config import use_normal_mode

def check_logger_levels():
    """检查各个logger的级别"""

    print("=" * 80)
    print("🔍 检查Logger级别")
    print("=" * 80)
    print()

    # 应用日志配置
    use_normal_mode()

    # 检查各个logger的级别
    loggers = [
        ("root", logging.getLogger()),
        ("tasks.run_event_driven_monitor", logging.getLogger("tasks.run_event_driven_monitor")),
        ("logic.full_market_scanner", logging.getLogger("logic.full_market_scanner")),
        ("logic.fund_flow_analyzer", logging.getLogger("logic.fund_flow_analyzer")),
        ("logic.qmt_health_check", logging.getLogger("logic.qmt_health_check")),
        ("__main__", logging.getLogger("__main__")),
    ]

    print("Logger级别:")
    print("-" * 80)
    for name, logger in loggers:
        level_num = logger.level
        level_name = logging.getLevelName(level_num)
        effective_level = logging.getLevelName(logger.getEffectiveLevel())
        print(f"  {name}")
        print(f"    级别: {level_name} ({level_num})")
        print(f"    有效级别: {effective_level}")
        print()

    print("=" * 80)

if __name__ == "__main__":
    check_logger_levels()