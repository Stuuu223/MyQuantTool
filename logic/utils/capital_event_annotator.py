# 资金事件标注器
# 版本：V1（简化版）
# 目标：先让网宿1-26稳定点亮，再谈复杂权重

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np


@dataclass
class CapitalEvent:
    """资金事件标注"""
    code: str
    date: str
    ratio: float  # 主力净流入/流通市值
    price_strength: float  # 价格强度（相对开盘）
    ratio_percentile: float  # ratio在全市场的分位数
    price_percentile: float  # price_strength在全市场的分位数
    is_attack: bool  # 是否触发资金事件
    attack_type: str  # 资金事件类型（MARKET_TOP_3/SECTOR_TOP_1/COMBINED）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'date': self.date,
            'ratio': self.ratio,
            'price_strength': self.price_strength,
            'ratio_percentile': self.ratio_percentile,
            'price_percentile': self.price_percentile,
            'is_attack': self.is_attack,
            'attack_type': self.attack_type
        }


class CapitalEventAnnotator:
    """资金事件标注器（简化版）"""
    
    def __init__(self):
        self.events = []
    
    def calculate_percentile(self, value: float, all_values: List[float]) -> float:
        """
        计算值在列表中的分位数
        
        Args:
            value: 当前值
            all_values: 市场所有股票的值列表
        
        Returns:
            float: 分位数（0-1）
        """
        if not all_values:
            return 0.5
        
        sorted_values = sorted(all_values)
        rank = len([x for x in sorted_values if x < value])
        return rank / len(sorted_values)
    
    def annotate_capital_event(
        self,
        code: str,
        date: str,
        ratio: float,
        price_strength: float,
        all_ratios: List[float],
        all_price_strengths: List[float],
        sector_ratio_percentile: Optional[float] = None
    ) -> CapitalEvent:
        """
        标注资金事件（简化版标准）
        
        Args:
            code: 股票代码
            date: 日期
            ratio: 主力净流入/流通市值
            price_strength: 价格强度（相对开盘）
            all_ratios: 全市场所有股票的ratio列表
            all_price_strengths: 全市场所有股票的price_strength列表
            sector_ratio_percentile: 板块内ratio分位数（可选）
        
        Returns:
            CapitalEvent: 资金事件标注结果
        """
        # 计算市场分位数
        ratio_percentile = self.calculate_percentile(ratio, all_ratios)
        price_percentile = self.calculate_percentile(price_strength, all_price_strengths)
        
        # 简化版标准
        is_attack = False
        attack_type = "NONE"
        
        # 条件1：ratio在全市场前3% OR 板块前1%
        ratio_top_3 = ratio_percentile >= 0.97  # 前3%
        sector_top_1 = (sector_ratio_percentile is not None and sector_ratio_percentile >= 0.99)
        
        # 条件2：price_strength在全市场前10%
        price_top_10 = price_percentile >= 0.90
        
        # 综合判断
        if ratio_top_3 and price_top_10:
            is_attack = True
            attack_type = "MARKET_TOP_3_PRICE_TOP_10"
        elif sector_top_1 and price_top_10:
            is_attack = True
            attack_type = "SECTOR_TOP_1_PRICE_TOP_10"
        
        event = CapitalEvent(
            code=code,
            date=date,
            ratio=ratio,
            price_strength=price_strength,
            ratio_percentile=ratio_percentile,
            price_percentile=price_percentile,
            is_attack=is_attack,
            attack_type=attack_type
        )
        
        self.events.append(event)
        return event
    
    def get_events_by_date(self, date: str) -> List[CapitalEvent]:
        """获取指定日期的所有资金事件"""
        return [e for e in self.events if e.date == date]
    
    def get_attack_events(self) -> List[CapitalEvent]:
        """获取所有资金事件"""
        return [e for e in self.events if e.is_attack]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取标注摘要"""
        if not self.events:
            return {}
        
        attack_events = self.get_attack_events()
        
        return {
            'total_events': len(self.events),
            'attack_count': len(attack_events),
            'attack_rate': len(attack_events) / len(self.events) * 100 if self.events else 0,
            'attack_types': {
                'MARKET_TOP_3_PRICE_TOP_10': len([e for e in attack_events if e.attack_type == 'MARKET_TOP_3_PRICE_TOP_10']),
                'SECTOR_TOP_1_PRICE_TOP_10': len([e for e in attack_events if e.attack_type == 'SECTOR_TOP_1_PRICE_TOP_10'])
            }
        }


# 使用示例
if __name__ == '__main__':
    # 模拟数据
    all_ratios = [0.001, 0.002, 0.003, 0.004, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05]
    all_price_strengths = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    
    annotator = CapitalEventAnnotator()
    
    # 网宿1-26（模拟数据）
    event = annotator.annotate_capital_event(
        code='300017.SZ',
        date='2026-01-26',
        ratio=0.05,  # 前3%（0.97分位数）
        price_strength=0.127,  # 前10%（1.0分位数）
        all_ratios=all_ratios,
        all_price_strengths=all_price_strengths,
        sector_ratio_percentile=0.995  # 板块前1%
    )
    
    print(f"网宿1-26资金事件标注:")
    print(f"  ratio: {event.ratio:.4f}")
    print(f"  price_strength: {event.price_strength:.4f}")
    print(f"  ratio_percentile: {event.ratio_percentile:.4f}")
    print(f"  price_percentile: {event.price_percentile:.4f}")
    print(f"  is_attack: {event.is_attack}")
    print(f"  attack_type: {event.attack_type}")