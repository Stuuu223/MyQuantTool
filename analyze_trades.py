#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

with open('backtest/results/t1_single_stock_7days.json') as f:
    data = json.load(f)

trades = data['t1_trades']
print('=== 逐笔交易分析 ===')
for i, t in enumerate(trades):
    if t['exit_date']:
        print(f"{i+1}. {t['entry_date']}开仓@{t['entry_price']:.2f} -> {t['exit_date']}平仓@{t['exit_price']:.2f} 盈亏:{t['pnl']:.0f}")
    else:
        print(f"{i+1}. {t['entry_date']}开仓@{t['entry_price']:.2f} -> 未平仓")

print()
print('=== 关键发现 ===')
closed_trades = [t for t in trades if t['exit_date']]
print(f'已平仓交易: {len(closed_trades)}笔')
print(f'未平仓交易: {len(trades) - len(closed_trades)}笔')

# 找出重复记录
print()
print('=== 检查重复记录 ===')
from collections import Counter
entry_keys = [f"{t['entry_date']} {t['entry_time']}" for t in trades]
duplicates = {k: v for k, v in Counter(entry_keys).items() if v > 1}
if duplicates:
    print(f'发现重复开仓记录: {duplicates}')
else:
    print('无重复开仓记录')

print()
print('=== 手算验证 ===')
total_pnl = sum(t['pnl'] for t in closed_trades if t['pnl'])
print(f'已平仓总盈亏: {total_pnl:.0f}')
print(f'初始资金: 100000')
print(f'预期最终权益: {100000 + total_pnl:.0f}')
print(f'JSON final_capital: {data["trade_layer"]["final_capital"]:.0f}')
print(f'差异: {data["trade_layer"]["final_capital"] - (100000 + total_pnl):.0f}')

print()
print('=== T+1阻塞统计 ===')
print(f"因T+1限制无法卖出: {data['blocked_stats']['by_t1_rule']}次")
print(f"因涨停无法买入: {data['blocked_stats']['by_limit_up']}次")
print(f"因资金不足: {data['blocked_stats']['by_cash']}次")
