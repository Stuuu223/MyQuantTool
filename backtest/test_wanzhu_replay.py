#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试脚本（5只股票）
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 只测试前5只股票
from backtest.run_wanzhu_behavior_replay import load_wanzhu_stocks, run_wanzhu_behavior_replay, CONFIG

if __name__ == '__main__':
    # 加载所有股票，只取前5只
    all_stocks = load_wanzhu_stocks(CONFIG['wanzhu_csv'])
    test_stocks = all_stocks[:5]
    
    print(f"🧪 快速测试: {len(test_stocks)} 只股票")
    print(f"测试股票: {test_stocks}")
    print(f"日期范围: {CONFIG['start_date']} ~ {CONFIG['end_date']}")
    
    # 运行测试
    results = run_wanzhu_behavior_replay(
        stock_codes=test_stocks,
        start_date=CONFIG['start_date'],
        end_date=CONFIG['end_date']
    )
    
    # 显示结果
    print(f"\n{'='*60}")
    print(f"📊 测试结果摘要")
    print(f"{'='*60}")
    print(f"总信号天数: {results['summary']['total_signals']}")
    print(f"强攻击: {results['summary']['strong_attack_days']}")
    print(f"中攻击: {results['summary']['medium_attack_days']}")
    print(f"弱攻击: {results['summary']['weak_attack_days']}")
    print(f"TRAP过滤: {results['summary']['trap_days']}")
    
    # 显示前3条记录
    print(f"\n前3条记录:")
    for record in results['daily_records'][:3]:
        print(f"  {record['date']} {record['code']}: {record['signals']}, {record['attack_score']}, TRAP={record['is_trap']}")