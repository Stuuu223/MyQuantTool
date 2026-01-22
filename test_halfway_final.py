# -*- coding: utf-8 -*-
"""
最终测试：验证盲扫模式的换手率和量比
"""
from logic.algo import QuantAlgo
import json

print("=" * 80)
print("🚀 最终测试：验证盲扫模式的换手率和量比")
print("=" * 80)

result = QuantAlgo.scan_halfway_stocks(limit=3, min_score=30)

print("\n📊 扫描结果:")
print(f"  数据状态: {result.get('数据状态')}")
print(f"  扫描数量: {result.get('扫描数量')}")
print(f"  符合条件数量: {result.get('符合条件数量')}")

stocks = result.get('半路板列表', [])
print(f"\n📋 前 {min(3, len(stocks))} 只符合条件的股票:")
print("=" * 80)

for i, stock in enumerate(stocks[:3], 1):
    print(f"\n{i}. {stock['代码']} {stock['名称']}")
    print(f"   最新价: {stock['最新价']:.2f}")
    print(f"   涨跌幅: {stock['涨跌幅']:.2f}%")
    print(f"   换手率: {stock['换手率']:.2f}%")
    print(f"   量比: {stock['量比']:.2f}")
    print(f"   评分: {stock['评分']}")
    print(f"   评级: {stock['评级']}")
    print(f"   信号: {stock['信号']}")
    print(f"   操作建议: {stock['操作建议']}")

print("\n" + "=" * 80)
print("✅ 测试完成！")
print("=" * 80)

# 验证换手率和量比是否为默认值
invalid_count = 0
for stock in stocks:
    if stock['换手率'] == 0 or stock['量比'] == 1:
        invalid_count += 1

if invalid_count > 0:
    print(f"\n⚠️  警告：有 {invalid_count} 只股票的换手率或量比为默认值")
else:
    print(f"\n✅ 所有 {len(stocks)} 只股票的换手率和量比都正确获取！")