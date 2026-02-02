#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资金性质分类器
用于判断资金性质：游资、机构、长线庄家等
"""
from typing import List, Dict, Any, Optional
from datetime import datetime


class CapitalClassifier:
    """资金性质分类器"""

    def __init__(self):
        """初始化分类器"""
        self.classification_rules = {
            'LONG_TERM': {
                'description': '长线资金',
                'risk_level': 'LOW',
                'holding_period': '> 20天'
            },
            'INSTITUTIONAL': {
                'description': '机构资金',
                'risk_level': 'LOW',
                'holding_period': '5-15天'
            },
            'HOT_MONEY': {
                'description': '游资资金',
                'risk_level': 'HIGH',
                'holding_period': '< 5天'
            },
            'UNCLEAR': {
                'description': '资金性质不明确',
                'risk_level': 'MEDIUM',
                'holding_period': '未知'
            }
        }

    def classify(self, daily_data: List[Dict[str, Any]], window: int = 30) -> Dict[str, Any]:
        """
        分类逻辑:
        1. HOT_MONEY: 短期游资（检测到诱多陷阱）
        2. INSTITUTIONAL: 机构（持续流入 + 波动小）
        3. LONG_TERM: 长线庄家（累计大额 + 稳定吸筹）
        4. UNCLEAR: 无法判断

        Args:
            daily_data: 包含资金流向的日线数据
            window: 检测窗口大小（默认30天）

        Returns:
            dict: 分类结果，包含类型、置信度、证据等
        """
        if len(daily_data) < 10:
            return {
                'type': 'UNCLEAR',
                'type_name': '数据不足',
                'confidence': 0.0,
                'evidence': '数据天数不足10天',
                'risk_level': 'UNKNOWN',
                'holding_period_estimate': None,
                'classify_time': self._get_current_time()
            }

        # 获取最近一天的数据
        latest = daily_data[-1]

        # 关键指标
        latest_inflow = latest.get('institution', 0)
        flow_5d = sum(d['institution'] for d in daily_data[-5:])
        flow_10d = sum(d['institution'] for d in daily_data[-10:])
        flow_20d = sum(d['institution'] for d in daily_data[-20:]) if len(daily_data) >= 20 else None

        # 计算波动率（最近10天的标准差）
        recent_10_inflows = [d.get('institution', 0) for d in daily_data[-10:]]
        volatility = self._calculate_volatility(recent_10_inflows)

        # 检查是否有诱多陷阱（关键判断逻辑）
        has_traps, trap_count = self._detect_traps(daily_data)

        evidence_parts = []

        # 1. HOT_MONEY: 游资判断（优先级最高）
        if has_traps:
            evidence_parts.append(f"检测到 {trap_count} 个诱多陷阱")
            evidence_parts.append(f"波动率: {volatility:.2f}")

            if flow_5d is not None:
                evidence_parts.append(f"5日: {flow_5d:.2f}万")
            if flow_10d is not None:
                evidence_parts.append(f"10日: {flow_10d:.2f}万")

            return {
                'type': 'HOT_MONEY',
                'type_name': '短期游资',
                'confidence': min(0.75 + (trap_count * 0.05), 0.95),
                'evidence': '；'.join(evidence_parts),
                'flow_5d': round(flow_5d, 2) if flow_5d is not None else None,
                'flow_10d': round(flow_10d, 2) if flow_10d is not None else None,
                'flow_20d': round(flow_20d, 2) if flow_20d is not None else None,
                'volatility': round(volatility, 2),
                'risk_level': 'HIGH',
                'holding_period_estimate': '1-3天',
                'classify_time': self._get_current_time()
            }

        # 2. LONG_TERM: 长线庄家判断
        if flow_20d is not None and flow_20d > 10000 and volatility < 3000:
            evidence_parts.append(f"20日滚动: {flow_20d:.2f}万")
            evidence_parts.append(f"波动率低: {volatility:.2f}")

            return {
                'type': 'LONG_TERM',
                'type_name': '长线庄家',
                'confidence': 0.70,
                'evidence': '；'.join(evidence_parts),
                'flow_5d': round(flow_5d, 2) if flow_5d is not None else None,
                'flow_10d': round(flow_10d, 2) if flow_10d is not None else None,
                'flow_20d': round(flow_20d, 2),
                'volatility': round(volatility, 2),
                'risk_level': 'MEDIUM',
                'holding_period_estimate': '1-3月',
                'classify_time': self._get_current_time()
            }

        # 3. INSTITUTIONAL: 机构判断
        if flow_10d is not None and flow_10d > 5000 and volatility < 2000:
            evidence_parts.append(f"10日滚动: {flow_10d:.2f}万")
            evidence_parts.append(f"波动稳定: {volatility:.2f}")

            return {
                'type': 'INSTITUTIONAL',
                'type_name': '机构资金',
                'confidence': 0.65,
                'evidence': '；'.join(evidence_parts),
                'flow_5d': round(flow_5d, 2) if flow_5d is not None else None,
                'flow_10d': round(flow_10d, 2),
                'volatility': round(volatility, 2),
                'risk_level': 'MEDIUM',
                'holding_period_estimate': '1-2月',
                'classify_time': self._get_current_time()
            }

        # 4. UNCLEAR: 无法判断
        if flow_5d is not None:
            evidence_parts.append(f"5日: {flow_5d:.2f}")
        if flow_10d is not None:
            evidence_parts.append(f"10日: {flow_10d:.2f}")
        evidence_parts.append(f"波动率: {volatility:.2f}")

        return {
            'type': 'UNCLEAR',
            'type_name': '未知',
            'confidence': 0.4,
            'evidence': '；'.join(evidence_parts) if evidence_parts else '资金流向无明显模式',
            'flow_5d': round(flow_5d, 2) if flow_5d is not None else None,
            'flow_10d': round(flow_10d, 2) if flow_10d is not None else None,
            'volatility': round(volatility, 2),
            'risk_level': 'MEDIUM',
            'holding_period_estimate': None,
            'classify_time': self._get_current_time()
        }

    def _detect_traps(self, daily_data: List[Dict[str, Any]]) -> tuple[bool, int]:
        """检测诱多陷阱"""
        trap_count = 0

        for i in range(len(daily_data) - 1):
            prev_day = daily_data[i]
            curr_day = daily_data[i + 1]

            # 诱多特征：前一天大额吸筹 + 后一天反手卖出
            big_inflow = prev_day.get('institution', 0) > 5000
            big_outflow = curr_day.get('institution', 0) < -2500

            if big_inflow and big_outflow:
                trap_count += 1

        return (trap_count > 0, trap_count)

    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动率（标准差）"""
        if len(values) < 2:
            return 0.0

        try:
            import statistics
            return statistics.stdev(values)
        except:
            return 0.0

    def _get_current_time(self) -> str:
        """获取当前时间"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# 便捷函数
def classify_capital(daily_data: List[Dict[str, Any]], window: int = 30) -> Dict[str, Any]:
    """便捷函数：分类资金性质"""
    classifier = CapitalClassifier()
    return classifier.classify(daily_data, window)


if __name__ == "__main__":
    # 测试代码
    import json

    print("=" * 80)
    print("资金性质分类器测试")
    print("=" * 80)

    # 测试1: 长线资金
    test_long_term = [
        {'date': f'2026-01-{i+1:02d}', 'institution': 100 + i * 10} for i in range(30)
    ]

    print("\n测试1: 长线资金")
    classifier = CapitalClassifier()
    result = classifier.classify(test_long_term)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试2: 机构资金
    test_institutional = [
        {'date': f'2026-01-{i+1:02d}', 'institution': 150 if i % 2 == 0 else 50} for i in range(15)
    ]

    print("\n测试2: 机构资金")
    result = classifier.classify(test_institutional)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试3: 游资（有诱多陷阱）
    test_hot_money = [
        {'date': f'2026-01-{i+1:02d}', 'institution': -200 - i * 10} for i in range(28)
    ]
    test_hot_money.append({'date': '2026-01-29', 'institution': 6692.94})
    test_hot_money.append({'date': '2026-01-30', 'institution': -2961.97})

    print("\n测试3: 游资（有诱多陷阱）")
    result = classifier.classify(test_hot_money)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试4: 不明确
    test_unclear = [
        {'date': f'2026-01-{i+1:02d}', 'institution': (i % 5 - 2) * 100} for i in range(15)
    ]

    print("\n测试4: 不明确")
    result = classifier.classify(test_unclear)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n✅ 测试完成")
