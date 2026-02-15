"""
V15 数据提供者合并脚本 - Day2
功能：合并logic/data/到logic/data_providers/，迁移logic主目录文件
作者：CTO + AI总监
日期：2026-02-15
"""

import shutil
from pathlib import Path
import sys

# 项目根目录
ROOT = Path(__file__).parent.parent

# ========== 第一部分：合并logic/data/到logic/data_providers/ ==========

DATA_MIGRATIONS = [
    # 从logic/data/迁移到logic/data_providers/
    "logic/data/cache_manager.py",
    "logic/data/data_adapter_akshare.py",
    "logic/data/data_adapter.py",
    "logic/data/data_cleaner.py",
    "logic/data/data_manager.py",
    "logic/data/data_provider_factory.py",
    "logic/data/data_source_manager.py",
    "logic/data/easyquotation_adapter.py",
    "logic/data/fund_flow_analyzer.py",
    "logic/data/fund_flow_cache.py",
    "logic/data/fund_flow_collector.py",
    "logic/data/money_flow_master.py",
    "logic/data/multi_source_adapter.py",
    "logic/data/qmt_manager.py",
    "logic/data/realtime_data_provider.py",
]

# ========== 第二部分：迁移logic主目录文件到子目录 ==========

# 核心模块（迁到logic/core/）
CORE_MIGRATIONS = [
    ("logic/rate_limiter.py", "logic/core/rate_limiter.py"),
    ("logic/error_handler.py", "logic/core/error_handler.py"),
    ("logic/log_config.py", "logic/core/log_config.py"),
    ("logic/retry_decorator.py", "logic/core/retry_decorator.py"),
    ("logic/network_utils.py", "logic/core/network_utils.py"),
    ("logic/version.py", "logic/core/version.py"),
]

# 数据相关（迁到logic/data_providers/）
DATA_PROVIDER_MIGRATIONS = [
    ("logic/database_manager.py", "logic/data_providers/database_manager.py"),
]

# 监控相关（迁到logic/monitors/）
MONITOR_MIGRATIONS = [
    ("logic/event_recorder.py", "logic/monitors/event_recorder.py"),
    ("logic/late_trading_scanner.py", "logic/monitors/late_trading_scanner.py"),
]

# 策略相关（迁到logic/strategies/）
STRATEGY_MIGRATIONS = [
    ("logic/active_stock_filter.py", "logic/strategies/active_stock_filter.py"),
    ("logic/market_environment_filter.py", "logic/strategies/market_environment_filter.py"),
    ("logic/national_team_detector.py", "logic/strategies/national_team_detector.py"),
    ("logic/national_team_guard.py", "logic/strategies/national_team_guard.py"),
    ("logic/time_strategy_manager.py", "logic/strategies/time_strategy_manager.py"),
]

# 分析相关（迁到logic/analyzers/）
ANALYZER_MIGRATIONS = [
    ("logic/multi_day_analysis.py", "logic/analyzers/multi_day_analysis.py"),
    ("logic/parameter_optimizer.py", "logic/analyzers/parameter_optimizer.py"),
    ("logic/performance_benchmark.py", "logic/analyzers/performance_benchmark.py"),
    ("logic/performance_optimizer.py", "logic/analyzers/performance_optimizer.py"),
    ("logic/predictive_engine.py", "logic/analyzers/predictive_engine.py"),
    ("logic/portfolio_optimizer.py", "logic/analyzers/portfolio_optimizer.py"),
    ("logic/out_of_sample_validator.py", "logic/analyzers/out_of_sample_validator.py"),
    ("logic/scenario_classifier.py", "logic/analyzers/scenario_classifier.py"),
]

# 工具相关（迁到logic/utils/）
UTIL_MIGRATIONS = [
    ("logic/comparator.py", "logic/utils/comparator.py"),
    ("logic/output_formatter.py", "logic/utils/output_formatter.py"),
    ("logic/stock_name_fetcher.py", "logic/utils/stock_name_fetcher.py"),
    ("logic/tab_manager.py", "logic/utils/tab_manager.py"),
]

# 可视化相关（迁到logic/visualizers/）
VISUALIZER_MIGRATIONS = [
    ("logic/advanced_visualizer.py", "logic/visualizers/advanced_visualizer.py"),
    ("logic/visualizer.py", "logic/visualizers/visualizer.py"),
]

# ML相关（迁到logic/ml/）
ML_MIGRATIONS = [
    ("logic/distributed_training_system.py", "logic/ml/distributed_training_system.py"),
    ("logic/intelligent_trading_system.py", "logic/ml/intelligent_trading_system.py"),
    ("logic/multi_agent_system.py", "logic/ml/multi_agent_system.py"),
    ("logic/multi_strategy_fusion.py", "logic/ml/multi_strategy_fusion.py"),
    ("logic/multifactor_fusion.py", "logic/ml/multifactor_fusion.py"),
    ("logic/rl_agent.py", "logic/ml/rl_agent.py"),
    ("logic/opportunity_predictor.py", "logic/ml/opportunity_predictor.py"),
]

