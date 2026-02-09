"""检查所有交易的Attack评分"""
import json

with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print("Attack评分检查:")
print("="*80)

for trade in trades:
    snapshot = trade['buy_snapshot']
    attack = snapshot['attack_score']
    main_inflow = snapshot['flow']['main_net_inflow_wan']
    amount = snapshot['price']['amount_yi']
    pct = snapshot['price']['pct_chg']

    print(f"{trade['code']}: attack={attack:.1f}, 主力={main_inflow:.1f}万, 成交={amount:.2f}亿, 涨幅={pct:.2f}%")