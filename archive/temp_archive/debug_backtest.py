#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试回测逻辑"""

import sys
sys.path.append('E:/MyQuantTool')

from logic.backtest_framework import BacktestEngine

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000.0)

# 加载真实快照
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
snapshots = engine.load_snapshots_from_dir(snapshot_dir)

print(f"✅ 加载了 {len(snapshots)} 个真实快照\n")

# 打印每个快照的信息
for snapshot in snapshots:
    trade_date = snapshot['trade_date']
    opportunities = snapshot.get('results', {}).get('opportunities', [])

    print(f"快照 {trade_date}:")
    print(f"  股票数量: {len(opportunities)}")

    # 检查是否有涨跌幅 > 5% 的股票
    high_pct = [s for s in opportunities if s['price_data']['pct_chg'] > 5]
    print(f"  涨幅 > 5%: {len(high_pct)} 只")

    # 检查是否有风险分数 < 0.3 的股票
    low_risk = [s for s in opportunities if s['risk_score'] < 0.3]
    print(f"  风险 < 0.3: {len(low_risk)} 只")

    print()

# 运行回测
engine.run_backtest(snapshots, max_positions=5)

# 打印报告
engine.print_report()