# 服务相关（迁到logic/services/）
SERVICE_MIGRATIONS = [
    ("logic/email_alert_service.py", "logic/services/email_alert_service.py"),
    ("logic/wechat_notification_service.py", "logic/services/wechat_notification_service.py"),
    ("logic/live_test_recorder.py", "logic/services/live_test_recorder.py"),
]

# 通知相关（迁到logic/notifications/）
NOTIFICATION_MIGRATIONS = [
    ("logic/unban_warning_system.py", "logic/notifications/unban_warning_system.py"),
]

# LLM相关（迁到logic/llm/）
LLM_MIGRATIONS = [
    ("logic/llm_interface.py", "logic/llm/llm_interface.py"),
    ("logic/keyword_extractor.py", "logic/llm/keyword_extractor.py"),
    ("logic/hot_topic_extractor.py", "logic/llm/hot_topic_extractor.py"),
    ("logic/auto_reviewer.py", "logic/llm/auto_reviewer.py"),
]

# 网络相关（迁到logic/network/）
NETWORK_MIGRATIONS = [
    ("logic/api_robust.py", "logic/network/api_robust.py"),
    ("logic/proxy_manager.py", "logic/network/proxy_manager.py"),
    ("logic/news_crawler.py", "logic/network/news_crawler.py"),
]

# 管理相关（迁到logic/managers/）
MANAGER_MIGRATIONS = [
    ("logic/watchlist_manager.py", "logic/managers/watchlist_manager.py"),
    ("logic/review_manager.py", "logic/managers/review_manager.py"),
    ("logic/user_preferences.py", "logic/managers/user_preferences.py"),
]

# 调整相关（迁到logic/adjustment/）
ADJUSTMENT_MIGRATIONS = [
    ("logic/online_parameter_adjustment.py", "logic/adjustment/online_parameter_adjustment.py"),
]

# 并发相关（迁到logic/concurrent/）
CONCURRENT_MIGRATIONS = [
    ("logic/concurrent_executor.py", "logic/concurrent/concurrent_executor.py"),
]

# 移动相关（迁到logic/mobile/）
MOBILE_MIGRATIONS = [
    ("logic/mobile_adapter.py", "logic/mobile/mobile_adapter.py"),
]

# 推荐相关（迁到logic/recommenders/）
RECOMMENDER_MIGRATIONS = [
    ("logic/smart_recommender.py", "logic/recommenders/smart_recommender.py"),
]

# 指标相关（迁到logic/metrics/）
METRICS_MIGRATIONS = [
    ("logic/enhanced_metrics.py", "logic/metrics/enhanced_metrics.py"),
]

# ========== 函数定义 ==========

def dry_run_data_merge():
    """dry_run预览data合并"""
    print("=" * 80)
    print("V15 数据提供者合并 - dry_run预览")
    print("=" * 80)

    print(f"\n📊 将迁移 {len(DATA_MIGRATIONS)} 个文件：")
    for src in DATA_MIGRATIONS:
        src_path = ROOT / src
        if src_path.exists():
            print(f"   ✅ {src}")
        else:
            print(f"   ⚠️  {src} (文件不存在)")

    print(f"\n💡 提示：确认后运行 real_merge_data() 执行合并")
    print("=" * 80)

def real_merge_data():
    """合并logic/data/到logic/data_providers/"""
    print("=" * 80)
    print("V15 数据提供者合并 - real_merge_data执行")
    print("=" * 80)

    count = 0
    errors = []

    for src in DATA_MIGRATIONS:
        src_path = ROOT / src
        filename = src_path.name
        dest_path = ROOT / "logic" / "data_providers" / filename

        if not src_path.exists():
            error_msg = f"⚠️  源文件不存在：{src}"
            print(f"   {error_msg}")
            errors.append(error_msg)
            continue

        try:
            # 移动文件
            shutil.move(str(src_path), str(dest_path))
            print(f"   ✅ 迁移：{src} → logic/data_providers/{filename}")
            count += 1
        except Exception as e:
            error_msg = f"❌ 迁移失败：{src} - {e}"
            print(f"   {error_msg}")
            errors.append(error_msg)

    print(f"\n📊 迁移结果：")
    print(f"   成功：{count} 个文件")
    print(f"   失败：{len(errors)} 个文件")

    if errors:
        print(f"\n❌ 错误列表：")
        for error in errors:
            print(f"   {error}")

    # 删除空的data目录
    data_dir = ROOT / "logic" / "data"
    if data_dir.exists():
        try:
            shutil.rmtree(data_dir)
            print(f"\n✅ 删除空目录：logic/data/")
        except Exception as e:
            print(f"\n⚠️  删除目录失败：logic/data/ - {e}")

    print("=" * 80)

    return count

