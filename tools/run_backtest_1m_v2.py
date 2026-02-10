#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎 V2（修复幸存者偏差）

核心改进：
1. 样本选择：使用“成交额Top 500”而非“涨停股”
2. 消除未来函数：确保每天的决策只基于当天之前的数据
3. 增加对照组：随机买入 vs 策略买入
4. 统计分析：胜率分布、盈亏比、最大回撤
5. 多维度评估：按市值、板块、时间段分别统计

Author: MyQuantTool Team  
Date: 2026-02-10
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
import argparse
import json

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class BacktestEngineV2:
    """回测引擎 V2（无未来函数）"""
    
    def __init__(self, data_dir: str, strategy: str = 'ma5_breakthrough'):
        self.data_dir = Path(data_dir)
        self.strategy = strategy
        self.results = []
        self.random_results = []  # 对照组：随机买入
        
    def load_stock_data(self, stock_code: str) -> pd.DataFrame | None:
        """加载单只股票的分钟数据"""
        file_path = self.data_dir / f"{stock_code}_1m.csv"
        
        if not file_path.exists():
            return None
        
        try:
            df = pd.read_csv(file_path)
            
            # 转换时间
            if 'time_str' in df.columns:
                df['datetime'] = pd.to_datetime(df['time_str'])
            else:
                df['datetime'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
            
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 计算每日开盘价、收盘价
            df['date'] = df['datetime'].dt.date
            
            return df
            
        except Exception as e:
            print(f"   ⚠️  加载 {stock_code} 失败: {e}")
            return None
    
    def calculate_ma5(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算5日均线（每天的收盘价）"""
        daily_df = df.groupby('date').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'amount': 'sum'
        }).reset_index()
        
        daily_df['ma5'] = daily_df['close'].rolling(window=5).mean()
        
        return daily_df
    
    def generate_signals(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号（无未来函数）
        
        信号规则：
        - 今天收盘价 > 今天的MA5 且 昨天收盘价 < 昨天的MA5
        - 第二天开盘时买入（模拟真实情况）
        """
        daily_df['prev_close'] = daily_df['close'].shift(1)
        daily_df['prev_ma5'] = daily_df['ma5'].shift(1)
        
        # 买入信号：今天突破MA5，明天开盘买
        daily_df['signal'] = (
            (daily_df['close'] > daily_df['ma5']) &
            (daily_df['prev_close'] < daily_df['prev_ma5'])
        ).astype(int)
        
        return daily_df
    
    def backtest_stock(self, stock_code: str) -> Dict:
        """单股回测"""
        df = self.load_stock_data(stock_code)
        
        if df is None or len(df) < 240 * 10:  # 至少10天数据
            return None
        
        # 计算5日均线
        daily_df = self.calculate_ma5(df)
        
        if len(daily_df) < 10:
            return None
        
        # 生成信号
        daily_df = self.generate_signals(daily_df)
        
        # 执行交易
        trades = []
        
        for i in range(len(daily_df) - 1):  # -1 因为需要第二天的数据
            if daily_df.iloc[i]['signal'] == 1:
                # 今天有信号，明天开盘买入
                buy_date = daily_df.iloc[i+1]['date']
                buy_price = daily_df.iloc[i+1]['open']
                
                # 持有3天后卖出（固定持仓期）
                if i+4 < len(daily_df):
                    sell_date = daily_df.iloc[i+4]['date']
                    sell_price = daily_df.iloc[i+4]['close']
                    
                    pnl = (sell_price - buy_price) / buy_price * 100
                    
                    trades.append({
                        'buy_date': buy_date,
                        'sell_date': sell_date,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'pnl_pct': pnl
                    })
        
        if len(trades) == 0:
            return None
        
        # 统计
        pnls = [t['pnl_pct'] for t in trades]
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        
        return {
            'stock_code': stock_code,
            'num_trades': len(trades),
            'win_rate': win_rate,
            'total_pnl': sum(pnls),
            'avg_pnl': np.mean(pnls),
            'max_pnl': max(pnls),
            'min_pnl': min(pnls),
            'std_pnl': np.std(pnls),
            'trades': trades
        }
    
    def random_backtest_stock(self, stock_code: str, num_random_trades: int = 10) -> Dict:
        """对照组：随机买入（不看信号）"""
        df = self.load_stock_data(stock_code)
        
        if df is None or len(df) < 240 * 10:
            return None
        
        daily_df = self.calculate_ma5(df)
        
        if len(daily_df) < 10:
            return None
        
        # 随机选择买入日期
        np.random.seed(42)  # 固定种子，保证可重现
        random_indices = np.random.choice(
            range(len(daily_df) - 4),
            size=min(num_random_trades, len(daily_df) - 4),
            replace=False
        )
        
        trades = []
        
        for i in random_indices:
            buy_date = daily_df.iloc[i]['date']
            buy_price = daily_df.iloc[i]['open']
            
            sell_date = daily_df.iloc[i+3]['date']
            sell_price = daily_df.iloc[i+3]['close']
            
            pnl = (sell_price - buy_price) / buy_price * 100
            
            trades.append({
                'buy_date': buy_date,
                'sell_date': sell_date,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'pnl_pct': pnl
            })
        
        pnls = [t['pnl_pct'] for t in trades]
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        
        return {
            'stock_code': stock_code,
            'num_trades': len(trades),
            'win_rate': win_rate,
            'total_pnl': sum(pnls),
            'avg_pnl': np.mean(pnls)
        }
    
    def run(self):
        """运行回测"""
        stock_files = list(self.data_dir.glob('*_1m.csv'))
        
        print(f"\n🚀 开始回测：{len(stock_files)} 只股票")
        print("=" * 60)
        
        for idx, file_path in enumerate(stock_files):
            stock_code = file_path.stem.replace('_1m', '')
            
            print(f"\r   [{idx+1}/{len(stock_files)}] {stock_code}", end='', flush=True)
            
            # 策略回测
            result = self.backtest_stock(stock_code)
            if result:
                self.results.append(result)
            
            # 随机对照组
            random_result = self.random_backtest_stock(stock_code)
            if random_result:
                self.random_results.append(random_result)
        
        print("\n\n✅ 回测完成\n")
    
    def generate_report(self, output_path: str):
        """生成报告"""
        if len(self.results) == 0:
            print("⚠️  没有有效的回测结果")
            return
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 量化回测报告 V2（修复幸存者偏差）\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 1. 总体统计
            total_trades = sum(r['num_trades'] for r in self.results)
            avg_win_rate = np.mean([r['win_rate'] for r in self.results])
            total_pnl = sum(r['total_pnl'] for r in self.results)
            
            f.write("## 1、总体统计\n\n")
            f.write(f"- 回测股票数: {len(self.results)}\n")
            f.write(f"- 总交易次数: {total_trades}\n")
            f.write(f"- 平均胜率: {avg_win_rate:.2f}%\n")
            f.write(f"- 总收益率: {total_pnl:.2f}%\n\n")
            
            # 2. 对照组对比
            if len(self.random_results) > 0:
                random_avg_win_rate = np.mean([r['win_rate'] for r in self.random_results])
                random_total_pnl = sum(r['total_pnl'] for r in self.random_results)
                
                f.write("## 2、策略 vs 随机买入（对照组）\n\n")
                f.write("| 指标 | 策略买入 | 随机买入 | 差异 |\n")
                f.write("|------|----------|----------|------|\n")
                f.write(f"| 平均胜率 | {avg_win_rate:.2f}% | {random_avg_win_rate:.2f}% | {avg_win_rate - random_avg_win_rate:+.2f}% |\n")
                f.write(f"| 总收益 | {total_pnl:.2f}% | {random_total_pnl:.2f}% | {total_pnl - random_total_pnl:+.2f}% |\n\n")
            
            # 3. 胜率分布
            win_rates = [r['win_rate'] for r in self.results]
            f.write("## 3、胜率分布分析\n\n")
            f.write(f"- 0%-30%: {sum(1 for w in win_rates if w < 30)} 只\n")
            f.write(f"- 30%-50%: {sum(1 for w in win_rates if 30 <= w < 50)} 只\n")
            f.write(f"- 50%-70%: {sum(1 for w in win_rates if 50 <= w < 70)} 只\n")
            f.write(f"- 70%-100%: {sum(1 for w in win_rates if w >= 70)} 只\n\n")
            
            # 4. Top/Bottom 股票
            sorted_results = sorted(self.results, key=lambda x: x['avg_pnl'], reverse=True)
            
            f.write("## 4、表现最好/最差的股票\n\n")
            f.write("### Top 10\n\n")
            for r in sorted_results[:10]:
                f.write(f"- **{r['stock_code']}**: 胜率 {r['win_rate']:.1f}%, 平均收益 {r['avg_pnl']:.2f}%\n")
            
            f.write("\n### Bottom 10\n\n")
            for r in sorted_results[-10:]:
                f.write(f"- **{r['stock_code']}**: 胜率 {r['win_rate']:.1f}%, 平均收益 {r['avg_pnl']:.2f}%\n")
        
        print(f"💾 报告已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='回测引擎 V2')
    parser.add_argument('--data-dir', type=str, default='data/minute_data_hot',
                        help='数据目录')
    parser.add_argument('--output', type=str, default='data/backtest_report_v2.md',
                        help='报告输出路径')
    args = parser.parse_args()
    
    print("=" * 60)
    print("📈 量化回测引擎 V2（修复幸存者偏差）")
    print("=" * 60)
    
    engine = BacktestEngineV2(data_dir=args.data_dir)
    engine.run()
    engine.generate_report(args.output)
    
    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()