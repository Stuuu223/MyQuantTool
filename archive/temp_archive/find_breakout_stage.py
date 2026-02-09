"""查找涨停前拉升段（5-8%涨幅，2-5%占比）"""
import json
import os
from collections import Counter

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("查找涨停前拉升段")
print("="*80)

samples = []

for filename in sorted(os.listdir(snapshot_dir)):
    if not filename.startswith('full_market_snapshot_') or not filename.endswith('_rebuild.json'):
        continue

    filepath = os.path.join(snapshot_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    trade_date = snapshot['trade_date']

    # 检查所有股票
    all_stocks = snapshot['results']['opportunities'] + snapshot['results']['watchlist']

    for stock in all_stocks:
        code = stock['code']
        main_net_inflow = stock['flow_data']['main_net_inflow']  # 单位：千元
        daily_amount = stock['price_data']['amount']  # 单位：千元
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0
        pct_chg = stock['price_data']['pct_chg']

        # 涨停前拉升段：5-8%涨幅，2-5%占比
        if 5.0 <= pct_chg <= 8.0 and 0.02 <= inflow_to_amount < 0.05:
            samples.append({
                'code': code,
                'date': trade_date,
                'pct': pct_chg,
                'ratio': inflow_to_amount,
                'pool': stock['decision_tag']
            })

print(f"找到 {len(samples)} 个涨停前拉升段样本")
print("="*80)

# 统计池位分布
pool_counter = Counter([s['pool'] for s in samples])
print("\n池位分布:")
for pool, count in pool_counter.items():
    print(f"  {pool}: {count}")

# 统计代码分布（排除重复）
unique_codes = set([s['code'] for s in samples])
print(f"\n涉及股票数: {len(unique_codes)}")

# 显示样本详情
print("\n样本详情:")
print("代码       日期     涨幅     占比     池位")
print("-"*60)
for s in samples[:30]:
    print(f"{s['code']}   {s['date']}  {s['pct']:5.2f}%  {s['ratio']*100:5.2f}%  {s['pool']}")

if len(samples) > 30:
    print(f"...还有 {len(samples)-30} 个样本")

print("="*80)