def dry_run_logic_cleanup():
    """dry_run预览logic主目录清理"""
    print("=" * 80)
    print("V15 Logic主目录清理 - dry_run预览")
    print("=" * 80)

    all_migrations = (
        CORE_MIGRATIONS +
        DATA_PROVIDER_MIGRATIONS +
        MONITOR_MIGRATIONS +
        STRATEGY_MIGRATIONS +
        ANALYZER_MIGRATIONS +
        UTIL_MIGRATIONS +
        VISUALIZER_MIGRATIONS +
        ML_MIGRATIONS +
        SERVICE_MIGRATIONS +
        NOTIFICATION_MIGRATIONS +
        LLM_MIGRATIONS +
        NETWORK_MIGRATIONS +
        MANAGER_MIGRATIONS +
        ADJUSTMENT_MIGRATIONS +
        CONCURRENT_MIGRATIONS +
        MOBILE_MIGRATIONS +
        RECOMMENDER_MIGRATIONS +
        METRICS_MIGRATIONS
    )

    print(f"\n📊 将迁移 {len(all_migrations)} 个文件：")

    for src, dest in all_migrations:
        src_path = ROOT / src
        if src_path.exists():
            print(f"   ✅ {src} → {dest}")
        else:
            print(f"   ⚠️  {src} (文件不存在)")

    print(f"\n💡 提示：确认后运行 real_logic_cleanup() 执行迁移")
    print("=" * 80)

def real_logic_cleanup():
    """清理logic主目录，迁移文件到子目录"""
    print("=" * 80)
    print("V15 Logic主目录清理 - real_logic_cleanup执行")
    print("=" * 80)

    all_migrations = (
        CORE_MIGRATIONS +
        DATA_PROVIDER_MIGRATIONS +
        MONITOR_MIGRATIONS +
        STRATEGY_MIGRATIONS +
        ANALYZER_MIGRATIONS +
        UTIL_MIGRATIONS +
        VISUALIZER_MIGRATIONS +
        ML_MIGRATIONS +
        SERVICE_MIGRATIONS +
        NOTIFICATION_MIGRATIONS +
        LLM_MIGRATIONS +
        NETWORK_MIGRATIONS +
        MANAGER_MIGRATIONS +
        ADJUSTMENT_MIGRATIONS +
        CONCURRENT_MIGRATIONS +
        MOBILE_MIGRATIONS +
        RECOMMENDER_MIGRATIONS +
        METRICS_MIGRATIONS
    )

    count = 0
    errors = []

    for src, dest in all_migrations:
        src_path = ROOT / src
        dest_path = ROOT / dest

        if not src_path.exists():
            error_msg = f"⚠️  源文件不存在：{src}"
            print(f"   {error_msg}")
            errors.append(error_msg)
            continue

        try:
            # 创建目标目录
            dest_path.parent.mkdir(exist_ok=True, parents=True)

            # 移动文件
            shutil.move(str(src_path), str(dest_path))
            print(f"   ✅ 迁移：{src} → {dest}")
            count += 1
        except Exception as e:
            error_msg = f"❌ 迁移失败：{src} - {e}"
            print(f"   {error_msg}")
            errors.append(error_msg)

    print(f"\n📊 迁移结果：")
    print(f"   成功：{count} 个文件")
    print(f"   失败：{len(errors)} 个文件")

    if errors:
        print(f"\n❌ 错误列表：")
        for error in errors:
            print(f"   {error}")

    print("=" * 80)

    return count

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("V15 数据提供者合并 + Logic主目录清理脚本")
    print("=" * 80 + "\n")

    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法：")
        print("  python scripts/v15_data_providers_merge.py dry_run_data     # 预览data合并")
        print("  python scripts/v15_data_providers_merge.py real_merge_data # 执行data合并")
        print("  python scripts/v15_data_providers_merge.py dry_run_logic    # 预览logic清理")
        print("  python scripts/v15_data_providers_merge.py real_logic_cleanup # 执行logic清理")
        print("  python scripts/v15_data_providers_merge.py all              # 执行全部")
        sys.exit(1)

    command = sys.argv[1]

    if command == "dry_run_data":
        dry_run_data_merge()
    elif command == "real_merge_data":
        real_merge_data()
    elif command == "dry_run_logic":
        dry_run_logic_cleanup()
    elif command == "real_logic_cleanup":
        real_logic_cleanup()
    elif command == "all":
        print("⚠️  将执行全部合并：data合并 → logic清理")
        input("按Enter继续，Ctrl+C取消...")

        real_merge_data()
        print("\n")
        real_logic_cleanup()
        print("\n✅ V15 合并完成！")
    else:
        print(f"❌ 未知命令：{command}")
        sys.exit(1)

if __name__ == "__main__":
    main()