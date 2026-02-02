"""
资金性质分类器
判断资金是"机构"还是"游资"还是"长线资金"
"""
from typing import List, Dict, Any, Optional
from datetime import datetime


class CapitalClassifier:
    """
    资金性质分类器

    分类标准:
    - INSTITUTIONAL（机构）: 持续小额吸筹，5日+10日均为正
    - LONG_TERM（长线）: 累计大额流入，持续时间>20天
    - HOT_MONEY（游资）: 单日巨量，前后无连续性
    - UNCLEAR（不明确）: 无法判断
    """

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
        分类当前资金性质

        Args:
            daily_data: 每日资金流向数据
            window: 检测窗口大小（默认30天）

        Returns:
            分类结果字典
        """
        if len(daily_data) < 5:
            return {
                'type': 'UNCLEAR',
                'type_name': '资金性质不明确',
                'confidence': 0.0,
                'evidence': '数据不足，至少需要5天数据',
                'risk_level': 'MEDIUM',
                'classify_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        # 获取最近的数据
        if len(daily_data) < window:
            recent = daily_data
        else:
            recent = daily_data[-window:]

        latest = daily_data[-1]

        # 计算滚动指标
        flow_5d = sum(d['institution'] for d in daily_data[-5:])
        flow_10d = sum(d['institution'] for d in daily_data[-10:])
        flow_20d = sum(d['institution'] for d in daily_data[-20:]) if len(daily_data) >= 20 else None
        flow_30d = sum(d['institution'] for d in daily_data[-30:]) if len(daily_data) >= 30 else None

        latest_inflow = latest.get('institution', 0)

        # 计算流入天数
        inflow_days_5d = sum(1 for d in daily_data[-5:] if d.get('institution', 0) > 0)
        inflow_days_10d = sum(1 for d in daily_data[-10:] if d.get('institution', 0) > 0)

        # 计算连续流入天数
        consecutive_inflow = self._get_consecutive_inflow_days(daily_data)

        # 计算波动性
        volatility = self._calculate_volatility(daily_data[-10:])

        # ========== 规则判断 ==========

        # 规则 1: 长线资金（稳定持续流入）
        if flow_20d and flow_20d > 0:
            if flow_5d > 0 and flow_10d > 0:
                # 检查流入的稳定性
                if inflow_days_10d >= 7 and consecutive_inflow >= 3:
                    confidence = 0.75 + min(consecutive_inflow * 0.02, 0.20)
                    if latest_inflow > 0 and latest_inflow < flow_10d / 3:
                        confidence += 0.05

                    return {
                        'type': 'LONG_TERM',
                        'type_name': '长线资金',
                        'confidence': round(min(confidence, 0.95), 2),
                        'evidence': (
                            f"5/10/20日滚动均为正流入（{flow_5d:.2f}/{flow_10d:.2f}/{flow_20d:.2f}万），"
                            f"10日内{inflow_days_10d}天流入，连续{consecutive_inflow}天流入，"
                            f"单日{latest_inflow:.2f}万符合持续模式"
                        ),
                        'flow_5d': round(flow_5d, 2),
                        'flow_10d': round(flow_10d, 2),
                        'flow_20d': round(flow_20d, 2),
                        'consecutive_inflow_days': consecutive_inflow,
                        'inflow_days_10d': inflow_days_10d,
                        'volatility': round(volatility, 2),
                        'risk_level': 'LOW',
                        'holding_period_estimate': '> 20天',
                        'classify_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

        # 规则 2: 机构资金（中等规模持续吸筹）
        if flow_5d > 0 and flow_10d > 0:
            if 0 < flow_5d < 3000 and flow_10d < 5000:
                if inflow_days_5d >= 3 and inflow_days_10d >= 6:
                    confidence = 0.65
                    if flow_10d > 2000:
                        confidence += 0.10
                    if volatility < 0.5:
                        confidence += 0.10

                    return {
                        'type': 'INSTITUTIONAL',
                        'type_name': '机构资金',
                        'confidence': round(min(confidence, 0.90), 2),
                        'evidence': (
                            f"5/10日滚动均为正流入（{flow_5d:.2f}/{flow_10d:.2f}万），"
                            f"10日内{inflow_days_10d}天流入，5日内{inflow_days_5d}天流入，"
                            f"符合稳健吸筹模式"
                        ),
                        'flow_5d': round(flow_5d, 2),
                        'flow_10d': round(flow_10d, 2),
                        'inflow_days_5d': inflow_days_5d,
                        'inflow_days_10d': inflow_days_10d,
                        'volatility': round(volatility, 2),
                        'risk_level': 'LOW',
                        'holding_period_estimate': '5-15天',
                        'classify_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

        # 规则 3: 游资（单日巨量，前后无连续）
        if latest_inflow > 2000:
            # 检查前期是否有明显流出
            if flow_10d < 0 or (flow_20d and flow_20d < -3000):
                # 检查流入的天数（游资通常单日为主）
                if inflow_days_5d <= 2 and consecutive_inflow <= 1:
                    confidence = 0.70
                    if latest_inflow > 5000:
                        confidence += 0.10
                    if flow_10d < -2000:
                        confidence += 0.10
                    # 计算填坑率
                    if flow_10d < 0:
                        fill_ratio = latest_inflow / abs(flow_10d)
                        if fill_ratio > 0.5:
                            confidence += 0.05
                        if fill_ratio > 1.0:
                            confidence += 0.05

                    return {
                        'type': 'HOT_MONEY',
                        'type_name': '游资资金',
                        'confidence': round(min(confidence, 0.95), 2),
                        'evidence': (
                            f"单日巨量{latest_inflow:.2f}万，"
                            f"但10日累计{flow_10d:.2f}万（前期明显流出），"
                            f"10日内仅{inflow_days_10d}天流入，"
                            f"符合游资突袭特征"
                        ),
                        'latest_inflow': latest_inflow,
                        'flow_10d': round(flow_10d, 2),
                        'flow_20d': round(flow_20d, 2) if flow_20d else None,
                        'inflow_days_5d': inflow_days_5d,
                        'inflow_days_10d': inflow_days_10d,
                        'consecutive_inflow_days': consecutive_inflow,
                        'volatility': round(volatility, 2),
                        'risk_level': 'HIGH',
                        'holding_period_estimate': '< 5天',
                        'classify_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

        # 规则 4: 持续流出（减仓）
        if flow_5d < 0 and flow_10d < 0:
            if inflow_days_5d <= 1 and inflow_days_10d <= 3:
                confidence = 0.60 + abs(flow_10d) / 10000 * 0.1

                return {
                    'type': 'INSTITUTIONAL_SELLING',
                    'type_name': '机构减仓',
                    'confidence': round(min(confidence, 0.90), 2),
                    'evidence': (
                        f"5/10日滚动均为负流出（{flow_5d:.2f}/{flow_10d:.2f}万），"
                        f"10日内仅{inflow_days_10d}天流入，"
                        f"持续减仓中"
                    ),
                    'flow_5d': round(flow_5d, 2),
                    'flow_10d': round(flow_10d, 2),
                    'inflow_days_5d': inflow_days_5d,
                    'inflow_days_10d': inflow_days_10d,
                    'risk_level': 'HIGH',
                    'holding_period_estimate': '减仓中',
                    'classify_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

        # 默认：不明确
        return {
            'type': 'UNCLEAR',
            'type_name': '资金性质不明确',
            'confidence': 0.40,
            'evidence': (
                f"资金流向无明显模式，"
                f"5日累计{flow_5d:.2f}万，"
                f"10日累计{flow_10d:.2f}万，"
                f"波动性{volatility:.2f}"
            ),
            'flow_5d': round(flow_5d, 2),
            'flow_10d': round(flow_10d, 2),
            'volatility': round(volatility, 2),
            'risk_level': 'MEDIUM',
            'holding_period_estimate': '未知',
            'classify_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _get_consecutive_inflow_days(self, daily_data: List[Dict[str, Any]]) -> int:
        """计算从最近一天开始的连续流入天数"""
        consecutive = 0
        for i in range(len(daily_data) - 1, -1, -1):
            if daily_data[i].get('institution', 0) > 0:
                consecutive += 1
            else:
                break
        return consecutive

    def _calculate_volatility(self, data: List[Dict[str, Any]]) -> float:
        """计算资金流向的波动性（标准差 / 平均值的绝对值）"""
        if not data:
            return 0.0

        flows = [d.get('institution', 0) for d in data]
        if not flows:
            return 0.0

        avg_flow = sum(flows) / len(flows)
        if avg_flow == 0:
            # 如果平均值为0，使用绝对平均值作为分母
            avg_abs_flow = sum(abs(f) for f in flows) / len(flows)
            if avg_abs_flow == 0:
                return 0.0
            variance = sum((f - 0) ** 2 for f in flows) / len(flows)
            std = variance ** 0.5
            return std / avg_abs_flow

        variance = sum((f - avg_flow) ** 2 for f in flows) / len(flows)
        std = variance ** 0.5
        return std / abs(avg_flow)

    def get_capital_summary(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        """获取分类结果的摘要信息"""
        capital_type = classification.get('type', 'UNCLEAR')
        type_info = self.classification_rules.get(capital_type, self.classification_rules['UNCLEAR'])

        return {
            'type': capital_type,
            'type_name': type_info['description'],
            'confidence': classification.get('confidence', 0),
            'risk_level': type_info['risk_level'],
            'holding_period': type_info['holding_period'],
            'evidence': classification.get('evidence', ''),
            'flow_5d': classification.get('flow_5d'),
            'flow_10d': classification.get('flow_10d'),
            'recommendation': self._get_recommendation(capital_type, classification.get('confidence', 0))
        }

    def _get_recommendation(self, capital_type: str, confidence: float) -> str:
        """根据资金性质给出建议"""
        if confidence < 0.5:
            return "信号不明确，继续观察"

        if capital_type == 'LONG_TERM':
            if confidence >= 0.8:
                return "长线资金进场，可考虑中长线布局"
            else:
                return "疑似长线资金，可小仓位试探"
        elif capital_type == 'INSTITUTIONAL':
            if confidence >= 0.75:
                return "机构稳健吸筹，可考虑跟随"
            else:
                return "疑似机构资金，观察确认"
        elif capital_type == 'HOT_MONEY':
            if confidence >= 0.8:
                return "游资突袭，高风险，建议观望或短线快进快出"
            else:
                return "疑似游资，谨慎参与"
        elif capital_type == 'INSTITUTIONAL_SELLING':
            return "机构减仓中，建议回避"
        else:
            return "资金性质不明确，继续观察"


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

    # 测试3: 游资
    test_hot_money = [
        {'date': f'2026-01-{i+1:02d}', 'institution': -200 - i * 10} for i in range(29)
    ]
    test_hot_money.append({'date': '2026-01-30', 'institution': 5025})

    print("\n测试3: 游资")
    result = classifier.classify(test_hot_money)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试4: 机构减仓
    test_selling = [
        {'date': f'2026-01-{i+1:02d}', 'institution': -150 - i * 5} for i in range(15)
    ]

    print("\n测试4: 机构减仓")
    result = classifier.classify(test_selling)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 测试5: 不明确
    test_unclear = [
        {'date': f'2026-01-{i+1:02d}', 'institution': (i % 5 - 2) * 100} for i in range(15)
    ]

    print("\n测试5: 不明确")
    result = classifier.classify(test_unclear)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n✅ 测试完成")