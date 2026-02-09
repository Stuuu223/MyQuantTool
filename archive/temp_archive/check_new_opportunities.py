"""检查新快照下的机会池股票"""
import json
import os

# 检查每笔交易的买入日是否还在机会池
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("="*80)
print("检查新阈值下的机会池状态")
print("="*80)

for trade in trades:
    code = trade['code']
    buy_date = trade['buy_date']
    main_inflow = trade['buy_snapshot']['flow']['main_net_inflow_wan']
    
    # 加载当天的快照
    snapshot_file = f'{snapshot_dir}/full_market_snapshot_{buy_date}_rebuild.json'
    
    if not os.path.exists(snapshot_file):
        print(f"\n{code} ({buy_date}): 快照不存在")
        continue
    
    with open(snapshot_file, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
    
    # 检查这只股票在哪个池子
    pool = None
    for pool_name in ['opportunities', 'watchlist', 'blacklist']:
        for stock in snapshot['results'][pool_name]:
            if stock['code'] == code:
                pool = pool_name
                break
        if pool:
            break
    
    print(f"\n{code} ({buy_date})")
    print(f"  主力流入: {main_inflow:.1f}万")
    print(f"  当前池子: {pool}")
    
    if pool == 'opportunities':
        print(f"  ✅ 仍在机会池")
    elif pool == 'watchlist':
        print(f"  ⚠️  在观察池（新阈值下被降级）")
    else:
        print(f"  ❌ 在黑名单（新阈值下被过滤）")

print("\n" + "="*80)