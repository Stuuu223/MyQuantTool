"""
多模态融合决策系统
实现文本、图像、时间序列三种模态的特征提取和融合决策
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sqlite3
from collections import deque
import re


class TextFeatureExtractor:
    """文本特征提取器"""
    
    def __init__(self):
        """初始化文本特征提取器"""
        self.keywords = {
            'positive': ['利好', '增长', '上涨', '突破', '创新高', '强势', '买入', '增持'],
            'negative': ['利空', '下跌', '暴跌', '跌破', '风险', '减持', '卖出', '回调']
        }
    
    def extract(self, text: str) -> Dict:
        """
        提取文本特征
        
        Args:
            text: 文本内容
            
        Returns:
            特征字典
        """
        if not text:
            return {
                'sentiment': 0,
                'positive_count': 0,
                'negative_count': 0,
                'length': 0,
                'keyword_density': 0
            }
        
        # 情绪分析
        sentiment = self._analyze_sentiment(text)
        
        # 关键词统计
        positive_count = sum(1 for kw in self.keywords['positive'] if kw in text)
        negative_count = sum(1 for kw in self.keywords['negative'] if kw in text)
        
        # 文本长度
        length = len(text)
        
        # 关键词密度
        keyword_density = (positive_count + negative_count) / max(1, length)
        
        return {
            'sentiment': sentiment,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'length': length,
            'keyword_density': keyword_density
        }
    
    def _analyze_sentiment(self, text: str) -> float:
        """分析文本情绪"""
        positive_score = sum(1 for kw in self.keywords['positive'] if kw in text)
        negative_score = sum(1 for kw in self.keywords['negative'] if kw in text)
        
        total = positive_score + negative_score
        if total == 0:
            return 0
        
        # 计算情绪得分 (-1 到 1)
        sentiment = (positive_score - negative_score) / total
        return sentiment


class ImageFeatureExtractor:
    """图像特征提取器（K线图）"""
    
    def __init__(self):
        """初始化图像特征提取器"""
        pass
    
    def extract(self, kline_data: pd.DataFrame) -> Dict:
        """
        提取K线图特征
        
        Args:
            kline_data: K线数据
            
        Returns:
            特征字典
        """
        if len(kline_data) < 5:
            return {
                'trend': 0,
                'volatility': 0,
                'momentum': 0,
                'pattern_count': 0,
                'volume_trend': 0
            }
        
        # 趋势特征
        trend = self._calculate_trend(kline_data)
        
        # 波动率
        volatility = self._calculate_volatility(kline_data)
        
        # 动量
        momentum = self._calculate_momentum(kline_data)
        
        # 形态识别
        pattern_count = self._count_patterns(kline_data)
        
        # 成交量趋势
        volume_trend = self._calculate_volume_trend(kline_data)
        
        return {
            'trend': trend,
            'volatility': volatility,
            'momentum': momentum,
            'pattern_count': pattern_count,
            'volume_trend': volume_trend
        }
    
    def _calculate_trend(self, df: pd.DataFrame) -> float:
        """计算趋势"""
        if len(df) < 2:
            return 0
        
        # 使用线性回归斜率
        x = np.arange(len(df))
        y = df['close'].values
        
        # 计算斜率
        slope = np.polyfit(x, y, 1)[0]
        
        # 归一化
        avg_price = np.mean(y)
        normalized_slope = slope / avg_price if avg_price > 0 else 0
        
        return np.clip(normalized_slope * 100, -1, 1)
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """计算波动率"""
        if len(df) < 2:
            return 0
        
        returns = df['close'].pct_change().dropna()
        volatility = returns.std()
        
        # 归一化到 0-1
        return min(1.0, volatility * 10)
    
    def _calculate_momentum(self, df: pd.DataFrame) -> float:
        """计算动量"""
        if len(df) < 5:
            return 0
        
        # 计算5日动量
        momentum = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
        
        return np.clip(momentum, -1, 1)
    
    def _count_patterns(self, df: pd.DataFrame) -> int:
        """统计形态数量"""
        patterns = 0
        
        # 检测十字星
        for i in range(len(df)):
            body = abs(df['close'].iloc[i] - df['open'].iloc[i])
            range_val = df['high'].iloc[i] - df['low'].iloc[i]
            
            if range_val > 0 and body / range_val < 0.1:
                patterns += 1
        
        return min(5, patterns)  # 最多统计5个
    
    def _calculate_volume_trend(self, df: pd.DataFrame) -> float:
        """计算成交量趋势"""
        if len(df) < 2:
            return 0
        
        # 计算成交量变化趋势
        volume_changes = df['volume'].pct_change().dropna()
        avg_change = volume_changes.mean()
        
        return np.clip(avg_change, -1, 1)


class TimeSeriesFeatureExtractor:
    """时间序列特征提取器"""
    
    def __init__(self):
        """初始化时间序列特征提取器"""
        pass
    
    def extract(self, ts_data: pd.DataFrame, window: int = 20) -> Dict:
        """
        提取时间序列特征
        
        Args:
            ts_data: 时间序列数据
            window: 滑动窗口大小
            
        Returns:
            特征字典
        """
        if len(ts_data) < window:
            return {
                'ma_ratio': 0,
                'rsi': 50,
                'macd': 0,
                'bollinger_position': 0.5,
                'volume_ratio': 1
            }
        
        # 移动平均线比率
        ma_ratio = self._calculate_ma_ratio(ts_data, window)
        
        # RSI
        rsi = self._calculate_rsi(ts_data, window)
        
        # MACD
        macd = self._calculate_macd(ts_data)
        
        # 布林带位置
        bollinger_position = self._calculate_bollinger_position(ts_data, window)
        
        # 成交量比率
        volume_ratio = self._calculate_volume_ratio(ts_data, window)
        
        return {
            'ma_ratio': ma_ratio,
            'rsi': rsi,
            'macd': macd,
            'bollinger_position': bollinger_position,
            'volume_ratio': volume_ratio
        }
    
    def _calculate_ma_ratio(self, df: pd.DataFrame, window: int) -> float:
        """计算移动平均线比率"""
        if len(df) < window:
            return 0
        
        ma = df['close'].rolling(window=window).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        ratio = (current_price - ma) / ma if ma > 0 else 0
        return np.clip(ratio, -1, 1)
    
    def _calculate_rsi(self, df: pd.DataFrame, window: int = 14) -> float:
        """计算RSI"""
        if len(df) < window + 1:
            return 50
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def _calculate_macd(self, df: pd.DataFrame) -> float:
        """计算MACD"""
        if len(df) < 26:
            return 0
        
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        macd = ema12 - ema26
        
        return macd.iloc[-1] / df['close'].iloc[-1] if df['close'].iloc[-1] > 0 else 0
    
    def _calculate_bollinger_position(self, df: pd.DataFrame, window: int = 20) -> float:
        """计算布林带位置"""
        if len(df) < window:
            return 0.5
        
        sma = df['close'].rolling(window=window).mean()
        std = df['close'].rolling(window=window).std()
        
        upper_band = sma + 2 * std
        lower_band = sma - 2 * std
        
        current_price = df['close'].iloc[-1]
        
        # 计算在布林带中的位置 (0-1)
        if upper_band.iloc[-1] - lower_band.iloc[-1] > 0:
            position = (current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])
        else:
            position = 0.5
        
        return position
    
    def _calculate_volume_ratio(self, df: pd.DataFrame, window: int = 5) -> float:
        """计算成交量比率"""
        if len(df) < window:
            return 1
        
        avg_volume = df['volume'].rolling(window=window).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        ratio = current_volume / avg_volume if avg_volume > 0 else 1
        return ratio


class MultimodalFeatureExtractor:
    """多模态特征提取器"""
    
    def __init__(self):
        """初始化多模态特征提取器"""
        self.text_extractor = TextFeatureExtractor()
        self.image_extractor = ImageFeatureExtractor()
        self.ts_extractor = TimeSeriesFeatureExtractor()
    
    def extract(self, 
                text: str,
                kline_data: pd.DataFrame,
                ts_data: pd.DataFrame) -> Dict:
        """
        提取多模态特征
        
        Args:
            text: 文本数据
            kline_data: K线数据
            ts_data: 时间序列数据
            
        Returns:
            多模态特征字典
        """
        # 提取各模态特征
        text_features = self.text_extractor.extract(text)
        image_features = self.image_extractor.extract(kline_data)
        ts_features = self.ts_extractor.extract(ts_data)
        
        return {
            'text': text_features,
            'image': image_features,
            'time_series': ts_features
        }


class CrossModalAttention:
    """跨模态注意力机制"""
    
    def __init__(self, d_model: int = 64):
        """
        初始化跨模态注意力
        
        Args:
            d_model: 模型维度
        """
        self.d_model = d_model
        self.W_q = np.random.randn(d_model, d_model) * 0.01
        self.W_k = np.random.randn(d_model, d_model) * 0.01
        self.W_v = np.random.randn(d_model, d_model) * 0.01
    
    def attention(self, query: np.ndarray, key: np.ndarray, value: np.ndarray) -> np.ndarray:
        """
        计算注意力
        
        Args:
            query: 查询向量
            key: 键向量
            value: 值向量
            
        Returns:
            注意力输出
        """
        # 计算注意力分数
        scores = np.dot(query, key.T) / np.sqrt(self.d_model)
        
        # Softmax
        attention_weights = self._softmax(scores)
        
        # 加权求和
        output = np.dot(attention_weights, value)
        
        return output
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax函数"""
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


