#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机会评分函数 (Opportunity Scorer)

V17生产用途：统一评分标准，回测和实盘共用

评分维度：
1. 形态分 (0-40分)：Halfway/龙头/低吸等战法信号质量
2. 资金分 (0-40分)：主力净流入强度、持续性
3. 风险分 (0-20分)：TrapDetector、板块风险扣分

总分：0-100分，标准化为0-1

使用方式：
- 回测：每天选评分最高的1只开仓
- 实盘：输出"首选"(最高)+"备选"(次高2-3只)

Author: AI Project Director
Version: V1.0
Date: 2026-02-17
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class OpportunityFactors:
    """机会因子"""
    # 形态因子 (0-40分)
    pattern_type: str = ""  # 'halfway', 'leader', 'dip_buy', 'none'
    pattern_quality: float = 0.0  # 0-1，形态质量
    platform_volatility: float = 0.0  # 平台波动率
    breakout_strength: float = 0.0  # 突破强度
    volume_surge: float = 0.0  # 量能放大倍数
    
    # 资金因子 (0-40分)
    capital_inflow: float = 0.0  # 主力净流入金额
    capital_strength: float = 0.0  # 0-1，资金强度
    capital_sustained: bool = False  # 资金是否持续流入
    
    # 风险因子 (0-20分，扣分制)
    is_trap: bool = False  # TrapDetector判断
    sector_risk: float = 0.0  # 板块风险评分
    market_sentiment: float = 0.5  # 市场情绪 0-1


