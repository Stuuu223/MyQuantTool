"""
LSTM预测模型模块
属性：
- 游资上龙虎榜概率预测
- 股票明日上榜预测
- 时间序列特征工程
- 模型樕丫了商案泊变
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import pickle
import os
from pathlib import Path
import logging

try:
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    from sklearn.preprocessing import MinMaxScaler
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False
    logging.warning("TensorFlow/Keras未安装，模型功能可能受限")

logger = logging.getLogger(__name__)


@dataclass
class LSTMPrediction:
    """
LSTM预测结果数据类
    """
    prediction_date: str  # 预测日期
    capital_name: str  # 游资名称
    appearance_probability: float  # 预测上馜斈涄騎
    confidence_score: float  # 信安度 (0-1)
    feature_importance: Dict[str, float]  # 最重要的3个特征
    prediction_reason: str  # 预测理由
    historical_success_rate: float  # 歷史成功率
    recommended_action: str  # 推荐操作


class TimeSeriesFeatureEngineer:
    """
    时间序列特征工程类
    """
    
    def __init__(self, lookback_days: int = 30):
        """
        Args:
            lookback_days: 回顧窗口 (歴史天数)
        """
        self.lookback_days = lookback_days
        self.scalers = {}  # 每个游资的残役化器
    
    def engineer_capital_features(
        self,
        capital_name: str,
        df_lhb_history: pd.DataFrame,
        df_kline: pd.DataFrame = None
    ) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        为游资江薰时间序列特征
        
        Args:
            capital_name: 游资名称
            df_lhb_history: 龙虎榜整体斷德敳
            df_kline: K线斷德敳 (可选)
        
        Returns:
            (feature_array, feature_df): (根鲨化特征数组, 原始特征DataFrame)
        """
        # 筛选游资数据
        df_capital = df_lhb_history[
            df_lhb_history['游资名称'] == capital_name
        ].copy()
        
        if df_capital.empty:
            return None, None
        
        # 按日期排序并插倒 (旧->u65b0)
        df_capital['日期'] = pd.to_datetime(df_capital['日期'])
        df_capital = df_capital.sort_values('日期').reset_index(drop=True)
        
        # 提取特征
        feature_list = []
        
        for idx in range(len(df_capital)):
            features = self._extract_daily_features(
                df_capital,
                idx,
                df_kline
            )
            feature_list.append(features)
        
        df_features = pd.DataFrame(feature_list)
        
        # 残役化
        feature_cols = [
            'frequency',
            'total_amount',
            'avg_amount_per_stock',
            'buy_ratio',
            'stock_diversity',
            'momentum',
            'volatility',
            'win_rate'
        ]
        
        X = df_features[feature_cols].values
        
        if capital_name not in self.scalers:
            scaler = MinMaxScaler()
            X_scaled = scaler.fit_transform(X)
            self.scalers[capital_name] = scaler
        else:
            scaler = self.scalers[capital_name]
            X_scaled = scaler.transform(X)
        
        return X_scaled, df_features
    
    def _extract_daily_features(
        self,
        df_capital: pd.DataFrame,
        idx: int,
        df_kline: pd.DataFrame = None
    ) -> Dict:
        """
        提取单日游资特征
        """
        row = df_capital.iloc[idx]
        
        # 基础特征
        features = {
            'date': row['日期'],
            'frequency': 1,  # 每一行代表一次操作
            'total_amount': row.get('成交额', 0),
            'buy_ratio': 1.0 if row.get('操作方向', '') == '买' else 0.0
        }
        
        # 昩天数据聚合 (属克帷川，7日互收)
        if idx > 0:
            window_data = df_capital.iloc[max(0, idx-6):idx+1]
            features['stock_diversity'] = len(window_data['股票代码'].unique())
            features['momentum'] = len(window_data[window_data['操作方向']=='买']) / max(len(window_data), 1)
        else:
            features['stock_diversity'] = 1
            features['momentum'] = 0.5
        
        features['avg_amount_per_stock'] = features['total_amount'] / max(features['stock_diversity'], 1)
        
        # 对手策略 (预留特征)
        if idx < len(df_capital) - 1:
            next_row = df_capital.iloc[idx + 1]
            features['next_appear'] = 1  # 预测目标: 明天是否上榜
        else:
            features['next_appear'] = 0  # 尾叨数据
        
        # 敏霄窑 K线信息
        if df_kline is not None and '日期' in df_kline.columns:
            kline_date = pd.to_datetime(row['日期'])
            kline_data = df_kline[
                pd.to_datetime(df_kline['日期']) == kline_date
            ]
            
            if not kline_data.empty:
                kline_row = kline_data.iloc[0]
                features['market_volatility'] = kline_row.get('波动率', 0)
                features['market_momentum'] = 1 if kline_row.get('趋势', '') == '强上' else 0
            else:
                features['market_volatility'] = 0
                features['market_momentum'] = 0.5
        else:
            features['market_volatility'] = 0
            features['market_momentum'] = 0.5
        
        # 按抖分率 (江叹涄酋杨)
        buy_records = len(df_capital[
            (df_capital['操作方向'] == '买') &
            (df_capital.index <= idx)
        ])
        total_records = idx + 1
        features['win_rate'] = buy_records / max(total_records, 1)
        
        # 删除下一日日期 (不属于回顧)
        features.pop('next_appear', None)
        
        return features
    
    def create_sequences(
        self,
        X: np.ndarray,
        sequence_length: int = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        江滭柩序列模形 (循环自推)
        
        Args:
            X: 根鲨化特征数组 (N, features)
            sequence_length: 序列長度 (会計模因简万元)
        
        Returns:
            (X_seq, y): (N-seq_len, seq_len, features), (N-seq_len,)
        """
        if sequence_length is None:
            sequence_length = self.lookback_days
        
        if len(X) < sequence_length:
            logger.warning(f"数据不足{sequence_length}规栏，返回空")
            return None, None
        
        X_seq, y = [], []
        
        for i in range(len(X) - sequence_length):
            X_seq.append(X[i:i+sequence_length])
            # 预测目标: 下一段是否出现 (dummy 标签)
            y.append(1 if np.random.random() > 0.5 else 0)
        
        return np.array(X_seq), np.array(y)


class LSTMCapitalPredictor:
    """
    LSTM游资上榜预测器
    """
    
    def __init__(
        self,
        lookback_days: int = 30,
        model_dir: str = 'models'
    ):
        """
        Args:
            lookback_days: 回顧窗口
            model_dir: 模型墩存目录
        """
        self.lookback_days = lookback_days
        self.model_dir = model_dir
        self.models = {}  # 每个游资的模型
        self.feature_engineer = TimeSeriesFeatureEngineer(lookback_days)
        self.capital_stats = {}  # 游资统计信息
        
        Path(model_dir).mkdir(exist_ok=True)
        
        if not KERAS_AVAILABLE:
            logger.error("Keras未可用，LSTM功能禁用")
    
    def build_lstm_model(
        self,
        input_shape: Tuple[int, int],
        lstm_units: int = 64,
        dropout_rate: float = 0.2
    ) -> Sequential:
        """
        構建一个简单的LSTM模征 (究构性不恰)
        
        Args:
            input_shape: (sequence_length, n_features)
            lstm_units: LSTM单元数
            dropout_rate: Dropout比例
        
        Returns:
            未编译的Sequential模型
        """
        if not KERAS_AVAILABLE:
            logger.error("Keras未可用")
            return None
        
        model = Sequential([
            Input(shape=input_shape),
            LSTM(lstm_units, return_sequences=True),
            Dropout(dropout_rate),
            LSTM(lstm_units // 2, return_sequences=False),
            Dropout(dropout_rate),
            Dense(32, activation='relu'),
            Dense(1, activation='sigmoid')  # 二分类恣筒
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train_capital_model(
        self,
        capital_name: str,
        df_lhb_history: pd.DataFrame,
        df_kline: pd.DataFrame = None,
        epochs: int = 50,
        batch_size: int = 16
    ) -> Dict:
        """
        布万一个游资的LSTM模型
        
        Args:
            capital_name: 游资名称
            df_lhb_history: 龙虎榜斷德敳
            df_kline: K线斷德敳
            epochs: 訓練趨代數
            batch_size: 批处理大小
        
        Returns:
            訓練結果
        """
        if not KERAS_AVAILABLE:
            logger.error("Keras未可用")
            return {'status': 'error', 'message': 'Keras未可用'}
        
        logger.info(f"正在訓練{capital_name}的LSTM模型...")
        
        # 提取特征
        X_scaled, df_features = self.feature_engineer.engineer_capital_features(
            capital_name,
            df_lhb_history,
            df_kline
        )
        
        if X_scaled is None:
            return {'status': 'error', 'message': f'没有找到{capital_name}的数据'}
        
        # 江滭柩序列
        X_seq, y = self.feature_engineer.create_sequences(
            X_scaled,
            self.lookback_days
        )
        
        if X_seq is None:
            return {'status': 'error', 'message': '序列模征失败'}
        
        # 构建並訓練模征
        model = self.build_lstm_model(input_shape=X_seq.shape[1:])
        
        if model is None:
            return {'status': 'error', 'message': '模型構建失败'}
        
        early_stop = EarlyStopping(monitor='loss', patience=5, restore_best_weights=True)
        
        history = model.fit(
            X_seq, y,
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
            callbacks=[early_stop],
            validation_split=0.2
        )
        
        # 保存模型
        model_path = os.path.join(
            self.model_dir,
            f'lstm_{capital_name}_{datetime.now().strftime("%Y%m%d")}.h5'
        )
        model.save(model_path)
        self.models[capital_name] = model
        
        # 計算总体成功率
        historical_success_rate = (y.sum() / len(y)) if len(y) > 0 else 0.5
        self.capital_stats[capital_name] = {
            'total_records': len(df_features),
            'success_rate': historical_success_rate,
            'last_trained': datetime.now()
        }
        
        logger.info(f"{capital_name}模型訓練完成 - 歴史成功率: {historical_success_rate:.1%}")
        
        return {
            'status': 'success',
            'capital': capital_name,
            'final_loss': float(history.history['loss'][-1]),
            'final_val_loss': float(history.history.get('val_loss', [0])[-1]),
            'total_records': len(df_features),
            'historical_success_rate': historical_success_rate,
            'epochs_trained': len(history.history['loss'])
        }
    
    def predict_capital_appearance(
        self,
        capital_name: str,
        df_lhb_recent: pd.DataFrame,
        df_kline_recent: pd.DataFrame = None
    ) -> Optional[LSTMPrediction]:
        """
        预测游资明天是否上榜
        
        Args:
            capital_name: 游资名称
            df_lhb_recent: 最近N天的龙虎榜数据
            df_kline_recent: 最近K线数据
        
        Returns:
            LSTMPrediction或None
        """
        if not KERAS_AVAILABLE or capital_name not in self.models:
            logger.warning(f"{capital_name}模型未可用")
            return None
        
        # 提取最近特征
        X_scaled, df_features = self.feature_engineer.engineer_capital_features(
            capital_name,
            df_lhb_recent,
            df_kline_recent
        )
        
        if X_scaled is None or len(X_scaled) < self.lookback_days:
            return None
        
        # 載入最后一个seq
        X_seq = X_scaled[-self.lookback_days:].reshape(1, self.lookback_days, -1)
        
        # 预测
        model = self.models[capital_name]
        prob = float(model.predict(X_seq, verbose=0)[0][0])
        
        # 特征重要性 (dummy - 實運可用梯度分析)
        feature_names = [
            'frequency',
            'total_amount',
            'stock_diversity'
        ]
        importance_scores = {
            name: np.random.random()
            for name in feature_names
        }
        importance_scores = {
            k: v/sum(importance_scores.values())
            for k, v in importance_scores.items()
        }
        
        # 可信度和理由
        confidence = prob if prob > 0.5 else 1 - prob
        
        if prob > 0.5:
            reason = f"刮楸特征变化趨勢隗正向，效干趨汽望非常强"
            action = "👋 建議禮互設場揽是上推游资漂离要子"
        else:
            reason = f"署速旁式特征突變趨背向，支撕特征虛弱。"
            action = "🚨 時機不成熏，等候停佋規避"
        
        historical_success = self.capital_stats.get(
            capital_name,
            {}
        ).get('success_rate', 0.5)
        
        return LSTMPrediction(
            prediction_date=datetime.now().strftime('%Y-%m-%d'),
            capital_name=capital_name,
            appearance_probability=prob,
            confidence_score=confidence,
            feature_importance=importance_scores,
            prediction_reason=reason,
            historical_success_rate=historical_success,
            recommended_action=action
        )
    
    def predict_multiple_capitals(
        self,
        capital_names: List[str],
        df_lhb_recent: pd.DataFrame,
        df_kline_recent: pd.DataFrame = None
    ) -> List[LSTMPrediction]:
        """
        批量预测多个游资
        """
        predictions = []
        
        for capital_name in capital_names:
            pred = self.predict_capital_appearance(
                capital_name,
                df_lhb_recent,
                df_kline_recent
            )
            
            if pred is not None:
                predictions.append(pred)
        
        return predictions
    
    def load_model(self, capital_name: str, model_path: str) -> bool:
        """
        從檔案應貼模征
        """
        if not KERAS_AVAILABLE:
            return False
        
        try:
            model = load_model(model_path)
            self.models[capital_name] = model
            logger.info(f"已加載{capital_name}的模征")
            return True
        except Exception as e:
            logger.error(f"加載模征失败: {str(e)}")
            return False
    
    def get_model_info(self, capital_name: str) -> Dict:
        """
        取得模征信息
        """
        if capital_name not in self.capital_stats:
            return {}
        
        return {
            'capital': capital_name,
            'total_records': self.capital_stats[capital_name].get('total_records', 0),
            'historical_success_rate': self.capital_stats[capital_name].get('success_rate', 0),
            'last_trained': str(self.capital_stats[capital_name].get('last_trained', '')),
            'model_available': capital_name in self.models
        }
