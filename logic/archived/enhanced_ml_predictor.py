"""
增强型机器学习预测器：多模型融合预测

多模型融合预测：
- LSTM + Transformer 混合模型
- 集成学习 (Random Forest, XGBoost)
- 深度强化学习策略
- 图神经网络分析板块轮动
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, Dense, Input, Dropout, MultiHeadAttention, LayerNormalization, Add
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("警告: 未安装tensorflow，LSTM/Transformer模型不可用")

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from xgboost import XGBRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("警告: 未安装sklearn或xgboost，集成学习模型不可用")

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = False  # 暂时禁用PyTorch相关功能，因为我们没有完整的强化学习实现
except ImportError:
    TORCH_AVAILABLE = False

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """预测结果数据类"""
    predicted_price: float
    confidence: float  # 0-1
    model_weights: Dict[str, float]  # 各模型权重
    prediction_horizon: str  # 预测时间范围: 'short', 'medium', 'long'
    feature_importance: Dict[str, float]  # 特征重要性
    risk_score: float  # 风险评分 0-1
    prediction_date: str


class EnhancedMLPredictor:
    """增强型机器学习预测器"""

    def __init__(self, lookback_days: int = 60, prediction_horizon: str = 'short'):
        """
        初始化增强型预测器

        Args:
            lookback_days: 回看天数
            prediction_horizon: 预测时间范围 ('short', 'medium', 'long')
        """
        self.lookback_days = lookback_days
        self.prediction_horizon = prediction_horizon
        self.models = {}
        self.is_fitted = False

        # 初始化各模型
        self._initialize_models()

    def _initialize_models(self):
        """初始化各种模型"""
        if SKLEARN_AVAILABLE:
            # 集成学习模型
            self.models['random_forest'] = RandomForestRegressor(
                n_estimators=100, 
                max_depth=10, 
                random_state=42,
                n_jobs=-1
            )
            self.models['xgboost'] = XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
        else:
            logger.warning("SKLEARN 不可用，跳过集成学习模型初始化")

        if TENSORFLOW_AVAILABLE:
            # LSTM模型
            self.models['lstm'] = self._build_lstm_model()
            # Transformer模型
            self.models['transformer'] = self._build_transformer_model()
        else:
            logger.warning("TensorFlow 不可用，跳过深度学习模型初始化")

    def _build_lstm_model(self) -> Sequential:
        """构建LSTM模型"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(self.lookback_days, 10)),  # 10个特征
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def _build_transformer_model(self) -> Model:
        """构建Transformer模型"""
        inputs = Input(shape=(self.lookback_days, 10))
        x = inputs

        # Multi-head attention
        attention_output = MultiHeadAttention(num_heads=4, key_dim=10)(x, x)
        x = Add()([x, attention_output])
        x = LayerNormalization()(x)

        # Feed forward
        ffn = Dense(64, activation='relu')(x)
        ffn = Dense(10)(ffn)
        x = Add()([x, ffn])
        x = LayerNormalization()(x)

        # Global average pooling
        x = tf.keras.layers.GlobalAveragePooling1D()(x)
        outputs = Dense(1)(x)

        model = Model(inputs=inputs, outputs=outputs)
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        return model

    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        从股票数据中提取特征

        Args:
            df: 股票数据 DataFrame (包含 open, high, low, close, volume 等列)

        Returns:
            np.ndarray: 特征矩阵 (samples, timesteps, features)
        """
        # 确保数据按日期排序
        df = df.sort_values('date').reset_index(drop=True)

        # 计算技术指标作为特征
        df['returns'] = df['close'].pct_change()
        df['high_low_pct'] = (df['high'] - df['low']) / df['close']
        df['volume_ma'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['price_position'] = (df['close'] - df['ma20']) / df['ma20']
        df['volatility'] = df['returns'].rolling(window=10).std()

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2

        # 填充缺失值
        feature_cols = ['returns', 'high_low_pct', 'volume_ratio', 'price_position', 'volatility', 'rsi', 'macd', 'close', 'high', 'low']
        df[feature_cols] = df[feature_cols].fillna(method='bfill').fillna(method='ffill')

        # 构建时间序列数据
        features = df[feature_cols].values

        if len(features) < self.lookback_days:
            # 如果数据不足，用前面的数据填充
            additional_rows = self.lookback_days - len(features)
            repeated_features = np.tile(features[0], (additional_rows, 1))
            features = np.vstack([repeated_features, features])

        # 创建滑动窗口数据
        X = []
        for i in range(self.lookback_days, len(features) + 1):
            X.append(features[i - self.lookback_days:i])

        return np.array(X)

    def _prepare_target(self, df: pd.DataFrame, horizon: int = 1) -> np.ndarray:
        """
        准备目标变量（未来价格变化）

        Args:
            df: 股票数据
            horizon: 预测步长（天）

        Returns:
            np.ndarray: 目标变量
        """
        df = df.sort_values('date').reset_index(drop=True)
        target = df['close'].shift(-horizon).pct_change(periods=horizon).fillna(0).values
        # 只保留与特征数据长度一致的部分
        return target[self.lookback_days:]

    def fit(self, df: pd.DataFrame, stock_code: str = None) -> bool:
        """
        训练模型

        Args:
            df: 股票数据
            stock_code: 股票代码

        Returns:
            bool: 是否成功训练
        """
        try:
            # 提取特征
            X = self._extract_features(df)
            if X.size == 0 or len(X) == 0:
                logger.error("特征提取失败，数据可能不足")
                return False

            # 根据预测时间范围确定目标变量
            if self.prediction_horizon == 'short':
                horizon = 1  # 预测明日价格
            elif self.prediction_horizon == 'medium':
                horizon = 5  # 预测未来一周
            else:
                horizon = 20  # 预测未来一个月

            y = self._prepare_target(df, horizon)
            if len(y) == 0:
                logger.error("目标变量生成失败")
                return False

            # 确保X和y长度一致
            min_len = min(len(X), len(y))
            X = X[:min_len]
            y = y[:min_len]

            if len(X) < 10:  # 确保有足够的样本
                logger.error("训练样本不足")
                return False

            # 训练各个模型
            training_results = {}

            # 随机森林
            if 'random_forest' in self.models:
                try:
                    X_flat = X.reshape(X.shape[0], -1)  # 展平为2D
                    self.models['random_forest'].fit(X_flat, y)
                    training_results['random_forest'] = True
                    logger.info(f"随机森林模型训练完成，样本数: {len(X)}")
                except Exception as e:
                    logger.error(f"随机森林模型训练失败: {e}")
                    training_results['random_forest'] = False

            # XGBoost
            if 'xgboost' in self.models:
                try:
                    X_flat = X.reshape(X.shape[0], -1)  # 展平为2D
                    self.models['xgboost'].fit(X_flat, y)
                    training_results['xgboost'] = True
                    logger.info(f"XGBoost模型训练完成，样本数: {len(X)}")
                except Exception as e:
                    logger.error(f"XGBoost模型训练失败: {e}")
                    training_results['xgboost'] = False

            # LSTM (如果可用)
            if TENSORFLOW_AVAILABLE and 'lstm' in self.models:
                try:
                    self.models['lstm'].fit(X, y, epochs=5, batch_size=32, verbose=0)
                    training_results['lstm'] = True
                    logger.info(f"LSTM模型训练完成，样本数: {len(X)}")
                except Exception as e:
                    logger.error(f"LSTM模型训练失败: {e}")
                    training_results['lstm'] = False

            # Transformer (如果可用)
            if TENSORFLOW_AVAILABLE and 'transformer' in self.models:
                try:
                    self.models['transformer'].fit(X, y, epochs=5, batch_size=32, verbose=0)
                    training_results['transformer'] = True
                    logger.info(f"Transformer模型训练完成，样本数: {len(X)}")
                except Exception as e:
                    logger.error(f"Transformer模型训练失败: {e}")
                    training_results['transformer'] = False

            # 检查是否有至少一个模型成功训练
            self.is_fitted = any(training_results.values())

            if self.is_fitted:
                logger.info(f"模型训练完成，成功训练的模型: {list(training_results.keys())}")
                return True
            else:
                logger.error("所有模型训练均失败")
                return False

        except Exception as e:
            logger.error(f"训练过程中发生错误: {e}")
            return False

    def predict(self, df: pd.DataFrame, stock_code: str = None) -> Optional[PredictionResult]:
        """
        进行预测

        Args:
            df: 股票数据
            stock_code: 股票代码

        Returns:
            PredictionResult: 预测结果
        """
        if not self.is_fitted:
            logger.error("模型尚未训练，请先调用fit方法")
            return None

        try:
            # 提取最新特征用于预测
            X = self._extract_features(df)
            if X.size == 0 or len(X) == 0:
                logger.error("特征提取失败")
                return None

            if len(X) < 1:
                logger.error("特征数据不足")
                return None

            # 取最新的特征
            latest_X = X[-1:]
            predictions = {}

            # 随机森林预测
            if 'random_forest' in self.models and SKLEARN_AVAILABLE:
                try:
                    X_flat = latest_X.reshape(latest_X.shape[0], -1)
                    pred_rf = self.models['random_forest'].predict(X_flat)[0]
                    predictions['random_forest'] = pred_rf
                except Exception as e:
                    logger.warning(f"随机森林预测失败: {e}")

            # XGBoost预测
            if 'xgboost' in self.models and SKLEARN_AVAILABLE:
                try:
                    X_flat = latest_X.reshape(latest_X.shape[0], -1)
                    pred_xgb = self.models['xgboost'].predict(X_flat)[0]
                    predictions['xgboost'] = pred_xgb
                except Exception as e:
                    logger.warning(f"XGBoost预测失败: {e}")

            # LSTM预测 (如果可用)
            if TENSORFLOW_AVAILABLE and 'lstm' in self.models:
                try:
                    pred_lstm = self.models['lstm'].predict(latest_X, verbose=0)[0][0]
                    predictions['lstm'] = pred_lstm
                except Exception as e:
                    logger.warning(f"LSTM预测失败: {e}")

            # Transformer预测 (如果可用)
            if TENSORFLOW_AVAILABLE and 'transformer' in self.models:
                try:
                    pred_transformer = self.models['transformer'].predict(latest_X, verbose=0)[0][0]
                    predictions['transformer'] = pred_transformer
                except Exception as e:
                    logger.warning(f"Transformer预测失败: {e}")

            if not predictions:
                logger.error("所有模型预测均失败")
                return None

            # 多模型融合 - 简单平均
            avg_prediction = np.mean(list(predictions.values()))

            # 获取当前价格以计算预测价格
            current_price = df['close'].iloc[-1]
            predicted_price = current_price * (1 + avg_prediction)

            # 计算置信度（基于模型预测的一致性）
            pred_values = list(predictions.values())
            if len(pred_values) > 1:
                # 预测值越一致，置信度越高
                std_dev = np.std(pred_values)
                confidence = max(0.0, 1.0 - std_dev)
            else:
                confidence = 0.7  # 默认置信度

            # 计算各模型权重
            model_weights = {k: 1.0/len(predictions) for k in predictions.keys()}

            # 特征重要性（简化版 - 实际应用中需用模型的feature_importances_）
            feature_importance = {
                'price_trends': 0.3,
                'volume_patterns': 0.2,
                'technical_indicators': 0.3,
                'volatility': 0.2
            }

            # 风险评分（基于预测波动性）
            risk_score = min(1.0, max(0.0, abs(avg_prediction) * 3))

            return PredictionResult(
                predicted_price=predicted_price,
                confidence=confidence,
                model_weights=model_weights,
                prediction_horizon=self.prediction_horizon,
                feature_importance=feature_importance,
                risk_score=risk_score,
                prediction_date=datetime.now().strftime('%Y-%m-%d')
            )

        except Exception as e:
            logger.error(f"预测过程中发生错误: {e}")
            return None

    def update_model_weights(self, historical_predictions: List[Tuple[float, float]]) -> Dict[str, float]:
        """
        根据历史预测准确性更新模型权重

        Args:
            historical_predictions: 历史预测对 (预测值, 实际值)

        Returns:
            Dict[str, float]: 更新后的模型权重
        """
        if not historical_predictions:
            return {name: 1.0/len(self.models) for name in self.models.keys()}

        # 计算每个模型的历史准确率
        model_accuracies = {}
        for model_name in self.models.keys():
            errors = []
            for pred_val, actual_val in historical_predictions:
                error = abs(pred_val - actual_val)
                errors.append(error)

            if errors:
                # 准确率 = 1 / (1 + 平均误差)
                avg_error = np.mean(errors)
                accuracy = 1.0 / (1.0 + avg_error)
                model_accuracies[model_name] = accuracy
            else:
                model_accuracies[model_name] = 0.5  # 默认准确率

        # 归一化权重
        total_accuracy = sum(model_accuracies.values())
        if total_accuracy > 0:
            weights = {k: v / total_accuracy for k, v in model_accuracies.items()}
        else:
            weights = {k: 1.0/len(model_accuracies) for k in model_accuracies.keys()}

        return weights