class OpportunityScorer:
    """机会评分器"""
    
    def __init__(self):
        # 权重配置
        self.pattern_weight = 0.40  # 形态40%
        self.capital_weight = 0.40  # 资金40%
        self.risk_weight = 0.20  # 风险20%
        
        # 阈值配置
        self.min_score_threshold = 0.60  # 最低及格线60分
    
    def score_pattern(self, factors: OpportunityFactors) -> float:
        """计算形态分 (0-40分，标准化为0-1)"""
        if factors.pattern_type == 'none':
            return 0.0
        
        score = 0.0
        
        # 基础分：有信号就给20分
        score += 0.20
        
        # 形态质量 (0-10分)
        score += factors.pattern_quality * 0.10
        
        # 平台稳定性：波动率低加分 (0-5分)
        if factors.platform_volatility < 0.03:
            score += 0.05
        elif factors.platform_volatility < 0.05:
            score += 0.03
        
        # 突破强度 (0-5分)
        if factors.breakout_strength > 0.02:
            score += 0.05
        elif factors.breakout_strength > 0.01:
            score += 0.03
        
        # 量能配合 (0-5分)
        if factors.volume_surge > 2.0:
            score += 0.05
        elif factors.volume_surge > 1.5:
            score += 0.03
        
        return min(score, 0.40)  # 最高40分
    
    def score_capital(self, factors: OpportunityFactors) -> float:
        """计算资金分 (0-40分，标准化为0-1)"""
        score = 0.0
        
        # 资金强度基础分 (0-20分)
        score += factors.capital_strength * 0.20
        
        # 净流入规模 (0-10分)
        if factors.capital_inflow > 10000000:  # 1000万
            score += 0.10
        elif factors.capital_inflow > 5000000:  # 500万
            score += 0.07
        elif factors.capital_inflow > 1000000:  # 100万
            score += 0.04
        
        # 持续性加分 (0-10分)
        if factors.capital_sustained:
            score += 0.10
        
        return min(score, 0.40)  # 最高40分
    
    def score_risk(self, factors: OpportunityFactors) -> float:
        """计算风险分 (0-20分，扣分制，返回的是"安全分")"""
        score = 0.20  # 满分20分
        
        # Trap扣分 (最高-10分)
        if factors.is_trap:
            score -= 0.10
        
        # 板块风险扣分 (最高-5分)
        score -= factors.sector_risk * 0.05
        
        # 市场情绪扣分 (最高-5分)
        if factors.market_sentiment < 0.3:  # 情绪极差
            score -= 0.05
        elif factors.market_sentiment < 0.5:  # 情绪偏冷
            score -= 0.02
        
        return max(score, 0.0)  # 最低0分
    
    def calculate_score(self, factors: OpportunityFactors) -> Dict[str, Any]:
        """计算综合评分
        
        Returns:
            {
                'total_score': 0-1,
                'pattern_score': 0-1,
                'capital_score': 0-1,
                'risk_score': 0-1,
                'passed': bool,
                'details': {...}
            }
        """
        # 计算各维度得分
        pattern_score = self.score_pattern(factors)
        capital_score = self.score_capital(factors)
        risk_score = self.score_risk(factors)
        
        # 加权总分
        total_score = (
            pattern_score * self.pattern_weight +
            capital_score * self.capital_weight +
            risk_score * self.risk_weight
        ) * 2.5  # 归一化到0-1 (因为原始满分是0.4+0.4+0.2=1.0，但risk是倒算的)
        
        # 实际应该是: (pattern + capital + risk) / (0.4 + 0.4 + 0.2) * 0.4
        # 修正计算
        raw_score = pattern_score + capital_score + risk_score
        max_possible = 0.40 + 0.40 + 0.20  # 满分100分对应的原始分
        total_score = raw_score / max_possible
        
        return {
            'total_score': round(total_score, 4),
            'pattern_score': round(pattern_score / 0.40, 4),  # 归一化为0-1
            'capital_score': round(capital_score / 0.40, 4),
            'risk_score': round(risk_score / 0.20, 4),
            'passed': total_score >= self.min_score_threshold,
            'details': {
                'pattern_type': factors.pattern_type,
                'breakout_strength': factors.breakout_strength,
                'volume_surge': factors.volume_surge,
                'capital_inflow': factors.capital_inflow,
                'is_trap': factors.is_trap,
            }
        }
    
    def rank_opportunities(self, opportunities: list) -> list:
        """对多个机会进行排序
        
        Args:
            opportunities: [(stock_code, factors), ...]
            
        Returns:
            按评分排序的列表，每个元素包含stock_code和score详情
        """
        scored = []
        for stock_code, factors in opportunities:
            score_result = self.calculate_score(factors)
            scored.append({
                'stock_code': stock_code,
                'score': score_result['total_score'],
                'passed': score_result['passed'],
                'details': score_result
            })
        
        # 按评分降序排序
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored
    
    def select_daily_pick(self, opportunities: list) -> Dict[str, Any]:
        """选择每日首选和备选
        
        Returns:
            {
                'primary': {'stock_code': ..., 'score': ...} or None,
                'alternatives': [{'stock_code': ..., 'score': ...}, ...],
                'all_scored': [...]
            }
        """
        ranked = self.rank_opportunities(opportunities)
        
        # 过滤掉不及格的
        passed = [o for o in ranked if o['passed']]
        
        if not passed:
            return {
                'primary': None,
                'alternatives': [],
                'all_scored': ranked
            }
        
        # 首选：评分最高的
        primary = passed[0]
        
        # 备选：评分次高的2-3只
        alternatives = passed[1:4] if len(passed) > 1 else []
        
        return {
            'primary': primary,
            'alternatives': alternatives,
            'all_scored': ranked
        }


# 全局评分器实例（单例模式）
_scorer_instance = None


def get_opportunity_scorer() -> OpportunityScorer:
    """获取全局评分器实例"""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = OpportunityScorer()
    return _scorer_instance


# 便捷函数
def score_opportunity(factors: OpportunityFactors) -> Dict[str, Any]:
    """快速评分函数"""
    scorer = get_opportunity_scorer()
    return scorer.calculate_score(factors)


def select_best_opportunity(opportunities: list) -> Dict[str, Any]:
    """快速选择函数"""
    scorer = get_opportunity_scorer()
    return scorer.select_daily_pick(opportunities)
