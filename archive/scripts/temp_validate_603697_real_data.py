#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 603697 场景识别（使用真实历史数据）

基于 603697_20260202_10days_report.txt 中的真实数据
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.rolling_risk_features import compute_all_scenario_features
from logic.scenario_classifier import ScenarioClassifier

def main():
    print("=" * 80)
    print("🔍 验证 603697 场景识别（真实数据）")
    print("=" * 80)

    # 603697 的真实历史资金流数据（单位：元）
    # 数据来源：603697_20260202_10days_report.txt
    # 机构 = 超大单 + 大单
    flow_records = [
        {
            "date": "2026-02-02",
            "main_net_inflow": 50251045,  # 机构 5025.10万
            "super_large_net_in": 38619229,  # 超大单 3861.92万
            "large_net_in": 11631816,   # 大单 1163.18万
            "medium_net_in": -13582276,
            "small_net_in": -36668769
        },
        {
            "date": "2026-01-30",
            "main_net_inflow": 2112397,   # 机构 211.24万
            "super_large_net_in": 2660307,  # 超大单 266.03万
            "large_net_in": -547910,     # 大单 -54.79万
            "medium_net_in": 722871,
            "small_net_in": -2835269
        },
        {
            "date": "2026-01-29",
            "main_net_inflow": -3175389,  # 机构 -317.54万
            "super_large_net_in": -3628571, # 超大单 -362.86万
            "large_net_in": 453182,      # 大单 45.32万
            "medium_net_in": 9335729,
            "small_net_in": -6160340
        },
        {
            "date": "2026-01-28",
            "main_net_inflow": -9911922,  # 机构 -991.19万
            "super_large_net_in": -3503178, # 超大单 -350.32万
            "large_net_in": -6408744,    # 大单 -640.87万
            "medium_net_in": 461837,
            "small_net_in": 9450084
        },
        {
            "date": "2026-01-27",
            "main_net_inflow": -4011408,  # 机构 -401.14万
            "super_large_net_in": -1717533, # 超大单 -171.75万
            "large_net_in": -2293875,    # 大单 -229.39万
            "medium_net_in": 141596,
            "small_net_in": 3869813
        },
        {
            "date": "2026-01-26",
            "main_net_inflow": -4577945,  # 机构 -457.79万
            "super_large_net_in": -1165160, # 超大单 -116.52万
            "large_net_in": -3412785,    # 大单 -341.28万
            "medium_net_in": -673057,
            "small_net_in": 5251003
        },
        {
            "date": "2026-01-23",
            "main_net_inflow": 5336567,   # 机构 533.66万
            "super_large_net_in": 1352794,  # 超大单 135.28万
            "large_net_in": 3983773,     # 大单 398.38万
            "medium_net_in": 7208,
            "small_net_in": -5343776
        },
        {
            "date": "2026-01-22",
            "main_net_inflow": -1444647,  # 机构 -144.46万
            "super_large_net_in": 1005133,  # 超大单 100.51万
            "large_net_in": -2449780,    # 大单 -244.98万
            "medium_net_in": 4008590,
            "small_net_in": -2563943
        },
        {
            "date": "2026-01-21",
            "main_net_inflow": -3672924,  # 机构 -367.29万
            "super_large_net_in": -134506,  # 超大单 -13.45万
            "large_net_in": -3538418,    # 大单 -353.84万
            "medium_net_in": -1634838,
            "small_net_in": 5307764
        },
        {
            "date": "2026-01-20",
            "main_net_inflow": -13321292, # 机构 -1332.13万
            "super_large_net_in": -4431806, # 超大单 -443.18万
            "large_net_in": -8889486,    # 大单 -888.95万
            "medium_net_in": -2452939,
            "small_net_in": 15774230
        }
    ]

    print("\n📊 计算场景特征...")
    scenario_features = compute_all_scenario_features(
        code="603697",
        trade_date="2026-02-02",
        flow_records=flow_records,
        capital_type="HOTMONEY",
        sector_20d_pct_change=15,  # 假设板块涨15%
        sector_5d_trend=2         # 假设板块趋势向上
    )

    print("\n" + "-" * 80)
    print("📈 场景特征结果")
    print("-" * 80)
    print(f"\n多日资金流:")
    print(f"  net_main_5d:   {scenario_features.get('net_main_5d', 'N/A')/1e4:.2f}万")
    print(f"  net_main_10d:  {scenario_features.get('net_main_10d', 'N/A')/1e4:.2f}万")
    print(f"  net_main_20d:  {scenario_features.get('net_main_20d', 'N/A')/1e4:.2f}万")
    print(f"  net_main_30d:  {scenario_features.get('net_main_30d', 'N/A')/1e4:.2f}万")

    print(f"\n拉高出货模式:")
    print(f"  pump_dump_pattern:  {scenario_features.get('one_day_pump_next_day_dump', 'N/A')}")
    print(f"  confidence:         {scenario_features.get('confidence', 'N/A'):.2f}")

    print(f"\n补涨尾声模式:")
    print(f"  tail_rally_pattern: {scenario_features.get('first_pump_after_30d_outflow', 'N/A')}")
    print(f"  tail_confidence:    {scenario_features.get('tail_confidence', 'N/A'):.2f}")
    print(f"  reasons:            {scenario_features.get('tail_reasons', 'N/A')}")

    print(f"\n板块阶段:")
    print(f"  sector_stage:       {scenario_features.get('sector_stage', 'N/A')}")
    print(f"  stage_name:         {scenario_features.get('stage_name', 'N/A')}")

    print("\n🎯 场景分类...")
    classifier = ScenarioClassifier()
    scenario_result = classifier.classify({
        'code': '603697',
        'trade_date': '2026-02-02',
        'capital_type': 'HOTMONEY',
        **scenario_features
    })

    print("\n" + "-" * 80)
    print("🔥 最终场景分类结果")
    print("-" * 80)
    print(f"\n场景类型:         {scenario_result.scenario_type}")
    print(f"is_tail_rally:     {scenario_result.is_tail_rally}")
    print(f"is_potential_trap: {scenario_result.is_potential_trap}")
    print(f"is_potential_mainline: {scenario_result.is_potential_mainline}")
    print(f"confidence:        {scenario_result.confidence:.2f}")
    print(f"reasons:           {scenario_result.reasons}")

    print("\n" + "=" * 80)
    print("✅ 验证完成")
    print("=" * 80)

    # 返回关键结果
    return scenario_result.is_tail_rally

if __name__ == "__main__":
    is_tail_rally = main()

    # 根据结果给出建议
    print("\n" + "=" * 80)
    print("💡 决策建议")
    print("=" * 80)
    if is_tail_rally:
        print("✅ 603697 被正确识别为 TAIL_RALLY（补涨尾声）")
        print("   参数设置正确，可以直接上马时机斧")
    else:
        print("⚠️  603697 未被识别为 TAIL_RALLY")
        print("   需要微调参数")
    print("=" * 80)
