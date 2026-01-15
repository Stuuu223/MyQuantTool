"""
测试深度特征工程
验证高级特征对模型性能的提升
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

from logic.feature_engineer import FeatureEngineer
from logic.ml_predictor import LightGBMPredictor, CatBoostPredictor, EnsemblePredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_mock_data(n_days=500):
    """生成模拟股票数据"""
    np.random.seed(42)
    
    dates = pd.date_range(end=datetime.now(), periods=n_days)
    
    # 生成价格走势（带趋势和波动）
    trend = np.linspace(10, 20, n_days)
    noise = np.random.normal(0, 0.5, n_days)
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


def test_feature_engineering():
    """测试特征工程"""
    logger.info("="*60)
    logger.info("开始测试深度特征工程")
    logger.info("="*60)
    
    # 生成模拟数据
    logger.info("\n生成模拟数据...")
    df = generate_mock_data(500)
    logger.info(f"数据形状: {df.shape}")
    
    # 初始化特征工程器
    logger.info("\n初始化特征工程器...")
    fe = FeatureEngineer()
    
    # 计算技术特征
    logger.info("\n计算技术特征...")
    df = fe.calculate_technical_features(df)
    logger.info(f"技术特征数量: {len([col for col in df.columns if 'rsi_' in col or 'macd_' in col or 'bb_' in col])}")
    
    # 计算截面特征
    logger.info("\n计算截面特征...")
    df = fe.calculate_cross_sectional_features(df)
    logger.info(f"截面特征数量: {len([col for col in df.columns if 'rel_' in col or 'rank_' in col])}")
    
    # 计算微观结构特征
    logger.info("\n计算微观结构特征...")
    df = fe.calculate_microstructure_features(df)
    logger.info(f"微观结构特征数量: {len([col for col in df.columns if 'order_' in col or 'volume_' in col])}")
    
    # 计算多目标
    logger.info("\n计算多目标...")
    df = fe.calculate_multi_targets(df)
    logger.info(f"多目标: {[col for col in df.columns if col.startswith('target_')]}")
    
    # 获取特征列表
    features = fe.get_feature_list()
    logger.info(f"\n总特征数量: {len(features)}")
    logger.info(f"特征列表: {features[:10]}...")
    
    # 显示特征重要性示例
    logger.info("\n特征说明:")
    feature_descriptions = {
        'rsi_slope': 'RSI 斜率 - 捕捉动量变化趋势',
        'volume_ratio': '量比 - 成交量相对强度',
        'rel_strength': '相对强弱 - 个股相对大盘表现',
        'rank_in_sector': '板块排名 - 在板块内的相对位置',
        'order_imbalance': '订单不平衡 - 买卖盘力量对比',
        'price_momentum_5d': '5日价格动量 - 短期趋势',
        'volatility_20d': '20日波动率 - 风险度量',
        'macd_divergence': 'MACD 背离 - 潜在反转信号'
    }
    
    for feat, desc in feature_descriptions.items():
        if feat in df.columns:
            logger.info(f"  ✓ {feat}: {desc}")
        else:
            logger.info(f"  ✗ {feat}: {desc} (未生成)")
    
    return df


def test_model_with_features():
    """测试模型使用特征工程"""
    logger.info("\n" + "="*60)
    logger.info("测试模型使用特征工程")
    logger.info("="*60)
    
    # 生成数据
    df = generate_mock_data(500)
    
    # 测试 LightGBM（带特征工程）
    logger.info("\n测试 LightGBM（带特征工程）...")
    lgb_predictor = LightGBMPredictor(use_feature_engineering=True)
    try:
        lgb_predictor.train(df)
        logger.info(f"✓ LightGBM 训练成功")
        logger.info(f"  特征重要性 Top 5:")
        if lgb_predictor.feature_importance:
            sorted_features = sorted(lgb_predictor.feature_importance.items(), 
                                     key=lambda x: x[1], reverse=True)[:5]
            for feat, imp in sorted_features:
                logger.info(f"    {feat}: {imp:.2f}")
    except ImportError as e:
        logger.warning(f"LightGBM 未安装: {e}")
    
    # 测试 CatBoost（带特征工程）
    logger.info("\n测试 CatBoost（带特征工程）...")
    cat_predictor = CatBoostPredictor(use_feature_engineering=True)
    try:
        cat_predictor.train(df)
        logger.info(f"✓ CatBoost 训练成功")
        logger.info(f"  特征数量: {len(cat_predictor.feature_names)}")
    except ImportError as e:
        logger.warning(f"CatBoost 未安装: {e}")
    
    # 测试集成模型
    logger.info("\n测试集成预测器...")
    try:
        ensemble = EnsemblePredictor()
        ensemble.train(df)
        logger.info(f"✓ 集成模型训练成功")
    except Exception as e:
        logger.warning(f"集成模型训练失败: {e}")


def compare_with_without_features():
    """对比有无特征工程的性能"""
    logger.info("\n" + "="*60)
    logger.info("对比：有无特征工程的性能差异")
    logger.info("="*60)
    
    df = generate_mock_data(500)
    
    # 准备测试数据（避免数据泄露）
    train_size = int(len(df) * 0.8)
    train_df = df.iloc[:train_size].copy()
    test_df = df.iloc[train_size:].copy()
    
    logger.info(f"\n训练集大小: {len(train_df)}, 测试集大小: {len(test_df)}")
    
    # 基础特征
    logger.info("\n使用基础特征...")
    try:
        lgb_basic = LightGBMPredictor(use_feature_engineering=False)
        lgb_basic.train(train_df)
        predictions_basic = lgb_basic.predict(test_df)
        
        if len(predictions_basic) > 0:
            actual = test_df['close'].pct_change().shift(-1).dropna().values[:len(predictions_basic)]
            mae_basic = np.mean(np.abs(predictions_basic - actual))
            logger.info(f"  基础特征 MAE: {mae_basic:.4f}")
    except Exception as e:
        logger.warning(f"基础特征测试失败: {e}")
        mae_basic = None
    
    # 高级特征
    logger.info("\n使用高级特征...")
    try:
        lgb_advanced = LightGBMPredictor(use_feature_engineering=True)
        lgb_advanced.train(train_df)
        predictions_advanced = lgb_advanced.predict(test_df)
        
        if len(predictions_advanced) > 0:
            actual = test_df['close'].pct_change().shift(-1).dropna().values[:len(predictions_advanced)]
            mae_advanced = np.mean(np.abs(predictions_advanced - actual))
            logger.info(f"  高级特征 MAE: {mae_advanced:.4f}")
            
            if mae_basic is not None:
                improvement = (mae_basic - mae_advanced) / mae_basic * 100
                logger.info(f"\n✓ 性能提升: {improvement:.2f}%")
    except Exception as e:
        logger.warning(f"高级特征测试失败: {e}")


if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("深度特征工程测试")
    logger.info("="*60)
    
    # 运行测试
    df = test_feature_engineering()
    test_model_with_features()
    compare_with_without_features()
    
    logger.info("\n" + "="*60)
    logger.info("测试完成！")
    logger.info("="*60)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_feature_engineering_results_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("深度特征工程测试结果\n")
        f.write("="*60 + "\n\n")
        f.write(f"数据形状: {df.shape}\n")
        f.write(f"特征数量: {len([col for col in df.columns if col not in ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'turnover']])}\n")
        f.write(f"\n特征列表:\n")
        
        fe = FeatureEngineer()
        features = fe.get_feature_list()
        for i, feat in enumerate(features, 1):
            f.write(f"  {i}. {feat}\n")
    
    logger.info(f"\n结果已保存到: {output_file}")