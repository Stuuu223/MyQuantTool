"""
市场情绪指数模块

功能：
- 基于新闻和社交媒体的情感分析
- 量价关系情绪指标
- 资金流向情绪指标
"""

import re
import jieba
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from textblob import TextBlob
import math
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import warnings
warnings.filterwarnings('ignore')

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: 未安装akshare，部分市场情绪数据获取功能将受限")

@dataclass
class SentimentResult:
    """情感分析结果"""
    score: float          # 情绪分数 (-1 到 1, -1 表示极度负面, 1 表示极度正面)
    confidence: float     # 置信度 (0 到 1)
    sentiment_type: str   # 情绪类型 ('bearish', 'bullish', 'neutral')
    keywords: List[str]   # 关键词
    source: str           # 数据源

@dataclass
class MarketSentimentIndex:
    """市场情绪指数"""
    overall_sentiment: float      # 整体情绪分数
    news_sentiment: float         # 新闻情绪分数
    social_sentiment: float       # 社交媒体情绪分数
    price_sentiment: float        # 价格相关情绪分数
    fund_flow_sentiment: float    # 资金流向情绪分数
    timestamp: datetime
    volatility_adjusted: float    # 波动率调整后的情绪分数

class SentimentAnalyzer:
    """情感分析器"""
    
    def __init__(self):
        # 初始化中文情感词典
        self.positive_words = {
            '涨', '上涨', '强势', '利好', '买入', '增长', '利好消息', '突破', '创新高', 
            '盈利', '增长', '强劲', '反弹', '复苏', '繁荣', '积极', '看好', '推荐', 
            '上涨空间', '超预期', '绩优', '龙头', '领涨', '飙升'
        }
        
        self.negative_words = {
            '跌', '下跌', '弱势', '利空', '卖出', '下跌', '风险', '亏损', '破位', 
            '熊市', '崩盘', '暴跌', '恐慌', '抛售', '低迷', '疲软', '萎缩', '衰退',
            '负面', '担忧', '看空', '下跌空间', '不及预期', '亏损', '退市', '爆雷'
        }
        
        # 初始化情感分析模型
        self.model = self._train_sentiment_model()
    
    def _train_sentiment_model(self):
        """训练情感分析模型"""
        # 这里使用简单的基于词典的方法，实际应用中可以使用更复杂的模型
        # 为了演示，返回None，使用基于词典的方法
        return None
    
    def analyze_text_sentiment(self, text: str) -> SentimentResult:
        """分析文本情感"""
        # 使用jieba进行中文分词
        words = list(jieba.cut(text))
        
        # 统计正面和负面词汇数量
        pos_count = sum(1 for word in words if word in self.positive_words)
        neg_count = sum(1 for word in words if word in self.negative_words)
        
        # 计算情感分数
        total_sentiment_words = pos_count + neg_count
        if total_sentiment_words == 0:
            score = 0.0
        else:
            score = (pos_count - neg_count) / total_sentiment_words
            score = max(-1.0, min(1.0, score))  # 限制在[-1, 1]范围内
        
        # 计算置信度
        confidence = total_sentiment_words / max(1, len(words))  # 基于情感词汇密度
        
        # 确定情绪类型
        if score > 0.1:
            sentiment_type = 'bullish'
        elif score < -0.1:
            sentiment_type = 'bearish'
        else:
            sentiment_type = 'neutral'
        
        # 提取关键词
        keywords = [w for w in words if w in self.positive_words or w in self.negative_words]
        
        return SentimentResult(
            score=score,
            confidence=confidence,
            sentiment_type=sentiment_type,
            keywords=keywords,
            source='text_analysis'
        )
    
    def analyze_news_sentiment(self, news_list: List[Dict]) -> SentimentResult:
        """分析新闻情感"""
        if not news_list:
            return SentimentResult(0.0, 0.0, 'neutral', [], 'news')
        
        total_score = 0
        total_confidence = 0
        all_keywords = []
        
        for news in news_list:
            title = news.get('title', '')
            content = news.get('content', '')
            text = title + ' ' + content
            
            result = self.analyze_text_sentiment(text)
            total_score += result.score
            total_confidence += result.confidence
            all_keywords.extend(result.keywords)
        
        avg_score = total_score / len(news_list)
        avg_confidence = total_confidence / len(news_list)
        
        # 基于新闻发布时间进行加权（最新新闻权重更高）
        weighted_score = self._apply_time_weighting(news_list, avg_score)
        
        return SentimentResult(
            score=weighted_score,
            confidence=avg_confidence,
            sentiment_type='bullish' if weighted_score > 0.1 else 'bearish' if weighted_score < -0.1 else 'neutral',
            keywords=list(set(all_keywords)),
            source='news'
        )
    
    def _apply_time_weighting(self, news_list: List[Dict], base_score: float) -> float:
        """应用时间加权"""
        now = datetime.now()
        total_weight = 0
        weighted_score = 0
        
        for news in news_list:
            pub_time = news.get('publish_time', now)
            if isinstance(pub_time, str):
                try:
                    pub_time = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                except:
                    pub_time = now
            
            # 计算时间差（小时）
            time_diff = (now - pub_time).total_seconds() / 3600
            # 越近的新闻权重越高，使用指数衰减
            weight = math.exp(-time_diff / 24)  # 24小时衰减常数
            
            content = news.get('title', '') + ' ' + news.get('content', '')
            text_result = self.analyze_text_sentiment(content)
            
            weighted_score += text_result.score * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_score / total_weight
        else:
            return base_score

