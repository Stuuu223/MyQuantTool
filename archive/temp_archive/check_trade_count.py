"""检查交易数"""
import json

with open('E:/MyQuantTool/data/backtest_results_real/trade_details.json', 'r', encoding='utf-8') as f:
    trades = json.load(f)

print(f'总交易数: {len(trades)}')
for t in trades:
    print(f"{t['code']}: {t['buy_date']}")