"""
测试中期系统集成
"""

import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 测试多模态融合决策系统
print("=" * 50)
print("测试1: 多模态融合决策系统")
print("=" * 50)

try:
    from logic.multimodal_fusion_system import MultimodalFusionSystem

    system = MultimodalFusionSystem()

    # 模拟数据
    text = "公司发布重大利好，业绩大幅增长，创新高，市场看好"

    dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30)
    kline_data = pd.DataFrame({
        'date': dates,
        'open': np.linspace(10, 15, 30),
        'close': np.linspace(10.5, 15.5, 30),
        'high': np.linspace(10.6, 15.6, 30),
        'low': np.linspace(9.9, 14.9, 30),
        'volume': np.linspace(1000000, 5000000, 30)
    })

    ts_data = kline_data.copy()

    # 分析
    result = system.analyze(
        stock_code='600000',
        text=text,
        kline_data=kline_data,
        ts_data=ts_data
    )

    print(f"✅ 股票代码: {result['stock_code']}")
    print(f"✅ 决策: {result['decision']}")
    print(f"✅ 置信度: {result['confidence']:.2f}")
    print(f"✅ 文本贡献度: {result['text_contribution']:.2f}")
    print(f"✅ 图像贡献度: {result['image_contribution']:.2f}")
    print(f"✅ 时序贡献度: {result['ts_contribution']:.2f}")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    print()

# 测试自适应情绪权重系统
print("=" * 50)
print("测试2: 自适应情绪权重系统")
print("=" * 50)

try:
    from logic.adaptive_sentiment_weights import AdaptiveSentimentWeightsSystem

    system = AdaptiveSentimentWeightsSystem()

    # 模拟市场数据
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30)
    market_data = pd.DataFrame({
        'date': dates,
        'close': np.linspace(3000, 3200, 30) + np.random.randn(30) * 50,
        'volume': np.linspace(100000000, 150000000, 30),
        'pct_chg': np.random.randn(30) * 0.02
    })

    # 分析和调整
    result = system.analyze_and_adjust(market_data)

    print(f"✅ 市场环境: {result['environment']}")
    print(f"✅ 置信度: {result['confidence']:.2f}")
    print(f"✅ 预测持续时间: {result['duration']} 天")
    print(f"✅ 当前权重:")
    for key, value in result['weights'].items():
        print(f"   {key}: {value:.2f}")

    if result['adjustment']['adjusted']:
        print(f"✅ 权重已调整:")
        for key, change in result['adjustment']['changes'].items():
            if abs(change) > 0.01:
                print(f"   {key}: {change:+.2f}")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    print()

# 测试龙头战法自适应参数系统
print("=" * 50)
print("测试3: 龙头战法自适应参数系统")
print("=" * 50)

try:
    from logic.dragon_adaptive_params import DragonAdaptiveParameterSystem

    system = DragonAdaptiveParameterSystem()

    # 模拟历史数据
    dates = pd.date_range(start=datetime.now() - timedelta(days=100), periods=100)
    historical_data = pd.DataFrame({
        'date': dates,
        'close': np.linspace(10, 20, 100) + np.random.randn(100) * 2,
        'volume': np.linspace(1000000, 5000000, 100),
        'pct_chg': np.random.randn(100) * 0.05
    })

    # 优化参数
    print("优化参数中...")
    optimization_result = system.optimize(historical_data, n_iterations=10)

    print(f"✅ 最佳评分: {optimization_result['best_score']:.4f}")
    print(f"✅ 最佳参数:")
    for key, value in optimization_result['best_params'].items():
        print(f"   {key}: {value:.4f}")

    # 在线调整
    performance = {
        'sharpe_ratio': 0.8,
        'win_rate': 0.35,
        'avg_return': 0.12,
        'max_drawdown': 0.18
    }

    adjustment = system.online_adjust(performance)

    print(f"✅ 调整状态: {'已调整' if adjustment['adjusted'] else '未调整'}")
    if adjustment['adjusted']:
        print(f"✅ 调整次数: {len(adjustment['adjustments'])}")

    print(f"✅ 当前参数:")
    for key, value in system.get_current_params().items():
        print(f"   {key}: {value:.4f}")
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    print()

# 测试元学习系统
print("=" * 50)
print("测试4: 元学习系统")
print("=" * 50)

try:
    from logic.meta_learning_system import MetaLearningSystem

    system = MetaLearningSystem()

    # 创建训练任务
    print("创建训练任务...")
    for i in range(5):
        dates = pd.date_range(start=datetime.now() - timedelta(days=20), periods=20)
        train_data = pd.DataFrame({
            'date': dates[:15],
            'close': np.linspace(10, 15, 15) + np.random.randn(15) * 0.5,
            'volume': np.linspace(1000000, 2000000, 15),
            'pct_chg': np.random.randn(15) * 0.02
        })

        test_data = pd.DataFrame({
            'date': dates[15:],
            'close': np.linspace(15, 18, 5) + np.random.randn(5) * 0.5,
            'volume': np.linspace(2000000, 2500000, 5),
            'pct_chg': np.random.randn(5) * 0.02
        })

        system.create_task(f'task_{i}', train_data, test_data)

    # 元训练
    print("元训练中...")
    training_result = system.meta_train(n_epochs=20, tasks_per_epoch=3)

    if training_result['success']:
        print(f"✅ 训练完成!")
        print(f"✅ 最终元损失: {training_result['final_meta_loss']:.4f}")
    else:
        print(f"❌ 训练失败: {training_result['message']}")

    # 适应新任务
    print("适应新任务...")
    new_dates = pd.date_range(start=datetime.now() - timedelta(days=10), periods=10)
    support_data = pd.DataFrame({
        'date': new_dates[:5],
        'close': np.linspace(20, 22, 5) + np.random.randn(5) * 0.5,
        'volume': np.linspace(3000000, 3500000, 5),
        'pct_chg': np.random.randn(5) * 0.02
    })

    query_data = pd.DataFrame({
        'date': new_dates[5:],
        'close': np.linspace(22, 24, 5) + np.random.randn(5) * 0.5,
        'volume': np.linspace(3500000, 4000000, 5),
        'pct_chg': np.random.randn(5) * 0.02
    })

    adaptation_result = system.adapt_to_new_task(
        'new_task',
        support_data,
        query_data,
        n_steps=5
    )

    print(f"✅ 任务ID: {adaptation_result['task_id']}")
    print(f"✅ 适应损失: {adaptation_result['adaptation_loss']:.4f}")
    print(f"✅ 测试损失: {adaptation_result['test_loss']:.4f}")
    print(f"✅ 预测值: {adaptation_result['predictions'][:3]}...")  # 只显示前3个
    print()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    print()

print("=" * 50)
print("✅ 所有中期系统测试完成！")
print("=" * 50)