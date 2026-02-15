"""
V15 精准清理脚本 - Day1
功能：dry_run预览96删 → real_cleanup删除 → 提炼精华
作者：CTO + AI总监
日期：2026-02-15
"""

import shutil
from pathlib import Path
from typing import List, Set
import sys

# 项目根目录
ROOT = Path(__file__).parent.parent

# ========== 删除清单（基于grep调用分析） ==========

# tools/目录 - 32个文件（82%冗余率）
DELETE_TOOLS = [
    # 分析类
    "tools/analyze_backtest_result.py",
    "tools/analyze_logic_files.py",
    # 诊断类
    "tools/diagnose_backtest.py",
    "tools/diagnose_tick_data.py",
    "tools/check_qmt_tick.py",
    # 归档类
    "tools/archive_daily_logs.py",
    # 回测类
    "tools/backtest_scanner.py",
    "tools/run_backtest_1m_v2.py",
    # 下载类
    "tools/download_missing_hot_stocks.py",
    "tools/download_real_batch_1m.py",
    "tools/download_wanzhu_120.py",
    "tools/download_wanzhu_missing.py",
    # 生成类
    "tools/generate_active_pool_akshare.py",
    "tools/generate_active_pool_auction.py",
    "tools/generate_active_pool_qmt.py",
    "tools/generate_active_pool.py",
    "tools/generate_auction_daily_report.py",
    "tools/generate_stock_names_v2.py",
    "tools/generate_t1_report.py",
    # 获取类
    "tools/get_hot_stocks_codes.py",
    "tools/get_hot_stocks_v2.py",
    # 数据类
    "tools/harvest_data.py",
    "tools/import_tushare_to_cache.py",
    # 集成类
    "tools/integrate_wanzhu_cup.py",
    # 验证类
    "tools/verify_data_consistency.py",
    # 情绪类
    "tools/wanzhu_sentiment_factor.py",
    # 修复类（14个）
    "tools/fix_auction_collector.py",
    "tools/fix_hot_money_flow.py",
    "tools/fix_realtime_flow.py",
    "tools/fix_realtime_flow_v2.py",
    "tools/fix_realtime_flow_v3.py",
    "tools/fix_realtime_flow_v4.py",
    "tools/fix_tushare_money_flow.py",
    # 丰富类
    "tools/enrich_scan_results.py",
]

# tasks/目录 - 4个文件（22%冗余率）
DELETE_TASKS = [
    "tasks/daily_summary.py",
    "tasks/run_pre_market_warmup.py",
    "tasks/sync_equity_info_multi_date.py",
    "tasks/sync_equity_info_tushare.py",
    "tasks/validate_auction_pipeline.py",
]

# logic/strategies/目录 - 24个文件（75%冗余率）
DELETE_STRATEGIES = [
    # 半路战法（已被triple_funnel替代）
    "logic/strategies/midway_strategy.py",
    # 市场扫描器（已被full_market_scanner替代）
    "logic/strategies/market_scanner.py",
    # 买点扫描器
    "logic/strategies/buy_point_scanner.py",
    # 事件检测器（已被event_detector整合）
    "logic/strategies/auction_event_detector.py",
    "logic/strategies/auction_trap_detector.py",
    "logic/strategies/dip_buy_event_detector.py",
    "logic/strategies/halfway_event_detector.py",
    "logic/strategies/leader_event_detector.py",
    # 战法类（未投入使用）
    "logic/strategies/dragon_tactics.py",
    "logic/strategies/market_tactics.py",
    # 检测器类（未投入使用）
    "logic/strategies/fake_order_detector.py",
    "logic/strategies/low_suction_engine.py",
    "logic/strategies/order_imbalance.py",
    "logic/strategies/predator_system.py",
    "logic/strategies/second_wave_detector.py",
    # 配置加载器（未投入使用）
    "logic/strategies/scanner_v121_config_loader.py",
    # 回测引擎（未投入使用）
    "logic/strategies/snapshot_backtest_engine.py",
    # 策略比较器（重复）
    "logic/strategies/strategy_comparator.py",
    "logic/strategies/strategy_comparison.py",
    # 策略工厂（未投入使用）
    "logic/strategies/strategy_factory.py",
    "logic/strategies/strategy_library.py",
    # 策略编排（未投入使用）
    "logic/strategies/strategy_orchestrator.py",
    # 交易日志（未投入使用）
    "logic/strategies/trade_log.py",
    # 风向过滤使用（未投入使用）
    "logic/strategies/wind_filter_usage.py",
]

