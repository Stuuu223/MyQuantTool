"""分析所有股票的涨幅和占比分布"""
import json
import os

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("分析涨幅和占比分布")
print("="*80)

# 统计涨幅分布
pct_ranges = {
    '<0': 0,
    '0-2': 0,
    '2-5': 0,
    '5-8': 0,
    '8-10': 0,
    '≥10': 0
}

# 统计占比分布
ratio_ranges = {
    '<0': 0,
    '0-1': 0,
    '1-2': 0,
    '2-5': 0,
    '5-10': 0,
    '≥10': 0
}

# 统计5-8%涨幅的占比分布
pct_5_8_ratio = []

total_stocks = 0

for filename in sorted(os.listdir(snapshot_dir)):
    if not filename.startswith('full_market_snapshot_') or not filename.endswith('_rebuild.json'):
        continue

    filepath = os.path.join(snapshot_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    all_stocks = snapshot['results']['opportunities'] + snapshot['results']['watchlist']

    for stock in all_stocks:
        total_stocks += 1
        main_net_inflow = stock['flow_data']['main_net_inflow']
        daily_amount = stock['price_data']['amount']
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0
        pct_chg = stock['price_data']['pct_chg']

        # 统计涨幅
        if pct_chg < 0:
            pct_ranges['<0'] += 1
        elif pct_chg < 2:
            pct_ranges['0-2'] += 1
        elif pct_chg < 5:
            pct_ranges['2-5'] += 1
        elif pct_chg < 8:
            pct_ranges['5-8'] += 1
        elif pct_chg < 10:
            pct_ranges['8-10'] += 1
        else:
            pct_ranges['≥10'] += 1

        # 统计占比
        if inflow_to_amount < 0:
            ratio_ranges['<0'] += 1
        elif inflow_to_amount < 0.01:
            ratio_ranges['0-1'] += 1
        elif inflow_to_amount < 0.02:
            ratio_ranges['1-2'] += 1
        elif inflow_to_amount < 0.05:
            ratio_ranges['2-5'] += 1
        elif inflow_to_amount < 0.10:
            ratio_ranges['5-10'] += 1
        else:
            ratio_ranges['≥10'] += 1

        # 记录5-8%涨幅的占比
        if 5.0 <= pct_chg <= 8.0:
            pct_5_8_ratio.append(inflow_to_amount * 100)

print(f"总股票数: {total_stocks}")
print("\n涨幅分布:")
for range_name, count in pct_ranges.items():
    print(f"  {range_name}: {count} ({count/total_stocks*100:.1f}%)")

print("\n占比分布:")
for range_name, count in ratio_ranges.items():
    print(f"  {range_name}: {count} ({count/total_stocks*100:.1f}%)")

print(f"\n5-8%涨幅的股票数: {len(pct_5_8_ratio)}")
if pct_5_8_ratio:
    print(f"占比分布: 最小{min(pct_5_8_ratio):.2f}%, 最大{max(pct_5_8_ratio):.2f}%, 平均{sum(pct_5_8_ratio)/len(pct_5_8_ratio):.2f}%")
    # 统计占比分布
    ratio_dist = {
        '<1': 0,
        '1-2': 0,
        '2-5': 0,
        '≥5': 0
    }
    for r in pct_5_8_ratio:
        if r < 1:
            ratio_dist['<1'] += 1
        elif r < 2:
            ratio_dist['1-2'] += 1
        elif r < 5:
            ratio_dist['2-5'] += 1
        else:
            ratio_dist['≥5'] += 1
    print("占比分布:")
    for range_name, count in ratio_dist.items():
        print(f"  {range_name}: {count} ({count/len(pct_5_8_ratio)*100:.1f}%)")

print("="*80)