# -*- coding: utf-8 -*-
"""测试盲扫模式 - 详细版本"""
from logic.algo import QuantAlgo
import json

print("=" * 60)
print("🚀 开始测试半路战法扫描（盲扫模式）")
print("=" * 60)

result = QuantAlgo.scan_halfway_stocks(limit=10, min_score=30)

print("\n" + "=" * 60)
print("📊 扫描结果")
print("=" * 60)
print(f"数据状态: {result.get('数据状态')}")
print(f"说明: {result.get('说明')}")
print(f"扫描数量: {result.get('扫描数量')}")
print(f"符合条件数量: {result.get('符合条件数量')}")

# 打印所有候选股票
candidates = result.get('候选股票', [])
if candidates:
    print(f"\n🎯 符合条件的股票（共{len(candidates)}只）:")
    for i, stock in enumerate(candidates, 1):
        print(f"\n  {i}. {stock['代码']} {stock['名称']}")
        print(f"     涨跌幅: {stock['涨跌幅']:.2f}%")
        print(f"     评分: {stock['评分']}")
        print(f"     评级: {stock['评级']}")
        print(f"     信号: {stock['信号']}")
        print(f"     量比: {stock['量比']}")
        print(f"     换手率: {stock['换手率']}")
        print(f"     买一价: {stock['买一价']}")
        print(f"     卖一价: {stock['卖一价']}")
        print(f"     买一量: {stock['买一量']}")
        print(f"     卖一量: {stock['卖一量']}")
        print(f"     操作建议: {stock['操作建议']}")
else:
    print("\n❌ 没有找到符合条件的股票")
    print(f"\n完整返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

print("=" * 60)