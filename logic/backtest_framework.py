#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日线回测框架 - 基于历史快照重建
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd


class BacktestPosition:
    """持仓信息"""
    def __init__(self, code: str, entry_price: float, entry_date: str, quantity: int = 100):
        self.code = code
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.quantity = quantity
        self.exit_price = None
        self.exit_date = None
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.holding_days = 0

    def close(self, exit_price: float, exit_date: str):
        """平仓"""
        self.exit_price = exit_price
        self.exit_date = exit_date
        self.pnl = (exit_price - self.entry_price) * self.quantity
        self.pnl_pct = (exit_price - self.entry_price) / self.entry_price * 100

        # 计算持仓天数
        entry_dt = datetime.strptime(self.entry_date, '%Y%m%d')
        exit_dt = datetime.strptime(exit_date, '%Y%m%d')
        self.holding_days = (exit_dt - entry_dt).days

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'code': self.code,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date,
            'exit_price': self.exit_price,
            'exit_date': self.exit_date,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'holding_days': self.holding_days
        }


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: List[BacktestPosition] = []
        self.closed_positions: List[BacktestPosition] = []
        self.trades = []
        self.daily_equity = []
        
        # 添加冷却期跟踪（防止反复交易）
        self.cooldown_stocks = {}  # {code: cooldown_end_date}
        self.COOLDOWN_DAYS = 7  # 冷却7天

    def load_snapshot(self, snapshot_path: str) -> Optional[Dict]:
        """
        加载历史快照

        Args:
            snapshot_path: 快照文件路径

        Returns:
            快照数据字典
        """
        if not os.path.exists(snapshot_path):
            print(f"⚠️ 快照文件不存在: {snapshot_path}")
            return None

        with open(snapshot_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data

    def load_snapshots_from_dir(self, snapshot_dir: str) -> List[Dict]:
        """
        从目录加载所有快照

        Args:
            snapshot_dir: 快照目录

        Returns:
            快照列表（按日期排序）
        """
        snapshots = []

        if not os.path.exists(snapshot_dir):
            print(f"⚠️ 快照目录不存在: {snapshot_dir}")
            return snapshots

        for filename in os.listdir(snapshot_dir):
            if filename.startswith('full_market_snapshot_') and filename.endswith('_rebuild.json'):
                filepath = os.path.join(snapshot_dir, filename)
                snapshot = self.load_snapshot(filepath)
                if snapshot:
                    snapshots.append(snapshot)

        # 按日期排序
        snapshots.sort(key=lambda x: x['trade_date'])

        return snapshots

    def should_buy(self, stock_data: Dict) -> bool:
        """
        买入信号判断（资金猛攻版）

        Args:
            stock_data: 股票数据（来自快照，包含 decision_tag、risk_score）

        Returns:
            是否买入
        """
        code = stock_data['code']
        
        # 检查冷却期
        if code in self.cooldown_stocks:
            cooldown_end = self.cooldown_stocks[code]
            current_date = stock_data['trade_date']
            if current_date <= cooldown_end:
                return False  # 还在冷却期
        
        # 计算资金猛攻强度评分
        attack_score = self._calculate_attack_intensity(stock_data)
        
        # 买入条件（资金猛攻版）：
        # 1. 资金猛攻强度 > 30分
        # 2. 风险分数 < 0.7
        # 3. 不限制必须在机会池或观察池（从所有池子里找资金猛攻的票）
        
        decision_tag = stock_data.get('decision_tag', None)
        risk_score = stock_data.get('risk_score', 1.0)
        
        # 只买资金猛攻的票
        if attack_score < 30:
            return False
        
        # 风险不能太高
        if risk_score >= 0.7:
            return False
        
        return True
    
    def _calculate_attack_intensity(self, stock_data: Dict) -> float:
        """
        资金猛攻强度评分（0-100分）
        权重：主力流入50% + 涨幅30% + 成交额20%
        """
        flow = stock_data['flow_data']
        price = stock_data['price_data']
        
        # 主力流入评分（100万=20分，500万=100分）
        main_inflow = flow.get('main_net_inflow', 0)
        flow_score = min(main_inflow / 1000000 * 20, 100)
        
        # 涨幅评分（5%=0分，10%=80分，15%+=100分）
        pct_chg = price['pct_chg']
        if pct_chg < 5:
            pct_score = 0
        elif pct_chg < 10:
            pct_score = pct_chg * 16
        else:
            pct_score = 80 + (pct_chg - 10) * 10
        
        # 成交额评分（越小越容易推动）
        # Tushare的amount单位是千元，需要先转成元，再转成亿
        amount_yi = price['amount'] * 1000 / 1e8
        if amount_yi < 0.05:
            amount_score = 100
        elif amount_yi < 0.1:
            amount_score = 80
        elif amount_yi < 0.3:
            amount_score = 50
        else:
            amount_score = 20
        
        # 综合评分（主力流入50% + 涨幅30% + 成交额20%）
        total_score = flow_score * 0.5 + pct_score * 0.3 + amount_score * 0.2
        
        return total_score

    def should_sell(self, position: BacktestPosition, stock_data: Dict) -> bool:
        """
        卖出信号判断（短线风格）

        Args:
            position: 持仓
            stock_data: 当前股票数据（来自快照）

        Returns:
            是否卖出
        """
        # 计算当前盈亏
        current_price = stock_data['price_data']['close']
        pnl_pct = (current_price - position.entry_price) / position.entry_price * 100

        # 短线卖出条件（快进快出）：
        # 1. 硬止损：亏损超过 2%
        # 2. 硬止盈：盈利超过 5%（短线止盈）
        # 3. 持仓超过 3 天：不管涨跌都卖（短线不磨叽）
        # 4. 风险翻高：风险分数 >= 0.8
        # 5. 主力大幅流出：持有超过 1 天且主力流出

        risk_score = stock_data.get('risk_score', 0.0)
        trap_signals = stock_data.get('trap_signals', [])
        flow_data = stock_data.get('flow_data', {})
        main_net_inflow = flow_data.get('main_net_inflow', 0)

        # 硬止损（更严格）
        if pnl_pct <= -2:
            return True

        # 硬止盈（更快）
        if pnl_pct >= 5:
            return True

        # 持仓时间限制（3天强制卖出）
        if position.holding_days >= 3:
            return True

        # 风险翻高
        if risk_score >= 0.8:
            return True

        # 诱多信号
        if len(trap_signals) > 0:
            return True

        # 主力大幅流出（1天就卖）
        if main_net_inflow < 0 and position.holding_days >= 1:
            return True

        return False

    def run_backtest(self, snapshots: List[Dict], max_positions: int = 5):
        """
        运行回测

        Args:
            snapshots: 历史快照列表
            max_positions: 最大持仓数
        """
        print("=" * 60)
        print("开始回测")
        print("=" * 60)
        print(f"初始资金: {self.initial_capital:,.2f}")
        print(f"快照数量: {len(snapshots)}")
        print(f"最大持仓: {max_positions}")
        print("=" * 60)

        for snapshot in snapshots:
            trade_date = snapshot['trade_date']
            opportunities = snapshot.get('results', {}).get('opportunities', [])

            # 记录每日权益
            daily_value = self.current_capital
            for pos in self.positions:
                # 假设当日价格就是 close
                current_price = self._get_stock_price(opportunities, pos.code, trade_date)
                if current_price:
                    daily_value += (current_price - pos.entry_price) * pos.quantity

            self.daily_equity.append({
                'date': trade_date,
                'equity': daily_value
            })

            # 卖出逻辑
            positions_to_close = []
            for pos in self.positions:
                stock_data = self._get_stock_data(opportunities, pos.code)
                if stock_data:
                    current_price = stock_data['price_data']['close']

                    if self.should_sell(pos, stock_data):
                        pos.close(current_price, trade_date)
                        self.closed_positions.append(pos)
                        self.current_capital += pos.pnl
                        positions_to_close.append(pos)
                        
                        # 添加冷却期
                        self.cooldown_stocks[pos.code] = trade_date

                        self.trades.append({
                            'type': 'sell',
                            'code': pos.code,
                            'date': trade_date,
                            'price': current_price,
                            'pnl': pos.pnl,
                            'pnl_pct': pos.pnl_pct
                        })
                    else:
                        # 调试输出（已关闭）
                        pass

            # 移除已平仓的持仓
            for pos in positions_to_close:
                self.positions.remove(pos)

            # 更新持仓天数
            from datetime import datetime
            for pos in self.positions:
                entry_dt = datetime.strptime(pos.entry_date, '%Y%m%d')
                current_dt = datetime.strptime(trade_date, '%Y%m%d')
                pos.holding_days = (current_dt - entry_dt).days

            # 买入逻辑
            if len(self.positions) < max_positions:
                available_slots = max_positions - len(self.positions)

                # 合并所有池子（机会池、观察池、黑名单），从中选资金猛攻的票
                all_candidates = (snapshot['results'].get('opportunities', []) + 
                                   snapshot['results'].get('watchlist', []) +
                                   snapshot['results'].get('blacklist', []))
                
                for stock_data in all_candidates:
                    if available_slots <= 0:
                        break

                    code = stock_data['code']

                    # 检查是否已持仓
                    if any(pos.code == code for pos in self.positions):
                        continue

                    # 检查买入信号
                    if self.should_buy(stock_data):
                        entry_price = stock_data['price_data']['close']
                        position = BacktestPosition(code, entry_price, trade_date)
                        self.positions.append(position)

                        # 扣除资金
                        cost = entry_price * position.quantity
                        self.current_capital -= cost

                        self.trades.append({
                            'type': 'buy',
                            'code': code,
                            'date': trade_date,
                            'price': entry_price
                        })

                        available_slots -= 1

        # 强制平仓所有持仓
        last_date = snapshots[-1]['trade_date'] if snapshots else '20260206'
        last_snapshot = snapshots[-1] if snapshots else None

        for pos in self.positions:
            # 在所有池子里查找股票数据（机会池、观察池、黑名单）
            stock_data = None
            if last_snapshot:
                # 按优先级查找：机会池 > 观察池 > 黑名单
                for pool_name in ['opportunities', 'watchlist', 'blacklist']:
                    pool = last_snapshot['results'].get(pool_name, [])
                    for stock in pool:
                        if stock['code'] == pos.code:
                            stock_data = stock
                            break
                    if stock_data:
                        break

            # 获取实际价格
            if stock_data:
                current_price = stock_data['price_data']['close']
            else:
                # 如果快照里找不到，从Tushare获取当日价格
                try:
                    import tushare as ts
                    api = ts.pro_api('1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b')
                    df = api.daily(ts_code=pos.code, trade_date=last_date)
                    if len(df) > 0:
                        current_price = df.iloc[0]['close']
                    else:
                        current_price = pos.entry_price
                except:
                    current_price = pos.entry_price

            pos.close(current_price, last_date)
            self.closed_positions.append(pos)

            # 返还资金
            self.current_capital += pos.entry_price * pos.quantity + pos.pnl

            self.trades.append({
                'type': 'sell',
                'code': pos.code,
                'date': last_date,
                'price': pos.exit_price,
                'pnl': pos.pnl,
                'pnl_pct': pos.pnl_pct
            })

        self.positions.clear()

        print("=" * 60)
        print("回测完成")
        print("=" * 60)

    def _get_stock_data(self, opportunities: List[Dict], code: str) -> Optional[Dict]:
        """获取股票数据"""
        for stock_data in opportunities:
            if stock_data['code'] == code:
                return stock_data
        return None

    def _get_stock_price(self, opportunities: List[Dict], code: str, trade_date: str) -> Optional[float]:
        """获取股票价格"""
        stock_data = self._get_stock_data(opportunities, code)
        if stock_data:
            return stock_data['price_data']['close']
        return None

    def calculate_metrics(self) -> Dict:
        """
        计算回测指标

        Returns:
            指标字典
        """
        total_trades = len(self.closed_positions)
        if total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'avg_holding_days': 0.0,
                'final_capital': self.current_capital
            }

        # 胜率
        winning_trades = [pos for pos in self.closed_positions if pos.pnl > 0]
        win_rate = len(winning_trades) / total_trades * 100

        # 总收益率
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100

        # 最大回撤
        max_drawdown = self._calculate_max_drawdown()

        # 平均持仓天数
        avg_holding_days = sum(pos.holding_days for pos in self.closed_positions) / total_trades

        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'avg_holding_days': avg_holding_days,
            'final_capital': self.current_capital
        }

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if len(self.daily_equity) < 2:
            return 0.0

        equity_series = pd.DataFrame(self.daily_equity)['equity']
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100

        return abs(drawdown.min())

    def print_report(self):
        """打印回测报告"""
        metrics = self.calculate_metrics()

        print("\n" + "=" * 60)
        print("回测报告")
        print("=" * 60)
        print(f"初始资金: {self.initial_capital:,.2f}")
        print(f"最终资金: {metrics['final_capital']:,.2f}")
        print(f"总收益率: {metrics['total_return']:.2f}%")
        print(f"最大回撤: {metrics['max_drawdown']:.2f}%")
        print(f"总交易数: {metrics['total_trades']}")
        print(f"胜率: {metrics['win_rate']:.2f}%")
        print(f"平均持仓天数: {metrics['avg_holding_days']:.2f}")
        print("=" * 60)

    def save_trades(self, output_path: str):
        """保存交易记录"""
        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ 交易记录已保存: {output_path}")

    def save_positions(self, output_path: str):
        """保存持仓记录"""
        positions_df = pd.DataFrame([pos.to_dict() for pos in self.closed_positions])
        positions_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ 持仓记录已保存: {output_path}")


def main():
    """主函数"""
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=100000.0)

    # 加载快照
    snapshot_dir = 'E:/MyQuantTool/data/rebuild_snapshots'
    snapshots = engine.load_snapshots_from_dir(snapshot_dir)

    if len(snapshots) == 0:
        print("⚠️ 没有找到历史快照，请先执行历史快照重建")
        return

    # 运行回测
    engine.run_backtest(snapshots, max_positions=5)

    # 打印报告
    engine.print_report()

    # 保存结果
    output_dir = 'E:/MyQuantTool/data/backtest_results'
    os.makedirs(output_dir, exist_ok=True)

    engine.save_trades(f'{output_dir}/trades.csv')
    engine.save_positions(f'{output_dir}/positions.csv')


if __name__ == '__main__':
    main()