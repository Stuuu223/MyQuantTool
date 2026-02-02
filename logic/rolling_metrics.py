"""
滚动指标计算器
为资金流向数据添加滚动指标，用于判断"持续吸筹 vs 单日诱多"
"""
import copy
from typing import List, Dict, Any


class RollingMetricsCalculator:
    """滚动指标计算器"""

    @staticmethod
    def add_rolling_metrics(daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        为每日数据添加滚动指标

        Args:
            daily_data: 每日资金流向数据列表
                每个记录应包含:
                - date: 日期
                - institution: 机构净流入

        Returns:
            包含滚动指标的增强数据列表

        新增字段:
            - flow_5d_net: 过去5天累计净流入（万元）
            - flow_10d_net: 过去10天累计净流入（万元）
            - flow_20d_net: 过去20天累计净流入（万元）
            - inflow_rank_percentile: 当前流入在历史中的排名（百分位 0-1）
        """
        if not daily_data:
            return []

        enriched = []

        for i, record in enumerate(daily_data):
            # 复制原始数据，避免修改原数据
            enhanced = copy.deepcopy(record)

            # ========== 1. 计算滚动净流入 ==========

            # 5日滚动
            if i >= 4:  # 至少5天数据
                flow_5d = sum(daily_data[j]['institution'] for j in range(i-4, i+1))
                enhanced['flow_5d_net'] = round(flow_5d, 2)
            else:
                enhanced['flow_5d_net'] = None

            # 10日滚动
            if i >= 9:  # 至少10天数据
                flow_10d = sum(daily_data[j]['institution'] for j in range(i-9, i+1))
                enhanced['flow_10d_net'] = round(flow_10d, 2)
            else:
                enhanced['flow_10d_net'] = None

            # 20日滚动
            if i >= 19:  # 至少20天数据
                flow_20d = sum(daily_data[j]['institution'] for j in range(i-19, i+1))
                enhanced['flow_20d_net'] = round(flow_20d, 2)
            else:
                enhanced['flow_20d_net'] = None

            # ========== 2. 计算流入排名百分位 ==========

            # 获取所有历史数据（截至当前天）
            all_flows = [d['institution'] for d in daily_data[:i+1]]

            if all_flows:
                # 计算当前流入在历史中的排名
                # 排名 = 比当前流入小的数量 / 总数量
                smaller_count = sum(1 for f in all_flows if f < record['institution'])
                rank = smaller_count / len(all_flows)
                enhanced['inflow_rank_percentile'] = round(rank, 4)
            else:
                enhanced['inflow_rank_percentile'] = 0.5

            # ========== 3. 额外的辅助指标 ==========

            # 流入级别（基于绝对值，不是百分位）
            # TINY: < 500万
            # SMALL: 500-1500万
            # MEDIUM: 1500-3000万
            # LARGE: 3000-5000万
            # MEGA: > 5000万
            inflow_amount = abs(record.get('institution', 0))
            if inflow_amount >= 5000:
                enhanced['inflow_level'] = 'MEGA'
            elif inflow_amount >= 3000:
                enhanced['inflow_level'] = 'LARGE'
            elif inflow_amount >= 1500:
                enhanced['inflow_level'] = 'MEDIUM'
            elif inflow_amount >= 500:
                enhanced['inflow_level'] = 'SMALL'
            else:
                enhanced['inflow_level'] = 'TINY'

            enriched.append(enhanced)

        return enriched

    @staticmethod
    def get_rolling_summary(daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取滚动指标的汇总统计

        Args:
            daily_data: 包含滚动指标的数据

        Returns:
            汇总统计信息
        """
        if not daily_data:
            return {}

        latest = daily_data[-1]

        # 过滤掉 None 值
        flow_5d_values = [d['flow_5d_net'] for d in daily_data if d.get('flow_5d_net') is not None]
        flow_10d_values = [d['flow_10d_net'] for d in daily_data if d.get('flow_10d_net') is not None]
        flow_20d_values = [d['flow_20d_net'] for d in daily_data if d.get('flow_20d_net') is not None]

        summary = {
            'latest_date': latest['date'],
            'latest_inflow': latest['institution'],
            'latest_inflow_level': latest.get('inflow_level', 'UNKNOWN'),
            'latest_inflow_rank': latest.get('inflow_rank_percentile', 0),
            'latest_flow_5d': latest.get('flow_5d_net'),
            'latest_flow_10d': latest.get('flow_10d_net'),
            'latest_flow_20d': latest.get('flow_20d_net'),
            'total_days': len(daily_data),
            'valid_5d_days': len(flow_5d_values),
            'valid_10d_days': len(flow_10d_values),
            'valid_20d_days': len(flow_20d_values),
        }

        # 添加滚动趋势统计
        if flow_5d_values:
            summary['flow_5d_max'] = max(flow_5d_values)
            summary['flow_5d_min'] = min(flow_5d_values)
            summary['flow_5d_avg'] = round(sum(flow_5d_values) / len(flow_5d_values), 2)

        if flow_10d_values:
            summary['flow_10d_max'] = max(flow_10d_values)
            summary['flow_10d_min'] = min(flow_10d_values)
            summary['flow_10d_avg'] = round(sum(flow_10d_values) / len(flow_10d_values), 2)

        if flow_20d_values:
            summary['flow_20d_max'] = max(flow_20d_values)
            summary['flow_20d_min'] = min(flow_20d_values)
            summary['flow_20d_avg'] = round(sum(flow_20d_values) / len(flow_20d_values), 2)

        return summary


# 便捷函数
def add_rolling_metrics(daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """便捷函数：为数据添加滚动指标"""
    return RollingMetricsCalculator.add_rolling_metrics(daily_data)


if __name__ == "__main__":
    # 测试代码
    import json

    # 模拟数据
    test_data = [
        {'date': '2026-01-01', 'institution': 100},
        {'date': '2026-01-02', 'institution': 200},
        {'date': '2026-01-03', 'institution': 300},
        {'date': '2026-01-04', 'institution': 400},
        {'date': '2026-01-05', 'institution': 500},  # 第5天，可以计算 flow_5d_net
        {'date': '2026-01-06', 'institution': -100},
        {'date': '2026-01-07', 'institution': -200},
        {'date': '2026-01-08', 'institution': -300},
        {'date': '2026-01-09', 'institution': -400},
        {'date': '2026-01-10', 'institution': 5025},  # 第10天，可以计算 flow_10d_net
    ]

    print("=" * 80)
    print("滚动指标计算器测试")
    print("=" * 80)

    # 添加滚动指标
    result = add_rolling_metrics(test_data)

    # 输出结果
    print("\n前5天（5日滚动可用）:")
    for i, item in enumerate(result[:5]):
        print(f"{item['date']}: "
              f"机构流入={item['institution']}, "
              f"5日滚动={item['flow_5d_net']}, "
              f"排名={item['inflow_rank_percentile']:.2%}, "
              f"级别={item['inflow_level']}")

    print("\n第10天（10日滚动可用）:")
    print(f"{result[9]['date']}: "
          f"机构流入={result[9]['institution']}, "
          f"5日滚动={result[9]['flow_5d_net']}, "
          f"10日滚动={result[9]['flow_10d_net']}, "
          f"排名={result[9]['inflow_rank_percentile']:.2%}, "
          f"级别={result[9]['inflow_level']}")

    # 输出汇总
    print("\n汇总统计:")
    summary = RollingMetricsCalculator.get_rolling_summary(result)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    print("\n✅ 测试完成")