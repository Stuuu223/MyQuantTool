#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试回测框架逻辑"""

import json
import os
from datetime import datetime, timedelta

# 创建模拟快照
def create_mock_snapshot(trade_date: str, prices: dict, flows: dict, risks: dict) -> dict:
    """创建模拟快照"""
    opportunities = []

    for code, price in prices.items():
        stock_data = {
            'code': code,
            'code_6digit': code[:6],
            'trade_date': trade_date,
            'price_data': {
                'open': price * 0.98,
                'high': price * 1.02,
                'low': price * 0.97,
                'close': price,
                'pre_close': price * 0.99,
                'change': price * 0.01,
                'pct_chg': 1.01,
                'volume': 100000,
                'amount': 1000000
            },
            'tech_factors': {
                'ma5': price * 0.99,
                'pct_chg_3d': 0.02
            },
            'flow_data': {
                'main_net_inflow': flows.get(code, 0),
                'source': 'tushare'
            },
            'decision_tag': None,
            'risk_score': risks.get(code, 0.0),
            'trap_signals': []
        }
        opportunities.append(stock_data)

    return {
        'scan_time': f'{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}T10:00:00',
        'mode': 'rebuild',
        'trade_date': trade_date,
        'summary': {
            'total_stocks': len(opportunities),
            'success_count': len(opportunities),
            'failed_count': 0
        },
        'results': {
            'opportunities': opportunities
        }
    }


# 生成10天的模拟数据
base_date = datetime(2026, 2, 1)
snapshots = []

# 测试股票
test_stocks = ['000001.SZ', '000002.SZ', '600000.SH']

for i in range(10):
    trade_date = (base_date + timedelta(days=i)).strftime('%Y%m%d')

    # 价格走势：先涨后跌
    prices = {}
    flows = {}
    risks = {}

    for stock in test_stocks:
        base_price = 10.0
        if i < 5:
            # 前5天上涨
            price = base_price * (1 + i * 0.02)
            flow = 100000 * i  # 主力流入
            risk = 0.0
        else:
            # 后5天下跌
            price = base_price * (1 + (9 - i) * 0.02)
            flow = -100000 * (i - 4)  # 主力流出
            risk = 0.8  # 高风险

        prices[stock] = price
        flows[stock] = flow
        risks[stock] = risk

    snapshot = create_mock_snapshot(trade_date, prices, flows, risks)
    snapshots.append(snapshot)

# 保存模拟快照
output_dir = 'E:/MyQuantTool/data/rebuild_snapshots_test'
os.makedirs(output_dir, exist_ok=True)

for snapshot in snapshots:
    filename = f"full_market_snapshot_{snapshot['trade_date']}_rebuild.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print(f"✅ 生成快照: {filename}")

print(f"\n✅ 共生成 {len(snapshots)} 个模拟快照")
print(f"📁 保存位置: {output_dir}")

# 运行回测
import sys
sys.path.append('E:/MyQuantTool')

from logic.backtest_framework import BacktestEngine

engine = BacktestEngine(initial_capital=100000.0)
engine.run_backtest(snapshots, max_positions=3)
engine.print_report()

# 保存结果
output_dir = 'E:/MyQuantTool/data/backtest_results_test'
os.makedirs(output_dir, exist_ok=True)

engine.save_trades(f'{output_dir}/trades.csv')
engine.save_positions(f'{output_dir}/positions.csv')