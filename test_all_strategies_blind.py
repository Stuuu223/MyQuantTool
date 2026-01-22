# -*- coding: utf-8 -*-
"""测试所有三个战法的盲扫模式"""
from logic.algo import QuantAlgo
import json

print("=" * 80)
print("🚀 开始测试所有战法的盲扫模式")
print("=" * 80)

# 测试龙头战法
print("\n" + "=" * 80)
print("🔥 测试龙头战法（盲扫模式）")
print("=" * 80)
dragon_result = QuantAlgo.scan_dragon_stocks(limit=10, min_score=30)
print(f"数据状态: {dragon_result.get('数据状态')}")
print(f"说明: {dragon_result.get('说明')}")
print(f"扫描数量: {dragon_result.get('扫描数量')}")
print(f"符合条件数量: {dragon_result.get('符合条件数量')}")
candidates = dragon_result.get('候选股票', [])
if candidates:
    print(f"\n🎯 符合条件的股票（前3只）:")
    for i, stock in enumerate(candidates[:3], 1):
        print(f"  {i}. {stock['代码']} {stock['名称']} 涨跌幅:{stock['涨跌幅']:.2f}% 评分:{stock['评分']}")
else:
    print("\n❌ 没有找到符合条件的股票")

# 测试趋势战法
print("\n" + "=" * 80)
print("🛡️ 测试趋势战法（盲扫模式）")
print("=" * 80)
trend_result = QuantAlgo.scan_trend_stocks(limit=10, min_score=30)
print(f"数据状态: {trend_result.get('数据状态')}")
print(f"说明: {trend_result.get('说明')}")
print(f"扫描数量: {trend_result.get('扫描数量')}")
print(f"符合条件数量: {trend_result.get('符合条件数量')}")
candidates = trend_result.get('候选股票', [])
if candidates:
    print(f"\n🎯 符合条件的股票（前3只）:")
    for i, stock in enumerate(candidates[:3], 1):
        print(f"  {i}. {stock['代码']} {stock['名称']} 涨跌幅:{stock['涨跌幅']:.2f}% 评分:{stock['评分']}")
else:
    print("\n❌ 没有找到符合条件的股票")

# 测试半路战法
print("\n" + "=" * 80)
print("🚀 测试半路战法（盲扫模式）")
print("=" * 80)
halfway_result = QuantAlgo.scan_halfway_stocks(limit=10, min_score=30)
print(f"数据状态: {halfway_result.get('数据状态')}")
print(f"说明: {halfway_result.get('说明')}")
print(f"扫描数量: {halfway_result.get('扫描数量')}")
print(f"符合条件数量: {halfway_result.get('符合条件数量')}")
candidates = halfway_result.get('候选股票', [])
if candidates:
    print(f"\n🎯 符合条件的股票（前3只）:")
    for i, stock in enumerate(candidates[:3], 1):
        print(f"  {i}. {stock['代码']} {stock['名称']} 涨跌幅:{stock['涨跌幅']:.2f}% 评分:{stock['评分']}")
else:
    print("\n❌ 没有找到符合条件的股票")

print("\n" + "=" * 80)
print("✅ 所有战法盲扫模式测试完成")
print("=" * 80)