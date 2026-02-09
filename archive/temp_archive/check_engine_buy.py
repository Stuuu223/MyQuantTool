#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查正式回测引擎买入的股票"""

import sys
sys.path.append('E:/MyQuantTool')

from logic.backtest_framework import BacktestEngine
import json

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000.0)

# 加载真实快照
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
snapshots = engine.load_snapshots_from_dir(snapshot_dir)

print(f"✅ 加载了 {len(snapshots)} 个真实快照\n")

# 运行回测（但不真正执行，只是记录买入）
positions = []

for snapshot in snapshots:
    trade_date = snapshot['trade_date']
    opportunities = snapshot['results']['opportunities']

    print(f"=== {trade_date} ===")

    # 买入逻辑（复制自回测引擎）
    if len(positions) < 5:
        available_slots = 5 - len(positions)

        for stock_data in opportunities:
            if available_slots <= 0:
                break

            code = stock_data['code']

            # 检查是否已持仓
            if any(pos['code'] == code for pos in positions):
                continue

            # 检查买入信号
            if engine.should_buy(stock_data):
                flow_data = stock_data.get('flow_data', {})
                main_net_inflow = flow_data.get('main_net_inflow', 0)

                positions.append({
                    'code': code,
                    'date': trade_date,
                    'price': stock_data['price_data']['close'],
                    'main_net_inflow': main_net_inflow
                })
                print(f"  买入 {code}: 价格={stock_data['price_data']['close']:.2f}, 主力净流入={main_net_inflow:.0f}")

                available_slots -= 1

print(f"\n最终持仓数量: {len(positions)}")