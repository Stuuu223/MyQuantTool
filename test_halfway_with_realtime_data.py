# -*- coding: utf-8 -*-
"""
测试半路战法（带实时换手率和量比）
"""
from logic.algo import QuantAlgo

print("=" * 80)
print("🚀 测试半路战法（带实时换手率和量比）")
print("=" * 80)

result = QuantAlgo.scan_halfway_stocks(limit=5, min_score=30)

print("\n📊 扫描结果:")
print(f"  数据状态: {result.get('数据状态')}")
print(f"  符合条件数量: {result.get('符合条件数量')}")

print("\n📋 前5只符合条件的股票:")
stocks = result.get('候选股票', [])
for i, stock in enumerate(stocks[:5], 1):
    print(f"\n{i}. {stock['代码']} {stock['名称']}")
    print(f"   涨幅: {stock['涨跌幅']:.2f}%")
    print(f"   评分: {stock['评分']}")
    print(f"   评级: {stock['评级']}")
    print(f"   换手率: {stock['换手率']:.2f}%")
    print(f"   量比: {stock['量比']:.2f}")
    print(f"   信号: {stock['信号']}")
    print(f"   操作建议: {stock['操作建议']}")