class MultimodalFusionModel:
    """多模态融合模型"""
    
    def __init__(self):
        """初始化融合模型"""
        self.attention = CrossModalAttention()
        self.fusion_weights = {
            'text': 0.3,
            'image': 0.4,
            'time_series': 0.3
        }
    
    def fuse(self, features: Dict) -> Dict:
        """
        融合多模态特征
        
        Args:
            features: 多模态特征字典
            
        Returns:
            融合结果
        """
        text_features = features['text']
        image_features = features['image']
        ts_features = features['time_series']
        
        # 将特征转换为向量
        text_vec = self._features_to_vector(text_features)
        image_vec = self._features_to_vector(image_features)
        ts_vec = self._features_to_vector(ts_features)
        
        # 跨模态注意力
        fused_vec = self._cross_modal_attention(text_vec, image_vec, ts_vec)
        
        # 加权融合
        weighted_fusion = (
            text_vec * self.fusion_weights['text'] +
            image_vec * self.fusion_weights['image'] +
            ts_vec * self.fusion_weights['time_series']
        )
        
        # 最终融合
        final_vec = (fused_vec + weighted_fusion) / 2
        
        # 决策
        decision = self._make_decision(final_vec)
        
        return {
            'fused_vector': final_vec,
            'decision': decision,
            'confidence': self._calculate_confidence(final_vec),
            'text_contribution': self._calculate_contribution(text_vec, final_vec),
            'image_contribution': self._calculate_contribution(image_vec, final_vec),
            'ts_contribution': self._calculate_contribution(ts_vec, final_vec)
        }
    
    def _features_to_vector(self, features: Dict) -> np.ndarray:
        """将特征字典转换为向量"""
        return np.array(list(features.values()))
    
    def _cross_modal_attention(self, 
                               text_vec: np.ndarray,
                               image_vec: np.ndarray,
                               ts_vec: np.ndarray) -> np.ndarray:
        """跨模态注意力融合"""
        # 确保向量长度一致
        max_len = max(len(text_vec), len(image_vec), len(ts_vec))
        
        text_vec = np.pad(text_vec, (0, max_len - len(text_vec)))
        image_vec = np.pad(image_vec, (0, max_len - len(image_vec)))
        ts_vec = np.pad(ts_vec, (0, max_len - len(ts_vec)))
        
        # 堆叠向量
        vectors = np.vstack([text_vec, image_vec, ts_vec])
        
        # 计算注意力
        attended = self.attention.attention(vectors, vectors, vectors)
        
        # 平均池化
        fused = np.mean(attended, axis=0)
        
        return fused
    
    def _make_decision(self, fused_vec: np.ndarray) -> str:
        """做出决策"""
        # 计算综合得分
        score = np.mean(fused_vec)
        
        if score > 0.5:
            return '买入'
        elif score > 0.2:
            return '持有'
        elif score > -0.2:
            return '观望'
        elif score > -0.5:
            return '减仓'
        else:
            return '卖出'
    
    def _calculate_confidence(self, fused_vec: np.ndarray) -> float:
        """计算置信度"""
        # 基于向量的一致性计算置信度
        variance = np.var(fused_vec)
        confidence = 1.0 / (1.0 + variance)
        
        return confidence
    
    def _calculate_contribution(self, vec: np.ndarray, fused_vec: np.ndarray) -> float:
        """计算贡献度"""
        # 使用余弦相似度
        norm_vec = np.linalg.norm(vec)
        norm_fused = np.linalg.norm(fused_vec)
        
        if norm_vec == 0 or norm_fused == 0:
            return 0
        
        similarity = np.dot(vec, fused_vec) / (norm_vec * norm_fused)
        return max(0, similarity)
    
    def set_fusion_weights(self, weights: Dict[str, float]):
        """
        设置融合权重
        
        Args:
            weights: 权重字典
        """
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f'权重总和必须为1，当前为{total}')
        
        self.fusion_weights.update(weights)


