"""验证amount单位修复"""
import json

with open('E:/MyQuantTool/data/rebuild_snapshots/full_market_snapshot_20260109_rebuild.json', 'r', encoding='utf-8') as f:
    snapshot = json.load(f)

# 查看前3只机会池股票
print("修复后的数据验证:")
print("="*60)

for i, stock in enumerate(snapshot['results']['opportunities'][:3]):
    main_inflow_wan = stock['flow_data']['main_net_inflow'] / 1e4
    amount_yi = stock['price_data']['amount'] / 1e8
    pct = stock['price_data']['pct_chg']

    print(f"{i+1}. {stock['code']}:")
    print(f"   主力流入: {main_inflow_wan:.1f}万")
    print(f"   成交额: {amount_yi:.2f}亿")
    print(f"   涨幅: {pct:.2f}%")
    print()