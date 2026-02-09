"""验证momentum_band逻辑是否正确（基于现有快照）"""
import json
import os
from collections import Counter

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("验证momentum_band逻辑（基于现有快照）")
print("="*80)

# 根据新逻辑重新计算momentum_band
def calculate_momentum_band(pct_chg, inflow_to_amount):
    """计算momentum_band"""
    if inflow_to_amount < 0.02 or pct_chg < 5.0:
        return 'BAND_0'  # 噪声
    elif 5.0 <= pct_chg < 8.0 and 0.02 <= inflow_to_amount < 0.05:
        return 'BAND_1'  # 保守小肉
    elif 8.0 <= pct_chg < 10.0 and 0.02 <= inflow_to_amount < 0.05:
        return 'BAND_2'  # 半路推背
    elif 8.0 <= pct_chg < 10.0 and inflow_to_amount >= 0.05:
        return 'BAND_3'  # 推背加强版
    elif inflow_to_amount >= 0.05:
        return 'BAND_0'  # ≥5%占比但涨幅不符合
    else:
        return 'BAND_0'  # 其他

# 统计
band_counter = Counter()
band_samples = {band: [] for band in ['BAND_0', 'BAND_1', 'BAND_2', 'BAND_3']}

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
        pct_chg = stock['price_data']['pct_chg']
        main_net_inflow = stock['flow_data']['main_net_inflow']
        daily_amount = stock['price_data']['amount']
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0

        # 计算momentum_band
        momentum_band = calculate_momentum_band(pct_chg, inflow_to_amount)
        band_counter[momentum_band] += 1

        # 保存样本（每个band保存前5个）
        if len(band_samples[momentum_band]) < 5:
            band_samples[momentum_band].append({
                'code': stock['code'],
                'date': trade_date,
                'pct': pct_chg,
                'ratio': inflow_to_amount,
                'pool': stock['decision_tag']
            })

print("="*80)
print("Momentum Band 统计")
print("="*80)
for band in ['BAND_0', 'BAND_1', 'BAND_2', 'BAND_3']:
    print(f"{band}: {band_counter[band]} 个样本")

print("\n" + "="*80)
print("样本验证")
print("="*80)

for band in ['BAND_1', 'BAND_2', 'BAND_3']:
    print(f"\n{band} 示例样本:")
    print("代码       日期     涨幅     占比     池位")
    print("-"*60)
    for sample in band_samples[band]:
        print(f"{sample['code']}   {sample['date']}  {sample['pct']:5.2f}%  {sample['ratio']*100:5.2f}%  {sample['pool']}")

print("\n" + "="*80)
print("预期结果验证")
print("="*80)

# BAND_1应该是5-8%涨幅 + 2-5%占比
if band_counter['BAND_1'] > 0:
    print(f"✅ BAND_1 (保守小肉): {band_counter['BAND_1']} 个样本")
    # 验证样本特征
    if band_samples['BAND_1']:
        sample = band_samples['BAND_1'][0]
        if 5.0 <= sample['pct'] < 8.0 and 0.02 <= sample['ratio'] < 0.05:
            print(f"✅ BAND_1 样本特征正确: 5-8%涨幅 + 2-5%占比")
        else:
            print(f"⚠️ BAND_1 样本特征不符合预期")

# BAND_2应该是8-10%涨幅 + 2-5%占比
if band_counter['BAND_2'] > 0:
    print(f"✅ BAND_2 (半路推背): {band_counter['BAND_2']} 个样本")
    if band_samples['BAND_2']:
        sample = band_samples['BAND_2'][0]
        if 8.0 <= sample['pct'] < 10.0 and 0.02 <= sample['ratio'] < 0.05:
            print(f"✅ BAND_2 样本特征正确: 8-10%涨幅 + 2-5%占比")
        else:
            print(f"⚠️ BAND_2 样本特征不符合预期")

# BAND_3应该是8-10%涨幅 + ≥5%占比
if band_counter['BAND_3'] > 0:
    print(f"✅ BAND_3 (推背加强版): {band_counter['BAND_3']} 个样本")
    if band_samples['BAND_3']:
        sample = band_samples['BAND_3'][0]
        if 8.0 <= sample['pct'] < 10.0 and sample['ratio'] >= 0.05:
            print(f"✅ BAND_3 样本特征正确: 8-10%涨幅 + ≥5%占比")
        else:
            print(f"⚠️ BAND_3 样本特征不符合预期")

print("\n" + "="*80)
print("对比之前的分析结果")
print("="*80)
print(f"之前分析的8-10%涨幅 + 2-5%占比样本: 132个")
print(f"现在计算的BAND_2样本: {band_counter['BAND_2']}个")
print(f"匹配度: {band_counter['BAND_2']/132*100:.1f}%" if band_counter['BAND_2'] > 0 else "无法计算")

print(f"\n之前分析的8-10%涨幅 + ≥5%占比样本: 18个")
print(f"现在计算的BAND_3样本: {band_counter['BAND_3']}个")
print(f"匹配度: {band_counter['BAND_3']/18*100:.1f}%" if band_counter['BAND_3'] > 0 else "无法计算")

print("="*80)