# logic/data/目录 - 22个文件（55%冗余率）
DELETE_DATA = [
    # 数据加载器（已被替代）
    "logic/data/akshare_data_loader.py",
    # 缓存回放（未投入使用）
    "logic/data/cache_replay_provider.py",
    # 数据收割（未投入使用）
    "logic/data/data_harvester.py",
    # 数据监控类（未投入使用）
    "logic/data/data_health_monitor.py",
    "logic/data/data_maintenance.py",
    "logic/data/data_monitor.py",
    "logic/data/data_quality_monitor.py",
    "logic/data/data_quality_validator.py",
    # 数据清洗（已被data_cleaner替代）
    "logic/data/data_sanitizer.py",
    # 股本访问（未投入使用）
    "logic/data/equity_data_accessor.py",
    # 资金流调度（未投入使用）
    "logic/data/fund_flow_freshness.py",
    "logic/data/fund_flow_scheduler.py",
    # 历史回放（未投入使用）
    "logic/data/historical_replay_provider.py",
    # 历史缓存（未投入使用）
    "logic/data/history_cache.py",
    "logic/data/history_manager.py",
    # 分层适配（未投入使用）
    "logic/data/layered_data_adapter.py",
    # 资金流数据源（未投入使用）
    "logic/data/moneyflow_data_source.py",
    # 盘前缓存（未投入使用）
    "logic/data/pre_market_cache.py",
    # QMT健康检查（未投入使用）
    "logic/data/qmt_health_check.py",
    # QMT历史提供（未投入使用）
    "logic/data/qmt_historical_provider.py",
    # QMT保活（未投入使用）
    "logic/data/qmt_keepalive.py",
    # QMT股票信息（未投入使用）
    "logic/data/qmt_stock_info.py",
    # QMT补充（未投入使用）
    "logic/data/qmt_supplement.py",
    # QMT Tick监控（未投入使用）
    "logic/data/qmt_tick_monitor.py",
    # 智能流估算（未投入使用）
    "logic/data/smart_flow_estimator.py",
]

# logic/analyzers/目录 - 9个文件（60%冗余率）
DELETE_ANALYZERS = [
    # 资金网络（未投入使用）
    "logic/analyzers/capital_network.py",
    "logic/analyzers/capital_profiler.py",
    # K线分析（未投入使用）
    "logic/analyzers/kline_analyzer.py",
    "logic/analyzers/kline_cache.py",
    "logic/analyzers/kline_pattern_recognizer.py",
    # 主力强度（未投入使用）
    "logic/analyzers/main_force_strength.py",
    # 滚动训练（未投入使用）
    "logic/analyzers/rolling_trainer.py",
    # 技术指标（已被technical_analyzer替代）
    "logic/analyzers/technical_indicators.py",
    # 诱多检测批量（未投入使用）
    "logic/analyzers/trap_detector_batch.py",
]

# logic/monitors/目录 - 5个文件（42%冗余率）
DELETE_MONITORS = [
    # 自动维护（未投入使用）
    "logic/monitors/auto_maintenance.py",
    # 铁律告警（未投入使用）
    "logic/monitors/iron_rule_alert.py",
    # 监控（已被intraday_monitor替代）
    "logic/monitors/monitor.py",
    # 真实券商API（未投入使用）
    "logic/monitors/real_broker_api.py",
    # 定时任务监控（未投入使用）
    "logic/monitors/scheduled_task_monitor.py",
]

# 总删除清单
ALL_DELETE = DELETE_TOOLS + DELETE_TASKS + DELETE_STRATEGIES + DELETE_DATA + DELETE_ANALYZERS + DELETE_MONITORS

# ========== 精华提取清单 ==========

SNIPPETS = [
    ("logic/strategies/triple_funnel_scanner.py", "triple_funnel_snippet.py", "三漏斗扫描器核心逻辑"),
    ("logic/analyzers/trap_detector.py", "trap_detector_snippet.py", "诱多检测器算法"),
    ("logic/analyzers/capital_classifier.py", "capital_classifier_snippet.py", "资金分类器"),
    ("logic/monitors/intraday_monitor.py", "intraday_monitor_snippet.py", "盘中监控"),
    ("logic/data_providers/level1_provider.py", "level1_inference_snippet.py", "Level-1资金流推断"),
    ("logic/strategies/full_market_scanner.py", "full_market_scanner_snippet.py", "全市场扫描器"),
    ("logic/data/qmt_manager.py", "qmt_manager_snippet.py", "QMT管理器"),
    ("logic/data_providers/factory.py", "provider_factory_snippet.py", "数据提供者工厂"),
    ("logic/data_providers/level2_provider.py", "level2_provider_snippet.py", "Level-2提供者"),
    ("logic/strategies/event_detector.py", "event_detector_snippet.py", "事件检测器"),
]

# ========== 函数定义 ==========

