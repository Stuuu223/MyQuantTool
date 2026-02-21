#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金强度评分器
Phase 1: Ratio化资金强度系统

核心功能：
1. 计算flow_5min相对于流通市值的ratio
2. 综合评分（ratio_stock 50% + sustain 30% + ratio_day 20%）
3. 输出0-1标准化强度分数
"""

from typing import Dict, Optional
from datetime import datetime
import math


class FlowIntensityScorer:
    """
    资金强度评分器
    
    解决固定阈值问题，实现动态ratio化阈值
    """
    
    def __init__(self, data_service):
        """
        初始化
        
        Args:
            data_service: DataService实例，用于获取流通市值
        """
        self.data_service = data_service
        
        # 🔥 Phase 1: Ratio分层评分标准（调整后更宽松）
        # 网宿510亿市值，587M flow_5min → ratio=1.15%
        # 需要让1-2%的ratio也能得到合理分数
        self.ratio_stock_thresholds = [
            (0.20, 1.0),   # >=20%: 满分（极强攻击）
            (0.15, 0.9),   # >=15%: 优秀（强攻击）
            (0.10, 0.75),  # >=10%: 良好（中高攻击）
            (0.05, 0.55),  # >=5%: 及格（中等攻击）
            (0.02, 0.35),  # >=2%: 一般（ noticeable）
            (0.01, 0.15),  # >=1%: 较弱（网宿587M/510亿≈1.15%在此档）
        ]
    
    def score(self, flow_5min: float, stock_code: str, trade_date: str, 
              flow_15min: float = None, ratio_day: float = None) -> Dict:
        """
        计算资金强度综合评分
        
        Args:
            flow_5min: 5分钟资金流（元）
            stock_code: 股票代码
            trade_date: 交易日期（如'2026-01-26'）
            flow_15min: 15分钟资金流（元），可选
            ratio_day: 当日资金分位（0-1），可选
            
        Returns:
            {
                'intensity_score': 0-1综合强度分,
                'ratio_stock': flow_5min/流通市值,
                'ratio_stock_score': ratio_stock单项分,
                'sustain_score': 持续性评分,
                'ratio_day_score': 当日分位评分,
                'circ_mv_bn': 流通市值（亿元）
            }
        """
        # 获取流通市值
        circ_mv_bn = self.data_service.get_circ_mv(stock_code, trade_date)
        circ_mv_yuan = circ_mv_bn * 1e8  # 亿元转元
        
        # 防止除零
        if circ_mv_yuan <= 0:
            circ_mv_yuan = 50e8  # 默认50亿
            circ_mv_bn = 50.0
        
        # 1. 计算flow_5min相对于流通市值的ratio
        ratio_stock = abs(flow_5min) / circ_mv_yuan if circ_mv_yuan > 0 else 0
        
        # 2. ratio_stock单项评分（分层）
        ratio_stock_score = 0.0
        for threshold, score in self.ratio_stock_thresholds:
            if ratio_stock >= threshold:
                ratio_stock_score = score
                break
        
        # 3. 持续性评分（flow_15min/flow_5min）
        sustain_score = 0.0
        if flow_15min is not None and abs(flow_5min) > 0:
            sustain_ratio = abs(flow_15min) / abs(flow_5min)
            # sustain_ratio > 1.2为良好，>1.5为优秀
            if sustain_ratio >= 1.5:
                sustain_score = 1.0
            elif sustain_ratio >= 1.2:
                sustain_score = 0.8
            elif sustain_ratio >= 1.0:
                sustain_score = 0.6
            elif sustain_ratio >= 0.8:
                sustain_score = 0.3
            else:
                sustain_score = 0.1
        else:
            # 无15分钟数据时，假设持续性中等
            sustain_score = 0.5
        
        # 4. 当日分位评分
        ratio_day_score = 0.0
        if ratio_day is not None:
            # ratio_day已经是0-1分位，直接映射
            ratio_day_score = min(1.0, max(0.0, ratio_day))
        else:
            # 无分位数据时，根据ratio_stock推断
            ratio_day_score = ratio_stock_score * 0.8
        
        # 5. 综合强度评分（加权）
        # ratio_stock 50% + sustain 30% + ratio_day 20%
        intensity_score = (
            ratio_stock_score * 0.5 +
            sustain_score * 0.3 +
            ratio_day_score * 0.2
        )
        
        return {
            'intensity_score': round(intensity_score, 4),
            'ratio_stock': round(ratio_stock, 6),
            'ratio_stock_score': round(ratio_stock_score, 4),
            'sustain_score': round(sustain_score, 4),
            'ratio_day_score': round(ratio_day_score, 4),
            'circ_mv_bn': round(circ_mv_bn, 2)
        }
    
    def is_strong_signal(self, flow_5min: float, stock_code: str, trade_date: str,
                         min_intensity: float = 0.6, **kwargs) -> bool:
        """
        判断是否为强信号
        
        Args:
            flow_5min: 5分钟资金流
            stock_code: 股票代码
            trade_date: 交易日期
            min_intensity: 最小强度阈值（默认0.6）
            
        Returns:
            是否达到强信号标准
        """
        result = self.score(flow_5min, stock_code, trade_date, **kwargs)
        return result['intensity_score'] >= min_intensity


# 便捷函数
def calculate_intensity(flow_5min: float, stock_code: str, trade_date: str,
                       data_service=None, **kwargs) -> Dict:
    """
    便捷计算资金强度
    
    Args:
        flow_5min: 5分钟资金流
        stock_code: 股票代码
        trade_date: 交易日期
        data_service: DataService实例，None则创建新实例
        
    Returns:
        强度评分字典
    """
    if data_service is None:
        from logic.services.data_service import DataService
        data_service = DataService()
    
    scorer = FlowIntensityScorer(data_service)
    return scorer.score(flow_5min, stock_code, trade_date, **kwargs)


if __name__ == "__main__":
    # 测试
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    
    from logic.services.data_service import DataService
    
    ds = DataService()
    scorer = FlowIntensityScorer(ds)
    
    # 测试网宿科技1.26数据（587M flow_5min，510亿市值）
    result = scorer.score(
        flow_5min=587_000_000,  # 5.87亿
        stock_code='300017',
        trade_date='2026-01-26',
        flow_15min=1100_000_000  # 11亿
    )
    
    print("="*60)
    print("资金强度评分测试 - 网宿科技 2026-01-26")
    print("="*60)
    print(f"流通市值: {result['circ_mv_bn']} 亿元")
    print(f"5分钟流/市值: {result['ratio_stock']*100:.2f}%")
    print(f"Ratio评分: {result['ratio_stock_score']}")
    print(f"持续性评分: {result['sustain_score']}")
    print(f"当日分位评分: {result['ratio_day_score']}")
    print(f"综合强度评分: {result['intensity_score']}")
    print(f"是否强信号(>=0.6): {result['intensity_score'] >= 0.6}")
