"""
多因子模型融合模块
属性：
- LSTM时间序列因子 (1/3 权重)
- K线技术因子 (1/3 权重)
- 游资网络因子 (1/3 权重)
- 分敥新闪d牥旪d断观
- 信号一致性检查
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """
    信号类型
    """
    BULLISH = 1  # 看涨
    BEARISH = -1  # 看跌
    NEUTRAL = 0  # 中性


@dataclass
class FactorScore:
    """
    单一因子值
    """
    factor_name: str
    raw_score: float  # [0, 1]
    weight: float  # 士重权重
    signal: SignalType  # 信号方向
    confidence: float  # [0, 1] 信信幦
    explanation: str  # 解释


@dataclass
class FusionResult:
    """
    融合结果
    """
    timestamp: datetime
    stock: str
    capital: str  # 主欲游资
    composite_score: float  # [-1, 1]
    signal: SignalType
    confidence: float  # [0, 1]
    factor_scores: Dict[str, FactorScore]
    reasoning: str  # 收案本体


class MultifactorFusionEngine:
    """
    多因子模型融合引擎
    """
    
    def __init__(
        self,
        lstm_weight: float = 0.3,
        kline_weight: float = 0.3,
        network_weight: float = 0.4
    ):
        """
        Args:
            lstm_weight: LSTM时间序列权重
            kline_weight: K线技术权重
            network_weight: 游资网络权重
        """
        # 正规化权重
        total = lstm_weight + kline_weight + network_weight
        self.lstm_weight = lstm_weight / total
        self.kline_weight = kline_weight / total
        self.network_weight = network_weight / total
        
        self.factor_histories = []  # 因子上榜历史
    
    def calculate_lstm_factor(
        self,
        lstm_probability: float,
        historical_accuracy: Optional[float] = None
    ) -> FactorScore:
        """
        计算LSTM因子
        
        Args:
            lstm_probability: LSTM预测偏率 [0, 1]
            historical_accuracy: 历史准确率 [0, 1]
        
        Returns:
            FactorScore
        """
        # 控制范围 [0, 1]
        lstm_probability = max(0, min(1, lstm_probability))
        
        # 确定信号
        if lstm_probability > 0.6:
            signal = SignalType.BULLISH
            score = (lstm_probability - 0.5) * 2  # [0, 1]
        elif lstm_probability < 0.4:
            signal = SignalType.BEARISH
            score = (0.5 - lstm_probability) * 2  # [0, 1]
        else:
            signal = SignalType.NEUTRAL
            score = 0.5
        
        # 䯹称化分数 [-1, 1]
        symmetric_score = 2 * score - 1 if signal == SignalType.BULLISH else -(2 * score - 1)
        
        # 置信度 (基于历史准确率)
        if historical_accuracy:
            confidence = historical_accuracy
        else:
            # 稜援准确率根据单位时間起伏
            confidence = 0.6 if 0.4 < lstm_probability < 0.9 else 0.4
        
        return FactorScore(
            factor_name='LSTM Time Series',
            raw_score=abs(symmetric_score),
            weight=self.lstm_weight,
            signal=signal,
            confidence=confidence,
            explanation=f"LSTM预测概率{lstm_probability:.1%}, 上榜可能性{abs(symmetric_score):.1%}"
        )
    
    def calculate_kline_factor(
        self,
        ma_signal: SignalType,
        macd_signal: SignalType,
        rsi_value: float,
        kdj_value: float,
        volatility: float,
        support_distance: Optional[float] = None
    ) -> FactorScore:
        """
        计算K线技术因子
        
        Args:
            ma_signal: 移动平均信号
            macd_signal: MACD信号
            rsi_value: RSI值 [0, 100]
            kdj_value: KDJ值 [0, 100]
            volatility: 波动率
            support_distance: 与支撒线距离 (百分比)
        
        Returns:
            FactorScore
        """
        # 贫起构造信号
        signal_count = 0  # 看涨信号数
        
        if ma_signal == SignalType.BULLISH:
            signal_count += 1
        elif ma_signal == SignalType.BEARISH:
            signal_count -= 1
        
        if macd_signal == SignalType.BULLISH:
            signal_count += 1
        elif macd_signal == SignalType.BEARISH:
            signal_count -= 1
        
        # 控制指体 (30-70为筸妧, <30是申绿, >70是庄剧)
        rsi_signal = 0
        if rsi_value < 30:
            rsi_signal = 1  # 趋势过卖
        elif rsi_value > 70:
            rsi_signal = -1  # 趋势过买
        else:
            rsi_signal = 0.5 if rsi_value > 50 else -0.5
        
        # 需动下援
        kdj_signal = 0
        if kdj_value < 20:
            kdj_signal = 1
        elif kdj_value > 80:
            kdj_signal = -1
        else:
            kdj_signal = 0.5 if kdj_value > 50 else -0.5
        
        # 总综信号 [-2, 2]
        total_signal = signal_count + rsi_signal + kdj_signal
        
        # 对称化 [-1, 1]
        symmetric_score = np.tanh(total_signal / 3)  # Soft normalization
        
        if total_signal > 0:
            signal = SignalType.BULLISH
        elif total_signal < 0:
            signal = SignalType.BEARISH
        else:
            signal = SignalType.NEUTRAL
        
        # 置信度 (基于信号一致性)
        indicator_agreement = abs(total_signal) / 3  # [0, 1]
        
        # 市场波动率会下优市场设测
        volatility_factor = 1 / (1 + volatility)  # 波动率越大信信幦越低
        
        confidence = indicator_agreement * 0.7 + volatility_factor * 0.3
        
        explanation = (
            f"K线上涨信号3({signal_count}),"
            f"RSI={rsi_value:.0f}, KDJ={kdj_value:.0f}, "
            f"溙基一致性{indicator_agreement:.1%}"
        )
        
        return FactorScore(
            factor_name='K-line Technical',
            raw_score=abs(symmetric_score),
            weight=self.kline_weight,
            signal=signal,
            confidence=confidence,
            explanation=explanation
        )
    
    def calculate_network_factor(
        self,
        capital_strength: float,  # [0, 1] 需来挺上量
        hub_score: float,  # [0, 1] 是否为hub游资
        competitive_advantage: float,  # [0, 1] 对斗胜率
        co_action_count: int = 0,  # 突来经状方吧司数
        trending_momentum: float = 0.5  # [0, 1] 趋势↤动
    ) -> FactorScore:
        """
        计算游资网络因子
        
        Args:
            capital_strength: 需来挺上量 (0-1)
            hub_score: 是否为hub游资 (0-1)
            competitive_advantage: 对斗胜率 (0-1)
            co_action_count: 突来经状方吧司数
            trending_momentum: 趋势↤动 (0-1)
        
        Returns:
            FactorScore
        """
        # 控制范围
        capital_strength = max(0, min(1, capital_strength))
        hub_score = max(0, min(1, hub_score))
        competitive_advantage = max(0, min(1, competitive_advantage))
        trending_momentum = max(0, min(1, trending_momentum))
        
        # 贫起构造复合因子
        # 简敦线强度 (40%)
        strength_signal = (capital_strength - 0.5) * 2  # [-1, 1]
        
        # 中对幈旧会测 (30%)
        hub_signal = (hub_score - 0.5) * 2  # [-1, 1]
        
        # 对斗胜負 (20%)
        competitive_signal = (competitive_advantage - 0.5) * 2  # [-1, 1]
        
        # 趋势↤动 (10%)
        momentum_signal = (trending_momentum - 0.5) * 2  # [-1, 1]
        
        composite_signal = (
            strength_signal * 0.4 +
            hub_signal * 0.3 +
            competitive_signal * 0.2 +
            momentum_signal * 0.1
        )
        
        # 确定信号
        if composite_signal > 0.2:
            signal = SignalType.BULLISH
        elif composite_signal < -0.2:
            signal = SignalType.BEARISH
        else:
            signal = SignalType.NEUTRAL
        
        # 置信度 (需来网络突提会 + co-action一致性)
        network_confidence = abs(composite_signal)
        co_action_bonus = min(0.2, co_action_count * 0.05)  # 最始添加+0.2
        confidence = min(1, network_confidence + co_action_bonus)
        
        explanation = (
            f"需来挺上{capital_strength:.1%}, "
            f"Hub突提{hub_score:.1%}, "
            f"对斗胜率{competitive_advantage:.1%}, "
            f"突来经状粗关系{co_action_count}"
        )
        
        return FactorScore(
            factor_name='Capital Network',
            raw_score=abs(composite_signal),
            weight=self.network_weight,
            signal=signal,
            confidence=confidence,
            explanation=explanation
        )
    
    def fuse_signals(
        self,
        stock: str,
        capital: str,
        factor_scores: List[FactorScore],
        signal_agreement_threshold: float = 0.6
    ) -> FusionResult:
        """
        融合多因子信号
        
        Args:
            stock: 股票代码
            capital: 游资名称
            factor_scores: 因子列表
            signal_agreement_threshold: 信号一致性阻值
        
        Returns:
            FusionResult
        """
        # 计算加权综合分数
        weighted_sum = 0
        total_weight = 0
        signal_count = {'BULLISH': 0, 'BEARISH': 0, 'NEUTRAL': 0}
        
        for factor in factor_scores:
            # 号赋轃
            if factor.signal == SignalType.BULLISH:
                score = factor.raw_score
                signal_count['BULLISH'] += 1
            elif factor.signal == SignalType.BEARISH:
                score = -factor.raw_score
                signal_count['BEARISH'] += 1
            else:
                score = 0
                signal_count['NEUTRAL'] += 1
            
            weighted_sum += score * factor.weight * factor.confidence
            total_weight += factor.weight * factor.confidence
        
        # 模型综合分 [-1, 1]
        composite_score = weighted_sum / max(total_weight, 1e-6)
        composite_score = max(-1, min(1, composite_score))
        
        # 决定信号
        if composite_score > 0.1:
            signal = SignalType.BULLISH
        elif composite_score < -0.1:
            signal = SignalType.BEARISH
        else:
            signal = SignalType.NEUTRAL
        
        # 计算信号一致性 (Rayleigh信号收助)
        total_signals = sum(signal_count.values())
        if total_signals > 0:
            agreement_score = max(signal_count.values()) / total_signals
        else:
            agreement_score = 0
        
        # 信信度 = 半律修正系数 * 号赋一致性
        base_confidence = abs(composite_score)
        final_confidence = base_confidence * (0.5 + agreement_score * 0.5)
        
        # 中文收案
        reasoning = f"""
        【多因子融合分析】
        
        一. 其他因子评流: 
        {chr(10).join([f"  - {f.factor_name}: {f.signal.name} ({f.raw_score:.1%})信信度{f.confidence:.1%}" for f in factor_scores])}
        
        二. 一致性收案 (vs {signal_agreement_threshold:.0%}阻值):
          - 看涨信号: {signal_count['BULLISH']}
          - 看跌信号: {signal_count['BEARISH']}
          - 中性信号: {signal_count['NEUTRAL']}
          - 一致性管筮: {agreement_score:.1%}
        
        三. 最终决策:
          - 综合分數: {composite_score:.2f} ([-1, 1])
          - 推荐信号: {signal.name}
          - 信信度: {final_confidence:.1%}
        """
        
        # 记止业绌
        fusion_result = FusionResult(
            timestamp=datetime.now(),
            stock=stock,
            capital=capital,
            composite_score=composite_score,
            signal=signal,
            confidence=final_confidence,
            factor_scores={f.factor_name: f for f in factor_scores},
            reasoning=reasoning
        )
        
        self.factor_histories.append(fusion_result)
        
        return fusion_result
    
    def get_fusion_report(
        self,
        stock: str = None
    ) -> pd.DataFrame:
        """
        获取融合报告
        
        Args:
            stock: 股票代码 (为None时返回所有)
        
        Returns:
            DataFrame
        """
        if not self.factor_histories:
            return pd.DataFrame()
        
        # 序列化结果
        rows = []
        for result in self.factor_histories:
            if stock and result.stock != stock:
                continue
            
            row = {
                'timestamp': result.timestamp,
                'stock': result.stock,
                'capital': result.capital,
                'composite_score': result.composite_score,
                'signal': result.signal.name,
                'confidence': result.confidence,
                'lstm_score': result.factor_scores.get('LSTM Time Series', None),
                'kline_score': result.factor_scores.get('K-line Technical', None),
                'network_score': result.factor_scores.get('Capital Network', None)
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # 据设渓上榜时间
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp', ascending=False)
        
        return df
    
    def evaluate_fusion_accuracy(
        self,
        df_actual_performance: pd.DataFrame
    ) -> Dict:
        """
        评估融合模型准确性
        
        Args:
            df_actual_performance: 实际上榜效果
                                    欄位: stock, actual_change (%)
        
        Returns:
            {
                'accuracy': float,
                'precision': float,
                'recall': float,
                'f1_score': float,
                'hit_rate': float
            }
        """
        if not self.factor_histories or df_actual_performance.empty:
            return {}
        
        # 匹配预测上榜与实际效果
        predictions = []
        actuals = []
        
        for result in self.factor_histories:
            actual_rows = df_actual_performance[
                df_actual_performance['stock'] == result.stock
            ]
            
            if not actual_rows.empty:
                actual_performance = actual_rows.iloc[0]['actual_change']
                predictions.append(1 if result.signal == SignalType.BULLISH else -1)
                actuals.append(1 if actual_performance > 0 else -1)
        
        if not predictions or not actuals:
            return {}
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        # 计算准确率
        accuracy = np.mean(predictions == actuals)
        
        # 精准率 (TP / (TP + FP))
        tp = np.sum((predictions == 1) & (actuals == 1))
        fp = np.sum((predictions == 1) & (actuals == -1))
        precision = tp / max(tp + fp, 1)
        
        # 召回率 (TP / (TP + FN))
        fn = np.sum((predictions == -1) & (actuals == 1))
        recall = tp / max(tp + fn, 1)
        
        # F1分数
        f1 = 2 * (precision * recall) / max(precision + recall, 1e-6)
        
        # 浦中率 (共右汁模汁浦中)
        hits = np.sum(predictions == actuals)
        hit_rate = hits / len(predictions)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'hit_rate': hit_rate,
            'total_predictions': len(predictions)
        }
