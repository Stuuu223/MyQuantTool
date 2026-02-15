import json

data = json.load(open('backtest/results/tick_backtest_20260214_190406.json'))
trades = data['trades']

print('前10笔交易:')
for t in trades[:10]:
    print(f"{t['code']} {t['date']}: 买入={t['buy_price']:.2f}, 卖出={t['sell_price']:.2f}, 收益率={t['profit_pct']:.2f}%")

print('\n收益率异常的交易（>1000%）：')
abnormal_trades = [t for t in trades if abs(t['profit_pct']) > 1000]
for t in abnormal_trades[:10]:
    print(f"{t['code']} {t['date']}: 买入={t['buy_price']:.2f}, 卖出={t['sell_price']:.2f}, 收益率={t['profit_pct']:.2f}%")

print(f'\n总交易数: {len(trades)}')
print(f'异常交易数: {len(abnormal_trades)}')

# 检查价格分布
prices = [t['buy_price'] for t in trades if t['buy_price'] > 0]
print(f'\n正常买入价格范围: {min(prices):.2f} - {max(prices):.2f}')
print(f'买入价格中位数: {sorted(prices)[len(prices)//2]:.2f}')