class SocialMediaSentiment:
    """社交媒体情感分析"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
    
    def analyze_weibo_sentiment(self, keywords: List[str], days: int = 7) -> SentimentResult:
        """分析微博情绪（模拟实现）"""
        # 在实际应用中，这里会调用微博API
        # 现在使用模拟数据
        print(f"分析微博关于关键词 {keywords} 的情绪（过去{days}天）")
        
        # 模拟微博数据
        mock_posts = [
            {"text": f"看好{keywords[0]}未来发展，政策利好不断", "timestamp": datetime.now() - timedelta(hours=2)},
            {"text": f"{keywords[0]}今天又涨了，牛市来了", "timestamp": datetime.now() - timedelta(hours=5)},
            {"text": f"担心市场回调，准备减仓", "timestamp": datetime.now() - timedelta(hours=10)},
            {"text": f"经济数据不佳，股市承压", "timestamp": datetime.now() - timedelta(days=1)},
        ]
        
        # 分析每条微博的情绪
        total_score = 0
        total_confidence = 0
        all_keywords = []
        
        for post in mock_posts:
            result = self.sentiment_analyzer.analyze_text_sentiment(post['text'])
            # 应用时间衰减权重
            time_diff = (datetime.now() - post['timestamp']).total_seconds() / 3600
            weight = math.exp(-time_diff / 24)  # 24小时衰减常数
            
            total_score += result.score * weight
            total_confidence += result.confidence * weight
            all_keywords.extend(result.keywords)
        
        total_weight = len(mock_posts)  # 简化的权重计算
        
        if total_weight > 0:
            avg_score = total_score / total_weight
            avg_confidence = total_confidence / total_weight
        else:
            avg_score = 0.0
            avg_confidence = 0.0
        
        return SentimentResult(
            score=avg_score,
            confidence=avg_confidence,
            sentiment_type='bullish' if avg_score > 0.1 else 'bearish' if avg_score < -0.1 else 'neutral',
            keywords=list(set(all_keywords)),
            source='weibo'
        )
    
    def analyze_general_social_sentiment(self, keywords: List[str]) -> SentimentResult:
        """分析通用社交媒体情绪"""
        # 这里可以集成多个社交媒体平台
        weibo_result = self.analyze_weibo_sentiment(keywords)
        
        # 可以添加其他社交媒体平台的分析
        # 如微信公众号、股吧等
        
        return weibo_result

class PriceBasedSentiment:
    """基于价格的情绪指标"""
    
    def calculate_technical_sentiment(self, price_data: pd.DataFrame) -> float:
        """
        基于技术指标计算情绪
        
        Args:
            price_data: 包含OHLCV数据的DataFrame
            
        Returns:
            情绪分数 (-1 到 1)
        """
        if len(price_data) < 20:
            return 0.0
        
        # 计算技术指标
        # 移动平均线情绪
        price_data['MA_5'] = price_data['close'].rolling(window=5).mean()
        price_data['MA_10'] = price_data['close'].rolling(window=10).mean()
        price_data['MA_20'] = price_data['close'].rolling(window=20).mean()
        
        # RSI指标
        delta = price_data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD指标
        exp1 = price_data['close'].ewm(span=12).mean()
        exp2 = price_data['close'].ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        macd_histogram = macd - signal
        
        # 量价关系指标
        price_data['volume_sma'] = price_data['volume'].rolling(window=20).mean()
        price_data['volume_ratio'] = price_data['volume'] / price_data['volume_sma']
        
        # 价格变化率
        price_data['price_change_pct'] = price_data['close'].pct_change()
        
        # 计算情绪分数
        ma_sentiment = 0
        rsi_sentiment = 0
        macd_sentiment = 0
        volume_price_sentiment = 0  # 量价关系情绪
        
        if len(price_data) > 20:
            # 移动平均线情绪：多头排列为积极
            recent_data = price_data.iloc[-5:]
            ma_alignment_score = recent_data.apply(
                lambda x: 1 if x['close'] > x['MA_5'] and x['MA_5'] > x['MA_10'] and x['MA_10'] > x['MA_20'] else 
                         -1 if x['close'] < x['MA_5'] and x['MA_5'] < x['MA_10'] and x['MA_10'] < x['MA_20'] else 0, 
                axis=1
            )
            ma_sentiment = ma_alignment_score.mean()
        
        if len(rsi) > 14:
            recent_rsi = rsi.iloc[-5:].mean()
            # RSI > 70 超买(负面情绪), RSI < 30 超卖(正面情绪)
            if recent_rsi > 70:
                rsi_sentiment = -0.5
            elif recent_rsi < 30:
                rsi_sentiment = 0.5
            else:
                rsi_sentiment = (50 - recent_rsi) / 50  # 标准化到[-1, 1]，但只占一半范围
        
        if len(macd) > 9:
            recent_macd_histogram = macd_histogram.iloc[-3:].mean()
            # MACD柱状图的正负和趋势
            if recent_macd_histogram > 0:
                macd_sentiment = 0.3
            else:
                macd_sentiment = -0.3
        
        # 量价关系情绪：价格上涨伴随成交量放大为积极
        if 'volume_ratio' in price_data.columns and 'price_change_pct' in price_data.columns:
            recent_data = price_data.iloc[-10:]
            positive_price_vol_corr = 0
            for idx in range(1, len(recent_data)):
                price_change = recent_data['price_change_pct'].iloc[idx]
                vol_change = recent_data['volume_ratio'].iloc[idx] - 1
                # 如果价格上涨且成交量放大，为积极信号
                if price_change > 0 and vol_change > 0.2:
                    positive_price_vol_corr += 1
                # 如果价格下跌且成交量萎缩，也为积极信号（健康回调）
                elif price_change < 0 and vol_change < -0.2:
                    positive_price_vol_corr += 0.5
            volume_price_sentiment = positive_price_vol_corr / len(recent_data) if len(recent_data) > 0 else 0
            # 标准化到[-0.5, 0.5]
            volume_price_sentiment = (volume_price_sentiment - 0.5) * 1.0
        
        # 综合情绪分数
        combined_sentiment = (
            ma_sentiment * 0.25 + 
            rsi_sentiment * 0.2 + 
            macd_sentiment * 0.2 + 
            volume_price_sentiment * 0.35  # 量价关系权重较高
        )
        return max(-1.0, min(1.0, combined_sentiment))
    
    def calculate_volume_price_sentiment(self, price_data: pd.DataFrame) -> float:
        """
        专门计算量价关系情绪指标
        
        Args:
            price_data: 包含OHLCV数据的DataFrame
            
        Returns:
            量价关系情绪分数 (-1 到 1)
        """
        if len(price_data) < 10:
            return 0.0
        
        # 计算成交量移动平均
        price_data['volume_sma'] = price_data['volume'].rolling(window=10).mean()
        price_data['volume_ratio'] = price_data['volume'] / price_data['volume_sma']
        
        # 计算价格变化率
        price_data['price_change_pct'] = price_data['close'].pct_change()
        
        # 计算量价配合度
        positive_signals = 0
        total_signals = 0
        
        for i in range(1, len(price_data)):
            price_chg = price_data['price_change_pct'].iloc[i]
            volume_ratio = price_data['volume_ratio'].iloc[i]
            
            if pd.notna(price_chg) and pd.notna(volume_ratio):
                total_signals += 1
                
                # 价格上涨且成交量放大 -> 积极信号
                if price_chg > 0.01 and volume_ratio > 1.2:
                    positive_signals += 1
                # 价格下跌但成交量萎缩 -> 相对积极信号（抛压减轻）
                elif price_chg < -0.01 and volume_ratio < 0.8:
                    positive_signals += 0.5
                # 价格上涨但成交量萎缩 -> 警告信号
                elif price_chg > 0.01 and volume_ratio < 0.8:
                    positive_signals += 0  # 不加分
                # 价格下跌且成交量放大 -> 消极信号
                elif price_chg < -0.01 and volume_ratio > 1.2:
                    positive_signals += 0  # 不加分
        
        if total_signals > 0:
            sentiment_score = (positive_signals / total_signals) * 2 - 1  # 转换到[-1, 1]
            return max(-1.0, min(1.0, sentiment_score))
        else:
            return 0.0

class FundFlowSentiment:
    """资金流向情绪指标"""
    
    def calculate_fund_flow_sentiment(self, fund_flow_data: pd.DataFrame) -> float:
        """
        基于资金流向计算情绪
        
        Args:
            fund_flow_data: 资金流向数据，应包含以下列：
                           - 'large_net_flow': 大单净流入
                           - 'medium_net_flow': 中单净流入
                           - 'small_net_flow': 小单净流入
                           - 'total_flow': 总资金流
            
        Returns:
            情绪分数 (-1 到 1)
        """
        if fund_flow_data.empty:
            return 0.0
        
        # 检查并获取各种资金流向数据
        large_flow = fund_flow_data['large_net_flow'].sum() if 'large_net_flow' in fund_flow_data.columns else 0
        medium_flow = fund_flow_data['medium_net_flow'].sum() if 'medium_net_flow' in fund_flow_data.columns else 0
        small_flow = fund_flow_data['small_net_flow'].sum() if 'small_net_flow' in fund_flow_data.columns else 0
        total_flow = fund_flow_data['total_flow'].sum() if 'total_flow' in fund_flow_data.columns else (abs(large_flow) + abs(medium_flow) + abs(small_flow))
        
        # 计算情绪分数，给不同类型资金不同权重
        # 大单资金（通常代表机构投资者）权重最高
        large_weight = 0.5
        medium_weight = 0.3
        small_weight = 0.2
        
        weighted_flow = (
            large_flow * large_weight +
            medium_flow * medium_weight +
            small_flow * small_weight
        )
        
        # 标准化到[-1, 1]
        if total_flow != 0:
            sentiment = weighted_flow / abs(total_flow)
            return max(-1.0, min(1.0, sentiment))
        else:
            return 0.0
    
    def calculate_institution_vs_retail_sentiment(self, fund_flow_data: pd.DataFrame) -> float:
        """
        计算机构与散户情绪对比
        
        Args:
            fund_flow_data: 资金流向数据
            
        Returns:
            机构vs散户情绪分数 (-1 到 1)
        """
        if fund_flow_data.empty:
            return 0.0
            
        # 获取机构资金（大单+中单）和散户资金（小单）
        institutional_flow = 0
        retail_flow = 0
        
        if 'large_net_flow' in fund_flow_data.columns:
            institutional_flow += fund_flow_data['large_net_flow'].sum() * 0.7
        if 'medium_net_flow' in fund_flow_data.columns:
            institutional_flow += fund_flow_data['medium_net_flow'].sum() * 0.3
        if 'small_net_flow' in fund_flow_data.columns:
            retail_flow = fund_flow_data['small_net_flow'].sum()
        
        total_institutional_retail_flow = abs(institutional_flow) + abs(retail_flow)
        
        if total_institutional_retail_flow != 0:
            # 机构资金情绪对比散户资金情绪
            sentiment = (institutional_flow - retail_flow) / total_institutional_retail_flow
            return max(-1.0, min(1.0, sentiment))
        else:
            return 0.0
    
    def calculate_fund_flow_trend(self, fund_flow_data: pd.DataFrame) -> float:
        """
        计算资金流向趋势情绪
        
        Args:
            fund_flow_data: 带时间序列的资金流向数据
            
        Returns:
            资金流向趋势情绪分数 (-1 到 1)
        """
        if fund_flow_data.empty or len(fund_flow_data) < 2:
            return 0.0
        
        # 假设数据有日期列，如果没有则使用索引
        if 'date' in fund_flow_data.columns:
            fund_flow_data = fund_flow_data.sort_values('date')
        
        # 计算资金流向的变化趋势
        if 'total_flow' in fund_flow_data.columns:
            flow_series = fund_flow_data['total_flow'].values
        else:
            # 如果没有总资金流，使用大单+中单+小单
            flow_series = []
            for col in ['large_net_flow', 'medium_net_flow', 'small_net_flow']:
                if col in fund_flow_data.columns:
                    flow_series = fund_flow_data[col].values if len(flow_series) == 0 else flow_series + fund_flow_data[col].values
        
        if len(flow_series) < 2:
            return 0.0
        
        # 计算资金流向的趋势
        recent_flow = np.mean(flow_series[-3:]) if len(flow_series) >= 3 else flow_series[-1]
        earlier_flow = np.mean(flow_series[:3]) if len(flow_series) >= 3 else flow_series[0]
        
        # 如果近期资金流入比早期更多，为积极信号
        if earlier_flow != 0:
            trend = (recent_flow - earlier_flow) / abs(earlier_flow)
            return max(-1.0, min(1.0, trend))
        else:
            return 1.0 if recent_flow > 0 else -1.0 if recent_flow < 0 else 0.0
    
    def get_market_sentiment_from_fund_flow(self, symbol: str = "000001") -> float:
        """从资金流向获取市场情绪（模拟实现）"""
        # 模拟获取资金流向数据
        # 在实际应用中，这里会调用真实的数据源
        np.random.seed(42)  # 为了可重复性
        
        # 模拟资金流向数据，包含多日数据以便计算趋势
        dates = pd.date_range(end=datetime.now(), periods=10)
        data = {
            'date': dates,
            'large_net_flow': np.random.normal(1000000, 500000, 10),  # 大单净流入
            'medium_net_flow': np.random.normal(500000, 200000, 10),  # 中单净流入
            'small_net_flow': np.random.normal(200000, 100000, 10),   # 小单净流入
            'total_flow': np.random.normal(1700000, 600000, 10)       # 总资金流
        }
        fund_flow_df = pd.DataFrame(data)
        
        # 计算多种资金流向情绪指标并综合
        basic_sentiment = self.calculate_fund_flow_sentiment(fund_flow_df)
        inst_vs_retail_sentiment = self.calculate_institution_vs_retail_sentiment(fund_flow_df)
        trend_sentiment = self.calculate_fund_flow_trend(fund_flow_df)
        
        # 综合情绪（给不同指标不同权重）
        combined_sentiment = (
            basic_sentiment * 0.4 + 
            inst_vs_retail_sentiment * 0.3 + 
            trend_sentiment * 0.3
        )
        
        return max(-1.0, min(1.0, combined_sentiment))

class MarketSentimentIndexCalculator:
    """市场情绪指数计算器"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.social_analyzer = SocialMediaSentiment()
        self.price_analyzer = PriceBasedSentiment()
        self.fund_flow_analyzer = FundFlowSentiment()
        
        # 各情绪指标的权重
        self.news_weight = 0.3
        self.social_weight = 0.2
        self.volume_weight = 0.25
        self.price_weight = 0.25
    
    def calculate_composite_index(self, 
                                   news_sentiment,
                                   social_sentiment,
                                   volume_sentiment,
                                   price_sentiment):
        """
        计算综合情绪指数
        
        Args:
            news_sentiment: 新闻情绪分数（可以是标量或Series）
            social_sentiment: 社交媒体情绪分数（可以是标量或Series）
            volume_sentiment: 量价情绪分数（可以是标量或Series）
            price_sentiment: 价格情绪分数（可以是标量或Series）
            
        Returns:
            float or Series: 综合情绪指数 (-1 到 1)
        """
        import pandas as pd
        
        composite = (
            news_sentiment * self.news_weight +
            social_sentiment * self.social_weight +
            volume_sentiment * self.volume_weight +
            price_sentiment * self.price_weight
        )
        
        # 限制在[-1, 1]范围内
        # 使用numpy的clip函数，它可以处理标量和Series
        import numpy as np
        return np.clip(composite, -1.0, 1.0)
    
    def calculate_comprehensive_sentiment(self, 
                                       symbols: List[str], 
                                       days: int = 7) -> MarketSentimentIndex:
        """
        计算综合市场情绪指数
        
        Args:
            symbols: 股票代码列表
            days: 分析天数
            
        Returns:
            MarketSentimentIndex: 市场情绪指数
        """
        # 获取新闻情绪
        news_sentiment = self._get_news_sentiment(symbols, days)
        
        # 获取社交媒体情绪
        social_sentiment = self.social_analyzer.analyze_general_social_sentiment(symbols)
        
        # 获取价格相关情绪（如果可能）
        price_sentiment = self._get_price_based_sentiment(symbols)
        
        # 获取资金流向情绪
        fund_flow_sentiment = self._get_fund_flow_sentiment(symbols[0] if symbols else "000001")
        
        # 计算整体情绪（加权平均）
        overall_sentiment = (
            news_sentiment.score * 0.3 +
            social_sentiment.score * 0.2 +
            price_sentiment * 0.25 +
            fund_flow_sentiment * 0.25
        )
        
        # 计算波动率调整后的情绪分数
        volatility_adjusted = self._adjust_for_volatility(
            overall_sentiment, symbols, days
        )
        
        return MarketSentimentIndex(
            overall_sentiment=overall_sentiment,
            news_sentiment=news_sentiment.score,
            social_sentiment=social_sentiment.score,
            price_sentiment=price_sentiment,
            fund_flow_sentiment=fund_flow_sentiment,
            timestamp=datetime.now(),
            volatility_adjusted=volatility_adjusted
        )
    
    def _get_news_sentiment(self, symbols: List[str], days: int) -> SentimentResult:
        """获取新闻情绪（模拟实现）"""
        # 模拟新闻数据
        mock_news = []
        for symbol in symbols:
            mock_news.extend([
                {
                    'title': f'{symbol}发布利好消息，市场看好',
                    'content': f'最新消息显示{symbol}公司业绩超预期，分析师普遍上调评级',
                    'publish_time': datetime.now() - timedelta(hours=5)
                },
                {
                    'title': f'政策利好{name}行业，相关股票受关注',
                    'content': f'政府发布支持{name}行业发展的政策，市场情绪积极',
                    'publish_time': datetime.now() - timedelta(hours=12)
                }
            ])
        
        return self.sentiment_analyzer.analyze_news_sentiment(mock_news)
    
    def _get_price_based_sentiment(self, symbols: List[str]) -> float:
        """获取价格相关情绪（模拟实现）"""
        # 模拟价格数据
        dates = pd.date_range(end=datetime.now(), periods=30)
        prices = 100 + np.cumsum(np.random.normal(0, 2, 30))  # 模拟价格走势
        
        price_data = pd.DataFrame({
            'date': dates,
            'open': prices + np.random.normal(0, 0.5, 30),
            'high': prices + abs(np.random.normal(0, 1, 30)),
            'low': prices - abs(np.random.normal(0, 1, 30)),
            'close': prices,
            'volume': np.random.normal(1000000, 200000, 30)
        })
        
        # 计算技术指标情绪
        technical_sentiment = self.price_analyzer.calculate_technical_sentiment(price_data)
        
        # 计算量价关系情绪
        volume_price_sentiment = self.price_analyzer.calculate_volume_price_sentiment(price_data)
        
        # 综合两种情绪指标
        combined_sentiment = (technical_sentiment * 0.6 + volume_price_sentiment * 0.4)
        
        return combined_sentiment
    
    def _get_fund_flow_sentiment(self, symbol: str) -> float:
        """获取资金流向情绪"""
        return self.fund_flow_analyzer.get_market_sentiment_from_fund_flow(symbol)
    
    def _adjust_for_volatility(self, sentiment: float, symbols: List[str], days: int) -> float:
        """基于市场波动率调整情绪分数"""
        # 简单的波动率调整：波动率高时，情绪信号可能更嘈杂
        # 模拟波动率计算
        volatility = 0.02  # 模拟市场波动率
        
        # 波动率越高，对情绪分数的信任度越低
        adjustment_factor = 1 / (1 + volatility * 50)  # 简化的调整公式
        
        return sentiment * adjustment_factor

