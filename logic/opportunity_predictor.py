"""
龙虎榜機会预测模型
三層特征融合: 历史规律 (40%) + 技术面 (35%) + 情緒指数 (25%)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class PredictedCapital:
    """预测的游资对象"""
    capital_name: str
    appearance_probability: float  # 0-1
    predict_reasons: List[str]  # 预测理由
    risk_level: str  # '低' / '中' / '高'
    expected_amount: float  # 预测成交额


@dataclass
class PredictedStock:
    """预测的股票对象"""
    code: str
    name: str
    appearance_probability: float
    likely_capitals: List[str]  # 可能操作的游资
    predicted_reason: str


@dataclass
class OpportunityPrediction:
    """预测结果对象"""
    tomorrow_date: str
    overall_activity: int  # 0-100
    prediction_confidence: float  # 0-1
    market_sentiment: str 
    predicted_capitals: List[PredictedCapital] = field(default_factory=list)
    predicted_stocks: List[PredictedStock] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)


class OpportunityPredictor:
    """龙虎榜機会预测器"""
    
    def __init__(self, lookback_days: int = 180, min_history: int = 5):
        """
        初始化预测器
        
        Args:
            lookback_days: 历史查看天数
            min_history: 最少历史记录
        """
        self.lookback_days = lookback_days
        self.min_history = min_history
    
    def predict_tomorrow(self, tomorrow_date: str, df_lhb_history: pd.DataFrame) -> OpportunityPrediction:
        """
        预测明天龙虎榜機会
        
        Args:
            tomorrow_date: 明天日期 (YYYY-MM-DD)
            df_lhb_history: 历史龙虎榜数据
        
        Returns:
            OpportunityPrediction: 预测结果
        """
        
        # 特征计算 (40% + 35% + 25%)
        feature_1_history = self._feature_1_history_patterns(df_lhb_history)  # 40%
        feature_2_technical = self._feature_2_technical_signals(df_lhb_history)  # 35%
        feature_3_sentiment = self._feature_3_sentiment_index(df_lhb_history)  # 25%
        
        # 综合权重融合
        activity_score = (
            feature_1_history['activity'] * 0.40 +
            feature_2_technical['activity'] * 0.35 +
            feature_3_sentiment['activity'] * 0.25
        )
        
        # 计算置信度
        confidence = (
            feature_1_history.get('confidence', 0.5) * 0.4 +
            feature_2_technical.get('confidence', 0.5) * 0.35 +
            feature_3_sentiment.get('confidence', 0.5) * 0.25
        )
        
        # 预测游资
        predicted_capitals = self._predict_capitals(
            df_lhb_history, activity_score
        )
        
        # 预测股票
        predicted_stocks = self._predict_stocks(
            df_lhb_history, predicted_capitals
        )
        
        # 市场情緒
        market_sentiment = self._determine_sentiment(activity_score)
        
        # 核心见解
        key_insights = self._generate_insights(
            activity_score, feature_1_history, feature_2_technical, feature_3_sentiment
        )
        
        return OpportunityPrediction(
            tomorrow_date=tomorrow_date,
            overall_activity=int(activity_score),
            prediction_confidence=confidence,
            predicted_capitals=predicted_capitals,
            predicted_stocks=predicted_stocks,
            market_sentiment=market_sentiment,
            key_insights=key_insights
        )
    
    def _feature_1_history_patterns(self, df: pd.DataFrame) -> Dict:
        """
        特征一: 历史规律 (40%)
        - 接近月末的活跃度
        - 历史规律日的龙虎榜数量
        - 月末加权
        """
        if '日期' not in df.columns or len(df) < self.min_history:
            return {'activity': 50, 'confidence': 0.5}
        
        df_sorted = df.sort_values('日期')
        latest_date = pd.to_datetime(df_sorted['日期']).max()
        
        # 最近的一周的活跃度
        week_ago = latest_date - timedelta(days=7)
        recent_activity = len(df_sorted[pd.to_datetime(df_sorted['日期']) >= week_ago])
        week_activity_score = min(recent_activity / 5 * 100, 100)  # 5次及以上为满分
        
        # 月底效应 (28-31日附近)
        today = latest_date.day
        if today >= 25:  # 月底时期
            month_end_bonus = 20
        else:
            month_end_bonus = 0
        
        # 上一个月末 (28-31日) 的活跃效应
        last_month_end = latest_date.replace(day=1) - timedelta(days=1)
        last_month_end_activity = len(df_sorted[
            (pd.to_datetime(df_sorted['日期']) >= last_month_end.replace(day=25)) &
            (pd.to_datetime(df_sorted['日期']) <= last_month_end)
        ])
        
        activity_score = (
            week_activity_score * 0.6 +
            (last_month_end_activity / 3 * 100) * 0.3 +
            month_end_bonus
        )
        
        confidence = min(len(df) / 20, 1.0)  # 数据越丰富信心越高
        
        return {'activity': min(activity_score, 100), 'confidence': confidence}
    
    def _feature_2_technical_signals(self, df: pd.DataFrame) -> Dict:
        """
        特征二: 技术面 (35%)
        - 涨停板数量
        - 探底信号 (低于10日均线)
        - 融资余额增长
        """
        if len(df) < self.min_history:
            return {'activity': 50, 'confidence': 0.5}
        
        # 涨停板数量 (大概估计: 每条记录表示1个题材, 里面的涨停股数)
        # 帮助指标: 笔者有自己的股票数据接口
        daily_limit_count = 3  # TODO: 从 akshare 接入
        daily_limit_score = min(daily_limit_count / 2 * 100, 100)  # 2个涨停股以上
        
        # 探底信号 (获取股票余额校验)
        # 帮助指标: 深市收红出现净买入下探底
        bottom_signal_ratio = 0.3  # 30%的股票下跌
        bottom_signal_score = bottom_signal_ratio * 100
        
        # 融资余额 (增长 = 行情向好)
        financing_increase_ratio = 0.1  # 假设上涨 (持续一周)
        financing_score = financing_increase_ratio * 100
        
        activity_score = (
            daily_limit_score * 0.4 +
            bottom_signal_score * 0.4 +
            financing_score * 0.2
        )
        
        return {'activity': min(activity_score, 100), 'confidence': 0.6}
    
    def _feature_3_sentiment_index(self, df: pd.DataFrame) -> Dict:
        """
        特征三: 情绪指数 (25%)
        - 短线买入比例高 = 看好 = 情绪阳性
        - 游资大家级成员情绪
        - 龙虎榜活跃次数增加
        """
        if len(df) < self.min_history:
            return {'activity': 50, 'confidence': 0.5}
        
        # 买入比例
        buy_count = len(df[df['操作方向'].str.contains('买', na=False)]) if '操作方向' in df.columns else 50
        sell_count = len(df[df['操作方向'].str.contains('卖', na=False)]) if '操作方向' in df.columns else 50
        total_count = buy_count + sell_count or 1
        buy_ratio = buy_count / total_count
        sentiment_score = buy_ratio * 100
        
        # 龙虎榜揺收次数
        if '游资名称' in df.columns:
            capital_participation = df['游资名称'].nunique()
            participation_score = min(capital_participation / 10 * 100, 100)  # 10个游资为满分
        else:
            participation_score = 50
        
        activity_score = sentiment_score * 0.6 + participation_score * 0.4
        
        return {'activity': min(activity_score, 100), 'confidence': 0.55}
    
    def _predict_capitals(self, df: pd.DataFrame, activity_score: float) -> List[PredictedCapital]:
        """预测高概率游资"""
        if '游资名称' not in df.columns:
            return []
        
        # 游资活跃度排名
        capital_freq = df['游资名称'].value_counts()
        
        result = []
        for capital_name, freq in capital_freq.head(5).items():
            # 出现概率 (历史频率 * 整体活跃度 / 100)
            appearance_prob = min((freq / len(df)) * (activity_score / 100), 1.0)
            
            # 预测理由
            reasons = []
            if appearance_prob > 0.5:
                reasons.append(f"历史平均频率{(freq/len(df)*100):.0f}%")
            if activity_score > 70:
                reasons.append("强势上涨动能关联游资")
            
            # 风险等级
            if appearance_prob > 0.7:
                risk_level = '高'
            elif appearance_prob > 0.4:
                risk_level = '中'
            else:
                risk_level = '低'
            
            # 预测成交额
            if '成交额' in df.columns:
                expected_amount = (df[df['游资名称'] == capital_name]['成交额'].sum() / len(df)) * 2
            else:
                # 如果没有成交额列，使用频率作为替代
                expected_amount = (freq / len(df)) * 1000000  # 默认值
            
            result.append(PredictedCapital(
                capital_name=capital_name,
                appearance_probability=appearance_prob,
                predict_reasons=reasons or ['正常活跃率'],
                risk_level=risk_level,
                expected_amount=expected_amount
            ))
        
        return result
    
    def _predict_stocks(self, df: pd.DataFrame, 
                       predicted_capitals: List[PredictedCapital]) -> List[PredictedStock]:
        """预测高概率股票"""
        if '股票代码' not in df.columns or '股票名称' not in df.columns:
            return []
        
        # 股票活跃度排名
        stock_freq = df.groupby(['股票代码', '股票名称']).size()
        
        result = []
        for (code, name), freq in stock_freq.head(10).items():
            # 出现概率
            appearance_prob = min((freq / len(df)) * 0.9, 1.0)  # 保守了些
            
            # 可能的游资
            likely_capitals = df[df['股票代码'] == code]['游资名称'].value_counts().head(3).index.tolist()
            
            result.append(PredictedStock(
                code=code,
                name=name,
                appearance_probability=appearance_prob,
                likely_capitals=likely_capitals,
                predicted_reason=f"历史{freq}次出现, 游资{', '.join(likely_capitals[:2])}"
            ))
        
        return result
    
    def _determine_sentiment(self, activity_score: float) -> str:
        """判断市场情绪"""
        if activity_score >= 70:
            return '乐观'  # 看涨
        elif activity_score >= 40:
            return '中性'  # 中性
        else:
            return '悲观'  # 看跌
    
    def _generate_insights(self, activity_score: float, f1: Dict, f2: Dict, f3: Dict) -> List[str]:
        """核心见解"""
        insights = []
        
        if activity_score >= 70:
            insights.append("明天龙虎榜活动可能活跃, 建议关注游资动态")
        elif activity_score <= 30:
            insights.append("明天龙虎榜活动较弱, 需等待新的上涨机会")
        
        if f1['activity'] > 70:
            insights.append("历史规律按上个月末和月末活跃程序, 明日可能是非常时刻")
        
        if f2['activity'] > 60:
            insights.append("技术面消息参考比较充足, 市场情绪向好")
        
        if f3['activity'] > 60:
            insights.append("情绪面积极友善, 建议积极布局")
        
        return insights or ["情况表明正常, 中一标了"]
