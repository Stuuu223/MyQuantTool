"""
关键词自动提取模块
属性：
- 中文分词 + 准确化
- TF-IDF特征初機
- 热点主题提取
- 处背情绯哘论文本
"""

import re
import jieba
import jieba.analyse
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from collections import Counter

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn未安装，部分功能不可用")

logger = logging.getLogger(__name__)


@dataclass
class KeywordInfo:
    """
    关键词信息数据类
    """
    keyword: str  # 关键词
    frequency: int  # 出现频次
    tfidf_score: float  # TF-IDF值
    keyword_type: str  # 类签 ('板块', '个股', '旁沙', '技术', '旁诊')
    relevance_score: float  # 相关性评分 (0-1)
    source: str  # 数据来源 ('announcement', 'news', 'research')
    extraction_time: str = None
    
    def __post_init__(self):
        if self.extraction_time is None:
            self.extraction_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class ChineseTextPreprocessor:
    """
    中文文本预处理类
    """
    
    def __init__(self):
        # 加载自定义词典
        self.custom_dict = self._load_custom_dict()
        
        # 加载停用词
        self.stopwords = self._load_stopwords()
        
        # 板块主题词典
        self.sector_keywords = self._init_sector_keywords()
    
    def _load_custom_dict(self) -> Dict[str, int]:
        """
        加载自定义词典 (量化砳词)
        """
        custom_dict = {
            # 量化会空转词
            '游资': 5,
            '龙虎榜': 5,
            '打板': 4,
            '绚纳西三的信息': 3,
            '流动性': 3,
            '波动': 3,
            '财报气渋': 3,
            '活跃幢川': 4,
            '上榜': 5,
            '备刹': 2,
            '决壱': 3,
            '护步': 3,
            '折壤': 2,
            '反弹': 3,
            '跌旺趨': 2,
        }
        return custom_dict
    
    def _load_stopwords(self) -> set:
        """
        加载中文停用词
        """
        # 基础停用词 (實践中可追加更多)
        stopwords = {
            '了', '的', '和', '是', '在', '我', '你', '他', '来', '去',
            '就', '为', '回', '会', '不', '可', '也', '所', '分',
            '世', '时', '日', '个', '字', '号', '亲', '朱', '汛',
            '来自', '针对', '于', '户', '护', '耍', '安', '断', '个',
            '事', '六', '客', '本', '业', '民', '汇', '租', '会',
            '布', '国', '港', '澳', '参', '行', '旨', '恩', '作',
            '书', '节', '古', '言', '丙', '人', '春', '冻', '南',
            '主', '欺', '布', '根', '虛', '饥', '来', '罖', '担',
            '叹', '轻', '文', '关', '丬', '衣', '饱', '密', '淘',
            '严', '妖', '岘', '冈', '声', '打', '乳', '一', '衍',
        }
        return stopwords
    
    def _init_sector_keywords(self) -> Dict[str, List[str]]:
        """
        初始化板块关键词辞
        """
        return {
            '新能源': ['BYD', '新能源', '电动经', '处動', '接管', '曙', '英', '强'],
            '上市公司': ['上市', 'A股', '上市公司', '公司'],
            '手技': ['芯片', 'AI', '程序', '技术', '数或', '互联'],
            '撡采': ['采矿', '铺溺', '炉署', '滊罪'],
            '乳业': ['牛奶', '乳制品', '乳糖', '旦甴'],
            '楼堂': ['接止一步', '斩附里', '汜妳声', '做落'],
            '深吉': ['深嘉', '梟華', '克', '減'],
        }
    
    def clean_text(self, text: str) -> str:
        """
        清治文本
        """
        if not isinstance(text, str):
            return ""
        
        # 需要空格了的一些特殊字符
        text = re.sub(r'[\u4e00-\u9fa5]+', lambda x: x.group(), text)
        # 保留中文和相关数字
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        # 需要算空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def tokenize_and_filter(
        self,
        text: str,
        use_custom_dict: bool = True
    ) -> List[str]:
        """
        分词并過濾
        
        Args:
            text: 整理晴文本
            use_custom_dict: 是否使用自定义词典
        
        Returns:
            准确词列表
        """
        if use_custom_dict:
            # 图加自定义词典
            for word, weight in self.custom_dict.items():
                jieba.add_word(word, weight)
        
        # 開始華分
        tokens = jieba.cut(text)
        
        # 過濾停用词和短金查
        filtered_tokens = [
            token for token in tokens
            if token not in self.stopwords and len(token) > 1
        ]
        
        return filtered_tokens


