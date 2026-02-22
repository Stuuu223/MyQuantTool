#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断BacktestEngine问题"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.strategies.backtest_engine import BacktestEngine
from logic.data_providers.data_manager import DataManager

print("="*60)
print("诊断BacktestEngine数据获取")
print("="*60)

# 测试1: DataManager能否初始化
print("\n1. 测试DataManager初始化...")
try:
    db = DataManager()
    print("✅ DataManager初始化成功")
    db.close()
except Exception as e:
    print(f"❌ DataManager初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试2: 获取单只股票历史数据
print("\n2. 测试获取历史数据...")
test_codes = ['600589.SH', '603533.SH', '300182.SZ']

try:
    db = DataManager()
    for code in test_codes:
        print(f"\n  尝试获取 {code}...")
        df = db.get_history_data(code)
        if df is not None and not df.empty:
            print(f"  ✅ 成功: {len(df)} 条记录, 日期范围 {df.index[0]} ~ {df.index[-1]}")
        else:
            print(f"  ⚠️ 无数据")
    db.close()
except Exception as e:
    print(f"❌ 获取历史数据失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("诊断完成")
print("="*60)
