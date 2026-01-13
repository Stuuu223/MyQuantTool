"""
自适应情绪权重系统
实现市场环境分类和动态权重调整
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sqlite3
from collections import deque
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib


class MarketEnvironmentClassifier:
    """市场环境分类器"""
    
    def __init__(self):
        """初始化分类器"""
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.features = ['volatility', 'trend', 'volume_ratio', 'breadth', 'momentum']
    
    def extract_features(self, market_data: pd.DataFrame) -> np.ndarray:
        """
        提取市场特征
        
        Args:
            market_data: 市场数据
            
        Returns:
            特征向量
        """
        if len(market_data) < 20:
            return np.zeros(len(self.features))
        
        # 1. 波动率
        volatility = self._calculate_volatility(market_data)
        
        # 2. 趋势
        trend = self._calculate_trend(market_data)
        
        # 3. 成交量比率
        volume_ratio = self._calculate_volume_ratio(market_data)
        
        # 4. 市场广度
        breadth = self._calculate_breadth(market_data)
        
        # 5. 动量
        momentum = self._calculate_momentum(market_data)
        
        return np.array([volatility, trend, volume_ratio, breadth, momentum])
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """计算波动率"""
        if 'close' not in df.columns:
            return 0
        
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() if len(returns) > 0 else 0
        
        # 归一化
        return min(1.0, volatility * 10)
    
    def _calculate_trend(self, df: pd.DataFrame) -> float:
        """计算趋势"""
        if 'close' not in df.columns or len(df) < 2:
            return 0
        
        # 使用线性回归斜率
        x = np.arange(len(df))
        y = df['close'].values
        
        slope = np.polyfit(x, y, 1)[0]
        avg_price = np.mean(y)
        
        # 归一化
        normalized_slope = slope / avg_price if avg_price > 0 else 0
        return np.clip(normalized_slope * 100, -1, 1)
    
    def _calculate_volume_ratio(self, df: pd.DataFrame) -> float:
        """计算成交量比率"""
        if 'volume' not in df.columns or len(df) < 5:
            return 1
        
        avg_volume = df['volume'].rolling(window=5).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        ratio = current_volume / avg_volume if avg_volume > 0 else 1
        return np.clip(ratio / 2, 0, 1)  # 归一化到 0-1
    
    def _calculate_breadth(self, df: pd.DataFrame) -> float:
        """计算市场广度"""
        if 'pct_chg' not in df.columns:
            return 0.5
        
        # 计算上涨股票比例
        up_count = sum(1 for pct in df['pct_chg'] if pct > 0)
        breadth = up_count / len(df['pct_chg'])
        
        return breadth
    
    def _calculate_momentum(self, df: pd.DataFrame) -> float:
        """计算动量"""
        if 'close' not in df.columns or len(df) < 5:
            return 0
        
        momentum = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        return np.clip(momentum, -1, 1)
    
    def classify(self, market_data: pd.DataFrame) -> Dict:
        """
        分类市场环境
        
        Args:
            market_data: 市场数据
            
        Returns:
            分类结果
        """
        features = self.extract_features(market_data)
        
        if not self.is_trained:
            # 使用规则分类
            environment = self._rule_based_classification(features)
            confidence = 0.7
        else:
            # 使用模型分类
            features_scaled = self.scaler.transform([features])
            environment = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            confidence = max(probabilities)
        
        # 预测持续时间
        duration = self._predict_duration(environment, features)
        
        return {
            'environment': environment,
            'confidence': confidence,
            'duration': duration,
            'features': features
        }
    
    def _rule_based_classification(self, features: np.ndarray) -> str:
        """基于规则分类"""
        volatility, trend, volume_ratio, breadth, momentum = features
        
        # 牛市特征
        if trend > 0.3 and breadth > 0.6 and momentum > 0.2:
            return 'bull'
        
        # 熊市特征
        if trend < -0.3 and breadth < 0.4 and momentum < -0.2:
            return 'bear'
        
        # 震荡市
        return 'sideways'
    
    def _predict_duration(self, environment: str, features: np.ndarray) -> int:
        """预测持续时间（天）"""
        duration_map = {
            'bull': 30,
            'bear': 20,
            'sideways': 15
        }
        
        base_duration = duration_map.get(environment, 20)
        
        # 根据动量调整
        momentum = features[4]
        adjusted_duration = base_duration * (1 + momentum * 0.5)
        
        return int(adjusted_duration)
    
    def train(self, 
              X_train: np.ndarray, 
              y_train: np.ndarray):
        """
        训练模型
        
        Args:
            X_train: 训练特征
            y_train: 训练标签
        """
        # 标准化
        X_scaled = self.scaler.fit_transform(X_train)
        
        # 训练
        self.model.fit(X_scaled, y_train)
        self.is_trained = True
    
    def save_model(self, path: str):
        """保存模型"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained
        }
        joblib.dump(model_data, path)
    
    def load_model(self, path: str):
        """加载模型"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']


class DynamicWeightAdjuster:
    """动态权重调整器"""
    
    def __init__(self):
        """初始化调整器"""
        self.base_weights = {
            'news_sentiment': 0.35,
            'social_sentiment': 0.25,
            'price_sentiment': 0.25,
            'fund_flow_sentiment': 0.15
        }
        
        self.adjustment_rules = self._load_adjustment_rules()
        self.current_weights = self.base_weights.copy()
        self.adjustment_history = deque(maxlen=100)
    
    def _load_adjustment_rules(self) -> List[Dict]:
        """加载调整规则"""
        return [
            {
                'environment': 'bull',
                'adjustments': {
                    'news_sentiment': 0.3,  # 降低新闻权重
                    'social_sentiment': 0.2,  # 降低社交媒体权重
                    'price_sentiment': 0.35,  # 提高价格权重
                    'fund_flow_sentiment': 0.15  # 保持资金流向权重
                }
            },
            {
                'environment': 'bear',
                'adjustments': {
                    'news_sentiment': 0.4,  # 提高新闻权重
                    'social_sentiment': 0.3,  # 提高社交媒体权重
                    'price_sentiment': 0.2,  # 降低价格权重
                    'fund_flow_sentiment': 0.1  # 降低资金流向权重
                }
            },
            {
                'environment': 'sideways',
                'adjustments': {
                    'news_sentiment': 0.35,
                    'social_sentiment': 0.25,
                    'price_sentiment': 0.25,
                    'fund_flow_sentiment': 0.15
                }
            }
        ]
    
    def adjust_weights(self, 
                      environment: str,
                      confidence: float) -> Dict:
        """
        根据市场环境调整权重
        
        Args:
            environment: 市场环境
            confidence: 分类置信度
            
        Returns:
            调整结果
        """
        # 获取调整规则
        rule = next((r for r in self.adjustment_rules if r['environment'] == environment), None)
        
        if rule is None:
            return {
                'adjusted': False,
                'weights': self.current_weights,
                'reason': '未找到调整规则'
            }
        
        # 根据置信度调整幅度
        target_weights = rule['adjustments']
        
        if confidence < 0.7:
            # 置信度低，部分调整
            adjustment_factor = confidence
            new_weights = {}
            for key in self.base_weights:
                new_weights[key] = (
                    self.current_weights[key] * (1 - adjustment_factor) +
                    target_weights[key] * adjustment_factor
                )
        else:
            # 置信度高，完全调整
            new_weights = target_weights.copy()
        
        # 记录调整历史
        adjustment_record = {
            'timestamp': datetime.now(),
            'environment': environment,
            'confidence': confidence,
            'old_weights': self.current_weights.copy(),
            'new_weights': new_weights.copy()
        }
        
        self.adjustment_history.append(adjustment_record)
        self.current_weights = new_weights
        
        return {
            'adjusted': True,
            'environment': environment,
            'confidence': confidence,
            'old_weights': adjustment_record['old_weights'],
            'new_weights': new_weights,
            'changes': self._calculate_changes(adjustment_record['old_weights'], new_weights)
        }
    
    def _calculate_changes(self, 
                          old_weights: Dict, 
                          new_weights: Dict) -> Dict:
        """计算权重变化"""
        changes = {}
        for key in old_weights:
            changes[key] = new_weights[key] - old_weights[key]
        return changes
    
    def get_current_weights(self) -> Dict:
        """获取当前权重"""
        return self.current_weights.copy()
    
    def get_adjustment_history(self, limit: int = 20) -> List[Dict]:
        """获取调整历史"""
        return list(self.adjustment_history)[-limit:]


class AdaptiveSentimentWeightsSystem:
    """自适应情绪权重系统（整合类）"""
    
    def __init__(self, db_path: str = 'data/adaptive_weights_cache.db'):
        """
        初始化系统
        
        Args:
            db_path: 数据库路径
        """
        self.classifier = MarketEnvironmentClassifier()
        self.weight_adjuster = DynamicWeightAdjuster()
        self.db_path = db_path
        self._init_db()
        self.history = deque(maxlen=100)
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS environment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                environment TEXT,
                confidence REAL,
                duration INTEGER,
                features TEXT,
                weights TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def analyze_and_adjust(self, market_data: pd.DataFrame) -> Dict:
        """
        分析市场环境并调整权重
        
        Args:
            market_data: 市场数据
            
        Returns:
            分析和调整结果
        """
        # 分类市场环境
        classification = self.classifier.classify(market_data)
        
        # 调整权重
        adjustment = self.weight_adjuster.adjust_weights(
            classification['environment'],
            classification['confidence']
        )
        
        # 构建结果
        result = {
            'environment': classification['environment'],
            'confidence': classification['confidence'],
            'duration': classification['duration'],
            'features': classification['features'],
            'weights': self.weight_adjuster.get_current_weights(),
            'adjustment': adjustment,
            'timestamp': datetime.now()
        }
        
        # 保存到历史
        self.history.append(result)
        self._save_to_db(result)
        
        return result
    
    def _save_to_db(self, result: Dict):
        """保存到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO environment_history 
            (environment, confidence, duration, features, weights)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            result['environment'],
            result['confidence'],
            result['duration'],
            str(result['features']),
            str(result['weights'])
        ))
        
        conn.commit()
        conn.close()
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """
        获取历史记录
        
        Args:
            limit: 返回数量
            
        Returns:
            历史记录列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, environment, confidence, duration, weights
            FROM environment_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'environment': row[1],
                'confidence': row[2],
                'duration': row[3],
                'weights': eval(row[4])
            }
            for row in rows
        ]
    
    def get_current_weights(self) -> Dict:
        """获取当前权重"""
        return self.weight_adjuster.get_current_weights()
    
    def train_classifier(self, 
                        X_train: np.ndarray,
                        y_train: np.ndarray):
        """
        训练分类器
        
        Args:
            X_train: 训练特征
            y_train: 训练标签
        """
        self.classifier.train(X_train, y_train)
    
    def save_model(self, path: str):
        """保存模型"""
        self.classifier.save_model(path)
    
    def load_model(self, path: str):
        """加载模型"""
        self.classifier.load_model(path)


# 使用示例
if __name__ == '__main__':
    # 创建系统
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
    
    print("自适应情绪权重分析结果:")
    print(f"市场环境: {result['environment']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"预测持续时间: {result['duration']} 天")
    print(f"\n当前权重:")
    for key, value in result['weights'].items():
        print(f"  {key}: {value:.2f}")
    
    if result['adjustment']['adjusted']:
        print(f"\n权重已调整:")
        for key, change in result['adjustment']['changes'].items():
            if abs(change) > 0.01:
                print(f"  {key}: {change:+.2f}")