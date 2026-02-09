"""调试涨停前拉升段分析"""
import json
import os

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("调试：检查数据结构")
print("="*80)

# 先检查一个快照
sample_file = f'{snapshot_dir}/full_market_snapshot_20260109_rebuild.json'
with open(sample_file, 'r', encoding='utf-8') as f:
    snapshot = json.load(f)

print(f"快照日期: {snapshot['trade_date']}")
print(f"机会池数量: {len(snapshot['results']['opportunities'])}")
print(f"观察池数量: {len(snapshot['results']['watchlist'])}")
print(f"黑名单数量: {len(snapshot['results']['blacklist'])}")

# 检查第一个股票的数据结构
if snapshot['results']['opportunities']:
    stock = snapshot['results']['opportunities'][0]
    print(f"\n第一个股票: {stock['code']}")
    print(f"  Keys: {list(stock.keys())}")
    print(f"  price_data: {list(stock['price_data'].keys())}")
    print(f"  flow_data: {list(stock['flow_data'].keys())}")
    print(f"  涨幅: {stock['price_data']['pct_chg']}")
    print(f"  成交额: {stock['price_data']['amount']}")
    print(f"  主力流入: {stock['flow_data']['main_net_inflow']}")
    
    # 计算占比
    ratio = stock['flow_data']['main_net_inflow'] / stock['price_data']['amount']
    print(f"  占成交额: {ratio*100:.2f}%")

print("\n" + "="*80)