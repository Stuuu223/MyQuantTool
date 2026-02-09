"""查看新阈值下的交易详情"""
import json

with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("="*80)
print("新阈值下的交易详情")
print("="*80)

for i, trade in enumerate(trades, 1):
    code = trade['code']
    buy_date = trade['buy_date']
    buy_price = trade['buy_snapshot']['price']['close']
    main_inflow = trade['buy_snapshot']['flow']['main_net_inflow_wan']
    pnl_pct = max([s['pnl_pct'] for s in trade['sell_records']])
    
    print(f"\n交易 {i}: {code}")
    print(f"  买入: {buy_date} @ {buy_price:.2f}")
    print(f"  主力流入: {main_inflow:.1f}万")
    print(f"  最终收益: {pnl_pct:+.2f}%")
    
    for sell in trade['sell_records']:
        print(f"  卖出: {sell['date']} @ {sell['price']:.2f} ({sell['pnl_pct']:+.2f}%, {sell['holding_days']}天)")

print("\n" + "="*80)