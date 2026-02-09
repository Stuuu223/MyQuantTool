"""测试momentum_band策略是否正确应用"""
import json
import os
from collections import Counter

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("测试momentum_band策略")
print("="*80)

# 统计momentum_band分布
band_counter = Counter()
band_to_pool = {}
sample_count = 0

for filename in sorted(os.listdir(snapshot_dir)):
    if not filename.startswith('full_market_snapshot_') or not filename.endswith('_rebuild.json'):
        continue

    filepath = os.path.join(snapshot_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    trade_date = snapshot['trade_date']

    # 检查所有股票
    all_stocks = snapshot['results']['opportunities'] + snapshot['results']['watchlist'] + snapshot['results']['blacklist']

    for stock in all_stocks:
        momentum_band = stock.get('momentum_band', 'UNKNOWN')
        decision_tag = stock['decision_tag']

        band_counter[momentum_band] += 1

        # 记录每个band对应的pool
        if momentum_band not in band_to_pool:
            band_to_pool[momentum_band] = {'opportunities': 0, 'watchlist': 0, 'blacklist': 0}

        # 映射decision_tag到pool
        pool_name = None
        if decision_tag == 'OPPORTUNITY':
            pool_name = 'opportunities'
        elif decision_tag == 'WATCHLIST':
            pool_name = 'watchlist'
        elif decision_tag == 'BLACKLIST':
            pool_name = 'blacklist'

        if pool_name:
            band_to_pool[momentum_band][pool_name] += 1

        sample_count += 1

        # 验证前20个样本的band是否正确
        if momentum_band != 'UNKNOWN' and len([k for k in band_counter.keys() if k != 'UNKNOWN']) <= 20:
            print(f"股票: {stock['code']}, 日期: {trade_date}")
            print(f"  涨幅: {pct_chg:.2f}%, 占比: {inflow_to_amount*100:.2f}%")
            print(f"  Momentum Band: {momentum_band}, Pool: {decision_tag}")
            print()

print("="*80)
print("Momentum Band 统计")
print("="*80)
for band, count in band_counter.items():
    print(f"{band}: {count} 个样本")
    if band in band_to_pool:
        print(f"  机会池: {band_to_pool[band]['opportunities']}")
        print(f"  观察池: {band_to_pool[band]['watchlist']}")
        print(f"  黑名单: {band_to_pool[band]['blacklist']}")

print("\n" + "="*80)
print("预期结果验证")
print("="*80)

# 检查是否应该有BAND_1, BAND_2, BAND_3
if 'BAND_1' in band_counter:
    print(f"✅ BAND_1 (保守小肉): {band_counter['BAND_1']} 个样本")
    if band_to_pool['BAND_1']['watchlist'] > 0:
        print(f"✅ BAND_1 主要在观察池，符合预期")
else:
    print("⚠️ BAND_1 为空，可能逻辑有误")

if 'BAND_2' in band_counter:
    print(f"✅ BAND_2 (半路推背): {band_counter['BAND_2']} 个样本")
    if band_to_pool['BAND_2']['opportunities'] > 0:
        print(f"✅ BAND_2 在机会池，符合预期")
else:
    print("⚠️ BAND_2 为空，可能逻辑有误")

if 'BAND_3' in band_counter:
    print(f"✅ BAND_3 (推背加强版): {band_counter['BAND_3']} 个样本")
    if band_to_pool['BAND_3']['opportunities'] > 0:
        print(f"✅ BAND_3 在机会池，符合预期")
else:
    print("⚠️ BAND_3 为空（数量少属于正常）")

# 检查BAND_0是否在黑名单中
if 'BAND_0' in band_counter:
    print(f"✅ BAND_0 (噪声): {band_counter['BAND_0']} 个样本")
    if band_to_pool['BAND_0']['blacklist'] > band_to_pool['BAND_0']['opportunities']:
        print(f"✅ BAND_0 主要在黑名单，符合预期")
    else:
        print(f"⚠️ BAND_0 在机会池的比例偏高，需要检查")

print("="*80)
print(f"总样本数: {sample_count}")
print("="*80)
