#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行为回放回测执行脚本
CTO指令：验证"维持能力"特征的历史表现

执行流程：
1. 从research_labels_v2.json加载verified样本
2. 运行BehaviorReplayEngine回测
3. 生成特征表现统计报告
4. 输出给strategy_params.json的参数建议
"""

import sys
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.backtest.behavior_replay_engine import BehaviorReplayEngine


def load_verified_samples(config_path: Path) -> list:
    """加载verified样本列表"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    samples = []
    for stock in config.get('samples', []):
        code = stock['code']
        name = stock['name']
        for date_info in stock.get('dates', []):
            if isinstance(date_info, dict) and date_info.get('verified', False):
                samples.append((code, name, date_info['date'], date_info['label']))
    
    return samples


def run_backtest_verified():
    """运行verified样本回测"""
    print("\n" + "="*80)
    print("Verified样本行为回放回测")
    print("="*80 + "\n")
    
    # 1. 加载样本
    config_path = PROJECT_ROOT / "data" / "wanzhu_data" / "research_labels_v2.json"
    samples = load_verified_samples(config_path)
    
    print(f"加载 {len(samples)} 个verified样本")
    
    # 按股票分组
    stock_dates = {}
    for code, name, date, label in samples:
        if code not in stock_dates:
            stock_dates[code] = {'name': name, 'dates': [], 'labels': []}
        stock_dates[code]['dates'].append(date)
        stock_dates[code]['labels'].append(label)
    
    print(f"涉及 {len(stock_dates)} 只股票")
    for code, info in stock_dates.items():
        print(f"  {code} {info['name']}: {len(info['dates'])}个样本")
    
    # 2. 创建回测引擎
    engine = BehaviorReplayEngine(
        initial_capital=1000000.0,
        max_positions=3,
        position_pct_per_trade=0.3,
        sustain_threshold=2.0  # 维持能力阈值：价格保持在entry_price*0.98以上
    )
    
    # 3. 运行回测
    stock_list = [(code, info['name']) for code, info in stock_dates.items()]
    
    # 确定时间范围
    all_dates = [date for code, info in stock_dates.items() for date in info['dates']]
    start_date = min(all_dates)
    end_date = max(all_dates)
    
    print(f"\n回测时间范围: {start_date} 至 {end_date}")
    print("="*80 + "\n")
    
    results = engine.replay_universe(stock_list, start_date, end_date)
    
    # 4. 生成报告
    output_dir = PROJECT_ROOT / "data" / "backtest_results"
    engine.generate_report(output_dir)
    
    # 5. 输出参数建议
    print("\n" + "="*80)
    print("Strategy Params参数建议（基于回测统计）")
    print("="*80)
    
    # 分析维持能力阈值
    stats_df = engine.analyze_features()
    if not stats_df.empty:
        print("\n维持能力阈值建议:")
        print("-" * 60)
        
        for _, row in stats_df.iterrows():
            if 'sustain_ability' in row['feature']:
                threshold = row['feature'].split('>')[1]
                print(f"  sustain_ability > {threshold}分钟:")
                print(f"    胜率: {row['win_rate']}, 平均盈亏: {row['avg_pnl']}, 样本数: {row['samples']}")
        
        print("\n建议策略参数:")
        print("-" * 60)
        
        # 找到最佳阈值（胜率>60%且样本数>10）
        best_rows = stats_df[
            (stats_df['feature'].str.contains('sustain_ability')) &
            (stats_df['samples'].astype(int) > 10)
        ]
        
        if not best_rows.empty:
            best = best_rows.iloc[-1]  # 取最高阈值
            print(f"  SUSTAIN_ABILITY_THRESHOLD: {best['feature'].split('>')[1]}  # 胜率{best['win_rate']}")
    
    print("\n" + "="*80)
    print("⚠️  重要提示:")
    print("  以上参数建议仅供研究参考，未经小样本实盘验证")
    print("  禁止直接写入strategy_params.json")
    print("  Phase 2需要小样本实盘验证(1-2周观察期)")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_backtest_verified()
