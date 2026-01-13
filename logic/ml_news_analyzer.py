"""
机器学习新闻分析模块
使用 scikit-learn 实现情绪分析和影响度预测
"""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, mean_squared_error, accuracy_score
from sklearn.preprocessing import LabelEncoder
import jieba
import joblib
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
import pickle


@dataclass
class NewsFeature:
    """新闻特征"""
    title_tfidf: np.ndarray
    content_tfidf: np.ndarray
    title_length: int
    content_length: int
    has_numbers: bool
    has_stock_codes: bool
    keyword_count: int
    source_encoded: int


@dataclass
class MLPredictionResult:
    """机器学习预测结果"""
    sentiment: str  # positive, negative, neutral
    sentiment_confidence: float
    impact_score: float
    features_used: Dict[str, any]


class FeatureExtractor:
    """特征提取器"""
    
    def __init__(self):
        self.tfidf_vectorizer_title = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        self.tfidf_vectorizer_content = TfidfVectorizer(max_features=2000, ngram_range=(1, 2))
        self.source_encoder = LabelEncoder()
        self.fitted = False
        
        # 财经关键词
        self.finance_keywords = [
            '增长', '上涨', '下跌', '盈利', '亏损', '涨停', '跌停',
            '业绩', '财报', '营收', '利润', '增长', '下降', '突破',
            '收购', '重组', '政策', '利好', '利空', '创新高', '暴跌',
            '加速', '放缓', '强劲', '疲软', '超预期', '不及预期'
        ]
    
    def fit(self, titles: List[str], contents: List[str], sources: List[str]):
        """训练特征提取器"""
        self.tfidf_vectorizer_title.fit(titles)
        self.tfidf_vectorizer_content.fit(contents)
        self.source_encoder.fit(sources)
        self.fitted = True
    
    def extract_features(self, title: str, content: str, source: str, related_stocks: List[str] = None) -> NewsFeature:
        """提取单个新闻的特征"""
        if not self.fitted:
            raise ValueError("特征提取器未训练，请先调用 fit()")
        
        # TF-IDF特征
        title_tfidf = self.tfidf_vectorizer_title.transform([title]).toarray()[0]
        content_tfidf = self.tfidf_vectorizer_content.transform([content]).toarray()[0]
        
        # 基础特征
        title_length = len(title)
        content_length = len(content)
        
        # 是否包含数字
        has_numbers = any(c.isdigit() for c in title + content)
        
        # 是否包含股票代码
        has_stock_codes = len(related_stocks) > 0 if related_stocks else False
        
        # 关键词数量
        keyword_count = sum(1 for kw in self.finance_keywords if kw in title + content)
        
        # 来源编码
        try:
            source_encoded = self.source_encoder.transform([source])[0]
        except:
            source_encoded = 0
        
        return NewsFeature(
            title_tfidf=title_tfidf,
            content_tfidf=content_tfidf,
            title_length=title_length,
            content_length=content_length,
            has_numbers=has_numbers,
            has_stock_codes=has_stock_codes,
            keyword_count=keyword_count,
            source_encoded=source_encoded
        )
    
    def extract_batch_features(self, titles: List[str], contents: List[str], 
                               sources: List[str], related_stocks_list: List[List[str]] = None) -> np.ndarray:
        """批量提取特征"""
        if not self.fitted:
            raise ValueError("特征提取器未训练，请先调用 fit()")
        
        features_list = []
        
        for i in range(len(titles)):
            related_stocks = related_stocks_list[i] if related_stocks_list else []
            feature = self.extract_features(titles[i], contents[i], sources[i], related_stocks)
            
            # 合并所有特征
            feature_vector = np.concatenate([
                feature.title_tfidf,
                feature.content_tfidf,
                [feature.title_length],
                [feature.content_length],
                [1 if feature.has_numbers else 0],
                [1 if feature.has_stock_codes else 0],
                [feature.keyword_count],
                [feature.source_encoded]
            ])
            
            features_list.append(feature_vector)
        
        return np.array(features_list)


