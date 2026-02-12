#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 603697 场景识别 - 模拟 TAIL_RALLY 场景

根据用户要求，603697 应该被识别为 TAIL_RALLY（补涨尾声）。

TAIL_RALLY 特征：
1. 30日累计净流出 > 0
2. 当日主力净流入 > 5000万
3. 资金类型 = HOTMONEY（游资）
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.rolling_risk_features import compute_all_scenario_features
from logic.scenario_classifier import ScenarioClassifier

def simulate_603697_tail_rally():
    """
    模拟 603697 的 TAIL_RALLY 场景资金流数据

    场景：前30天持续流出，今日突然大幅流入（游资主导）
    """
    flow_records = []

    # 前29天：持续流出（累计流出约 1.5亿）
    for i in range(29):
        flow_records.append({
            "date": f"2026-01-{30-i:02d}",
            "main_net_inflow": -5000000.0,  # 每天流出500万
            "super_large_net": -2000000.0,
            "large_net": -2000000.0,
            "medium_net": -500000.0,
            "small_net": -500000.0
        })

    # 第30天（最新，2026-02-08）：突然大幅流入（游资拉高）
    flow_records.insert(0, {
        "date": "2026-02-08",
        "main_net_inflow": 80000000.0,  # 流入8000万
        "super_large_net": 30000000.0,
        "large_net": 30000000.0,
        "medium_net": 10000000.0,
        "small_net": 10000000.0
    })

    return flow_records

def main():
    print("=" * 80)
    print("🔍 测试 603697 场景识别 - 模拟 TAIL_RALLY")
    print("=" * 80)

    # 构造模拟数据
    print("\n📊 构造模拟数据...")
    flow_records = simulate_603697_tail_rally()

    # 计算多日资金流
    print(f"\n💰 资金流统计:")
    net_30d = sum(r['main_net_inflow'] for r in flow_records)
    net_today = flow_records[0]['main_net_inflow']
    print(f"   30日累计净流入: {net_30d/10000:.2f}万")
    print(f"   今日净流入: {net_today/10000:.2f}万")

    # 计算场景特征
    print("\n🔧 计算场景特征...")
    scenario_features = compute_all_scenario_features(
        code="603697",
        trade_date="2026-02-08",
        flow_records=flow_records,
        capital_type="HOTMONEY",  # 游资
        sector_20d_pct_change=15,  # 板块涨15%
        sector_5d_trend=1  # 板块处于启动阶段
    )

    print("\n📋 场景特征:")
    print(f"   5日净流入: {scenario_features['net_main_5d']/10000:.2f}万")
    print(f"   10日净流入: {scenario_features['net_main_10d']/10000:.2f}万")
    print(f"   20日净流入: {scenario_features['net_main_20d']/10000:.2f}万")
    print(f"   30日净流入: {scenario_features['net_main_30d']/10000:.2f}万")
    print(f"   拉高出货: {scenario_features['one_day_pump_next_day_dump']}")
    print(f"   补涨尾声: {scenario_features['first_pump_after_30d_outflow']}")
    print(f"   30日风险评分: {scenario_features['risk_score_30d']:.2f}")
    print(f"   板块阶段: {scenario_features['stage_name']}")

    # 场景分类
    print("\n🎯 场景分类...")
    classifier = ScenarioClassifier()
    scenario_result = classifier.classify({
        'code': '603697',
        'code_6digit': '603697',
        'capital_type': 'HOTMONEY',
        'scenario_features': scenario_features,
        'sector_stage': scenario_features['sector_stage'],
        'trade_date': '2026-02-08'
    })

    print("\n" + "=" * 80)
    print("🔥 关键结果")
    print("=" * 80)
    print(f"\nis_tail_rally:           {scenario_result.is_tail_rally}")
    print(f"is_potential_trap:       {scenario_result.is_potential_trap}")
    print(f"is_potential_mainline:   {scenario_result.is_potential_mainline}")
    print(f"scenario_type:           {scenario_result.scenario_type}")
    print(f"scenario_confidence:     {scenario_result.scenario_confidence:.2f}")

    print("\n" + "=" * 80)
    print("📝 验证结论")
    print("=" * 80)

    if scenario_result.is_tail_rally:
        print("\n✅ 成功！603697 被正确识别为 TAIL_RALLY（补涨尾声）")
        print("\n💡 说明:")
        print("   1. 防守斧将拦截该股票（禁止入场）")
        print("   2. 参数调准：30日窗口、HOTMONEY 判断逻辑有效")
        print("   3. 下一步：直接上马时机斧")
    else:
        print("\n⚠️  失败！603697 未被识别为 TAIL_RALLY")
        print(f"\n💡 实际识别为: {scenario_result.scenario_type}")
        print("\n❌ 问题分析:")
        print("   1. 检查 tail_rally_pattern 阈值")
        print("   2. 检查 HOTMONEY 判断逻辑")
        print("   3. 需要回头微调参数")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()