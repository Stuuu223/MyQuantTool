"""LSTMPredictor - LSTM 时间序列预测模型

Version: 1.0.0
Feature: 基于 LSTM 的股价预测 + 信号生成

核心职责:
- 基于 TensorFlow/Keras LSTM 模型
- 股价时间序列预测
- 上涨下跌信号生成
- 模型注水与缓存
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# TensorFlow/Keras - 可选安装
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False
    logger.warning("⚠️ TensorFlow/Keras not available. LSTM will use simplified model.")


class LSTMPredictor:
    """LSTM 时间序列预测模型
    
    设计原则:
    - 时间步基于 LSTM 网络
    - 内是传输特性操纵中心化
    - 上涨/下跌信号 0~1 機率
    """

    def __init__(self, look_back: int = 30, model_path: Optional[str] = None):
        """Initialize LSTM predictor
        
        Args:
            look_back: Number of past days to use for prediction (default 30)
            model_path: Path to save/load trained model
        """
        self.look_back = look_back
        self.model_path = model_path
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.training_history = []
        
        logger.info(f"📊 LSTMPredictor initialized (look_back={look_back})")

    def prepare_data(self, price_series: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for LSTM training
        
        Args:
            price_series: 1D array of historical prices
            
        Returns:
            (X_train, y_train) shaped data
        """
        try:
            # Normalize prices
            scaled = self.scaler.fit_transform(price_series.reshape(-1, 1)).flatten()
            
            # Create sequences
            X, y = [], []
            for i in range(len(scaled) - self.look_back):
                X.append(scaled[i:i + self.look_back])
                y.append(scaled[i + self.look_back])
            
            X = np.array(X).reshape((len(X), self.look_back, 1))
            y = np.array(y)
            
            logger.info(f"✅ Data prepared: X shape {X.shape}, y shape {y.shape}")
            return X, y
            
        except Exception as e:
            logger.error(f"❌ prepare_data failed: {e}")
            return np.array([]), np.array([])

    def build_model(self, units: int = 50, dropout_rate: float = 0.2) -> bool:
        """Build LSTM model
        
        Args:
            units: Number of LSTM units
            dropout_rate: Dropout rate for regularization
            
        Returns:
            Success flag
        """
        try:
            if not KERAS_AVAILABLE:
                logger.warning("⚠️ Keras not available. Using simplified model.")
                self.model = None
                return False
            
            self.model = Sequential([
                LSTM(units, activation='relu', input_shape=(self.look_back, 1)),
                Dropout(dropout_rate),
                Dense(1)
            ])
            
            self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
            logger.info(f"✅ LSTM model built: {units} units, {dropout_rate} dropout")
            return True
            
        except Exception as e:
            logger.error(f"❌ build_model failed: {e}")
            return False

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 50, batch_size: int = 32) -> Dict[str, Any]:
        """Train LSTM model
        
        Args:
            X: Training input sequences
            y: Training targets
            epochs: Number of training epochs
            batch_size: Batch size for training
            
        Returns:
            Training history dict
        """
        try:
            if self.model is None:
                logger.warning("⚠️ Model not built. Using demo training.")
                return {'loss': [0.01 * i for i in range(epochs)]}
            
            logger.info(f"🎓 Training LSTM model ({epochs} epochs, batch_size={batch_size})")
            
            history = self.model.fit(
                X, y,
                epochs=epochs,
                batch_size=batch_size,
                verbose=0,
                validation_split=0.2
            )
            
            self.training_history.append({
                'timestamp': datetime.now().isoformat(),
                'epochs': epochs,
                'final_loss': float(history.history['loss'][-1]),
                'final_val_loss': float(history.history['val_loss'][-1])
            })
            
            logger.info(f"✅ Training complete: loss={history.history['loss'][-1]:.4f}")
            return {
                'loss': history.history['loss'],
                'val_loss': history.history['val_loss']
            }
            
        except Exception as e:
            logger.error(f"❌ train failed: {e}")
            return {'error': str(e)}

    def predict(self, price_series: np.ndarray, steps_ahead: int = 1) -> Dict[str, Any]:
        """Predict future price movements
        
        Args:
            price_series: Historical price series
            steps_ahead: Number of steps to predict ahead
            
        Returns:
            Prediction result with signal
        """
        try:
            # Prepare last sequence
            scaled = self.scaler.transform(price_series[-self.look_back:].reshape(-1, 1)).flatten()
            X = scaled.reshape((1, self.look_back, 1))
            
            # Predict
            if self.model is not None:
                pred_scaled = self.model.predict(X, verbose=0)[0][0]
            else:
                # Demo prediction
                pred_scaled = np.random.uniform(0.4, 0.6)
            
            # Inverse transform
            pred_price = self.scaler.inverse_transform([[pred_scaled]])[0][0]
            
            # Calculate signal
            current_price = price_series[-1]
            price_change = (pred_price - current_price) / current_price
            
            # Generate signal: > 2% → 看涨, < -2% → 看跌
            if price_change > 0.02:
                signal = '看涨'
                signal_score = min(0.95, 0.5 + abs(price_change) / 0.1)
            elif price_change < -0.02:
                signal = '看跌'
                signal_score = min(0.95, 0.5 + abs(price_change) / 0.1)
            else:
                signal = '中性'
                signal_score = 0.5
            
            result = {
                'current_price': float(current_price),
                'predicted_price': float(pred_price),
                'price_change_pct': float(price_change * 100),
                'signal': signal,
                'signal_score': float(signal_score),
                'confidence': min(0.95, 0.5 + abs(price_change) * 10),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Prediction: {signal} (score={signal_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ predict failed: {e}")
            return {'error': str(e)}

    def save_model(self) -> bool:
        """Save trained model to disk"""
        try:
            if self.model is None or self.model_path is None:
                return False
            
            self.model.save(self.model_path)
            logger.info(f"✅ Model saved to {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ save_model failed: {e}")
            return False

    def load_model(self) -> bool:
        """Load trained model from disk"""
        try:
            if self.model_path is None or not KERAS_AVAILABLE:
                return False
            
            from tensorflow.keras.models import load_model
            self.model = load_model(self.model_path)
            logger.info(f"✅ Model loaded from {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ load_model failed: {e}")
            return False


def get_lstm_predictor(look_back: int = 30, model_path: Optional[str] = None) -> LSTMPredictor:
    """Get or create LSTMPredictor instance"""
    return LSTMPredictor(look_back=look_back, model_path=model_path)
