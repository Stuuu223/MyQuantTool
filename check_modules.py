"""
检查 main.py 中引用的 UI 模块是否存在
"""

import os

ui_dir = "E:\\MyQuantTool\\ui"

# 从 main.py 中提取的所有 UI 模块
ui_modules = [
    'dragon_strategy',
    'ma_strategy',
    'limit_up',
    'auction',
    'volume_price',
    'capital',
    'midway_strategy',
    'buy_point_scanner',
    'capital_network',
    'capital_profiler',
    'short_term_trend',
    'opportunity_predictor',
    'multi_agent_analysis',
    'smart_news_analysis',  # 已注释
    'realtime_sentiment_tab',
    'dragon_tracking_tab',
    'auction_prediction_tab',
    'online_parameter_tab',
    'market_sentiment_tab',
    'trading_execution_tab',
    'backtest',
    'advanced_backtest',
    'lstm_predictor',
    'portfolio_optimizer_tab',
    'autonomous_learning_tab',
    'parameter_optimization',
    'kline_patterns',
    'strategy_factory_tab',
    'strategy_comparison_tab',
    'multimodal_fusion_tab',
    'adaptive_sentiment_weights_tab',
    'dragon_adaptive_params_tab',
    'meta_learning_tab',
    'rl_optimization_tab',
    'distributed_training_tab',
    'federated_learning_tab',
    'autonomous_evolution_tab',
    'paper_trading',
    'risk',
    'smart_recommend',
    'live_monitoring',
    'performance_optimizer',
    'settings',
    'history',
    'data_monitor'
]

print("=" * 60)
print("检查 UI 模块是否存在")
print("=" * 60)

missing_modules = []
existing_modules = []

for module in ui_modules:
    module_file = os.path.join(ui_dir, f"{module}.py")
    if os.path.exists(module_file):
        existing_modules.append(module)
    else:
        missing_modules.append(module)

print(f"\n✅ 存在的模块 ({len(existing_modules)} 个):")
for module in existing_modules:
    print(f"  - {module}")

print(f"\n❌ 缺失的模块 ({len(missing_modules)} 个):")
for module in missing_modules:
    print(f"  - {module}")

if missing_modules:
    print(f"\n⚠️ 警告：有 {len(missing_modules)} 个模块缺失，可能导致程序启动失败")
else:
    print("\n✅ 所有模块都存在")

print("=" * 60)