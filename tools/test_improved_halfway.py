#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试优化后的Halfway策略
使用更宽松的参数来验证改进
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.per_day_tick_runner import PerDayTickRunner
from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy


def test_improved_halfway():
    """
    测试改进后的Halfway策略
    """
    print("=" * 80)
    print("🧪 测试改进后的Halfway策略")
    print("=" * 80)
    
    # 使用更宽松的参数
    test_params = {
        'volatility_threshold': 0.05,  # 提高波动率阈值，降低平台要求
        'volume_surge': 1.2,          # 降低量能放大要求
        'breakout_strength': 0.003,   # 降低突破强度要求
        'min_history_points': 30      # 减少最小历史点数要求
    }
    
    print(f"📋 测试参数: {test_params}")
    
    # 测试股票和日期
    test_stock = "300997.SZ"
    test_date = "20251114"
    
    print(f"📊 测试 {test_stock} {test_date}")
    print("-" * 60)
    
    # 创建策略实例
    strategy = HalfwayTickStrategy(test_params)
    
    runner = PerDayTickRunner(
        stock_code=test_stock,
        trade_date=test_date,
        strategy=strategy
    )
    
    # 运行回放
    signals = runner.run()
    
    # 获取统计信息
    stats = runner.get_statistics()
    
    print(f"📈 信号统计:")
    print(f"   总信号数: {stats['total_signals']}")
    print(f"   1分钟胜率: {stats['win_rate']['1min']:.2%} ({stats['winning_counts']['1min']}/{stats['total_returns']['1min']})")
    print(f"   5分钟胜率: {stats['win_rate']['5min']:.2%} ({stats['winning_counts']['5min']}/{stats['total_returns']['5min']})")
    print(f"   10分钟胜率: {stats['win_rate']['10min']:.2%} ({stats['winning_counts']['10min']}/{stats['total_returns']['10min']})")
    print(f"   1分钟平均收益率: {stats['avg_return']['1min']:.4f}")
    print(f"   5分钟平均收益率: {stats['avg_return']['5min']:.4f}")
    print(f"   10分钟平均收益率: {stats['avg_return']['10min']:.4f}")
    
    if stats['total_signals'] > 0:
        print(f"\n🎯 详细信号信息:")
        for i, signal in enumerate(signals):
            from datetime import datetime
            signal_time = datetime.fromtimestamp(signal['time']/1000).strftime('%H:%M:%S')
            print(f"   信号 {i+1}: {signal_time}")
            print(f"      价格: {signal['price']:.2f}")
            print(f"      平台高点: {signal['extra_info'].get('platform_high', 'N/A')}")
            print(f"      当前波动率: {signal['extra_info'].get('current_volatility', 0):.6f}")
            print(f"      量能放大: {signal['extra_info'].get('current_volume_surge', 0):.2f}")
            print(f"      突破强度: {signal['extra_info'].get('breakout_strength', 0):.6f}")
    else:
        print(f"\n⚠️  没有触发任何信号")
        print(f"   可能原因：")
        print(f"   - 股票在该日期未出现符合条件的半路形态")
        print(f"   - 参数仍需进一步调整")
        print(f"   - 策略逻辑需要进一步优化")
    
    print("\n✅ 改进策略测试完成")
    print("=" * 80)
    
    return signals, stats


if __name__ == "__main__":
    signals, stats = test_improved_halfway()