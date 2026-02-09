"""找出所有"≥5%占成交额"的真实样本"""
import json
import os

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("查找所有'>=5%占成交额'的样本")
print("="*80)

high_ratio_samples = []

# 遍历所有快照
for filename in sorted(os.listdir(snapshot_dir)):
    if not filename.startswith('full_market_snapshot_') or not filename.endswith('_rebuild.json'):
        continue
    
    filepath = os.path.join(snapshot_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
    
    trade_date = snapshot['trade_date']
    
    # 检查机会池
    for stock in snapshot['results']['opportunities']:
        code = stock['code']
        main_net_inflow = stock['flow_data']['main_net_inflow']
        daily_amount = stock['price_data']['amount']
        
        # 计算占成交额比例
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0
        
        if inflow_to_amount >= 0.05:  # >= 5%
            high_ratio_samples.append({
                'code': code,
                'trade_date': trade_date,
                'inflow_to_amount': inflow_to_amount,
                'main_net_inflow_wan': main_net_inflow / 10000,
                'daily_amount_yi': daily_amount / 1e8,
                'close': stock['price_data']['close'],
                'pct_chg': stock['price_data']['pct_chg'],
                'risk_score': stock['risk_score']
            })

print(f"\n找到 {len(high_ratio_samples)} 个'>=5%占成交额'的样本\n")

# 按占比排序
high_ratio_samples.sort(key=lambda x: x['inflow_to_amount'], reverse=True)

print(f"{'代码':<8} {'日期':<10} {'占比':<10} {'主力流入':<12} {'成交额':<10} {'收盘价':<8} {'涨幅':<8} {'风险':<8}")
print("-"*80)

for i, sample in enumerate(high_ratio_samples, 1):
    print(f"{sample['code']:<8} {sample['trade_date']:<10} {sample['inflow_to_amount']*100:>6.2f}%     {sample['main_net_inflow_wan']:>8.1f}万      {sample['daily_amount_yi']:>6.2f}亿     {sample['close']:>6.2f}    {sample['pct_chg']:+6.2f}%   {sample['risk_score']:<8.2f}")

print("\n" + "="*80)
print(f"占比分布:")
print("-"*80)

# 按占比分桶
buckets = {
    '5-10%': [],
    '10-20%': [],
    '>=20%': []
}

for sample in high_ratio_samples:
    ratio = sample['inflow_to_amount']
    if ratio < 0.10:
        buckets['5-10%'].append(sample)
    elif ratio < 0.20:
        buckets['10-20%'].append(sample)
    else:
        buckets['≥20%'].append(sample)

for bucket_name, bucket_data in buckets.items():
    print(f"{bucket_name}: {len(bucket_data)}个")

print("="*80)