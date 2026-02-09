"""按资金流入占比分析真实交易表现"""
import json
import os

# 加载交易记录
with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

# 加载所有快照，获取成交额数据
snapshots = {}
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

for filename in os.listdir(snapshot_dir):
    if filename.startswith('full_market_snapshot_') and filename.endswith('_rebuild.json'):
        filepath = os.path.join(snapshot_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
            trade_date = snapshot['trade_date']
            snapshots[trade_date] = snapshot

print("="*80)
print("资金流入占比分析（基于真实交易样本）")
print("="*80)

# 存储所有数据点
data_points = []

for trade in trades:
    code = trade['code']
    buy_date = trade['buy_date']
    buy_snapshot = trade['buy_snapshot']
    
    # 获取当日快照的完整成交额数据
    snapshot = snapshots.get(buy_date)
    if not snapshot:
        continue
    
    # 找到这只股票的完整数据
    stock_data = None
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        for stock in snapshot['results'].get(pool, []):
            if stock['code'] == code:
                stock_data = stock
                break
        if stock_data:
            break
    
    if not stock_data:
        continue
    
    # 计算三个关键占比
    main_net_inflow = stock_data['flow_data']['main_net_inflow']
    daily_amount = stock_data['price_data']['amount']  # 单位：元
    circulating_mv = stock_data.get('circulating_market_cap', 0)
    
    # 如果没有流通市值，用估算
    if circulating_mv == 0:
        circulating_shares = stock_data.get('circulating_shares', 0)
        last_price = stock_data['price_data']['close']
        circulating_mv = circulating_shares * last_price
    
    # 比例1：主力净流入 / 当日成交额
    inflow_to_amount = (main_net_inflow / daily_amount * 100) if daily_amount > 0 else 0
    
    # 比例2：主力净流入 / 流通市值
    inflow_to_marketcap = (main_net_inflow / circulating_mv * 100) if circulating_mv > 0 else 0
    
    # 收益率
    best_sell = max(trade['sell_records'], key=lambda x: x['pnl_pct'])
    pnl_pct = best_sell['pnl_pct']
    holding_days = best_sell['holding_days']
    
    data_points.append({
        'code': code,
        'buy_date': buy_date,
        'inflow_to_amount': inflow_to_amount,  # %
        'inflow_to_marketcap': inflow_to_marketcap,  # %
        'pnl_pct': pnl_pct,
        'holding_days': holding_days,
        'main_net_inflow_wan': main_net_inflow / 10000,
        'daily_amount_yi': daily_amount / 1e8
    })

print(f"\n分析样本: {len(data_points)} 笔交易\n")

# 详细数据
print("="*80)
print("每笔交易的占比和收益")
print("="*80)
for dp in data_points:
    print(f"{dp['code']} ({dp['buy_date']})")
    print(f"  主力净流入: {dp['main_net_inflow_wan']:.1f}万 / 当日成交额{dp['daily_amount_yi']:.2f}亿")
    print(f"  占成交额: {dp['inflow_to_amount']:.2f}%")
    print(f"  占流通市值: {dp['inflow_to_marketcap']:.2f}%")
    print(f"  收益: {dp['pnl_pct']:+.2f}%, 持仓{dp['holding_days']}天")
    print()

# 按流入/成交额占比分桶
print("="*80)
print("按流入/成交额占比分桶分析")
print("="*80)

buckets = {
    '0-2%': [],
    '2-5%': [],
    '5-10%': [],
    '10-20%': [],
    '>20%': []
}

for dp in data_points:
    ratio = dp['inflow_to_amount']
    if ratio < 2:
        buckets['0-2%'].append(dp)
    elif ratio < 5:
        buckets['2-5%'].append(dp)
    elif ratio < 10:
        buckets['5-10%'].append(dp)
    elif ratio < 20:
        buckets['10-20%'].append(dp)
    else:
        buckets['>20%'].append(dp)

print(f"\n{'占比区间':<10} {'样本数':<8} {'平均收益':<10} {'中位收益':<10} {'最大收益':<10} {'最小收益':<10}")
print("-"*80)

for bucket_name, bucket_data in buckets.items():
    if not bucket_data:
        continue
    
    pnls = [dp['pnl_pct'] for dp in bucket_data]
    avg_pnl = sum(pnls) / len(pnls)
    median_pnl = sorted(pnls)[len(pnls) // 2]
    max_pnl = max(pnls)
    min_pnl = min(pnls)
    
    print(f"{bucket_name:<10} {len(bucket_data):<8} {avg_pnl:+.2f}%     {median_pnl:+.2f}%     {max_pnl:+.2f}%     {min_pnl:+.2f}%")

# 按流入/市值占比分桶
print("\n" + "="*80)
print("按流入/市值占比分桶分析")
print("="*80)

marketcap_buckets = {
    '0-0.1%': [],
    '0.1-0.2%': [],
    '0.2-0.4%': [],
    '0.4-1%': [],
    '>1%': []
}

for dp in data_points:
    ratio = dp['inflow_to_marketcap']
    if ratio < 0.1:
        marketcap_buckets['0-0.1%'].append(dp)
    elif ratio < 0.2:
        marketcap_buckets['0.1-0.2%'].append(dp)
    elif ratio < 0.4:
        marketcap_buckets['0.2-0.4%'].append(dp)
    elif ratio < 1.0:
        marketcap_buckets['0.4-1%'].append(dp)
    else:
        marketcap_buckets['>1%'].append(dp)

print(f"\n{'占比区间':<10} {'样本数':<8} {'平均收益':<10} {'中位收益':<10} {'最大收益':<10} {'最小收益':<10}")
print("-"*80)

for bucket_name, bucket_data in marketcap_buckets.items():
    if not bucket_data:
        continue
    
    pnls = [dp['pnl_pct'] for dp in bucket_data]
    avg_pnl = sum(pnls) / len(pnls)
    median_pnl = sorted(pnls)[len(pnls) // 2]
    max_pnl = max(pnls)
    min_pnl = min(pnls)
    
    print(f"{bucket_name:<10} {len(bucket_data):<8} {avg_pnl:+.2f}%     {median_pnl:+.2f}%     {max_pnl:+.2f}%     {min_pnl:+.2f}%")

print("\n" + "="*80)