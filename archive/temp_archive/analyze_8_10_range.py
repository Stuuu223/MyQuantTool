"""分析8-10%涨幅区间的特征"""
import json
import os
from collections import Counter
from datetime import datetime, timedelta

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("8-10%涨幅区间分析")
print("="*80)

# 两个桶
bucket_a = []  # 8-10%涨幅 + 2-5%占比
bucket_b = []  # 8-10%涨幅 + ≥5%占比

# 收集样本
for filename in sorted(os.listdir(snapshot_dir)):
    if not filename.startswith('full_market_snapshot_') or not filename.endswith('_rebuild.json'):
        continue

    filepath = os.path.join(snapshot_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    trade_date = snapshot['trade_date']
    all_stocks = snapshot['results']['opportunities'] + snapshot['results']['watchlist']

    for stock in all_stocks:
        code = stock['code']
        main_net_inflow = stock['flow_data']['main_net_inflow']
        daily_amount = stock['price_data']['amount']
        inflow_to_amount = (main_net_inflow / daily_amount) if daily_amount > 0 else 0
        pct_chg = stock['price_data']['pct_chg']
        close_price = stock['price_data']['close']

        if 8.0 <= pct_chg < 10.0:
            data = {
                'code': code,
                'date': trade_date,
                'pct': pct_chg,
                'ratio': inflow_to_amount,
                'price': close_price,
                'pool': stock['decision_tag']
            }

            if 0.02 <= inflow_to_amount < 0.05:
                bucket_a.append(data)
            elif inflow_to_amount >= 0.05:
                bucket_b.append(data)

print(f"桶A（8-10%涨幅 + 2-5%占比）: {len(bucket_a)}个样本")
print(f"桶B（8-10%涨幅 + ≥5%占比）: {len(bucket_b)}个样本")
print("="*80)

# 统计每个桶的次日表现
def analyze_bucket(bucket, name):
    print(f"\n{name}")
    print("-"*80)

    if not bucket:
        print("无样本")
        return

    # 次日表现统计
    limit_up = 0
    profit_count = 0
    loss_count = 0
    flat_count = 0
    total_pnl = 0
    valid_samples = 0

    print("代码       日期     涨幅     占比     次日结果")
    for d in bucket[:20]:  # 只显示前20个
        code = d['code']
        date = d['date']
        pct = d['pct']
        ratio = d['ratio']
        price = d['price']

        # 查找次日数据
        next_date = (datetime.strptime(date, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
        next_file = f'{snapshot_dir}/full_market_snapshot_{next_date}_rebuild.json'

        if os.path.exists(next_file):
            with open(next_file, 'r', encoding='utf-8') as f:
                next_snapshot = json.load(f)

            # 查找股票
            next_data = None
            for pool in ['opportunities', 'watchlist', 'blacklist']:
                for s in next_snapshot['results'][pool]:
                    if s['code'] == code:
                        next_data = s
                        break
                if next_data:
                    break

            if next_data:
                next_pct = next_data['price_data']['pct_chg']
                next_price = next_data['price_data']['close']
                pnl = (next_price - price) / price * 100

                is_limit_up = next_pct >= 9.8
                result_str = f"{'涨停' if is_limit_up else '正常'} {next_pct:+.2f}%"

                print(f"{code}   {date}  {pct:5.2f}%  {ratio*100:5.2f}%  {result_str}")

                valid_samples += 1
                if is_limit_up:
                    limit_up += 1
                if pnl > 0.5:  # >0.5%才算盈利
                    profit_count += 1
                elif pnl < -0.5:  # <-0.5%才算亏损
                    loss_count += 1
                else:
                    flat_count += 1
                total_pnl += pnl
            else:
                print(f"{code}   {date}  {pct:5.2f}%  {ratio*100:5.2f}%  无次日数据")
        else:
            print(f"{code}   {date}  {pct:5.2f}%  {ratio*100:5.2f}%  无次日文件")

    if len(bucket) > 20:
        print(f"...还有 {len(bucket)-20} 个样本")

    print("-"*80)
    if valid_samples > 0:
        print(f"有效样本: {valid_samples}/{len(bucket)}")
        print(f"涨停率: {limit_up}/{valid_samples} ({limit_up/valid_samples*100:.1f}%)")
        print(f"盈利: {profit_count}, 亏损: {loss_count}, 平盘: {flat_count}")
        print(f"平均收益: {total_pnl/valid_samples:+.2f}%")
        print(f"盈亏比: {profit_count/loss_count:.2f}" if loss_count > 0 else f"盈亏比: 无亏损")
    else:
        print("无有效样本")

# 分析两个桶
analyze_bucket(bucket_a, "桶A: 8-10%涨幅 + 2-5%占比")
analyze_bucket(bucket_b, "桶B: 8-10%涨幅 + ≥5%占比")

print("\n" + "="*80)
print("对比总结")
print("="*80)
print(f"桶A样本数: {len(bucket_a)}")
print(f"桶B样本数: {len(bucket_b)}")
print("="*80)