"""
智能新闻分析系统
实现多层过滤机制：
1. 新闻质量评估
2. 相关性过滤
3. 情绪分析
4. 影响度评估
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import re
from .llm_interface import LLMManager, LLMMessage, get_llm_manager


@dataclass
class NewsItem:
    """新闻项"""
    title: str
    content: str
    source: str
    publish_time: datetime
    url: str
    related_stocks: List[str]  # 相关股票代码


@dataclass
class NewsAnalysisResult:
    """新闻分析结果"""
    news: NewsItem
    
    # 第一层：质量评估
    quality_score: float  # 0-100
    quality_details: Dict[str, Any]
    
    # 第二层：相关性评估
    relevance_score: float  # 0-100
    relevance_details: Dict[str, Any]
    
    # 第三层：情绪分析
    sentiment: str  # positive, negative, neutral
    sentiment_score: float  # -1 to 1
    sentiment_details: Dict[str, Any]
    
    # 第四层：影响度评估
    impact_score: float  # 0-100
    impact_details: Dict[str, Any]
    
    # 综合评分
    overall_score: float  # 0-100
    recommendation: str
    
    # 过滤结果
    passed_filters: bool
    filter_reasons: List[str]


class NewsQualityAnalyzer:
    """新闻质量分析器（第一层过滤）"""
    
    def analyze(self, news: NewsItem) -> Dict[str, Any]:
        """分析新闻质量"""
        details = {}
        score = 0
        
        # 1. 来源可信度（30分）
        source_score = self._evaluate_source(news.source)
        details['source'] = {
            'source': news.source,
            'score': source_score,
            'max': 30
        }
        score += source_score
        
        # 2. 时效性（25分）
        timeliness_score = self._evaluate_timeliness(news.publish_time)
        details['timeliness'] = {
            'publish_time': news.publish_time,
            'score': timeliness_score,
            'max': 25
        }
        score += timeliness_score
        
        # 3. 内容完整性（20分）
        completeness_score = self._evaluate_completeness(news.content)
        details['completeness'] = {
            'content_length': len(news.content),
            'score': completeness_score,
            'max': 20
        }
        score += completeness_score
        
        # 4. 信息密度（15分）
        density_score = self._evaluate_density(news.content)
        details['density'] = {
            'score': density_score,
            'max': 15
        }
        score += density_score
        
        # 5. 标题质量（10分）
        title_score = self._evaluate_title(news.title)
        details['title'] = {
            'title': news.title,
            'score': title_score,
            'max': 10
        }
        score += title_score
        
        details['total_score'] = score
        details['total_max'] = 100
        
        return details
    
    def _evaluate_source(self, source: str) -> float:
        """评估来源可信度"""
        # 高可信度来源
        high_sources = ['新华社', '人民日报', '央视财经', '证券时报', '中国证券报', '上海证券报']
        # 中等可信度来源
        medium_sources = ['新浪财经', '东方财富', '同花顺', '金融界', '网易财经', '腾讯财经']
        # 低可信度来源
        low_sources = ['自媒体', '公众号', '博客']
        
        source_lower = source.lower()
        
        for s in high_sources:
            if s in source:
                return 30.0
        
        for s in medium_sources:
            if s in source:
                return 20.0
        
        for s in low_sources:
            if s in source:
                return 10.0
        
        # 默认中等
        return 15.0
    
    def _evaluate_timeliness(self, publish_time: datetime) -> float:
        """评估时效性"""
        if not publish_time:
            return 0.0
        
        now = datetime.now()
        hours_ago = (now - publish_time).total_seconds() / 3600
        
        if hours_ago <= 1:
            return 25.0  # 1小时内
        elif hours_ago <= 6:
            return 20.0  # 6小时内
        elif hours_ago <= 24:
            return 15.0  # 24小时内
        elif hours_ago <= 72:
            return 10.0  # 3天内
        elif hours_ago <= 168:
            return 5.0   # 1周内
        else:
            return 0.0   # 超过1周
    
    def _evaluate_completeness(self, content: str) -> float:
        """评估内容完整性"""
        if not content:
            return 0.0
        
        length = len(content)
        
        if length >= 500:
            return 20.0  # 内容完整
        elif length >= 300:
            return 15.0  # 内容较完整
        elif length >= 100:
            return 10.0  # 内容一般
        else:
            return 5.0   # 内容简略
    
    def _evaluate_density(self, content: str) -> float:
        """评估信息密度"""
        if not content:
            return 0.0
        
        # 检查关键信息
        keywords = ['增长', '下降', '盈利', '亏损', '涨停', '跌停', '收购', '重组', '业绩', '财报']
        keyword_count = sum(1 for kw in keywords if kw in content)
        
        if keyword_count >= 5:
            return 15.0
        elif keyword_count >= 3:
            return 10.0
        elif keyword_count >= 1:
            return 5.0
        else:
            return 0.0
    
    def _evaluate_title(self, title: str) -> float:
        """评估标题质量"""
        if not title:
            return 0.0
        
        # 检查标题长度
        if len(title) < 5:
            return 2.0  # 太短
        elif len(title) > 50:
            return 5.0  # 太长
        else:
            base_score = 8.0
        
        # 检查是否包含关键信息
        if any(kw in title for kw in ['增长', '下降', '涨', '跌', '业绩', '财报']):
            base_score += 2.0
        
        return min(base_score, 10.0)


class NewsRelevanceAnalyzer:
    """新闻相关性分析器（第二层过滤）"""
    
    def analyze(self, news: NewsItem, target_stocks: List[str] = None) -> Dict[str, Any]:
        """分析新闻相关性"""
        details = {}
        score = 0
        
        # 1. 股票相关性（40分）
        stock_score = self._evaluate_stock_relevance(news, target_stocks)
        details['stock_relevance'] = {
            'related_stocks': news.related_stocks,
            'target_stocks': target_stocks,
            'score': stock_score,
            'max': 40
        }
        score += stock_score
        
        # 2. 行业相关性（30分）
        industry_score = self._evaluate_industry_relevance(news)
        details['industry_relevance'] = {
            'score': industry_score,
            'max': 30
        }
        score += industry_score
        
        # 3. 主题相关性（30分）
        topic_score = self._evaluate_topic_relevance(news)
        details['topic_relevance'] = {
            'score': topic_score,
            'max': 30
        }
        score += topic_score
        
        details['total_score'] = score
        details['total_max'] = 100
        
        return details
    
    def _evaluate_stock_relevance(self, news: NewsItem, target_stocks: List[str]) -> float:
        """评估股票相关性"""
        if not target_stocks:
            return 20.0  # 没有目标股票，中等分数
        
        if not news.related_stocks:
            return 0.0
        
        # 计算匹配度
        matches = len(set(news.related_stocks) & set(target_stocks))
        ratio = matches / len(target_stocks)
        
        if ratio >= 0.5:
            return 40.0
        elif ratio >= 0.3:
            return 30.0
        elif ratio >= 0.1:
            return 20.0
        else:
            return 0.0
    
    def _evaluate_industry_relevance(self, news: NewsItem) -> float:
        """评估行业相关性"""
        # 定义热门行业
        hot_industries = ['人工智能', '新能源', '半导体', '医药', '白酒', '金融', '地产', '汽车']
        
        content_lower = news.content.lower()
        title_lower = news.title.lower()
        
        matches = 0
        for industry in hot_industries:
            if industry in content_lower or industry in title_lower:
                matches += 1
        
        if matches >= 2:
            return 30.0
        elif matches >= 1:
            return 20.0
        else:
            return 10.0
    
    def _evaluate_topic_relevance(self, news: NewsItem) -> float:
        """评估主题相关性"""
        # 定义热门主题
        hot_topics = ['业绩预告', '财报', '收购', '重组', '政策', '利好', '利空', '涨停', '跌停']
        
        content_lower = news.content.lower()
        title_lower = news.title.lower()
        
        matches = 0
        for topic in hot_topics:
            if topic in content_lower or topic in title_lower:
                matches += 1
        
        if matches >= 3:
            return 30.0
        elif matches >= 2:
            return 20.0
        elif matches >= 1:
            return 10.0
        else:
            return 5.0


class NewsSentimentAnalyzer:
    """新闻情绪分析器（第三层过滤）"""
    
    def __init__(self, llm_manager: LLMManager = None):
        self.llm_manager = llm_manager or get_llm_manager()
    
    def analyze(self, news: NewsItem) -> Dict[str, Any]:
        """分析新闻情绪"""
        details = {}
        
        # 使用LLM进行情绪分析
        prompt = f"""
