"""
机器学习预测模型
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class MLPredictorBase(ABC):
    """
    机器学习预测器基类
    """
    
    def __init__(self, name: str):
        """
        初始化预测器
        
        Args:
            name: 模型名称
        """
        self.name = name
        self.model = None
        self.is_trained = False
    
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


class LSTMPredictor(MLPredictorBase):
    """
    LSTM预测器
    """
    
    def __init__(self):
        super().__init__("LSTM预测器")
        self.lookback = 20
    
    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备LSTM训练数据
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            (X, y) 特征和标签
        """
        # 使用收盘价作为特征
        data = df['close'].values
        
        X, y = [], []
        
        for i in range(lookback, len(data)):
            X.append(data[i-lookback:i])
            y.append(data[i])
        
        X = np.array(X)
        y = np.array(y)
        
        # 归一化
        X = X / X[:, 0:1]
        y = y / X[:, 0]
        
        return X, y
    
    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练LSTM模型
        
        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
        except ImportError:
            logger.error("未安装 tensorflow，请运行: pip install tensorflow")
            return
        
        X, y = self.prepare_data(df, lookback)
        
        # 构建LSTM模型
        self.model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(lookback, 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        self.model.compile(optimizer='adam', loss='mse')
        
        # 训练
        self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
        
        self.is_trained = True
        logger.info("LSTM模型训练完成")
    
    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        LSTM预测
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            预测结果
        """
        if not self.is_trained:
            logger.warning("模型未训练，将先训练")
            self.train(df, lookback)
        
        X, _ = self.prepare_data(df, lookback)
        
        predictions = self.model.predict(X, verbose=0)
        
        # 反归一化
        data = df['close'].values
        predictions = predictions * data[lookback:len(data)]
        
        return predictions.flatten()


class TransformerPredictor(MLPredictorBase):
    """
    Transformer预测器
    """
    
    def __init__(self):
        super().__init__("Transformer预测器")
        self.lookback = 20
    
    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备Transformer训练数据
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            (X, y) 特征和标签
        """
        # 使用多特征
        features = ['open', 'high', 'low', 'close', 'volume']
        data = df[features].values
        
        X, y = [], []
        
        for i in range(lookback, len(data)):
            X.append(data[i-lookback:i])
            y.append(data[i, 3])  # 预测收盘价
        
        X = np.array(X)
        y = np.array(y)
        
        # 归一化
        X = X / X[:, 0:1, :]
        y = y / X[:, 0, 3]
        
        return X, y
    
    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练Transformer模型
        
        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import Dense, Dropout
            from tensorflow.keras.layers import MultiHeadAttention, LayerNormalization
        except ImportError:
            logger.error("未安装 tensorflow，请运行: pip install tensorflow")
            return
        
        X, y = self.prepare_data(df, lookback)
        
        # 简化的Transformer模型
        self.model = Sequential([
            Dense(64, activation='relu', input_shape=(lookback, 5)),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1)
        ])
        
        self.model.compile(optimizer='adam', loss='mse')
        
        # 训练
        self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
        
        self.is_trained = True
        logger.info("Transformer模型训练完成")
    
    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        Transformer预测
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            预测结果
        """
        if not self.is_trained:
            logger.warning("模型未训练，将先训练")
            self.train(df, lookback)
        
        X, _ = self.prepare_data(df, lookback)
        
        predictions = self.model.predict(X, verbose=0)
        
        # 反归一化
        data = df['close'].values
        predictions = predictions * data[lookback:len(data)]
        
        return predictions.flatten()


class XGBoostPredictor(MLPredictorBase):
    """
    XGBoost预测器
    """
    
    def __init__(self):
        super().__init__("XGBoost预测器")
        self.lookback = 20
    
    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备XGBoost训练数据
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            (X, y) 特征和标签
        """
        # 创建技术指标特征
        df = df.copy()
        
        # 移动平均
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        # 收益率
        df['returns'] = df['close'].pct_change()
        
        # 波动率
        df['volatility'] = df['returns'].rolling(20).std()
        
        # 成交量变化
        df['volume_change'] = df['volume'].pct_change()
        
        # 目标: 下一日收益率
        df['target'] = df['returns'].shift(-1)
        
        # 删除NaN
        df = df.dropna()
        
        # 特征列
        feature_cols = ['ma5', 'ma10', 'ma20', 'returns', 'volatility', 'volume_change']
        
        X = df[feature_cols].values
        y = df['target'].values
        
        return X, y
    
    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练XGBoost模型
        
        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        try:
            import xgboost as xgb
        except ImportError:
            logger.error("未安装 xgboost，请运行: pip install xgboost")
            return
        
        X, y = self.prepare_data(df, lookback)
        
        # 构建XGBoost模型
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        
        # 训练
        self.model.fit(X, y)
        
        self.is_trained = True
        logger.info("XGBoost模型训练完成")
    
    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        XGBoost预测
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            预测结果
        """
        if not self.is_trained:
            logger.warning("模型未训练，将先训练")
            self.train(df, lookback)
        
        X, _ = self.prepare_data(df, lookback)
        
        predictions = self.model.predict(X)
        
        return predictions


class EnsemblePredictor:
    """
    集成预测器
    
    融合多个预测模型
    """
    
    def __init__(self):
        """初始化集成预测器"""
        self.predictors = []
        self.weights = []
    
    def add_predictor(self, predictor: MLPredictorBase, weight: float = 1.0):
        """
        添加预测器
        
        Args:
            predictor: 预测器实例
            weight: 权重
        """
        self.predictors.append(predictor)
        self.weights.append(weight)
    
    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练所有预测器
        
        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        for predictor in self.predictors:
            predictor.train(df, lookback)
    
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
            pred = predictor.predict(df, lookback)
            predictions.append(pred)
        
        # 加权平均
        weights = np.array(self.weights)
        weights = weights / weights.sum()
        
        ensemble_pred = np.zeros_like(predictions[0])
        
        for i, pred in enumerate(predictions):
            ensemble_pred += weights[i] * pred
        
        return ensemble_pred
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        lookback: int = 20,
        threshold: float = 0.02
    ) -> pd.Series:
        """
        生成交易信号
        
        Args:
            df: K线数据
            lookback: 回看窗口
            threshold: 阈值
        
        Returns:
            交易信号
        """
        predictions = self.predict(df, lookback)
        
        # 计算预测收益率
        actual_prices = df['close'].values[lookback:]
        pred_returns = (predictions - actual_prices) / actual_prices
        
        signals = pd.Series(0, index=df.index[lookback:])
        
        # 预测上涨 > 阈值
        signals[pred_returns > threshold] = 1
        
        # 预测下跌 < -阈值
        signals[pred_returns < -threshold] = -1
        
        return signals


class GRUPredictor(MLPredictorBase):
    """
    GRU预测器
    """
    
    def __init__(self):
        super().__init__("GRU预测器")
        self.lookback = 20
    
    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备GRU训练数据
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            (X, y) 特征和标签
        """
        # 使用收盘价作为特征
        data = df['close'].values
        
        X, y = [], []
        
        for i in range(lookback, len(data)):
            X.append(data[i-lookback:i])
            y.append(data[i])
        
        X = np.array(X)
        y = np.array(y)
        
        # 归一化
        X = X / X[:, 0:1]
        y = y / X[:, 0]
        
        return X, y
    
    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练GRU模型
        
        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import GRU, Dense, Dropout
        except ImportError:
            logger.error("未安装 tensorflow，请运行: pip install tensorflow")
            return
        
        X, y = self.prepare_data(df, lookback)
        
        # 构建GRU模型
        self.model = Sequential([
            GRU(50, return_sequences=True, input_shape=(lookback, 1)),
            Dropout(0.2),
            GRU(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        self.model.compile(optimizer='adam', loss='mse')
        
        # 训练
        self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
        
        self.is_trained = True
        logger.info("GRU模型训练完成")
    
    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        GRU预测
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            预测结果
        """
        if not self.is_trained:
            logger.warning("模型未训练，将先训练")
            self.train(df, lookback)
        
        X, _ = self.prepare_data(df, lookback)
        
        predictions = self.model.predict(X, verbose=0)
        
        # 反归一化
        data = df['close'].values
        predictions = predictions * data[lookback:len(data)]
        
        return predictions.flatten()


class CNNPredictor(MLPredictorBase):
    """
    CNN预测器
    """
    
    def __init__(self):
        super().__init__("CNN预测器")
        self.lookback = 20
    
    def prepare_data(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备CNN训练数据
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            (X, y) 特征和标签
        """
        # 使用多特征
        features = ['open', 'high', 'low', 'close', 'volume']
        data = df[features].values
        
        X, y = [], []
        
        for i in range(lookback, len(data)):
            X.append(data[i-lookback:i])
            y.append(data[i, 3])  # 预测收盘价
        
        X = np.array(X)
        y = np.array(y)
        
        # 归一化
        X = X / X[:, 0:1, :]
        y = y / X[:, 0, 3]
        
        return X, y
    
    def train(self, df: pd.DataFrame, lookback: int = 20):
        """
        训练CNN模型
        
        Args:
            df: 训练数据
            lookback: 回看窗口
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
        except ImportError:
            logger.error("未安装 tensorflow，请运行: pip install tensorflow")
            return
        
        X, y = self.prepare_data(df, lookback)
        
        # 构建CNN模型
        self.model = Sequential([
            Conv1D(64, 3, activation='relu', input_shape=(lookback, 5)),
            MaxPooling1D(2),
            Conv1D(32, 3, activation='relu'),
            MaxPooling1D(2),
            Flatten(),
            Dense(50, activation='relu'),
            Dropout(0.2),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        
        self.model.compile(optimizer='adam', loss='mse')
        
        # 训练
        self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
        
        self.is_trained = True
        logger.info("CNN模型训练完成")
    
    def predict(self, df: pd.DataFrame, lookback: int = 20) -> np.ndarray:
        """
        CNN预测
        
        Args:
            df: K线数据
            lookback: 回看窗口
        
        Returns:
            预测结果
        """
        if not self.is_trained:
            logger.warning("模型未训练，将先训练")
            self.train(df, lookback)
        
        X, _ = self.prepare_data(df, lookback)
        
        predictions = self.model.predict(X, verbose=0)
        
        # 反归一化
        data = df['close'].values
        predictions = predictions * data[lookback:len(data)]
        
        return predictions.flatten()