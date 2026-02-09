"""分析创业板/科创板8-10%涨幅的特征"""
import json
import os
from collections import Counter

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

def get_market_type(code):
    """根据股票代码识别市场类型"""
    code_6digit = code.split('.')[0][-6:]

    if code_6digit.startswith('60'):
        return 'MAIN_10CM'
    elif code_6digit.startswith('00'):
        return 'MAIN_10CM'
    elif code_6digit.startswith('30'):
        return 'CY_20CM'
    elif code_6digit.startswith('68'):
        return 'KC_20CM'
    else:
        return 'UNKNOWN'

print("="*80)
print("创业板/科创板8-10%涨幅样本分析")
print("="*80)

# 收集创业板/科创板8-10%涨幅的样本
cy_8_10 = []
kc_8_10 = []

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
        code = stock['code']
        pct_chg = stock['price_data']['pct_chg']
        main_net_inflow = stock['flow_data']['main_net_inflow']
        daily_amount = stock['price_data']['amount']
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0

        # 只看8-10%涨幅
        if 8.0 <= pct_chg < 10.0:
            market_type = get_market_type(code)

            data = {
                'code': code,
                'date': trade_date,
                'pct': pct_chg,
                'ratio': inflow_to_amount,
                'pool': stock['decision_tag']
            }

            if market_type == 'CY_20CM':
                cy_8_10.append(data)
            elif market_type == 'KC_20CM':
                kc_8_10.append(data)

print(f"\n创业板8-10%涨幅样本: {len(cy_8_10)} 个")
print(f"科创板8-10%涨幅样本: {len(kc_8_10)} 个")

# 统计资金占比分布
cy_ratio_dist = {'<1%': 0, '1-2%': 0, '2-5%': 0, '≥5%': 0}
kc_ratio_dist = {'<1%': 0, '1-2%': 0, '2-5%': 0, '≥5%': 0}

for s in cy_8_10:
    ratio = s['ratio'] * 100
    if ratio < 1:
        cy_ratio_dist['<1%'] += 1
    elif ratio < 2:
        cy_ratio_dist['1-2%'] += 1
    elif ratio < 5:
        cy_ratio_dist['2-5%'] += 1
    else:
        cy_ratio_dist['≥5%'] += 1

for s in kc_8_10:
    ratio = s['ratio'] * 100
    if ratio < 1:
        kc_ratio_dist['<1%'] += 1
    elif ratio < 2:
        kc_ratio_dist['1-2%'] += 1
    elif ratio < 5:
        kc_ratio_dist['2-5%'] += 1
    else:
        kc_ratio_dist['≥5%'] += 1

print("\n" + "="*80)
print("创业板8-10%涨幅 - 资金占比分布")
print("="*80)
for range_name, count in cy_ratio_dist.items():
    if count > 0:
        print(f"{range_name}: {count} 个样本")

print("\n" + "="*80)
print("科创板8-10%涨幅 - 资金占比分布")
print("="*80)
for range_name, count in kc_ratio_dist.items():
    if count > 0:
        print(f"{range_name}: {count} 个样本")

# 如果有样本，显示前10个
if cy_8_10:
    print("\n" + "="*80)
    print("创业板8-10%涨幅样本（前10个）")
    print("="*80)
    print("代码       日期     涨幅     占比     池位")
    print("-"*60)
    for s in cy_8_10[:10]:
        print(f"{s['code']}   {s['date']}  {s['pct']:5.2f}%  {s['ratio']*100:5.2f}%  {s['pool']}")

if kc_8_10:
    print("\n" + "="*80)
    print("科创板8-10%涨幅样本（前10个）")
    print("="*80)
    print("代码       日期     涨幅     占比     池位")
    print("-"*60)
    for s in kc_8_10[:10]:
        print(f"{s['code']}   {s['date']}  {s['pct']:5.2f}%  {s['ratio']*100:5.2f}%  {s['pool']}")

print("="*80)