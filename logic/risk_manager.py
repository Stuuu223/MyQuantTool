# -*- coding: utf-8 -*-
"""
风险管理器

功能：
- 评估系统置信度（基于证据矩阵）
- 计算仓位上限
- 生成风控建议

Author: iFlow CLI
Date: 2026-02-05
Version: V1.0
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class RiskManager:
    """风险管理器
    
    职责：
    1. 评估系统置信度（基于证据矩阵）
    2. 计算仓位上限
    3. 生成风控建议
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化风险管理器
        
        Args:
            config: 配置字典
        """
        self.config = config or self._get_default_config()
        logger.info("✅ RiskManager 初始化成功")
    
    def _get_default_config(self) -> Dict:
        """
        获取默认配置
        
        Returns:
            默认配置字典
        """
        return {
            'base_position': 0.8,        # 基础仓位上限（80%）
            'min_position': 0.1,         # 最低仓位（10%）
            'key_factors': ['technical', 'fund_flow', 'market_sentiment'],
            'factor_weights': {
                'fund_flow': 2.0,        # 资金流最重要（识别诱多陷阱的关键）
                'technical': 1.0,
                'market_sentiment': 1.0
            }
        }
    
    def assess_confidence(self, evidence_matrix: Dict) -> Dict:
        """
        评估系统置信度
        
        Args:
            evidence_matrix: 证据矩阵
                {
                    'technical': {'available': bool, 'quality': str, ...},
                    'fund_flow': {'available': bool, 'quality': str, ...},
                    'market_sentiment': {'available': bool, 'quality': str, ...}
                }
        
        Returns:
            {
                'completeness': float,  # 完整性得分（0-1）
                'quality': float,       # 质量得分（0-1）
                'confidence': float,    # 综合置信度（0-1）
                'details': dict          # 详细信息
            }
        """
        key_factors = self.config['key_factors']
        weights = self.config['factor_weights']
        
        # 1. 计算完整性得分（加权平均）
        available_count = sum(1 for f in key_factors if evidence_matrix.get(f, {}).get('available', False))
        completeness = available_count / len(key_factors)
        
        # 2. 计算质量得分（加权平均）
        quality_map = {'GOOD': 1.0, 'MEDIUM': 0.7, 'LOW': 0.4, 'NONE': 0.0}
        
        total_weight = 0
        total_quality = 0
        
        for factor in key_factors:
            factor_info = evidence_matrix.get(factor, {})
            quality = quality_map.get(factor_info.get('quality', 'NONE'), 0)
            weight = weights.get(factor, 1.0)
            
            if factor_info.get('available', False):
                total_quality += quality * weight
                total_weight += weight
        
        quality = total_quality / total_weight if total_weight > 0 else 0
        
        # 3. 综合置信度
        confidence = completeness * quality
        
        return {
            'completeness': completeness,
            'quality': quality,
            'confidence': confidence,
            'details': {
                'available_factors': available_count,
                'total_factors': len(key_factors),
                'weighted_quality': total_quality,
                'total_weight': total_weight
            }
        }
    
    def calculate_position_limit(self, evidence_matrix: Dict) -> Dict:
        """
        计算仓位上限
        
        Args:
            evidence_matrix: 证据矩阵
        
        Returns:
            {
                'position_limit': float,  # 仓位上限（0-1）
                'confidence': float,       # 系统置信度（0-1）
                'reason': str,             # 决策原因
                'warnings': list,          # 警告列表
                'suggestions': list        # 建议
            }
        """
        # 评估置信度
        confidence_result = self.assess_confidence(evidence_matrix)
        confidence = confidence_result['confidence']
        
        # 计算仓位上限
        base_position = self.config['base_position']
        min_position = self.config['min_position']
        
        position_limit = base_position * confidence
        position_limit = max(position_limit, min_position)
        
        # 生成警告和建议
        warnings = []
        suggestions = []
        
        # 检查资金流
        fund_flow_info = evidence_matrix.get('fund_flow', {})
        if not fund_flow_info.get('available', False):
            warnings.append("⚠️ 资金流数据不可用，无法识别诱多陷阱")
            suggestions.append("建议降低仓位，避免追高风险")
        
        # 检查完整性
        if confidence_result['completeness'] < 0.5:
            warnings.append("⚠️ 关键因子缺失（完整度 < 50%）")
            suggestions.append("建议谨慎操作，控制风险敞口")
        
        # 检查质量
        if confidence_result['quality'] < 0.5:
            warnings.append("⚠️ 数据质量较差（平均质量 < 50%）")
            suggestions.append("建议等待数据恢复后再做决策")
        
        # 决策原因
        if confidence < 0.2:
            reason = "系统置信度极低（< 20%），禁止交易"
        elif confidence < 0.3:
            reason = "系统置信度极低（< 30%），强制降低仓位"
        elif confidence < 0.5:
            reason = "系统置信度较低（< 50%），适当降低仓位"
        elif confidence < 0.7:
            reason = "系统置信度一般（< 70%），正常仓位"
        else:
            reason = "系统置信度高（≥ 70%），允许高仓位"
        
        return {
            'position_limit': position_limit,
            'confidence': confidence,
            'reason': reason,
            'warnings': warnings,
            'suggestions': suggestions
        }