"""按市场类型（10cm vs 20cm）分析BAND_2/BAND_3样本"""
import json
import os
from collections import Counter
from datetime import datetime, timedelta

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

def get_market_type(code):
    """根据股票代码识别市场类型"""
    code_6digit = code.split('.')[0][-6:]

    # 60开头：沪市主板（10cm）
    if code_6digit.startswith('60'):
        return 'MAIN_10CM'

    # 00开头：深市主板（10cm）
    elif code_6digit.startswith('00'):
        return 'MAIN_10CM'

    # 30开头：创业板（20cm）
    elif code_6digit.startswith('30'):
        return 'CY_20CM'

    # 68开头：科创板（20cm）
    elif code_6digit.startswith('68'):
        return 'KC_20CM'

    else:
        return 'UNKNOWN'

print("="*80)
print("BAND_2/BAND_3 样本按市场类型分析")
print("="*80)

# 收集数据
band_2_main = []
band_2_cy = []
band_2_kc = []

band_3_main = []
band_3_cy = []
band_3_kc = []

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
        momentum_band = stock.get('momentum_band', 'UNKNOWN')
        code = stock['code']
        pct_chg = stock['price_data']['pct_chg']
        close_price = stock['price_data']['close']
        main_net_inflow = stock['flow_data']['main_net_inflow']
        daily_amount = stock['price_data']['amount']
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0

        # 只分析BAND_2和BAND_3
        if momentum_band not in ['BAND_2', 'BAND_3']:
            continue

        market_type = get_market_type(code)

        data = {
            'code': code,
            'date': trade_date,
            'pct': pct_chg,
            'ratio': inflow_to_amount,
            'price': close_price,
            'market': market_type
        }

        if momentum_band == 'BAND_2':
            if market_type == 'MAIN_10CM':
                band_2_main.append(data)
            elif market_type == 'CY_20CM':
                band_2_cy.append(data)
            elif market_type == 'KC_20CM':
                band_2_kc.append(data)
        elif momentum_band == 'BAND_3':
            if market_type == 'MAIN_10CM':
                band_3_main.append(data)
            elif market_type == 'CY_20CM':
                band_3_cy.append(data)
            elif market_type == 'KC_20CM':
                band_3_kc.append(data)

print(f"\nBAND_2 样本（8-10%涨幅 + 2-5%占比）:")
print(f"  主板10cm: {len(band_2_main)} 个样本")
print(f"  创业板20cm: {len(band_2_cy)} 个样本")
print(f"  科创板20cm: {len(band_2_kc)} 个样本")
print(f"  总计: {len(band_2_main) + len(band_2_cy) + len(band_2_kc)} 个样本")

print(f"\nBAND_3 样本（8-10%涨幅 + ≥5%占比）:")
print(f"  主板10cm: {len(band_3_main)} 个样本")
print(f"  创业板20cm: {len(band_3_cy)} 个样本")
print(f"  科创板20cm: {len(band_3_kc)} 个样本")
print(f"  总计: {len(band_3_main) + len(band_3_cy) + len(band_3_kc)} 个样本")

# 分析次日表现
def analyze_next_day(samples, name):
    if not samples:
        print(f"\n{name}: 无样本")
        return

    limit_up = 0
    profit_count = 0
    loss_count = 0
    total_pnl = 0
    valid_samples = 0

    for s in samples:
        code = s['code']
        date = s['date']
        price = s['price']

        # 查找次日数据
        next_date = (datetime.strptime(date, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
        next_file = f'{snapshot_dir}/full_market_snapshot_{next_date}_rebuild.json'

        if os.path.exists(next_file):
            with open(next_file, 'r', encoding='utf-8') as f:
                next_snapshot = json.load(f)

            # 查找股票
            next_data = None
            for pool in ['opportunities', 'watchlist', 'blacklist']:
                for stock in next_snapshot['results'][pool]:
                    if stock['code'] == code:
                        next_data = stock
                        break
                if next_data:
                    break

            if next_data:
                next_pct = next_data['price_data']['pct_chg']
                next_price = next_data['price_data']['close']
                pnl = (next_price - price) / price * 100

                is_limit_up = next_pct >= 9.8
                valid_samples += 1

                if is_limit_up:
                    limit_up += 1
                if pnl > 0.5:
                    profit_count += 1
                elif pnl < -0.5:
                    loss_count += 1
                total_pnl += pnl

    if valid_samples > 0:
        print(f"\n{name} 次日表现:")
        print(f"  有效样本: {valid_samples}")
        print(f"  涨停率: {limit_up}/{valid_samples} ({limit_up/valid_samples*100:.1f}%)")
        print(f"  盈利率: {profit_count}/{valid_samples} ({profit_count/valid_samples*100:.1f}%)")
        print(f"  亏损率: {loss_count}/{valid_samples} ({loss_count/valid_samples*100:.1f}%)")
        print(f"  平均收益: {total_pnl/valid_samples:+.2f}%")
    else:
        print(f"\n{name}: 无有效次日数据")

# 分析BAND_2
print("\n" + "="*80)
print("BAND_2（8-10%涨幅 + 2-5%占比）按市场类型分析")
print("="*80)
analyze_next_day(band_2_main, "主板10cm")
analyze_next_day(band_2_cy, "创业板20cm")
analyze_next_day(band_2_kc, "科创板20cm")

# 分析BAND_3
print("\n" + "="*80)
print("BAND_3（8-10%涨幅 + ≥5%占比）按市场类型分析")
print("="*80)
analyze_next_day(band_3_main, "主板10cm")
analyze_next_day(band_3_cy, "创业板20cm")
analyze_next_day(band_3_kc, "科创板20cm")

print("\n" + "="*80)
print("结论")
print("="*80)
print("✅ 已按市场类型拆分样本，现在可以看到10cm和20cm的真实差异")
print("="*80)