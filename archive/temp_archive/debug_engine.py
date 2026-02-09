#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在正式回测引擎中添加调试信息"""

import sys
sys.path.append('E:/MyQuantTool')

# 修改BacktestEngine，添加调试输出
from logic.backtest_framework import BacktestEngine as BaseEngine

class DebugBacktestEngine(BaseEngine):
    def run_backtest(self, snapshots, max_positions=5):
        """运行回测（带调试信息）"""
        print("=" * 60)
        print("开始回测（调试模式）")
        print("=" * 60)
        print(f"初始资金: {self.initial_capital:,.2f}")
        print(f"快照数量: {len(snapshots)}")
        print(f"最大持仓: {max_positions}")
        print("=" * 60)

        for snapshot in snapshots:
            trade_date = snapshot['trade_date']
            opportunities = snapshot.get('results', {}).get('opportunities', [])

            print(f"\n=== {trade_date} ===")
            print(f"持仓数量: {len(self.positions)}")

            # 卖出逻辑
            positions_to_close = []
            for pos in self.positions:
                stock_data = self._get_stock_data(opportunities, pos.code)
                if stock_data:
                    current_price = stock_data['price_data']['close']
                    should_sell = self.should_sell(pos, stock_data)

                    print(f"  检查卖出 {pos.code}: should_sell={should_sell}, holding_days={pos.holding_days}")

                    if should_sell:
                        pos.close(current_price, trade_date)
                        self.closed_positions.append(pos)
                        self.current_capital += pos.pnl
                        positions_to_close.append(pos)

                        print(f"    → 卖出: 价格={current_price:.2f}, 收益={pos.pnl:.2f}")

            # 移除已平仓的持仓
            for pos in positions_to_close:
                self.positions.remove(pos)

            # 买入逻辑
            if len(self.positions) < max_positions:
                available_slots = max_positions - len(self.positions)

                for stock_data in opportunities:
                    if available_slots <= 0:
                        break

                    code = stock_data['code']

                    # 检查是否已持仓
                    if any(pos.code == code for pos in self.positions):
                        continue

                    # 检查买入信号
                    if self.should_buy(stock_data):
                        entry_price = stock_data['price_data']['close']
                        position = self.BacktestPosition(code, entry_price, trade_date)
                        self.positions.append(position)

                        # 扣除资金
                        cost = entry_price * position.quantity
                        self.current_capital -= cost

                        print(f"  买入 {code}: 价格={entry_price:.2f}, 成本={cost:.2f}")

                        available_slots -= 1

            # 更新持仓天数
            for pos in self.positions:
                from datetime import datetime
                entry_dt = datetime.strptime(pos.entry_date, '%Y%m%d')
                current_dt = datetime.strptime(trade_date, '%Y%m%d')
                pos.holding_days = (current_dt - entry_dt).days

        # 强制平仓
        last_date = snapshots[-1]['trade_date'] if snapshots else '20260206'
        print(f"\n=== 强制平仓 {last_date} ===")
        for pos in self.positions:
            pos.close(pos.entry_price, last_date)
            self.closed_positions.append(pos)
            self.current_capital += pos.entry_price * pos.quantity
            print(f"  强制平仓 {pos.code}: 价格={pos.exit_price:.2f}")

        print("\n" + "=" * 60)
        print("回测完成")
        print("=" * 60)

# 修复BacktestPosition的引用
import types
DebugBacktestEngine.BacktestPosition = BaseEngine.__dict__['BacktestPosition']

# 创建回测引擎
engine = DebugBacktestEngine(initial_capital=100000.0)

# 加载真实快照
snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
snapshots = engine.load_snapshots_from_dir(snapshot_dir)

# 运行回测
engine.run_backtest(snapshots, max_positions=5)

# 打印报告
engine.print_report()