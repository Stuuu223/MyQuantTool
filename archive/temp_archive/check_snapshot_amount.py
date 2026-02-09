"""检查快照中amount的原始值"""
import json

with open('E:/MyQuantTool/data/rebuild_snapshots/full_market_snapshot_20260109_rebuild.json', 'r', encoding='utf-8') as f:
    snapshot = json.load(f)

# 检查第一只股票
stock = snapshot['results']['opportunities'][0]

print(f"代码: {stock['code']}")
print(f"amount原始值: {stock['price_data']['amount']:,}")
print(f"amount(元): {stock['price_data']['amount']:,}")
print(f"amount(亿元): {stock['price_data']['amount']/1e8:.4f}")

# 如果是千元单位，应该乘以1000转为元
print(f"\n如果amount是千元:")
print(f"  amount(元): {stock['price_data']['amount']*1000:,}")
print(f"  amount(亿元): {stock['price_data']['amount']*1000/1e8:.4f}")