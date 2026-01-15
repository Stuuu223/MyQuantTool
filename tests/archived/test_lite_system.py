"""
测试 Lite 版系统性能
验证优化后的系统是否正常工作
"""

import numpy as np
import pandas as pd
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    创建测试数据

    Args:
        n_samples: 样本数量

    Returns:
        测试数据 DataFrame
    """
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=n_samples)

    # 生成模拟股价数据
    returns = np.random.randn(n_samples) * 0.02
    prices = 100 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'high': prices * (1 + np.abs(np.random.randn(n_samples)) * 0.01),
        'low': prices * (1 - np.abs(np.random.randn(n_samples)) * 0.01),
        'volume': np.random.randint(1000000, 10000000, n_samples)
    })

    return df


def test_optuna_optimizer():
    """测试 Optuna 优化器"""
    logger.info("\n" + "="*60)
    logger.info("测试 Optuna 优化器")
    logger.info("="*60)

    from logic.autonomous_evolution_system import StrategyOptimizer

    def dummy_objective(trial, params):
        """模拟目标函数"""
        # 模拟计算延迟
        time.sleep(0.01)
        # 返回模拟评分
        return np.random.normal(0.8, 0.1)

    param_space = {
        'ma_short': (5, 20),
        'ma_long': (20, 60),
        'stop_loss': (0.02, 0.10),
        'strategy_type': ['MA', 'MACD', 'RSI']
    }

    optimizer = StrategyOptimizer(n_trials=10, n_jobs=-1)

    start_time = time.time()
    result = optimizer.optimize(
        objective_func=dummy_objective,
        param_space=param_space
    )
    elapsed_time = time.time() - start_time

    logger.info(f"✓ Optuna 优化完成")
    logger.info(f"  - 耗时: {elapsed_time:.2f}秒")
    logger.info(f"  - 最佳评分: {result['best_score']:.4f}")
    logger.info(f"  - 最佳参数: {result['best_params']}")

    # 测试参数重要性
    importance = optimizer.get_feature_importance()
    logger.info(f"  - 参数重要性: {importance}")

    return True


def test_lightgbm_predictor():
    """测试 LightGBM 预测器"""
    logger.info("\n" + "="*60)
    logger.info("测试 LightGBM 预测器")
    logger.info("="*60)

    from logic.ml_predictor import LightGBMPredictor

    # 创建测试数据
    df = create_test_data(1000)

    predictor = LightGBMPredictor()

    # 训练
    start_time = time.time()
    predictor.train(df)
    train_time = time.time() - start_time

    logger.info(f"✓ LightGBM 训练完成")
    logger.info(f"  - 训练耗时: {train_time:.2f}秒")

    # 预测
    start_time = time.time()
    predictions = predictor.predict(df)
    predict_time = time.time() - start_time

    logger.info(f"✓ LightGBM 预测完成")
    logger.info(f"  - 预测耗时: {predict_time:.4f}秒")
    logger.info(f"  - 预测数量: {len(predictions)}")
    logger.info(f"  - 预测示例（最后5个）: {predictions[-5:]}")

    # 特征重要性
    if predictor.feature_importance:
        top_features = sorted(predictor.feature_importance.items(),
                             key=lambda x: x[1], reverse=True)[:5]
        logger.info(f"  - 重要特征: {top_features}")

    return True


def test_catboost_predictor():
    """测试 CatBoost 预测器"""
    logger.info("\n" + "="*60)
    logger.info("测试 CatBoost 预测器")
    logger.info("="*60)

    from logic.ml_predictor import CatBoostPredictor

    df = create_test_data(1000)
    predictor = CatBoostPredictor()

    # 训练
    start_time = time.time()
    predictor.train(df)
    train_time = time.time() - start_time

    logger.info(f"✓ CatBoost 训练完成")
    logger.info(f"  - 训练耗时: {train_time:.2f}秒")

    # 预测
    start_time = time.time()
    predictions = predictor.predict(df)
    predict_time = time.time() - start_time

    logger.info(f"✓ CatBoost 预测完成")
    logger.info(f"  - 预测耗时: {predict_time:.4f}秒")
    logger.info(f"  - 预测数量: {len(predictions)}")

    return True


def test_xgboost_predictor():
    """测试 XGBoost 预测器"""
    logger.info("\n" + "="*60)
    logger.info("测试 XGBoost 预测器")
    logger.info("="*60)

    from logic.ml_predictor import XGBoostPredictor

    df = create_test_data(1000)
    predictor = XGBoostPredictor()

    # 训练
    start_time = time.time()
    predictor.train(df)
    train_time = time.time() - start_time

    logger.info(f"✓ XGBoost 训练完成")
    logger.info(f"  - 训练耗时: {train_time:.2f}秒")

    # 预测
    start_time = time.time()
    predictions = predictor.predict(df)
    predict_time = time.time() - start_time

    logger.info(f"✓ XGBoost 预测完成")
    logger.info(f"  - 预测耗时: {predict_time:.4f}秒")
    logger.info(f"  - 预测数量: {len(predictions)}")

    return True


def test_ensemble_predictor():
    """测试集成预测器"""
    logger.info("\n" + "="*60)
    logger.info("测试集成预测器")
    logger.info("="*60)

    from logic.ml_predictor import LightGBMPredictor, CatBoostPredictor, XGBoostPredictor, EnsemblePredictor

    df = create_test_data(1000)

    # 创建预测器
    lgb = LightGBMPredictor()
    cat = CatBoostPredictor()
    xgb = XGBoostPredictor()

    # 训练
    logger.info("训练各个模型...")
    lgb.train(df)
    cat.train(df)
    xgb.train(df)

    # 集成
    ensemble = EnsemblePredictor([lgb, cat, xgb])

    # 预测
    start_time = time.time()
    predictions = ensemble.predict(df)
    predict_time = time.time() - start_time

    logger.info(f"✓ 集成预测完成")
    logger.info(f"  - 预测耗时: {predict_time:.4f}秒")
    logger.info(f"  - 预测数量: {len(predictions)}")

    return True


def test_rule_based_agent():
    """测试规则代理"""
    logger.info("\n" + "="*60)
    logger.info("测试规则代理")
    logger.info("="*60)

    from logic.ai_agent import RuleBasedAgent

    agent = RuleBasedAgent()

    price_data = {
        'current_price': 10.50,
        'change_percent': 3.2,
        'volume': 5000000
    }

    technical_data = {
        'rsi': {'RSI': 65},
        'macd': {'Trend': '多头', 'Histogram': 0.05},
        'bollinger': {'上轨': 10.80, '下轨': 9.50, 'Trend': '上行'},
        'money_flow': {'资金流向': '流入', '主力净流入': 1000000},
        'kdj': {'K': 60, 'D': 55, 'J': 70}
    }

    start_time = time.time()
    report = agent.analyze_stock("000001", price_data, technical_data)
    elapsed_time = time.time() - start_time

    logger.info(f"✓ 规则代理分析完成")
    logger.info(f"  - 耗时: {elapsed_time:.4f}秒")
    logger.info(f"\n分析报告:\n{report}")

    return True


def test_incremental_learning():
    """测试增量学习"""
    logger.info("\n" + "="*60)
    logger.info("测试增量学习")
    logger.info("="*60)

    from logic.autonomous_learning_system import AutonomousLearningSystem

    # 创建模拟数据
    np.random.seed(42)
    X_init = np.random.randn(800, 10)
    y_init = np.sum(X_init, axis=1) + np.random.randn(800) * 0.1

    X_new = np.random.randn(200, 10)
    y_new = np.sum(X_new, axis=1) + np.random.randn(200) * 0.1

    # 初始化系统
    system = AutonomousLearningSystem(update_interval=1, enable_automl=True)

    # 初始化
    start_time = time.time()
    system.initialize(X_init, y_init)
    init_time = time.time() - start_time

    logger.info(f"✓ 系统初始化完成")
    logger.info(f"  - 初始化耗时: {init_time:.2f}秒")

    # 添加新数据
    start_time = time.time()
    system.add_new_data(X_new, y_new)
    update_time = time.time() - start_time

    logger.info(f"✓ 增量更新完成")
    logger.info(f"  - 更新耗时: {update_time:.2f}秒")

    # 预测
    X_test = np.random.randn(100, 10)
    start_time = time.time()
    predictions = system.predict(X_test)
    predict_time = time.time() - start_time

    logger.info(f"✓ 预测完成")
    logger.info(f"  - 预测耗时: {predict_time:.4f}秒")
    logger.info(f"  - 预测数量: {len(predictions)}")

    # 获取状态
    status = system.get_status()
    logger.info(f"  - 系统状态: {status}")

    return True


def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "="*60)
    logger.info("开始测试 Lite 版系统")
    logger.info("="*60)

    tests = [
        ("Optuna 优化器", test_optuna_optimizer),
        ("LightGBM 预测器", test_lightgbm_predictor),
        ("CatBoost 预测器", test_catboost_predictor),
        ("XGBoost 预测器", test_xgboost_predictor),
        ("集成预测器", test_ensemble_predictor),
        ("规则代理", test_rule_based_agent),
        ("增量学习", test_incremental_learning)
    ]

    results = {}
    total_start_time = time.time()

    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"运行测试: {test_name}")
            logger.info(f"{'='*60}")

            success = test_func()
            results[test_name] = "✓ 通过" if success else "✗ 失败"

        except Exception as e:
            logger.error(f"✗ 测试失败: {test_name}")
            logger.error(f"  错误: {str(e)}")
            results[test_name] = f"✗ 错误: {str(e)}"

    total_time = time.time() - total_start_time

    # 输出总结
    logger.info("\n" + "="*60)
    logger.info("测试总结")
    logger.info("="*60)

    for test_name, result in results.items():
        logger.info(f"{test_name}: {result}")

    logger.info(f"\n总耗时: {total_time:.2f}秒")
    logger.info("\n" + "="*60)

    return results


if __name__ == "__main__":
    results = run_all_tests()

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"test_lite_results_{timestamp}.txt"

    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("Lite 版系统测试结果\n")
        f.write(f"测试时间: {datetime.now()}\n")
        f.write("="*60 + "\n\n")

        for test_name, result in results.items():
            f.write(f"{test_name}: {result}\n")

    logger.info(f"\n测试结果已保存到: {result_file}")
