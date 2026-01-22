# -*- coding: utf-8 -*-
"""
调试：检查实时数据中的turnover字段
"""
import easyquotation
import json

print("连接行情源...")
quote = easyquotation.use('tencent')

# 测试几只股票
test_stocks = ['300606', '688630', '301590']

print(f"\n获取 {len(test_stocks)} 只股票的实时数据...")
market_data = quote.stocks(test_stocks)

print("\n实时数据详情:")
for code, data in market_data.items():
    print(f"\n股票代码: {code}")
    print(f"  名称: {data.get('name', 'N/A')}")
    print(f"  最新价: {data.get('now', 0):.2f}")
    print(f"  涨跌幅: {data.get('increase', 0):.2f}%")
    print(f"  成交量: {data.get('volume', 0)}")
    print(f"  turnover字段值: {data.get('turnover', 'NOT FOUND')}")