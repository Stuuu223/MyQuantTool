#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 603697 场景识别的测试脚本

目的：
1. 运行全市场扫描（使用现有缓存数据）
2. 提取 603697 的场景识别结果
3. 检查 is_tail_rally 是否为 True
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.full_market_scanner import FullMarketScanner
from logic.logger import get_logger

logger = get_logger(__name__)

def main():
    print("=" * 80)
    print("🔍 验证 603697 场景识别")
    print("=" * 80)

    # 创建扫描器
    scanner = FullMarketScanner()

    # 运行扫描（使用 premarket 模式，不依赖实时数据）
    print("\n🚀 开始扫描...")
    results = scanner.scan_market(mode='premarket')

    # 保存完整结果
    output_file = PROJECT_ROOT / "data" / "scan_results" / "2026-02-08_validation.json"
    scanner.save_results(results, str(output_file))
    print(f"\n💾 完整结果已保存: {output_file}")

    # 提取 603697 的数据
    target_code = "603697"
    print("\n" + "=" * 80)
    print(f"🎯 查找目标股票: {target_code}")
    print("=" * 80)

    found = False

    # 在机会池中查找
    for item in results.get('opportunities', []):
        if item.get('code') == target_code or item.get('code_6digit') == target_code:
            print(f"\n✅ 找到 {target_code} 在【机会池】中")
            found = True
            print_scene_details(item)
            break

    # 在观察池中查找
    if not found:
        for item in results.get('watchlist', []):
            if item.get('code') == target_code or item.get('code_6digit') == target_code:
                print(f"\n⚠️  找到 {target_code} 在【观察池】中")
                found = True
                print_scene_details(item)
                break

    # 在黑名单中查找
    if not found:
        for item in results.get('blacklist', []):
            if item.get('code') == target_code or item.get('code_6digit') == target_code:
                print(f"\n❌ 找到 {target_code} 在【黑名单】中")
                found = True
                print_scene_details(item)
                break

    if not found:
        print(f"\n⚠️  未找到 {target_code}，可能原因：")
        print("   1. 该股票不在当前扫描范围内")
        print("   2. 缺少历史资金流数据")
        print("   3. 不符合筛选条件")

    print("\n" + "=" * 80)
    print("✅ 验证完成")
    print("=" * 80)

def print_scene_details(item):
    """打印场景识别的详细信息"""
    print("\n" + "-" * 80)
    print("📊 场景识别详情")
    print("-" * 80)

    # 基本信息
    print(f"\n股票代码: {item.get('code')}")
    print(f"风险评分: {item.get('risk_score', 'N/A')}")

    # 场景识别结果（重点关注）
    print(f"\n🔥 关键场景标签:")
    print(f"   is_tail_rally:           {item.get('is_tail_rally', 'N/A')}")
    print(f"   is_potential_trap:       {item.get('is_potential_trap', 'N/A')}")
    print(f"   is_potential_mainline:   {item.get('is_potential_mainline', 'N/A')}")
    print(f"   scenario_type:           {item.get('scenario_type', 'N/A')}")
    print(f"   scenario_confidence:     {item.get('scenario_confidence', 'N/A')}")

    # 资金流特征
    print(f"\n💰 资金流特征:")
    print(f"   capital_type:            {item.get('capital_type', 'N/A')}")

    if 'scenario_features' in item:
        features = item['scenario_features']
        print(f"\n📈 多日资金流:")
        print(f"   net_main_5d:            {features.get('net_main_5d', 'N/A')}")
        print(f"   net_main_10d:           {features.get('net_main_10d', 'N/A')}")
        print(f"   net_main_20d:           {features.get('net_main_20d', 'N/A')}")
        print(f"   net_main_30d:           {features.get('net_main_30d', 'N/A')}")

        print(f"\n⚠️  风险信号:")
        print(f"   pump_dump_pattern:      {features.get('pump_dump_pattern', 'N/A')}")
        print(f"   tail_rally_pattern:     {features.get('tail_rally_pattern', 'N/A')}")
        print(f"   risk_score_30d:         {features.get('risk_score_30d', 'N/A')}")

    print("\n" + "-" * 80)

if __name__ == "__main__":
    main()