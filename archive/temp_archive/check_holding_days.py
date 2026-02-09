"""检查持仓天数"""
import json

with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print('='*80)
print('持仓天数检查')
print('='*80)

for t in trades:
    print(f"\n{t['code']}:")
    print(f"  买入日期: {t['buy_date']}")
    print(f"  卖出记录:")
    for s in t['sell_records']:
        holding_days = s['holding_days']
        flag = '❌ 负数!' if holding_days < 0 else '✅'
        print(f"    {s['date']}: {holding_days}天 {flag}")

print("\n" + "="*80)
negative_count = sum(1 for t in trades for s in t['sell_records'] if s['holding_days'] < 0)
print(f'总结: 共{len(trades)}笔交易, {negative_count}笔有负数持仓天数')
print("="*80)