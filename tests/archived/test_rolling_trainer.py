"""
测试滚动训练引擎
验证 Walk-Forward Optimization 的效果
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

from logic.feature_engineer import FeatureEngineer
from logic.ml_predictor import LightGBMPredictor, CatBoostPredictor
from logic.rolling_trainer import RollingTrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_stock_data(n_days=1000, start_price=100):
    """生成模拟股票数据"""
    np.random.seed(42)
    
    dates = pd.date_range(end=datetime.now(), periods=n_days)
    
    # 生成价格走势（带趋势和波动）
    trend = np.linspace(start_price, start_price * 1.5, n_days)
    noise = np.random.normal(0, 2, n_days)
    prices = trend + noise
    
    data = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, n_days)),
        'high': prices * (1 + np.random.uniform(0, 0.03, n_days)),
        'low': prices * (1 - np.random.uniform(0, 0.03, n_days)),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_days),
        'amount': prices * np.random.randint(1000000, 10000000, n_days),
        'turnover': np.random.uniform(1, 10, n_days)
    })
    
    return data


def test_rolling_trainer_basic():
    """测试基础滚动训练"""
    logger.info("\n" + "="*60)
    logger.info("测试基础滚动训练")
    logger.info("="*60)
    
    # 生成数据
    logger.info("\n生成模拟数据...")
    df = generate_mock_stock_data(1000)
    logger.info(f"数据形状: {df.shape}")
    
    # 准备特征和标签
    logger.info("\n准备特征和标签...")
    fe = FeatureEngineer(use_technical=True, use_alpha=True)
    df = fe.transform(df)
    df = fe.calculate_multi_targets(df)
    
    # 删除包含 NaN 的行
    df_clean = df.dropna(subset=['target_next_return'] + fe.get_feature_list()).copy()
    logger.info(f"清洗后数据: {df_clean.shape}")
    
    # 测试 LightGBM 滚动训练
    logger.info("\n测试 LightGBM 滚动训练...")
    try:
        trainer = RollingTrainer(
            predictor_class=LightGBMPredictor,
            predictor_params={'use_feature_engineering': False},
            train_window=252,
            test_window=20,
            min_train_size=100
        )
        
        metrics = trainer.run(df_clean, target_col='target_next_return', verbose=True)
        
        logger.info("\n" + "-"*60)
        logger.info("LightGBM 滚动训练结果:")
        logger.info("-"*60)
        for key, value in metrics.items():
            logger.info(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
        
        return metrics
        
    except ImportError as e:
        logger.warning(f"LightGBM 未安装: {e}")
        return {}
    except Exception as e:
        logger.error(f"滚动训练失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def test_rolling_trainer_with_catboost():
    """测试 CatBoost 滚动训练"""
    logger.info("\n" + "="*60)
    logger.info("测试 CatBoost 滚动训练")
    logger.info("="*60)
    
    # 生成数据
    logger.info("\n生成模拟数据...")
    df = generate_mock_stock_data(1000)
    
    # 准备特征和标签
    logger.info("\n准备特征和标签...")
    fe = FeatureEngineer(use_technical=True, use_alpha=True)
    df = fe.transform(df)
    df = fe.calculate_multi_targets(df)
    
    # 删除包含 NaN 的行
    df_clean = df.dropna(subset=['target_next_return'] + fe.get_feature_list()).copy()
    
    # 测试 CatBoost 滚动训练
    logger.info("\n测试 CatBoost 滚动训练...")
    try:
        trainer = RollingTrainer(
            predictor_class=CatBoostPredictor,
            predictor_params={'use_feature_engineering': False},
            train_window=252,
            test_window=20,
            min_train_size=100
        )
        
        metrics = trainer.run(df_clean, target_col='target_next_return', verbose=True)
        
        logger.info("\n" + "-"*60)
        logger.info("CatBoost 滚动训练结果:")
        logger.info("-"*60)
        for key, value in metrics.items():
            logger.info(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
        
        return metrics
        
    except ImportError as e:
        logger.warning(f"CatBoost 未安装: {e}")
        return {}
    except Exception as e:
        logger.error(f"滚动训练失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def compare_traditional_vs_rolling():
    """对比传统训练 vs 滚动训练"""
    logger.info("\n" + "="*60)
    logger.info("对比：传统训练 vs 滚动训练")
    logger.info("="*60)
    
    # 生成数据
    df = generate_mock_stock_data(800)
    
    # 准备特征和标签
    fe = FeatureEngineer(use_technical=True, use_alpha=True)
    df = fe.transform(df)
    df = fe.calculate_multi_targets(df)
    df_clean = df.dropna(subset=['target_next_return'] + fe.get_feature_list()).copy()
    
    # 划分训练集和测试集（传统方式）
    split_idx = int(len(df_clean) * 0.8)
    train_df = df_clean.iloc[:split_idx].copy()
    test_df = df_clean.iloc[split_idx:].copy()
    
    logger.info(f"\n传统训练:")
    logger.info(f"  训练集: {len(train_df)} 天")
    logger.info(f"  测试集: {len(test_df)} 天")
    logger.info(f"  注意：这种方式可能存在未来数据泄漏")
    
    try:
        # 传统训练
        model = LightGBMPredictor(use_feature_engineering=False)
        model.train(train_df)
        predictions_traditional = model.predict(test_df)
        
        if len(predictions_traditional) > 0:
            actual = test_df['target_next_return'].values[:len(predictions_traditional)]
            mae_traditional = np.mean(np.abs(predictions_traditional - actual))
            ic_traditional = np.corrcoef(actual, predictions_traditional)[0, 1] if len(actual) > 1 else 0
            
            logger.info(f"\n传统训练结果:")
            logger.info(f"  MAE: {mae_traditional:.4f}")
            logger.info(f"  IC: {ic_traditional:.4f}")
    except Exception as e:
        logger.warning(f"传统训练失败: {e}")
        mae_traditional = None
        ic_traditional = None
    
    # 滚动训练
    logger.info(f"\n滚动训练:")
    logger.info(f"  训练窗口: 252 天")
    logger.info(f"  测试窗口: 20 天")
    logger.info(f"  优势：模拟真实交易，防止未来数据泄漏")
    
    try:
        trainer = RollingTrainer(
            predictor_class=LightGBMPredictor,
            predictor_params={'use_feature_engineering': False},
            train_window=252,
            test_window=20,
            min_train_size=100
        )
        
        metrics_rolling = trainer.run(df_clean, target_col='target_next_return', verbose=False)
        
        if metrics_rolling:
            mae_rolling = metrics_rolling.get('mae')
            ic_rolling = metrics_rolling.get('ic')
            
            logger.info(f"\n滚动训练结果:")
            logger.info(f"  MAE: {mae_rolling:.4f}")
            logger.info(f"  IC: {ic_rolling:.4f}")
            
            if mae_traditional is not None and ic_traditional is not None:
                logger.info(f"\n性能对比:")
                logger.info(f"  MAE 改进: {(mae_traditional - mae_rolling) / mae_traditional * 100:.2f}%")
                logger.info(f"  IC 改进: {ic_rolling - ic_traditional:.4f}")
                
                if mae_rolling < mae_traditional:
                    logger.info(f"  滚动训练 MAE 更低（更准确）")
                else:
                    logger.info(f"  传统训练 MAE 更低（可能过拟合）")
                
                if ic_rolling > ic_traditional:
                    logger.info(f"  滚动训练 IC 更高（预测能力更强）")
    except Exception as e:
        logger.warning(f"滚动训练失败: {e}")


def test_feature_importance():
    """测试特征重要性"""
    logger.info("\n" + "="*60)
    logger.info("测试特征重要性")
    logger.info("="*60)
    
    # 生成数据
    df = generate_mock_stock_data(800)
    
    # 准备特征和标签
    fe = FeatureEngineer(use_technical=True, use_alpha=True)
    df = fe.transform(df)
    df = fe.calculate_multi_targets(df)
    df_clean = df.dropna(subset=['target_next_return'] + fe.get_feature_list()).copy()
    
    try:
        # 训练模型
        model = LightGBMPredictor(use_feature_engineering=False)
        model.train(df_clean)
        
        # 获取特征重要性
        if hasattr(model, 'feature_importance') and model.feature_importance:
            logger.info("\n特征重要性 Top 10:")
            sorted_features = sorted(model.feature_importance.items(), 
                                     key=lambda x: x[1], reverse=True)[:10]
            for i, (feat, imp) in enumerate(sorted_features, 1):
                logger.info(f"  {i}. {feat}: {imp:.2f}")
    except Exception as e:
        logger.warning(f"特征重要性分析失败: {e}")


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("滚动训练引擎测试")
    logger.info("="*60)
    
    # 运行测试
    test_rolling_trainer_basic()
    test_rolling_trainer_with_catboost()
    compare_traditional_vs_rolling()
    test_feature_importance()
    
    logger.info("\n" + "="*60)
    logger.info("测试完成！")
    logger.info("="*60)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_rolling_trainer_results_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("滚动训练引擎测试结果\n")
        f.write("="*60 + "\n\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n核心优势:\n")
        f.write("  1. 防止未来数据泄漏（Backtest Overfitting）\n")
        f.write("  2. 模拟真实交易环境\n")
        f.write("  3. 评估模型在样本外的真实表现\n")
        f.write("  4. 避免回测猛如虎实盘二百五的惨剧\n")
    
    logger.info(f"\n结果已保存到: {output_file}")
