"""
V15 Import路径修复脚本 - Day2
功能：修复logic/data/迁移后的import路径，logic主目录迁移后的引用
作者：CTO + AI总监
日期：2026-02-15

避坑指南：
1. 先grep预览，确认需要修复的引用
2. 使用批量替换，确保一致性
3. pytest验证修复效果
"""

import re
from pathlib import Path
import sys

# 项目根目录
ROOT = Path(__file__).parent.parent

# ========== Import路径映射 ==========

# logic/data/ → logic/data_providers/
IMPORT_DATA_REPLACEMENTS = [
    (r'from logic\.data\.', 'from logic.data_providers.'),
    (r'from logic\.database_manager', 'from logic.data_providers.database_manager'),
]

# logic主目录 → logic/core/
IMPORT_CORE_REPLACEMENTS = [
    (r'from logic\.rate_limiter', 'from logic.core.rate_limiter'),
    (r'from logic\.error_handler', 'from logic.core.error_handler'),
    (r'from logic\.log_config', 'from logic.core.log_config'),
    (r'from logic\.retry_decorator', 'from logic.core.retry_decorator'),
    (r'from logic\.network_utils', 'from logic.core.network_utils'),
    (r'from logic\.version', 'from logic.core.version'),
]

# logic主目录 → logic/managers/
IMPORT_MANAGER_REPLACEMENTS = [
    (r'from logic\.watchlist_manager', 'from logic.managers.watchlist_manager'),
    (r'from logic\.review_manager', 'from logic.managers.review_manager'),
    (r'from logic\.user_preferences', 'from logic.managers.user_preferences'),
]

# logic主目录 → logic/analyzers/
IMPORT_ANALYZER_REPLACEMENTS = [
    (r'from logic\.multi_day_analysis', 'from logic.analyzers.multi_day_analysis'),
    (r'from logic\.parameter_optimizer', 'from logic.analyzers.parameter_optimizer'),
    (r'from logic\.performance_benchmark', 'from logic.analyzers.performance_benchmark'),
    (r'from logic\.performance_optimizer', 'from logic.analyzers.performance_optimizer'),
    (r'from logic\.predictive_engine', 'from logic.analyzers.predictive_engine'),
    (r'from logic\.portfolio_optimizer', 'from logic.analyzers.portfolio_optimizer'),
    (r'from logic\.out_of_sample_validator', 'from logic.analyzers.out_of_sample_validator'),
    (r'from logic\.scenario_classifier', 'from logic.analyzers.scenario_classifier'),
]

# logic主目录 → logic/strategies/
IMPORT_STRATEGY_REPLACEMENTS = [
    (r'from logic\.active_stock_filter', 'from logic.strategies.active_stock_filter'),
    (r'from logic\.market_environment_filter', 'from logic.strategies.market_environment_filter'),
    (r'from logic\.national_team_detector', 'from logic.strategies.national_team_detector'),
    (r'from logic\.national_team_guard', 'from logic.strategies.national_team_guard'),
    (r'from logic\.time_strategy_manager', 'from logic.strategies.time_strategy_manager'),
]

# logic主目录 → logic/monitors/
IMPORT_MONITOR_REPLACEMENTS = [
    (r'from logic\.event_recorder', 'from logic.monitors.event_recorder'),
    (r'from logic\.late_trading_scanner', 'from logic.monitors.late_trading_scanner'),
]

# logic主目录 → logic/utils/
IMPORT_UTIL_REPLACEMENTS = [
    (r'from logic\.comparator', 'from logic.utils.comparator'),
    (r'from logic\.output_formatter', 'from logic.utils.output_formatter'),
    (r'from logic\.stock_name_fetcher', 'from logic.utils.stock_name_fetcher'),
    (r'from logic\.tab_manager', 'from logic.utils.tab_manager'),
]

