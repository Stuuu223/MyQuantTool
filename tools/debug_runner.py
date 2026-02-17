#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试信号密度扫描工具
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


def debug_runner():
    """
    调试runner的属性
    """
    print("🔍 调试PerDayTickRunner属性")
    print("=" * 50)
    
    # 创建一个测试实例
    params = {'volatility_threshold': 0.05, 'volume_surge': 1.2, 'breakout_strength': 0.005, 'min_history_points': 30}
    strategy = HalfwayTickStrategy(params)
    runner = PerDayTickRunner(
        stock_code="300997.SZ",
        trade_date="20251114",  # 使用已知有数据的日期
        strategy=strategy
    )
    
    print("运行前runner属性:")
    for attr in dir(runner):
        if not attr.startswith('_'):
            try:
                value = getattr(runner, attr)
                if not callable(value):
                    print(f"  {attr}: {value}")
            except:
                print(f"  {attr}: <无法获取>")
    
    # 运行回放
    signals = runner.run()
    
    print("\n运行后runner属性:")
    for attr in dir(runner):
        if not attr.startswith('_'):
            try:
                value = getattr(runner, attr)
                if not callable(value):
                    print(f"  {attr}: {value}")
            except:
                print(f"  {attr}: <无法获取>")
    
    print(f"\n信号数量: {len(signals)}")
    print(f"Tick数量: {runner.tick_count}")


if __name__ == "__main__":
    debug_runner()