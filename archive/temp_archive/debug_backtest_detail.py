#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""详细检查回测逻辑"""

import sys
sys.path.append('E:/MyQuantTool')

from logic.backtest_framework import BacktestEngine, BacktestPosition
import json
from datetime import datetime

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000.0)

# 加载真实快照
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
snapshots = engine.load_snapshots_from_dir(snapshot_dir)

print(f"✅ 加载了 {len(snapshots)} 个真实快照\n")

# 手动模拟回测过程
positions = []
all_trades = []

for snapshot in snapshots:
    trade_date = snapshot['trade_date']
    opportunities = snapshot['results']['opportunities']

    print(f"=== {trade_date} ===")

    # 检查卖出
    positions_to_close = []
    for pos in positions:
        stock_data = engine._get_stock_data(opportunities, pos.code)
        if stock_data:
            should_sell = engine.should_sell(pos, stock_data)
            print(f"  检查卖出 {pos.code}: should_sell={should_sell}, holding_days={pos.holding_days}")

            if should_sell:
                current_price = stock_data['price_data']['close']
                pos.close(current_price, trade_date)
                positions_to_close.append(pos)

                all_trades.append({
                    'type': 'sell',
                    'code': pos.code,
                    'date': trade_date,
                    'price': current_price,
                    'pnl': pos.pnl,
                    'pnl_pct': pos.pnl_pct
                })
                print(f"    → 卖出: 价格={current_price:.2f}, 收益={pos.pnl:.2f} ({pos.pnl_pct:.2f}%)")

    # 移除已平仓的持仓
    for pos in positions_to_close:
        positions.remove(pos)

    # 检查买入
    if len(positions) < 5:
        available_slots = 5 - len(positions)

        for stock_data in opportunities:
            if available_slots <= 0:
                break

            code = stock_data['code']

            # 检查是否已持仓
            if any(pos.code == code for pos in positions):
                continue

            # 检查买入信号
            if engine.should_buy(stock_data):
                entry_price = stock_data['price_data']['close']
                flow_data = stock_data.get('flow_data', {})
                main_net_inflow = flow_data.get('main_net_inflow', 0)

                pos = BacktestPosition(code, entry_price, trade_date)
                positions.append(pos)

                all_trades.append({
                    'type': 'buy',
                    'code': code,
                    'date': trade_date,
                    'price': entry_price
                })
                print(f"  买入 {code}: 价格={entry_price:.2f}, 主力净流入={main_net_inflow:.0f}")

                available_slots -= 1

    # 更新持仓天数
    for pos in positions:
        entry_dt = pos.entry_date  # 已经是字符串格式
        current_dt = trade_date

        # 计算天数差
        entry_date_obj = datetime.strptime(entry_dt, '%Y%m%d')
        current_date_obj = datetime.strptime(current_dt, '%Y%m%d')
        pos.holding_days = (current_date_obj - entry_date_obj).days

        print(f"  持仓 {pos.code}: holding_days={pos.holding_days}")

    print()

# 强制平仓
last_date = snapshots[-1]['trade_date']
for pos in positions:
    pos.close(pos.entry_price, last_date)
    all_trades.append({
        'type': 'sell',
        'code': pos.code,
        'date': last_date,
        'price': pos.exit_price,
        'pnl': pos.pnl,
        'pnl_pct': pos.pnl_pct
    })
    print(f"强制平仓 {pos.code}: 价格={pos.exit_price:.2f}, 收益={pos.pnl:.2f} ({pos.pnl_pct:.2f}%)")

print("\n=== 所有交易 ===")
for trade in all_trades:
    if trade['type'] == 'buy':
        print(f"买入 {trade['code']}: {trade['date']}, 价格={trade['price']:.2f}")
    else:
        print(f"卖出 {trade['code']}: {trade['date']}, 价格={trade['price']:.2f}, 收益={trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)")