class SentimentClassifier:
    """情绪分类器"""
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.feature_extractor = FeatureExtractor()
        self.trained = False
        self.label_encoder = LabelEncoder()
    
    def train(self, titles: List[str], contents: List[str], sources: List[str], 
              sentiments: List[str], related_stocks_list: List[List[str]] = None):
        """训练情绪分类器"""
        # 训练特征提取器
        self.feature_extractor.fit(titles, contents, sources)
        
        # 提取特征
        X = self.feature_extractor.extract_batch_features(titles, contents, sources, related_stocks_list)
        
        # 编码标签
        y = self.label_encoder.fit_transform(sentiments)
        
        # 训练模型
        # 检查是否每个类别至少有2个样本，如果是则使用 stratify，否则不使用
        unique_labels, counts = np.unique(y, return_counts=True)
        if all(count >= 2 for count in counts):
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        else:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model.fit(X_train, y_train)
        
        # 评估模型
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        self.trained = True
        
        return accuracy
    
    def predict(self, title: str, content: str, source: str, 
                related_stocks: List[str] = None) -> Tuple[str, float]:
        """预测情绪"""
        if not self.trained:
            raise ValueError("模型未训练，请先调用 train()")
        
        # 提取特征
        feature = self.feature_extractor.extract_features(title, content, source, related_stocks)
        
        # 合并特征
        X = np.concatenate([
            feature.title_tfidf,
            feature.content_tfidf,
            [feature.title_length],
            [feature.content_length],
            [1 if feature.has_numbers else 0],
            [1 if feature.has_stock_codes else 0],
            [feature.keyword_count],
            [feature.source_encoded]
        ]).reshape(1, -1)
        
        # 预测
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        
        # 解码标签
        sentiment = self.label_encoder.inverse_transform([prediction])[0]
        confidence = max(probabilities)
        
        return sentiment, confidence
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        if not self.trained:
            return {}
        
        feature_names = []
        
        # TF-IDF特征名称
        title_words = self.feature_extractor.tfidf_vectorizer_title.get_feature_names_out()
        content_words = self.feature_extractor.tfidf_vectorizer_content.get_feature_names_out()
        
        feature_names.extend([f"title_{w}" for w in title_words])
        feature_names.extend([f"content_{w}" for w in content_words])
        feature_names.extend(['title_length', 'content_length', 'has_numbers', 
                            'has_stock_codes', 'keyword_count', 'source_encoded'])
        
        importance_dict = dict(zip(feature_names, self.model.feature_importances_))
        
        # 返回最重要的20个特征
        sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return dict(sorted_features)


class ImpactPredictor:
    """影响度预测器"""
    
    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.feature_extractor = FeatureExtractor()
        self.trained = False
    
    def train(self, titles: List[str], contents: List[str], sources: List[str],
              impact_scores: List[float], related_stocks_list: List[List[str]] = None):
        """训练影响度预测模型"""
        # 训练特征提取器
        self.feature_extractor.fit(titles, contents, sources)
        
        # 提取特征
        X = self.feature_extractor.extract_batch_features(titles, contents, sources, related_stocks_list)
        y = np.array(impact_scores)
        
        # 训练模型
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model.fit(X_train, y_train)
        
        # 评估模型
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        
        self.trained = True
        
        return mse
    
    def predict(self, title: str, content: str, source: str,
                related_stocks: List[str] = None) -> float:
        """预测影响度"""
        if not self.trained:
            raise ValueError("模型未训练，请先调用 train()")
        
        # 提取特征
        feature = self.feature_extractor.extract_features(title, content, source, related_stocks)
        
        # 合并特征
        X = np.concatenate([
            feature.title_tfidf,
            feature.content_tfidf,
            [feature.title_length],
            [feature.content_length],
            [1 if feature.has_numbers else 0],
            [1 if feature.has_stock_codes else 0],
            [feature.keyword_count],
            [feature.source_encoded]
        ]).reshape(1, -1)
        
        # 预测
        impact_score = self.model.predict(X)[0]
        
        # 限制在0-100范围内
        impact_score = max(0, min(100, impact_score))
        
        return impact_score


