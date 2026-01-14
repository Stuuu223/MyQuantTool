"""
机器学习预测模型（Lite 版 + 深度特征工程）
使用 LightGBM/CatBoost 替代深度学习，速度提升 100 倍+
集成高级特征工程，从"拟合数据"进化为"寻找 Alpha"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from abc import ABC, abstractmethod
import logging
import pickle
import os
from datetime import datetime

from logic.feature_engineer import FeatureEngineer

logger = logging.getLogger(__name__)


class MLPredictorBase(ABC):
    """
    机器学习预测器基类（增强版）
    """

    def __init__(self, name: str, use_feature_engineering: bool = True):
        """
        初始化预测器

        Args:
            name: 模型名称
            use_feature_engineering: 是否使用特征工程
        """
        self.name = name
        self.model = None
        self.is_trained = False
        self.feature_importance = None
        self.use_feature_engineering = use_feature_engineering
        self.feature_engineer = FeatureEngineer() if use_feature_engineering else None

    @abstractmethod
    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据

        Args:
            df: K线数据
            lookback: 回看窗口

        Returns:
            (X, y) 特征和标签
        """
        pass

    @abstractmethod
    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练模型

        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        pass

    @abstractmethod
    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        预测

        Args:
            df: K线数据
            lookback: 回看窗口

        Returns:
            预测结果
        """
        pass

    def save_model(self, filepath: str):
        """
        保存模型

        Args:
            filepath: 保存路径
        """
        if not self.is_trained:
            logger.warning(f"模型 {self.name} 未训练，无法保存")
            return

        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'name': self.name,
                'is_trained': self.is_trained,
                'feature_importance': self.feature_importance,
                'saved_at': datetime.now()
            }, f)

        logger.info(f"模型 {self.name} 已保存到 {filepath}")

    def load_model(self, filepath: str):
        """
        加载模型

        Args:
            filepath: 模型路径
        """
        if not os.path.exists(filepath):
            logger.error(f"模型文件不存在: {filepath}")
            return

        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.name = data['name']
        self.is_trained = data['is_trained']
        self.feature_importance = data.get('feature_importance')

        logger.info(f"模型 {self.name} 已从 {filepath} 加载")


class LightGBMPredictor(MLPredictorBase):
    """
    LightGBM 预测器（增强版）
    速度最快，适合表格数据，集成深度特征工程
    """

    def __init__(self, objective: str = 'regression', num_leaves: int = 31, use_feature_engineering: bool = True):
        super().__init__("LightGBM预测器", use_feature_engineering)
        self.objective = objective
        self.num_leaves = num_leaves

    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据 - 使用深度特征工程

        Args:
            df: K线数据
            lookback: 回看窗口

        Returns:
            (X, y) 特征和标签
        """
        # 确保数据按时间排序
        df = df.sort_values('date').reset_index(drop=True)

        if self.use_feature_engineering and self.feature_engineer:
            # 使用特征工程器计算所有特征
            df = self.feature_engineer.calculate_technical_features(df)
            df = self.feature_engineer.calculate_cross_sectional_features(df)
            df = self.feature_engineer.calculate_microstructure_features(df)
            df = self.feature_engineer.calculate_multi_targets(df)

            # 使用高级特征列表
            features = self.feature_engineer.get_feature_list()
            target = 'target_next_return'  # 使用多目标中的主要目标
        else:
            # 使用基础特征（向后兼容）
            df = self._calculate_indicators(df, lookback)
            features = [
                'close', 'volume', 'amplitude',
                'ma_short', 'ma_long', 'ma_diff',
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
                'momentum', 'roc', 'volatility'
            ]
            target = 'target'

        # 删除包含 NaN 的行
        df_clean = df.dropna(subset=features + [target]).copy()

        X = df_clean[features].values
        y = df_clean[target].values

        logger.info(f"准备数据完成: X shape={X.shape}, y shape={y.shape}, features={len(features)}")

        return X, y

    def _calculate_indicators(self, df: pd.DataFrame, lookback: int) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            df: 原始数据
            lookback: 回看窗口

        Returns:
            添加了指标的数据
        """
        # 移动平均
        df['ma_short'] = df['close'].rolling(window=5).mean()
        df['ma_long'] = df['close'].rolling(window=lookback).mean()
        df['ma_diff'] = (df['ma_short'] - df['ma_long']) / df['ma_long']

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

        # 动量指标
        df['momentum'] = df['close'] - df['close'].shift(lookback)
        df['roc'] = (df['close'] - df['close'].shift(lookback)) / df['close'].shift(lookback) * 100

        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(window=lookback).std()

        # 振幅
        df['amplitude'] = (df['high'] - df['low']) / df['close'] * 100

        # 目标变量：预测未来 1 天的涨跌幅
        df['target'] = df['close'].pct_change().shift(-1) * 100

        return df

    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练 LightGBM 模型

        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        try:
            import lightgbm as lgb
        except ImportError:
            logger.error("未安装 lightgbm，请运行: pip install lightgbm")
            return

        X, y = self.prepare_data(df, lookback)

        # 划分训练集和验证集
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        # 创建 LightGBM 数据集
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        # 参数
        params = {
            'objective': self.objective,
            'metric': 'rmse',
            'num_leaves': self.num_leaves,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'n_jobs': -1
        }

        # 训练
        logger.info(f"开始训练 {self.name}...")
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=200,
            valid_sets=[train_data, val_data],
            callbacks=[
                lgb.early_stopping(stopping_rounds=20, verbose=False),
                lgb.log_evaluation(period=50)
            ]
        )

        self.is_trained = True
        self.feature_importance = dict(zip(
            ['close', 'volume', 'amplitude', 'ma_short', 'ma_long', 'ma_diff',
             'rsi', 'macd', 'macd_signal', 'macd_hist',
             'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
             'momentum', 'roc', 'volatility'],
            self.model.feature_importance()
        ))

        logger.info(f"{self.name} 训练完成！")

    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        预测

        Args:
            df: K线数据
            lookback: 回看窗口

        Returns:
            预测结果
        """
        if not self.is_trained:
            logger.warning(f"模型 {self.name} 未训练")
            return np.array([])

        X, _ = self.prepare_data(df, lookback)
        predictions = self.model.predict(X, num_iteration=self.model.best_iteration)

        return predictions


