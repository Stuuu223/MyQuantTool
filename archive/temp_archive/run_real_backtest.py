#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用真实快照运行回测"""

import sys
sys.path.append('E:/MyQuantTool')

from logic.backtest_framework import BacktestEngine

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000.0)

# 加载真实快照
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
snapshots = engine.load_snapshots_from_dir(snapshot_dir)

if len(snapshots) == 0:
    print("⚠️ 没有找到历史快照")
else:
    print(f"✅ 加载了 {len(snapshots)} 个真实快照")

    # 运行回测（降低最大持仓数到3）
    engine.run_backtest(snapshots, max_positions=3)
    # 打印报告
    engine.print_report()

    # 保存结果
    output_dir = 'E:/MyQuantTool/data/backtest_results_real'
    import os
    os.makedirs(output_dir, exist_ok=True)

    engine.save_trades(f'{output_dir}/trades.csv')
    engine.save_positions(f'{output_dir}/positions.csv')

    print(f"\n📁 回测结果已保存: {output_dir}")