class MultimodalFusionSystem:
    """多模态融合决策系统（整合类）"""
    
    def __init__(self, db_path: str = 'data/multimodal_cache.db'):
        """
        初始化系统
        
        Args:
            db_path: 数据库路径
        """
        self.feature_extractor = MultimodalFeatureExtractor()
        self.fusion_model = MultimodalFusionModel()
        self.db_path = db_path
        self._init_db()
        self.history = deque(maxlen=100)
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fusion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                stock_code TEXT,
                decision TEXT,
                confidence REAL,
                text_contribution REAL,
                image_contribution REAL,
                ts_contribution REAL,
                features TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def analyze(self,
                stock_code: str,
                text: str,
                kline_data: pd.DataFrame,
                ts_data: pd.DataFrame) -> Dict:
        """
        分析股票
        
        Args:
            stock_code: 股票代码
            text: 文本数据（新闻、公告等）
            kline_data: K线数据
            ts_data: 时间序列数据
            
        Returns:
            分析结果
        """
        # 提取特征
        features = self.feature_extractor.extract(text, kline_data, ts_data)
        
        # 融合特征
        fusion_result = self.fusion_model.fuse(features)
        
        # 构建结果
        result = {
            'stock_code': stock_code,
            'decision': fusion_result['decision'],
            'confidence': fusion_result['confidence'],
            'text_contribution': fusion_result['text_contribution'],
            'image_contribution': fusion_result['image_contribution'],
            'ts_contribution': fusion_result['ts_contribution'],
            'features': features,
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
            INSERT INTO fusion_history 
            (stock_code, decision, confidence, text_contribution, 
             image_contribution, ts_contribution, features)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['stock_code'],
            result['decision'],
            result['confidence'],
            result['text_contribution'],
            result['image_contribution'],
            result['ts_contribution'],
            str(result['features'])
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
            SELECT timestamp, stock_code, decision, confidence,
                   text_contribution, image_contribution, ts_contribution
            FROM fusion_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'timestamp': row[0],
                'stock_code': row[1],
                'decision': row[2],
                'confidence': row[3],
                'text_contribution': row[4],
                'image_contribution': row[5],
                'ts_contribution': row[6]
            }
            for row in rows
        ]
    
    def set_fusion_weights(self, weights: Dict[str, float]):
        """
        设置融合权重
        
        Args:
            weights: 权重字典
        """
        self.fusion_model.set_fusion_weights(weights)


# 使用示例
if __name__ == '__main__':
    # 创建系统
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
    
    print("多模态融合分析结果:")
    print(f"股票代码: {result['stock_code']}")
    print(f"决策: {result['decision']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"文本贡献度: {result['text_contribution']:.2f}")
    print(f"图像贡献度: {result['image_contribution']:.2f}")
    print(f"时序贡献度: {result['ts_contribution']:.2f}")
    print(f"时间戳: {result['timestamp']}")