class CatBoostPredictor(MLPredictorBase):
    """
    CatBoost 预测器（增强版）
    原生支持类别特征，无需 One-Hot 编码，集成深度特征工程
    """

    def __init__(self, use_feature_engineering: bool = True):
        super().__init__("CatBoost预测器", use_feature_engineering)
        self.feature_names = None

    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[pd.DataFrame, pd.Series]:
        """
        准备训练数据 - 使用深度特征工程，返回 DataFrame 保留列名

        Args:
            df: K线数据
            lookback: 回看窗口

        Returns:
            (X, y) 特征 DataFrame 和标签 Series
        """
        # 确保数据按时间排序
        df = df.sort_values('date').reset_index(drop=True)

        if self.use_feature_engineering and self.feature_engineer:
            # 使用特征工程器计算所有特征
            df = self.feature_engineer.calculate_technical_features(df)
            df = self.feature_engineer.calculate_cross_sectional_features(df)
            df = self.feature_engineer.calculate_microstructure_features(df)
            df = self.feature_engineer.calculate_multi_targets(df)

            # 使用高级特征列表
            features = self.feature_engineer.get_feature_list()
            target = 'target_next_return'
        else:
            # 使用基础特征（向后兼容）
            df = self._calculate_indicators(df, lookback)
            features = [
                'close', 'volume', 'amplitude',
                'ma_short', 'ma_long', 'ma_diff',
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
                'momentum', 'roc', 'volatility'
            ]
            df['target'] = df['close'].pct_change().shift(-1) * 100
            target = 'target'

        # 删除包含 NaN 的行
        df_clean = df.dropna(subset=features + [target]).copy()

        X = df_clean[features]
        y = df_clean[target]

        # 保存特征名称
        self.feature_names = features

        logger.info(f"准备数据完成: X shape={X.shape}, y shape={y.shape}, features={len(features)}")

        return X, y

    def _calculate_indicators(self, df: pd.DataFrame, lookback: int) -> pd.DataFrame:
        """计算技术指标（同 LightGBM）"""
        df['ma_short'] = df['close'].rolling(window=5).mean()
        df['ma_long'] = df['close'].rolling(window=lookback).mean()
        df['ma_diff'] = (df['ma_short'] - df['ma_long']) / df['ma_long']

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

        df['momentum'] = df['close'] - df['close'].shift(lookback)
        df['roc'] = (df['close'] - df['close'].shift(lookback)) / df['close'].shift(lookback) * 100
        df['volatility'] = df['close'].pct_change().rolling(window=lookback).std()
        df['amplitude'] = (df['high'] - df['low']) / df['close'] * 100
        df['target'] = df['close'].pct_change().shift(-1) * 100

        return df

    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练 CatBoost 模型（使用 DataFrame 保留列名）

        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        try:
            from catboost import CatBoostRegressor
        except ImportError:
            logger.error("未安装 catboost，请运行: pip install catboost")
            return

        X, y = self.prepare_data(df, lookback)

        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        self.model = CatBoostRegressor(
            depth=self.depth,
            learning_rate=self.learning_rate,
            iterations=200,
            loss_function='RMSE',
            verbose=False,
            thread_count=-1
        )

        logger.info(f"开始训练 {self.name}...")
        self.model.fit(
            X_train, y_train,
            eval_set=(X_val, y_val),
            early_stopping_rounds=20,
            verbose=False
            # 如果有类别特征，可以在这里指定:
            # cat_features=['sector', 'concept']
        )

        self.is_trained = True

        # 保存特征重要性（使用特征名称）
        if self.feature_names:
            self.feature_importance = dict(zip(
                self.feature_names,
                self.model.feature_importances_
            ))

        logger.info(f"{self.name} 训练完成！")

    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        预测（确保特征顺序与训练时一致）

        Args:
            df: K线数据
            lookback: 回看窗口

        Returns:
            预测结果
        """
        if not self.is_trained:
            logger.warning(f"模型 {self.name} 未训练")
            return np.array([])

        X, _ = self.prepare_data(df, lookback)

        # 确保特征顺序与训练时一致
        if self.feature_names is not None:
            X = X[self.feature_names]

        predictions = self.model.predict(X)

        return predictions


class XGBoostPredictor(MLPredictorBase):
    """
    XGBoost 预测器（保留，与原版兼容）
    """

    def __init__(self, max_depth: int = 6, learning_rate: float = 0.1):
        super().__init__("XGBoost预测器")
        self.max_depth = max_depth
        self.learning_rate = learning_rate

    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据"""
        df = df.sort_values('date').reset_index(drop=True)
        df = self._calculate_indicators(df, lookback)

        features = [
            'close', 'volume', 'amplitude',
            'ma_short', 'ma_long', 'ma_diff',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'momentum', 'roc', 'volatility'
        ]

        df_clean = df.dropna(subset=features + ['target']).copy()
        X = df_clean[features].values
        y = df_clean['target'].values

        return X, y

    def _calculate_indicators(self, df: pd.DataFrame, lookback: int) -> pd.DataFrame:
        """计算技术指标"""
        df['ma_short'] = df['close'].rolling(window=5).mean()
        df['ma_long'] = df['close'].rolling(window=lookback).mean()
        df['ma_diff'] = (df['ma_short'] - df['ma_long']) / df['ma_long']

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

        df['momentum'] = df['close'] - df['close'].shift(lookback)
        df['roc'] = (df['close'] - df['close'].shift(lookback)) / df['close'].shift(lookback) * 100
        df['volatility'] = df['close'].pct_change().rolling(window=lookback).std()
        df['amplitude'] = (df['high'] - df['low']) / df['close'] * 100
        df['target'] = df['close'].pct_change().shift(-1) * 100

        return df

    def train(self, df: pd.DataFrame, lookback: int = 20):
        """训练 XGBoost 模型"""
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("未安装 xgboost，请运行: pip install xgboost")
            return

        X, y = self.prepare_data(df, lookback)

        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        self.model = xgb.XGBRegressor(
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            n_estimators=200,
            objective='reg:squarederror',
            n_jobs=-1,
            verbosity=0
        )

        logger.info(f"开始训练 {self.name}...")
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        self.is_trained = True
        self.feature_importance = dict(zip(
            ['close', 'volume', 'amplitude', 'ma_short', 'ma_long', 'ma_diff',
             'rsi', 'macd', 'macd_signal', 'macd_hist',
             'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
             'momentum', 'roc', 'volatility'],
            self.model.feature_importances_
        ))

        logger.info(f"{self.name} 训练完成！")

    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """预测"""
        if not self.is_trained:
            logger.warning(f"模型 {self.name} 未训练")
            return np.array([])

        X, _ = self.prepare_data(df, lookback)
        predictions = self.model.predict(X)

        return predictions


