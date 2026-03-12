"""
批量分析Golden Samples的高位承接特征
CTO V108 能量重心探测器
"""
from xtquant import xtdata
import pandas as pd
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

xtdata.connect()

# 读取golden_samples
df = pd.read_csv('data/validation/golden_samples.csv')

print('=' * 80)
print('Golden Samples 高位承接特征研究')
print('CTO V108 能量重心探测器')
print('=' * 80)
print()

# 分析每个样本
results = []

for _, row in df.iterrows():
    stock = row['stock_code']
    date = str(row['date'])
    label = row['label']
    
    try:
        # 获取日K
        daily = xtdata.get_local_data([], [stock], period='1d', start_time=date, end_time=date)
        if stock not in daily or daily[stock] is None or len(daily[stock]) == 0:
            print(f'{stock} {date}: 无日K数据')
            continue
            
        df_d = daily[stock]
        prev_close = float(df_d['preClose'].iloc[0]) if 'preClose' in df_d.columns else 0
        if prev_close <= 0:
            continue
            
        # 判断涨停
        high = float(df_d['high'].iloc[0])
        close = float(df_d['close'].iloc[0])
        
        # 涨停价
        if stock.startswith(('30', '68')):
            limit_pct = 0.20
        else:
            limit_pct = 0.10
        limit_price = round(prev_close * (1 + limit_pct), 2)
        
        is_limit = abs(high - limit_price) / limit_price < 0.01 if limit_price > 0 else False
        
        # 获取Tick
        tick = xtdata.get_local_data([], [stock], period='tick', start_time=date, end_time=date)
        if stock not in tick or tick[stock] is None:
            continue
            
        df_t = tick[stock]
        if len(df_t) == 0:
            continue
        
        # 计算增量
        df_t['delta_amount'] = df_t['amount'].diff().fillna(0)
        valid = df_t[(df_t['lastPrice'] > 0) & (df_t['delta_amount'] > 0)].copy()
        
        if len(valid) == 0:
            continue
        
        # 计算能量重心
        total_amt = valid['delta_amount'].sum()
        if total_amt <= 0:
            continue
            
        energy_center = (valid['lastPrice'] * valid['delta_amount']).sum() / total_amt
        energy_ratio = energy_center / limit_price if limit_price > 0 else 0
        
        # 计算高位区占比 (涨停价的80%以上)
        high_altitude = 0
        for idx, r in valid.iterrows():
            price = r['lastPrice']
            delta = r['delta_amount']
            change_pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            if change_pct >= limit_pct * 80:  # 高位区
                high_altitude += delta
        
        high_ratio = high_altitude / total_amt * 100 if total_amt > 0 else 0
        
        # 判定类型
        if energy_ratio >= 0.80 and high_ratio > 50:
            sustain_type = '高位强承接'
        elif energy_ratio < 0.5:
            sustain_type = '偷袭'
        else:
            sustain_type = '中性'
        
        results.append({
            'stock': stock,
            'date': date,
            'label': label,
            'is_limit': is_limit,
            'prev_close': prev_close,
            'limit_price': limit_price,
            'energy_center': energy_center,
            'energy_ratio': energy_ratio,
            'high_ratio': high_ratio,
            'sustain_type': sustain_type
        })
        
    except Exception as e:
        print(f'{stock} {date}: 错误 {e}')
        continue

# 输出结果
print(f'样本分析结果 (共{len(results)}个有效样本)')
print('=' * 80)
print()

# 表头
header = f"{'股票':<12} {'日期':<10} {'标签':<4} {'涨停':<4} {'能量重心':<10} {'重心比例':<8} {'高位占比':<8} {'类型':<12}"
print(header)
print('-' * 80)

for r in results:
    limit_str = '是' if r['is_limit'] else '否'
    line = f"{r['stock']:<12} {r['date']:<10} {r['label']:<4} {limit_str:<4} {r['energy_center']:<10.2f} {r['energy_ratio']*100:<7.1f}% {r['high_ratio']:<7.1f}% {r['sustain_type']:<12}"
    print(line)

print()
print('=' * 80)
print('统计分析')
print('=' * 80)

limit_samples = [r for r in results if r['is_limit']]
high_sustain = [r for r in limit_samples if r['sustain_type'] == '高位强承接']
normal_samples = [r for r in limit_samples if r['sustain_type'] == '中性']
steal_samples = [r for r in limit_samples if r['sustain_type'] == '偷袭']

print(f'涨停样本数: {len(limit_samples)}')
print(f'高位强承接数: {len(high_sustain)} ({len(high_sustain)/len(limit_samples)*100:.1f}%)' if limit_samples else 0)
print(f'中性样本数: {len(normal_samples)} ({len(normal_samples)/len(limit_samples)*100:.1f}%)' if limit_samples else 0)
print(f'偷袭样本数: {len(steal_samples)} ({len(steal_samples)/len(limit_samples)*100:.1f}%)' if limit_samples else 0)

if high_sustain:
    print()
    print('【高位强承接样本】')
    for r in high_sustain:
        print(f"  {r['stock']} {r['date']}: 能量重心{r['energy_ratio']*100:.0f}%, 高位占比{r['high_ratio']:.1f}%")

if steal_samples:
    print()
    print('【偷袭样本】')
    for r in steal_samples:
        print(f"  {r['stock']} {r['date']}: 能量重心{r['energy_ratio']*100:.0f}%, 低位占比{100-r['high_ratio']:.1f}%")
