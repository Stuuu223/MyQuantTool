#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查持仓股票的资金流数据"""

import json
import sys
sys.path.append('E:/MyQuantTool')

# 加载快照
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
snapshots = []

for filename in ['full_market_snapshot_20260203_rebuild.json', 'full_market_snapshot_20260206_rebuild.json']:
    filepath = f'{snapshot_dir}/{filename}'
    with open(filepath, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
        snapshots.append(snapshot)

# 持仓股票
holdings = ['000039.SZ', '000070.SZ', '000157.SZ', '000338.SZ', '000408.SZ']

print("=" * 60)
print("检查持仓股票的资金流数据")
print("=" * 60)

for snapshot in snapshots:
    trade_date = snapshot['trade_date']
    opportunities = snapshot['results']['opportunities']

    print(f"\n{trade_date}:")
    print("-" * 60)

    for code in holdings:
        stock_data = None
        for s in opportunities:
            if s['code'] == code:
                stock_data = s
                break

        if stock_data:
            flow_data = stock_data.get('flow_data', {})
            main_net_inflow = flow_data.get('main_net_inflow', 0)
            source = flow_data.get('source', 'none')
            price = stock_data['price_data']['close']
            pct_chg = stock_data['price_data']['pct_chg']

            print(f"{code}: 价格={price:.2f}, 涨幅={pct_chg:.2f}%, 主力净流入={main_net_inflow:.0f}, 数据源={source}")
        else:
            print(f"{code}: 未找到数据")

print("\n" + "=" * 60)