def dry_run() -> int:
    """dry_run预览96删"""
    print("=" * 80)
    print("V15 清理 - dry_run预览")
    print("=" * 80)

    count = 0
    files_to_delete: Set[Path] = set()

    # 统计各目录
    tools_count = len(DELETE_TOOLS)
    tasks_count = len(DELETE_TASKS)
    strategies_count = len(DELETE_STRATEGIES)
    data_count = len(DELETE_DATA)
    analyzers_count = len(DELETE_ANALYZERS)
    monitors_count = len(DELETE_MONITORS)

    print(f"\n📊 删除统计：")
    print(f"   tools/：{tools_count} 个文件")
    print(f"   tasks/：{tasks_count} 个文件")
    print(f"   strategies/：{strategies_count} 个文件")
    print(f"   data/：{data_count} 个文件")
    print(f"   analyzers/：{analyzers_count} 个文件")
    print(f"   monitors/：{monitors_count} 个文件")
    print(f"   总计：{len(ALL_DELETE)} 个文件")

    print(f"\n🔍 预览删除文件：")

    for file_path in ALL_DELETE:
        full_path = ROOT / file_path
        if full_path.exists():
            files_to_delete.add(full_path)
            print(f"   ✅ {file_path}")
            count += 1
        else:
            print(f"   ⚠️  {file_path} (文件不存在)")

    print(f"\n📋 实际将删除：{count} 个文件")
    print(f"\n💡 提示：确认后运行 real_cleanup() 执行删除")
    print("=" * 80)

    return count

def real_cleanup() -> int:
    """real_cleanup删除96文件"""
    print("=" * 80)
    print("V15 清理 - real_cleanup执行")
    print("=" * 80)

    count = 0
    errors = []

    for file_path in ALL_DELETE:
        full_path = ROOT / file_path
        if full_path.exists():
            try:
                full_path.unlink()
                print(f"   ✅ 删除：{file_path}")
                count += 1
            except Exception as e:
                error_msg = f"❌ 删除失败：{file_path} - {e}"
                print(f"   {error_msg}")
                errors.append(error_msg)

    print(f"\n📊 删除结果：")
    print(f"   成功：{count} 个文件")
    print(f"   失败：{len(errors)} 个文件")

    if errors:
        print(f"\n❌ 错误列表：")
        for error in errors:
            print(f"   {error}")

    print("=" * 80)

    return count

def extract_snippets() -> int:
    """提炼精华 - 10个snippets"""
    print("=" * 80)
    print("V15 清理 - 提炼精华")
    print("=" * 80)

    snippets_dir = ROOT / "docs" / "core_snippets"
    snippets_dir.mkdir(exist_ok=True)

    count = 0
    errors = []

    for source_path, snippet_name, description in SNIPPETS:
        source_file = ROOT / source_path
        snippet_file = snippets_dir / snippet_name

        if not source_file.exists():
            error_msg = f"⚠️  源文件不存在：{source_path}"
            print(f"   {error_msg}")
            errors.append(error_msg)
            continue

        try:
            # 读取源文件
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 添加描述注释
            header = '"""\n'
            header += f'{description}\n'
            header += f'Source: {source_path}\n'
            header += f'Extracted: {Path(__file__).stat().st_mtime}\n'
            header += '"""\n\n'
            snippet_content = header + content

            # 写入snippet
            with open(snippet_file, 'w', encoding='utf-8') as f:
                f.write(snippet_content)

            print(f"   ✅ 提取：{snippet_name} ({description})")
            count += 1

        except Exception as e:
            error_msg = f"❌ 提取失败：{snippet_name} - {e}"
            print(f"   {error_msg}")
            errors.append(error_msg)

    print(f"\n📊 提取结果：")
    print(f"   成功：{count} 个snippets")
    print(f"   失败：{len(errors)} 个")
    print(f"   保存路径：{snippets_dir}")

    if errors:
        print(f"\n❌ 错误列表：")
        for error in errors:
            print(f"   {error}")

    print("=" * 80)

    return count

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("V15 精准清理脚本")
    print("=" * 80 + "\n")

    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法：")
        print("  python scripts/v15_precise_cleanup.py dry_run      # 预览删除")
        print("  python scripts/v15_precise_cleanup.py real_cleanup # 执行删除")
        print("  python scripts/v15_precise_cleanup.py snippets     # 提炼精华")
        print("  python scripts/v15_precise_cleanup.py all          # 执行全部")
        sys.exit(1)

    command = sys.argv[1]

    if command == "dry_run":
        dry_run()
    elif command == "real_cleanup":
        real_cleanup()
    elif command == "snippets":
        extract_snippets()
    elif command == "all":
        print("⚠️  将执行全部清理：dry_run → real_cleanup → snippets")
        input("按Enter继续，Ctrl+C取消...")

        dry_run()
        print("\n")
        real_cleanup()
        print("\n")
        extract_snippets()
        print("\n✅ V15 清理完成！")
    else:
        print(f"❌ 未知命令：{command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