class MLNewsAnalyzer:
    """机器学习新闻分析器"""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        self.sentiment_classifier = SentimentClassifier()
        self.impact_predictor = ImpactPredictor()
        
        self.sentiment_model_path = os.path.join(model_dir, "sentiment_classifier.pkl")
        self.impact_model_path = os.path.join(model_dir, "impact_predictor.pkl")
    
    def train_models(self, training_data: pd.DataFrame):
        """
        训练模型
        
        Args:
            training_data: 训练数据，包含列: title, content, source, sentiment, impact_score, related_stocks
        """
        print("开始训练情绪分类模型...")
        
        # 准备数据
        titles = training_data['title'].tolist()
        contents = training_data['content'].tolist()
        sources = training_data['source'].tolist()
        sentiments = training_data['sentiment'].tolist()
        impact_scores = training_data['impact_score'].tolist()
        
        related_stocks_list = []
        if 'related_stocks' in training_data.columns:
            related_stocks_list = training_data['related_stocks'].tolist()
        
        # 训练情绪分类器
        sentiment_accuracy = self.sentiment_classifier.train(
            titles, contents, sources, sentiments, related_stocks_list
        )
        print(f"情绪分类模型训练完成，准确率: {sentiment_accuracy:.4f}")
        
        # 训练影响度预测器
        print("开始训练影响度预测模型...")
        impact_mse = self.impact_predictor.train(
            titles, contents, sources, impact_scores, related_stocks_list
        )
        print(f"影响度预测模型训练完成，MSE: {impact_mse:.4f}")
        
        # 保存模型
        self.save_models()
        
        return {
            'sentiment_accuracy': sentiment_accuracy,
            'impact_mse': impact_mse
        }
    
    def analyze(self, title: str, content: str, source: str, 
                related_stocks: List[str] = None) -> MLPredictionResult:
        """分析新闻"""
        # 预测情绪
        sentiment, sentiment_confidence = self.sentiment_classifier.predict(
            title, content, source, related_stocks
        )
        
        # 预测影响度
        impact_score = self.impact_predictor.predict(
            title, content, source, related_stocks
        )
        
        # 获取特征重要性
        feature_importance = self.sentiment_classifier.get_feature_importance()
        
        return MLPredictionResult(
            sentiment=sentiment,
            sentiment_confidence=sentiment_confidence,
            impact_score=impact_score,
            features_used=feature_importance
        )
    
    def save_models(self):
        """保存模型"""
        joblib.dump(self.sentiment_classifier, self.sentiment_model_path)
        joblib.dump(self.impact_predictor, self.impact_model_path)
        print(f"模型已保存到 {self.model_dir}")
    
    def load_models(self):
        """加载模型"""
        if os.path.exists(self.sentiment_model_path):
            self.sentiment_classifier = joblib.load(self.sentiment_model_path)
            print("情绪分类模型加载成功")
        
        if os.path.exists(self.impact_model_path):
            self.impact_predictor = joblib.load(self.impact_model_path)
            print("影响度预测模型加载成功")
    
    def is_trained(self) -> bool:
        """检查模型是否已训练"""
        return (self.sentiment_classifier.trained and 
                self.impact_predictor.trained)
    
    def create_sample_training_data(self) -> pd.DataFrame:
        """创建示例训练数据"""
        sample_data = [
            {
                'title': '公司发布业绩预告，净利润同比增长50%',
                'content': '某公司今日发布业绩预告，预计2024年上半年净利润同比增长50%，主要受益于主营业务增长和新产品推出。',
                'source': '证券时报',
                'sentiment': 'positive',
                'impact_score': 75,
                'related_stocks': ['600519']
            },
            {
                'title': '股价暴跌，公司业绩不及预期',
                'content': '受市场环境影响，公司业绩大幅下滑，股价出现暴跌，投资者信心受挫。',
                'source': '新浪财经',
                'sentiment': 'negative',
                'impact_score': 80,
                'related_stocks': ['000858']
            },
            {
                'title': '公司发布季度财报，业绩符合预期',
                'content': '公司发布季度财报，营收和利润均符合市场预期，经营状况稳定。',
                'source': '东方财富网',
                'sentiment': 'neutral',
                'impact_score': 50,
                'related_stocks': ['600036']
            },
            {
                'title': '重大利好！公司获得政府补贴',
                'content': '公司获得政府专项补贴，将显著提升公司盈利能力，股价有望上涨。',
                'source': '证券日报',
                'sentiment': 'positive',
                'impact_score': 85,
                'related_stocks': ['600000']
            },
            {
                'title': '公司面临重大诉讼风险',
                'content': '公司卷入重大诉讼案件，可能对经营产生不利影响，投资者需谨慎。',
                'source': '第一财经',
                'sentiment': 'negative',
                'impact_score': 70,
                'related_stocks': ['601318']
            }
        ]
        
        return pd.DataFrame(sample_data)


# 使用示例
if __name__ == "__main__":
    # 创建分析器
    analyzer = MLNewsAnalyzer()
    
    # 创建示例训练数据
    training_data = analyzer.create_sample_training_data()
    
    print("训练数据:")
    print(training_data)
    print()
    
    # 训练模型
    print("=" * 60)
    print("开始训练模型...")
    print("=" * 60)
    results = analyzer.train_models(training_data)
    
    print()
    print("=" * 60)
    print("测试模型预测...")
    print("=" * 60)
    
    # 测试预测
    test_news = {
        'title': '公司业绩超预期，股价大涨',
        'content': '公司发布业绩报告，净利润大幅增长，超出市场预期，股价应声上涨。',
        'source': '证券时报',
        'related_stocks': ['600519']
    }
    
    prediction = analyzer.analyze(
        test_news['title'],
        test_news['content'],
        test_news['source'],
        test_news['related_stocks']
    )
    
    print(f"\n预测结果:")
    print(f"情绪倾向: {prediction.sentiment}")
    print(f"情绪置信度: {prediction.sentiment_confidence:.4f}")
    print(f"影响度评分: {prediction.impact_score:.2f}")
    print(f"\n重要特征:")
    for feature, importance in list(prediction.features_used.items())[:10]:
        print(f"  {feature}: {importance:.4f}")
    
    # 保存模型
    analyzer.save_models()
    
    # 测试加载模型
    print("\n" + "=" * 60)
    print("测试加载模型...")
    print("=" * 60)
    
    new_analyzer = MLNewsAnalyzer()
    new_analyzer.load_models()
    
    prediction2 = new_analyzer.analyze(
        test_news['title'],
        test_news['content'],
        test_news['source'],
        test_news['related_stocks']
    )
    
    print(f"\n加载模型后预测结果:")
    print(f"情绪倾向: {prediction2.sentiment}")
    print(f"情绪置信度: {prediction2.sentiment_confidence:.4f}")
    print(f"影响度评分: {prediction2.impact_score:.2f}")