class EnsemblePredictor:
    """
    集成预测器
    组合多个模型进行预测
    """

    def __init__(self, predictors: List[MLPredictorBase], weights: Optional[List[float]] = None):
        """
        初始化集成预测器

        Args:
            predictors: 预测器列表
            weights: 权重列表，None 表示平均权重
        """
        self.predictors = predictors
        self.weights = weights if weights is not None else [1.0 / len(predictors)] * len(predictors)

        if len(self.weights) != len(self.predictors):
            raise ValueError("权重数量必须与预测器数量相同")

    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        集成预测

        Args:
            df: K线数据
            lookback: 回看窗口

        Returns:
            集成预测结果
        """
        predictions = []

        for predictor in self.predictors:
            if predictor.is_trained:
                pred = predictor.predict(df, lookback)
                predictions.append(pred)
            else:
                logger.warning(f"预测器 {predictor.name} 未训练，跳过")

        if not predictions:
            return np.array([])

        # 加权平均
        ensemble_pred = np.zeros_like(predictions[0])
        for pred, weight in zip(predictions, self.weights):
            ensemble_pred += pred * weight

        return ensemble_pred


# 使用示例
if __name__ == "__main__":
    # 创建模拟数据
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=1000)
    df = pd.DataFrame({
        'date': dates,
        'close': np.cumprod(1 + np.random.randn(1000) * 0.02) * 100,
        'high': np.cumprod(1 + np.random.randn(1000) * 0.02) * 100 * 1.02,
        'low': np.cumprod(1 + np.random.randn(1000) * 0.02) * 100 * 0.98,
        'volume': np.random.randint(1000000, 10000000, 1000)
    })

    # 创建预测器
    lgb_predictor = LightGBMPredictor()
    cat_predictor = CatBoostPredictor()
    xgb_predictor = XGBoostPredictor()

    # 训练
    print("训练 LightGBM...")
    lgb_predictor.train(df)

    print("\n训练 CatBoost...")
    cat_predictor.train(df)

    print("\n训练 XGBoost...")
    xgb_predictor.train(df)

    # 集成预测
    ensemble = EnsemblePredictor([lgb_predictor, cat_predictor, xgb_predictor])
    predictions = ensemble.predict(df)

    print(f"\n集成预测结果（最后5天）:")
    print(predictions[-5:])