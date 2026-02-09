#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证回测引擎：运行随机策略作为对照"""

import sys
import random
sys.path.append('E:/MyQuantTool')

from logic.backtest_framework import BacktestEngine

class RandomStrategyEngine(BacktestEngine):
    """随机策略引擎"""

    def should_buy(self, stock_data: dict) -> bool:
        """买入信号：随机选择"""
        # 随机选择5%的股票
        return random.random() < 0.05

    def should_sell(self, position: 'BacktestPosition', stock_data: dict) -> bool:
        """卖出信号：持有3天无条件卖出"""
        return position.holding_days >= 3

# 创建回测引擎
engine = RandomStrategyEngine(initial_capital=100000.0)

# 加载真实快照
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
snapshots = engine.load_snapshots_from_dir(snapshot_dir)

print(f"✅ 加载了 {len(snapshots)} 个真实快照")

# 运行回测
engine.run_backtest(snapshots, max_positions=5)

# 打印报告
engine.print_report()

# 保存结果
output_dir = 'E:/MyQuantTool/data/backtest_results_random'
import os
os.makedirs(output_dir, exist_ok=True)

engine.save_trades(f'{output_dir}/trades.csv')
engine.save_positions(f'{output_dir}/positions.csv')

print(f"\n📁 随机策略结果已保存: {output_dir}")