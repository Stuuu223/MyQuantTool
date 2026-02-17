#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断日期过滤问题"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from logic.data_providers.data_manager import DataManager

print("="*60)
print("诊断日期过滤问题")
print("="*60)

db = DataManager()
code = '600589.SH'

print(f"\n1. 获取 {code} 原始数据...")
df = db.get_history_data(code)
print(f"   数据形状: {df.shape}")
print(f"   索引类型: {type(df.index)}")
print(f"   索引前5个值: {list(df.index[:5])}")
print(f"   列名: {list(df.columns)}")

print(f"\n2. 尝试日期转换...")
try:
    df_copy = df.copy()
    df_copy.index = pd.to_datetime(df_copy.index)
    print(f"   转换后索引类型: {type(df_copy.index)}")
    print(f"   转换后索引前5个值: {list(df_copy.index[:5])}")
except Exception as e:
    print(f"   转换失败: {e}")

print(f"\n3. 检查列中是否有日期信息...")
for col in df.columns:
    if 'date' in col.lower() or 'time' in col.lower():
        print(f"   发现潜在日期列 '{col}': {df[col].iloc[0] if len(df) > 0 else 'N/A'}")

print(f"\n4. 模拟回测日期过滤...")
start_date = '2025-11-01'
end_date = '2026-02-15'

try:
    df_test = df.copy()
    df_test.index = pd.to_datetime(df_test.index)
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    print(f"   过滤前: {len(df_test)} 条")
    df_filtered = df_test[(df_test.index >= start_dt) & (df_test.index <= end_dt)]
    print(f"   过滤后: {len(df_filtered)} 条")
    
    if len(df_filtered) == 0:
        print(f"   所有数据都被过滤掉了！")
        print(f"   数据实际日期范围: {df_test.index.min()} ~ {df_test.index.max()}")
        print(f"   请求的日期范围: {start_dt} ~ {end_dt}")
except Exception as e:
    print(f"   过滤失败: {e}")
    import traceback
    traceback.print_exc()

db.close()
print("\n" + "="*60)
print("诊断完成")
print("="*60)