# 使用示例
def demo_market_sentiment():
    """演示市场情绪分析"""
    # 创建市场情绪指数计算器
    calculator = MarketSentimentIndexCalculator()
    
    # 计算综合市场情绪
    symbols = ['000001', '600000', '300001']
    sentiment_index = calculator.calculate_comprehensive_sentiment(symbols)
    
    print("=== 市场情绪指数 ===")
    print(f"整体情绪分数: {sentiment_index.overall_sentiment:.3f}")
    print(f"新闻情绪分数: {sentiment_index.news_sentiment:.3f}")
    print(f"社交媒体情绪分数: {sentiment_index.social_sentiment:.3f}")
    print(f"价格相关情绪分数: {sentiment_index.price_sentiment:.3f}")
    print(f"资金流向情绪分数: {sentiment_index.fund_flow_sentiment:.3f}")
    print(f"波动率调整后情绪分数: {sentiment_index.volatility_adjusted:.3f}")
    print(f"分析时间: {sentiment_index.timestamp}")
    
    # 解释情绪水平
    overall = sentiment_index.overall_sentiment
    if overall > 0.3:
        sentiment_level = "极度乐观"
    elif overall > 0.1:
        sentiment_level = "乐观"
    elif overall > -0.1:
        sentiment_level = "中性"
    elif overall > -0.3:
        sentiment_level = "悲观"
    else:
        sentiment_level = "极度悲观"
    
    print(f"市场情绪水平: {sentiment_level}")

if __name__ == "__main__":
    demo_market_sentiment()