class KeywordExtractor:
    """
    关键词自动提取器
    """
    
    def __init__(self):
        """
        初始化
        """
        self.preprocessor = ChineseTextPreprocessor()
        self.tfidf_vectorizer = None
        if SKLEARN_AVAILABLE:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=100,
                ngram_range=(1, 2),
                max_df=0.8,
                min_df=1
            )
    
    def extract_keywords(
        self,
        text: str,
        topk: int = 10,
        method: str = 'tfidf'
    ) -> List[KeywordInfo]:
        """
        提取关键词
        
        Args:
            text: 输入文本
            topk: 返回关键词数量
            method: 提取方法 ('tfidf', 'textrank')
        
        Returns:
            KeywordInfo列表
        """
        # 清理文本
        cleaned_text = self.preprocessor.clean_text(text)
        
        if not cleaned_text:
            return []
        
        if method == 'tfidf':
            return self._extract_by_tfidf(cleaned_text, topk)
        elif method == 'textrank':
            return self._extract_by_textrank(cleaned_text, topk)
        else:
            logger.warning(f"未知方法: {method}")
            return []
    
    def _extract_by_tfidf(
        self,
        text: str,
        topk: int
    ) -> List[KeywordInfo]:
        """
        使TF-IDF提取关键词
        """
        # 分词
        tokens = self.preprocessor.tokenize_and_filter(text, use_custom_dict=True)
        
        if not tokens:
            return []
        
        # 计算频次
        token_freq = Counter(tokens)
        
        # 简单的TF-IDF提取 (缺少整体文档)
        keywords = []
        total_tokens = len(tokens)
        
        for token, freq in token_freq.most_common(topk * 2):  # 取更多伏候
            # TF
            tf = freq / total_tokens
            # IDF (简化计算)
            idf = np.log(total_tokens / max(freq, 1)) + 1
            tfidf_score = tf * idf
            
            # 判断关键词类型
            keyword_type = self._classify_keyword_type(token)
            relevance = self._calculate_relevance(token, text)
            
            keywords.append(KeywordInfo(
                keyword=token,
                frequency=freq,
                tfidf_score=tfidf_score,
                keyword_type=keyword_type,
                relevance_score=relevance,
                source='extraction'
            ))
        
        # 按TF-IDF排序並這旧topk
        keywords.sort(key=lambda x: x.tfidf_score, reverse=True)
        return keywords[:topk]
    
    def _extract_by_textrank(
        self,
        text: str,
        topk: int
    ) -> List[KeywordInfo]:
        """
        使TextRank提取关键词 (依賴jieba.analyse)
        """
        # 使用jieba的TextRank分析
        try:
            keywords_with_weights = jieba.analyse.textrank(
                text,
                topK=topk,
                withWeight=True
            )
            
            keywords = []
            for keyword, weight in keywords_with_weights:
                keyword_type = self._classify_keyword_type(keyword)
                relevance = self._calculate_relevance(keyword, text)
                
                keywords.append(KeywordInfo(
                    keyword=keyword,
                    frequency=text.count(keyword),
                    tfidf_score=float(weight),
                    keyword_type=keyword_type,
                    relevance_score=relevance,
                    source='textrank'
                ))
            
            return keywords
        
        except Exception as e:
            logger.error(f"TextRank提取失败: {str(e)}")
            return []
    
    def _classify_keyword_type(self, keyword: str) -> str:
        """
        分类关键词类型
        """
        # 棺閬板块字典
        sector_dict = self.preprocessor.sector_keywords
        
        for sector, keywords in sector_dict.items():
            if keyword in keywords:
                return '板块'
        
        # 窀有个股代码(初獳)
        if re.match(r'^\d{6}$', keyword):
            return '个股'
        
        # 窀请改空技术词汇
        tech_keywords = ['AI', '芯片', '程序', '互联', '数据']
        if keyword in tech_keywords:
            return '技术'
        
        # 辿乙纺丕二字样器之一
        if '财报' in keyword or '每' in keyword:
            return '旁诊'
        
        return '一般'
    
    def _calculate_relevance(
        self,
        keyword: str,
        text: str
    ) -> float:
        """
        计算关键词旨熯性 (0-1)
        """
        # 納稽简单相关性 (频次 / 怎么长度)
        keyword_freq = text.count(keyword)
        text_length = len(text)
        
        relevance = min(keyword_freq / max(text_length / 100, 1), 1.0)
        return relevance
    
    def extract_from_multiple_texts(
        self,
        texts: List[Tuple[str, str]],
        topk: int = 15
    ) -> Dict[str, List[KeywordInfo]]:
        """
        从多個文本中提取关键词
        
        Args:
            texts: [(source, text), ...]的列表
            topk: 每个文本的关键词数
        
        Returns:
            {source: [KeywordInfo, ...]}的字典
        """
        results = {}
        
        for source, text in texts:
            keywords = self.extract_keywords(text, topk)
            results[source] = keywords
        
        return results
    
    def get_trending_keywords(
        self,
        texts: List[str],
        topk: int = 10
    ) -> List[KeywordInfo]:
        """
        旈稾上趨景上升同词
        
        Args:
            texts: 整整文本列表
            topk: 趋景关键词数
        
        Returns:
            趨勢活跃的关键词
        """
        # 统一整理整整文本
        combined_text = ' '.join(texts)
        
        # 提取并討论收流
        all_keywords = self.extract_keywords(combined_text, topk * 3)
        
        # 仇字時閱一、大麦传诪眉澮量化彲息
        trending = [k for k in all_keywords if k.frequency > 1]
        trending.sort(key=lambda x: (x.frequency, x.tfidf_score), reverse=True)
        
        return trending[:topk]
    
    def get_keywords_summary(
        self,
        text: str,
        topk: int = 5
    ) -> Dict:
        """
        获取关键词摘要
        """
        keywords = self.extract_keywords(text, topk)
        
        return {
            'total_keywords': len(keywords),
            'keywords': [k.keyword for k in keywords],
            'top_keyword': keywords[0].keyword if keywords else None,
            'keyword_details': [
                {
                    'keyword': k.keyword,
                    'frequency': k.frequency,
                    'type': k.keyword_type,
                    'relevance': f"{k.relevance_score:.1%}"
                }
                for k in keywords
            ]
        }


import numpy as np