# logic主目录 → logic/visualizers/
IMPORT_VISUALIZER_REPLACEMENTS = [
    (r'from logic\.advanced_visualizer', 'from logic.visualizers.visualizers.advanced_visualizer'),
    (r'from logic\.visualizer', 'from logic.visualizers.visualizers.visualizer'),
]

# logic主目录 → logic/ml/
IMPORT_ML_REPLACEMENTS = [
    (r'from logic\.distributed_training_system', 'from logic.ml.distributed_training_system'),
    (r'from logic\.intelligent_trading_system', 'from logic.ml.intelligent_trading_system'),
    (r'from logic\.multi_agent_system', 'from logic.ml.multi_agent_system'),
    (r'from logic\.multi_strategy_fusion', 'from logic.ml.multi_strategy_fusion'),
    (r'from logic\.multifactor_fusion', 'from logic.ml.multifactor_fusion'),
    (r'from logic\.rl_agent', 'from logic.ml.rl_agent'),
    (r'from logic\.opportunity_predictor', 'from logic.ml.opportunity_predictor'),
]

# logic主目录 → logic/services/
IMPORT_SERVICE_REPLACEMENTS = [
    (r'from logic\.email_alert_service', 'from logic.services.email_alert_service'),
    (r'from logic\.wechat_notification_service', 'from logic.services.wechat_notification_service'),
    (r'from logic\.live_test_recorder', 'from logic.services.live_test_recorder'),
]

# logic主目录 → logic/notifications/
IMPORT_NOTIFICATION_REPLACEMENTS = [
    (r'from logic\.unban_warning_system', 'from logic.notifications.unban_warning_system'),
]

# logic主目录 → logic/llm/
IMPORT_LLM_REPLACEMENTS = [
    (r'from logic\.llm_interface', 'from logic.llm.llm_interface'),
    (r'from logic\.keyword_extractor', 'from logic.llm.keyword_extractor'),
    (r'from logic\.hot_topic_extractor', 'from logic.llm.hot_topic_extractor'),
    (r'from logic\.auto_reviewer', 'from logic.llm.auto_reviewer'),
]

# logic主目录 → logic/network/
IMPORT_NETWORK_REPLACEMENTS = [
    (r'from logic\.api_robust', 'from logic.network.api_robust'),
    (r'from logic\.proxy_manager', 'from logic.network.proxy_manager'),
    (r'from logic\.news_crawler', 'from logic.network.news_crawler'),
]

# logic主目录 → logic/concurrent/
IMPORT_CONCURRENT_REPLACEMENTS = [
    (r'from logic\.concurrent_executor', 'from logic.concurrent.concurrent_executor'),
]

# logic主目录 → logic/mobile/
IMPORT_MOBILE_REPLACEMENTS = [
    (r'from logic\.mobile_adapter', 'from logic.mobile.mobile_adapter'),
]

# logic主目录 → logic/recommenders/
IMPORT_RECOMMENDER_REPLACEMENTS = [
    (r'from logic\.smart_recommender', 'from logic.recommenders.smart_recommender'),
]

# logic主目录 → logic/metrics/
IMPORT_METRICS_REPLACEMENTS = [
    (r'from logic\.enhanced_metrics', 'from logic.metrics.enhanced_metrics'),
]

# logic主目录 → logic/adjustment/
IMPORT_ADJUSTMENT_REPLACEMENTS = [
    (r'from logic\.online_parameter_adjustment', 'from logic.adjustment.online_parameter_adjustment'),
]

