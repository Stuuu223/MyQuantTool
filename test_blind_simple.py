# -*- coding: utf-8 -*-
"""
简单测试盲扫模式的换手率和量比
"""
import easyquotation
import json

print("=" * 80)
print("🚀 测试实时数据的换手率和量比")
print("=" * 80)

# 初始化行情源
print("\n📡 连接行情源...")
quote = easyquotation.use('tencent')

# 测试几只热门股票
test_stocks = ['300731', '688630', '300490', '688277', '300757']

print(f"\n📊 获取 {len(test_stocks)} 只股票的实时数据...")
market_data = quote.stocks(test_stocks)

print("\n" + "=" * 80)
print("📋 实时数据详情")
print("=" * 80)

for code, data in market_data.items():
    print(f"\n股票代码: {code}")
    print(f"  名称: {data.get('name', 'N/A')}")
    print(f"  最新价: {data.get('now', 0):.2f}")
    print(f"  涨跌幅: {data.get('increase', 0):.2f}%")
    print(f"  成交量: {data.get('volume', 0)}")
    print(f"  换手率: {data.get('turnover', 0):.2f}%")
    print(f"  成交额: {data.get('turnover', 0)}万元")
    print(f"  买一价: {data.get('bid1', 0):.2f}")
    print(f"  卖一价: {data.get('ask1', 0):.2f}")
    print(f"  买一量: {data.get('bid1_volume', 0)}")
    print(f"  卖一量: {data.get('ask1_volume', 0)}")

    # 模拟量比估算
    turnover_rate = data.get('turnover', 0)
    if turnover_rate > 5:
        volume_ratio = 3.0 + (turnover_rate - 5) * 0.2
    elif turnover_rate > 2:
        volume_ratio = 1.5 + (turnover_rate - 2) * 0.5
    else:
        volume_ratio = 1.0
    
    print(f"  估算量比: {volume_ratio:.2f}")

print("\n" + "=" * 80)
print("✅ 测试完成！")
print("=" * 80)