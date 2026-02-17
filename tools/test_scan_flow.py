#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试完整的扫描流程
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.per_day_tick_runner import PerDayTickRunner
from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
import pandas as pd

def test_full_scan():
    print("🔍 测试完整扫描流程")
    print("=" * 50)
    
    # 模拟scan_signal_density函数中的逻辑
    stocks = ['300997.SZ']
    dates = ['20251114']
    params_list = [{'volatility_threshold': 0.05, 'volume_surge': 1.2, 'breakout_strength': 0.005, 'min_history_points': 30}]

    results = []
    for stock in stocks:
        for date in dates:
            for param_idx, params in enumerate(params_list):
                try:
                    strategy = HalfwayTickStrategy(params)
                    runner = PerDayTickRunner(
                        stock_code=stock,
                        trade_date=date,
                        strategy=strategy
                    )
                    
                    # 运行策略获取信号
                    signals = runner.run()
                    
                    # 现在tick_count已经通过run()方法设置
                    tick_count = runner.tick_count
                    
                    param_desc = f"vol_{params['volatility_threshold']}_vol_surge_{params['volume_surge']}_breakout_{params['breakout_strength']}"
                    result = {
                        'stock_code': stock,
                        'trade_date': date,
                        'param_id': param_idx,
                        'param_desc': param_desc,
                        'total_signals': len(signals),
                        'tick_count': tick_count,
                        'error': None  # 确保所有结果都有error字段
                    }
                    results.append(result)
                    print(f"✅ 添加结果: 信号数={len(signals)}, Tick数={tick_count}")
                    
                except Exception as e:
                    param_desc = f"vol_{params['volatility_threshold']}_vol_surge_{params['volume_surge']}_breakout_{params['breakout_strength']}"
                    result = {
                        'stock_code': stock,
                        'trade_date': date,
                        'param_id': param_idx,
                        'param_desc': param_desc,
                        'total_signals': 0,
                        'tick_count': 0,
                        'error': str(e)
                    }
                    results.append(result)
                    print(f"❌ 异常结果: {e}")

    print(f"\n📊 最终结果字典结构:")
    for i, res in enumerate(results):
        print(f"  结果 {i+1}: {list(res.keys())}")

    # 现在测试analyze_scan_results函数中的逻辑
    df = pd.DataFrame(results)
    print(f'\n📋 DataFrame列名: {df.columns.tolist()}')
    print('DataFrame:')
    print(df)

    # 测试出错的语句
    total_scans = len(df)
    successful_scans = len(df[df['tick_count'] > 0])
    scans_with_signals = len(df[df['total_signals'] > 0])

    print(f'\n✅ 统计结果:')
    print(f'  总扫描次数: {total_scans}')
    print(f'  成功获取Tick数据: {successful_scans}')
    print(f'  有Halfway信号: {scans_with_signals}')

if __name__ == "__main__":
    test_full_scan()