# 所有替换规则
ALL_REPLACEMENTS = (
    IMPORT_DATA_REPLACEMENTS +
    IMPORT_CORE_REPLACEMENTS +
    IMPORT_MANAGER_REPLACEMENTS +
    IMPORT_ANALYZER_REPLACEMENTS +
    IMPORT_STRATEGY_REPLACEMENTS +
    IMPORT_MONITOR_REPLACEMENTS +
    IMPORT_UTIL_REPLACEMENTS +
    IMPORT_VISUALIZER_REPLACEMENTS +
    IMPORT_ML_REPLACEMENTS +
    IMPORT_SERVICE_REPLACEMENTS +
    IMPORT_NOTIFICATION_REPLACEMENTS +
    IMPORT_LLM_REPLACEMENTS +
    IMPORT_NETWORK_REPLACEMENTS +
    IMPORT_CONCURRENT_REPLACEMENTS +
    IMPORT_MOBILE_REPLACEMENTS +
    IMPORT_RECOMMENDER_REPLACEMENTS +
    IMPORT_METRICS_REPLACEMENTS +
    IMPORT_ADJUSTMENT_REPLACEMENTS
)

# ========== 函数定义 ==========

def dry_run_import_fix():
    """dry_run预览import修复"""
    print("=" * 80)
    print("V15 Import路径修复 - dry_run预览")
    print("=" * 80)

    print(f"\n📊 将应用 {len(ALL_REPLACEMENTS)} 条替换规则：")

    for pattern, replacement in ALL_REPLACEMENTS:
        print(f"   {pattern} → {replacement}")

    print(f"\n📁 将扫描以下目录：")
    for py_dir in ['logic', 'tasks', 'tools', 'scripts', 'backtest']:
        dir_path = ROOT / py_dir
        if dir_path.exists():
            py_files = list(dir_path.rglob("*.py"))
            print(f"   {py_dir}/: {len(py_files)} 个Python文件")

    print(f"\n💡 提示：确认后运行 real_fix_imports() 执行修复")
    print("=" * 80)

def real_fix_imports():
    """修复所有import路径"""
    print("=" * 80)
    print("V15 Import路径修复 - real_fix_imports执行")
    print("=" * 80)

    # 扫描所有Python文件
    py_dirs = ['logic', 'tasks', 'tools', 'scripts', 'backtest']
    all_py_files = []

    for py_dir in py_dirs:
        dir_path = ROOT / py_dir
        if dir_path.exists():
            py_files = list(dir_path.rglob("*.py"))
            all_py_files.extend(py_files)

    print(f"\n📁 扫描到 {len(all_py_files)} 个Python文件")

    # 统计修复情况
    total_files = 0
    total_replacements = 0
    errors = []

    for py_file in all_py_files:
        try:
            # 读取文件
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            # 应用所有替换规则
            for pattern, replacement in ALL_REPLACEMENTS:
                content = re.sub(pattern, replacement, content)

            # 如果内容有变化，写回文件
            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                total_files += 1

                # 统计替换次数
                for pattern, replacement in ALL_REPLACEMENTS:
                    matches = re.findall(pattern, original_content)
                    total_replacements += len(matches)

                print(f"   ✅ 修复：{py_file.relative_to(ROOT)}")

        except Exception as e:
            error_msg = f"❌ 修复失败：{py_file.relative_to(ROOT)} - {e}"
            print(f"   {error_msg}")
            errors.append(error_msg)

    print(f"\n📊 修复结果：")
    print(f"   修复文件：{total_files} 个")
    print(f"   替换次数：{total_replacements} 次")
    print(f"   失败：{len(errors)} 个")

    if errors:
        print(f"\n❌ 错误列表：")
        for error in errors:
            print(f"   {error}")

    print("=" * 80)

    return total_files

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("V15 Import路径修复脚本")
    print("=" * 80 + "\n")

    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法：")
        print("  python scripts/v15_fix_imports.py dry_run  # 预览修复")
        print("  python scripts/v15_fix_imports.py real_fix # 执行修复")
        sys.exit(1)

    command = sys.argv[1]

    if command == "dry_run":
        dry_run_import_fix()
    elif command == "real_fix":
        real_fix_imports()
        print("\n✅ Import路径修复完成！请运行pytest验证修复效果。")
    else:
        print(f"❌ 未知命令：{command}")
        sys.exit(1)

if __name__ == "__main__":
    main()