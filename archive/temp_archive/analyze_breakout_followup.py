"""分析涨停前拉升段的次日表现"""
import json
import os
from datetime import datetime, timedelta

snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'

print("="*80)
print("分析涨停前拉升段（5-8%）的次日表现")
print("="*80)

# 找出所有涨停前拉升段
breakout_stage_samples = []

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
        
        if 5.0 <= pct_chg <= 8.0 and 0.02 <= inflow_to_amount < 0.05:
            breakout_stage_samples.append({
                'code': code,
                'trade_date': trade_date,
                'close': stock['price_data']['close'],
                'pct_chg': pct_chg,
                'inflow_to_amount': inflow_to_amount
            })

print(f"找到 {len(breakout_stage_samples)} 个涨停前拉升段样本\n")

# 分析次日表现
results = []

for sample in breakout_stage_samples:
    code = sample['code']
    current_date = sample['trade_date']
    current_price = sample['close']
    current_pct = sample['pct_chg']
    
    # 计算次日日期
    current_dt = datetime.strptime(current_date, '%Y%m%d')
    next_dt = current_dt + timedelta(days=1)
    next_date_str = next_dt.strftime('%Y%m%d')
    
    # 查找次日快照
    next_snapshot_file = f'{snapshot_dir}/full_market_snapshot_{next_date_str}_rebuild.json'
    
    if not os.path.exists(next_snapshot_file):
        results.append({
            'code': code,
            'current_date': current_date,
            'current_pct': current_pct,
            'next_date': '无数据',
            'next_pct': None,
            'next_price': None,
            'pnl_pct': None,
            'is_limit_up': False
        })
        continue
    
    with open(next_snapshot_file, 'r', encoding='utf-8') as f:
        next_snapshot = json.load(f)
    
    # 查找这只股票在次日快照中的数据
    next_stock = None
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        for stock in next_snapshot['results'][pool]:
            if stock['code'] == code:
                next_stock = stock
                break
        if next_stock:
            break
    
    if next_stock:
        next_price = next_stock['price_data']['close']
        next_pct = next_stock['price_data']['pct_chg']
        
        # 计算收益率
        pnl_pct = (next_price - current_price) / current_price * 100
        
        # 判断是否涨停
        is_limit_up = next_pct >= 9.8
        
        results.append({
            'code': code,
            'current_date': current_date,
            'current_pct': current_pct,
            'next_date': next_date_str,
            'next_pct': next_pct,
            'next_price': next_price,
            'pnl_pct': pnl_pct,
            'is_limit_up': is_limit_up
        })

print(f"代码       当前日期   当前涨幅   次日日期   次日涨幅   次日价格   收益率   是否涨停")
print("-"*80)

limit_up_count = 0
for r in results:
    limit_up_str = '是' if r['is_limit_up'] else '否'
    next_pct_str = f"{r['next_pct']:+.2f}%" if r['next_pct'] is not None else 'N/A'
    pnl_str = f"{r['pnl_pct']:+.2f}%" if r['pnl_pct'] is not None else 'N/A'
    print(f"{r['code']:<8} {r['current_date']:<10} {r['current_pct']:>+6.2f}%   {r['next_date']:<10} {next_pct_str:<10} {r['next_price']:>6.2f}  {pnl_str:<10}  {limit_up_str}")

print("\n" + "="*80)
print(f"统计:")
print(f"总样本数: {len(results)}")
print(f"次日涨停: {limit_up_count}个 ({limit_up_count/len(results)*100:.1f}%)")

# 计算平均收益率
valid_pnls = [r['pnl_pct'] for r in results if r['pnl_pct'] is not None]
if valid_pnls:
    avg_pnl = sum(valid_pnls) / len(valid_pnls)
    print(f"平均收益率: {avg_pnl:+.2f}%")

print("="*80)