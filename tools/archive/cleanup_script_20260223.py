#!/usr/bin/env python3
"""
Phase 7 野脚本清理清单
记录被删除/归档的临时脚本
"""

CLEANUP_LIST = {
    "tools/": [
        "check_0105_data.py",  # 单日检查，已归档
        "day_0105_final_battle.py",  # 单日回演，逻辑已迁移至main.py
        "dragon_gene_analyzer.py",  # 一次性分析，逻辑已迁移
        "extract_complete_top20.py",  # 一次性提取，逻辑已迁移
        "show_report_data.py",  # 一次性展示，逻辑已迁移
        "zhitexincai_0105_analysis.py",  # 单股分析，逻辑已迁移至main.py analyze
        "download_0105_data.py",  # 单日下载，逻辑已迁移
        "analyze_wangsu_extreme.py",  # 单股分析，已归档
        "run_wangsu_case.py",  # 单股回测，已归档
        "run_wangsu_ab_comparison.py",  # 单股对比，已归档
        "run_single_wanzhu_replay.py",  # 单票回测，逻辑已迁移
        "run_4stocks_quick.py",  # 临时测试，已归档
        "run_16stocks_replay.py",  # 临时测试，已归档
        "test_phase5.py",  # 临时测试，已归档
        "test_phase5_final.py",  # 临时测试，已归档
        "quick_audit_top10.py",  # 临时审计，逻辑已迁移至main.py verify
        "validate_sustain_ability.py",  # 临时验证，已归档
        "check_0126_distribution.py",  # 单日检查，已归档
        "check_float_cap.py",  # 临时检查，已归档
        "check_tick_time_range.py",  # 临时检查，已归档
        "check_volume_unit.py",  # 临时检查，已归档
        "verify_daily_volume.py",  # 临时验证，逻辑已迁移
        "verify_morning_breakout.py",  # 临时验证，已归档
        "full_scan_top10_audit.py",  # 临时审计，逻辑已迁移
        "supplement_tick_download.py",  # 临时下载，逻辑已迁移
    ],
    "tasks/": [
        "run_time_machine_backtest.py",  # 已迁移至main.py backtest
        "run_v18_holographic_replay.py",  # 已迁移至main.py backtest --strategy v18
        "run_full_market_scan.py",  # 已迁移至main.py scan
        "run_triple_funnel_scan.py",  # 已迁移至main.py scan
        "run_realtime_phase3_test.py",  # 已迁移至main.py simulate
        "run_historical_simulation.py",  # 已迁移至main.py simulate
        "tushare_market_filter.py",  # 已迁移至main.py scan --source tushare
    ]
}

# 保留的核心文件
KEPT_CORE_FILES = {
    "tools/": [
        "download_tick_with_vip.py",  # VIP下载核心
        "download_qmt_history.py",  # 历史数据下载核心
        "data_integrity_checker.py",  # 数据完整性检查核心
        "system_check.py",  # 系统检查
        "init_qmt.py",  # QMT初始化
        "cli_monitor.py",  # CLI监控（保留）
    ],
    "tasks/": [
        "production/*",  # 实盘交易任务保留
        "backtest/",  # 回测引擎核心保留
        "data_prefetch.py",  # 数据预取保留
        "manage_universe.py",  # 股票池管理保留
    ]
}

if __name__ == '__main__':
    print("Phase 7 野脚本清理清单")
    print("=" * 80)
    print(f"\n计划删除 tools/ 目录: {len(CLEANUP_LIST['tools/'])} 个文件")
    print(f"计划删除 tasks/ 目录: {len(CLEANUP_LIST['tasks/'])} 个文件")
    print(f"\n保留核心文件 tools/: {len(KEPT_CORE_FILES['tools/'])} 个")
    print(f"保留核心文件 tasks/: {len(KEPT_CORE_FILES['tasks/'])} 个")
    print("\n清理完成后，所有功能必须通过 main.py CLI 调用")