请分析以下新闻的情绪倾向：

标题：{news.title}
内容：{news.content}

请从以下维度分析：
1. 情绪倾向（正面/负面/中性）
2. 情绪强度（0-10）
3. 关键情绪词

请以JSON格式返回结果：
{{
    "sentiment": "positive/negative/neutral",
    "intensity": 0-10,
    "keywords": ["关键词1", "关键词2"]
}}
"""
        
        try:
            messages = [
                LLMMessage(role="system", content="你是一个专业的金融情绪分析师"),
                LLMMessage(role="user", content=prompt)
            ]
            
            response = self.llm_manager.chat(messages)
            
            # 解析响应
            import json
            try:
                result = json.loads(response.content)
                sentiment = result.get('sentiment', 'neutral')
                intensity = result.get('intensity', 5)
                keywords = result.get('keywords', [])
                
                # 转换情绪为分数
                if sentiment == 'positive':
                    sentiment_score = intensity / 10
                elif sentiment == 'negative':
                    sentiment_score = -intensity / 10
                else:
                    sentiment_score = 0
                
            except:
                # 如果解析失败，使用规则分析
                sentiment, sentiment_score, keywords = self._rule_based_sentiment(news)
                intensity = abs(sentiment_score) * 10
        
        except:
            # 如果LLM调用失败，使用规则分析
            sentiment, sentiment_score, keywords = self._rule_based_sentiment(news)
            intensity = abs(sentiment_score) * 10
        
        details['sentiment'] = sentiment
        details['sentiment_score'] = sentiment_score
        details['intensity'] = intensity
        details['keywords'] = keywords
        
        return details
    
    def _rule_based_sentiment(self, news: NewsItem) -> tuple:
        """基于规则的情绪分析"""
        positive_words = ['增长', '上涨', '盈利', '利好', '突破', '创新高', '加速', '强劲', '优异', '超预期']
        negative_words = ['下降', '下跌', '亏损', '利空', '暴跌', '跌破', '放缓', '疲软', '不及预期', '风险']
        
        content = news.title + ' ' + news.content
        
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        
        keywords = []
        for word in positive_words:
            if word in content:
                keywords.append(word)
        for word in negative_words:
            if word in content:
                keywords.append(word)
        
        if positive_count > negative_count:
            sentiment = 'positive'
            sentiment_score = min(positive_count / 10, 1.0)
        elif negative_count > positive_count:
            sentiment = 'negative'
            sentiment_score = -min(negative_count / 10, 1.0)
        else:
            sentiment = 'neutral'
            sentiment_score = 0.0
        
        return sentiment, sentiment_score, keywords


class NewsImpactAnalyzer:
    """新闻影响度分析器（第四层过滤）"""
    
    def analyze(self, news: NewsItem, sentiment_score: float) -> Dict[str, Any]:
        """分析新闻影响度"""
        details = {}
        score = 0
        
        # 1. 市场影响（30分）
        market_score = self._evaluate_market_impact(news, sentiment_score)
        details['market_impact'] = {
            'score': market_score,
            'max': 30
        }
        score += market_score
        
        # 2. 行业影响（25分）
        industry_score = self._evaluate_industry_impact(news)
        details['industry_impact'] = {
            'score': industry_score,
            'max': 25
        }
        score += industry_score
        
        # 3. 个股影响（25分）
        stock_score = self._evaluate_stock_impact(news)
        details['stock_impact'] = {
            'related_stocks_count': len(news.related_stocks),
            'score': stock_score,
            'max': 25
        }
        score += stock_score
        
        # 4. 持续时间（20分）
        duration_score = self._evaluate_duration(news)
        details['duration'] = {
            'score': duration_score,
            'max': 20
        }
        score += duration_score
        
        details['total_score'] = score
        details['total_max'] = 100
        
        return details
    
    def _evaluate_market_impact(self, news: NewsItem, sentiment_score: float) -> float:
        """评估市场影响"""
        # 情绪强度影响
        intensity = abs(sentiment_score)
        
        # 检查是否为重大消息
        major_keywords = ['政策', '央行', '证监会', '国务院', '重大', '突发']
        is_major = any(kw in news.title or kw in news.content for kw in major_keywords)
        
        base_score = intensity * 20
        if is_major:
            base_score += 10
        
        return min(base_score, 30.0)
    
    def _evaluate_industry_impact(self, news: NewsItem) -> float:
        """评估行业影响"""
        # 检查是否涉及热门行业
        hot_industries = ['人工智能', '新能源', '半导体', '医药']
        
        content = news.title + ' ' + news.content
        matches = sum(1 for ind in hot_industries if ind in content)
        
        if matches >= 2:
            return 25.0
        elif matches >= 1:
            return 15.0
        else:
            return 10.0
    
    def _evaluate_stock_impact(self, news: NewsItem) -> float:
        """评估个股影响"""
        stock_count = len(news.related_stocks)
        
        if stock_count >= 10:
            return 25.0
        elif stock_count >= 5:
            return 20.0
        elif stock_count >= 1:
            return 15.0
        else:
            return 5.0
    
    def _evaluate_duration(self, news: NewsItem) -> float:
        """评估持续时间"""
        # 检查消息类型
        long_term_keywords = ['战略', '长期', '规划', '重组']
        short_term_keywords = ['突发', '临时', '公告']
        
        content = news.title + ' ' + news.content
        
        long_term = any(kw in content for kw in long_term_keywords)
        short_term = any(kw in content for kw in short_term_keywords)
        
        if long_term:
            return 20.0  # 长期影响
        elif short_term:
            return 10.0  # 短期影响
        else:
            return 15.0  # 中期影响


class IntelligentNewsAnalyzer:
    """智能新闻分析系统 - 多层过滤"""
    
    def __init__(self, llm_manager: LLMManager = None):
        self.llm_manager = llm_manager or get_llm_manager()
        
        # 初始化各层分析器
        self.quality_analyzer = NewsQualityAnalyzer()
        self.relevance_analyzer = NewsRelevanceAnalyzer()
        self.sentiment_analyzer = NewsSentimentAnalyzer(self.llm_manager)
        self.impact_analyzer = NewsImpactAnalyzer()
        
        # 设置各层过滤阈值
        self.quality_threshold = 60.0
        self.relevance_threshold = 50.0
        self.impact_threshold = 50.0
    
    def analyze(self, news: NewsItem, target_stocks: List[str] = None) -> NewsAnalysisResult:
        """多层过滤分析"""
        
        # 第一层：质量评估
        quality_details = self.quality_analyzer.analyze(news)
        quality_score = quality_details['total_score']
        
        # 第二层：相关性评估
        relevance_details = self.relevance_analyzer.analyze(news, target_stocks)
        relevance_score = relevance_details['total_score']
        
        # 第三层：情绪分析
        sentiment_details = self.sentiment_analyzer.analyze(news)
        sentiment = sentiment_details['sentiment']
        sentiment_score = sentiment_details['sentiment_score']
        
        # 第四层：影响度评估
        impact_details = self.impact_analyzer.analyze(news, sentiment_score)
        impact_score = impact_details['total_score']
        
        # 综合评分（加权平均）
        overall_score = (
            quality_score * 0.3 +
            relevance_score * 0.25 +
            (abs(sentiment_score) * 100) * 0.2 +
            impact_score * 0.25
        )
        
        # 过滤判断
        passed_filters = True
        filter_reasons = []
        
        if quality_score < self.quality_threshold:
            passed_filters = False
            filter_reasons.append(f"质量评分过低（{quality_score:.1f} < {self.quality_threshold}）")
        
        if relevance_score < self.relevance_threshold:
            passed_filters = False
            filter_reasons.append(f"相关性评分过低（{relevance_score:.1f} < {self.relevance_threshold}）")
        
        if impact_score < self.impact_threshold:
            passed_filters = False
            filter_reasons.append(f"影响度评分过低（{impact_score:.1f} < {self.impact_threshold}）")
        
        # 生成建议
        if passed_filters:
            if overall_score >= 80:
                recommendation = "强烈推荐关注"
            elif overall_score >= 60:
                recommendation = "推荐关注"
            else:
                recommendation = "可以关注"
        else:
            recommendation = "不建议关注"
        
        return NewsAnalysisResult(
            news=news,
            quality_score=quality_score,
            quality_details=quality_details,
            relevance_score=relevance_score,
            relevance_details=relevance_details,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            sentiment_details=sentiment_details,
            impact_score=impact_score,
            impact_details=impact_details,
            overall_score=overall_score,
            recommendation=recommendation,
            passed_filters=passed_filters,
            filter_reasons=filter_reasons
        )
    
    def batch_analyze(self, news_list: List[NewsItem], target_stocks: List[str] = None) -> List[NewsAnalysisResult]:
        """批量分析"""
        results = []
        for news in news_list:
            result = self.analyze(news, target_stocks)
            results.append(result)
        
        # 按综合评分排序
        results.sort(key=lambda x: x.overall_score, reverse=True)
        
        return results


# 使用示例
if __name__ == "__main__":
    # 创建新闻项
    news = NewsItem(
        title="某公司发布业绩预告，净利润同比增长50%",
        content="某公司今日发布业绩预告，预计2024年上半年净利润同比增长50%，主要受益于主营业务增长和新产品推出。公司表示，将继续加大研发投入，提升市场竞争力。受此消息影响，相关概念股有望受益。",
        source="证券时报",
        publish_time=datetime.now(),
        url="https://example.com/news/123",
        related_stocks=["600519", "000858"]
    )
    
    # 创建分析器
    analyzer = IntelligentNewsAnalyzer()
    
    # 分析新闻
    result = analyzer.analyze(news, target_stocks=["600519"])
    
    # 打印结果
    print("=" * 60)
    print("智能新闻分析结果")
    print("=" * 60)
    print(f"\n新闻标题: {result.news.title}")
    print(f"来源: {result.news.source}")
    print(f"发布时间: {result.news.publish_time}")
    
    print("\n" + "-" * 60)
    print("第一层：质量评估")
    print("-" * 60)
    print(f"质量评分: {result.quality_score:.1f}/100")
    for key, value in result.quality_details.items():
        if key not in ['total_score', 'total_max']:
            print(f"{key}: {value['score']:.1f}/{value['max']}")
    
    print("\n" + "-" * 60)
    print("第二层：相关性评估")
    print("-" * 60)
    print(f"相关性评分: {result.relevance_score:.1f}/100")
    for key, value in result.relevance_details.items():
        if key not in ['total_score', 'total_max']:
            print(f"{key}: {value['score']:.1f}/{value['max']}")
    
    print("\n" + "-" * 60)
    print("第三层：情绪分析")
    print("-" * 60)
    print(f"情绪倾向: {result.sentiment}")
    print(f"情绪分数: {result.sentiment_score:.2f}")
    print(f"关键词: {result.sentiment_details.get('keywords', [])}")
    
    print("\n" + "-" * 60)
    print("第四层：影响度评估")
    print("-" * 60)
    print(f"影响度评分: {result.impact_score:.1f}/100")
    for key, value in result.impact_details.items():
        if key not in ['total_score', 'total_max']:
            print(f"{key}: {value['score']:.1f}/{value['max']}")
    
    print("\n" + "=" * 60)
    print("综合结果")
    print("=" * 60)
    print(f"综合评分: {result.overall_score:.1f}/100")
    print(f"建议: {result.recommendation}")
    print(f"通过过滤: {'是' if result.passed_filters else '否'}")
    if result.filter_reasons:
        print(f"过滤原因: {'; '.join(result.filter_reasons)}")