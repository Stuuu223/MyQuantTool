#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试从QMT获取市值数据
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from xtquant import xtdata

print("=" * 80)
print("🔍 测试从QMT获取市值数据")
print("=" * 80)

# 测试几只股票
test_codes = ['000001.SZ', '600000.SH', '000002.SZ']

print(f"\n📋 测试股票: {test_codes}\n")

# 方法1: 从 tick 数据获取
print("方法1: 从 tick 数据获取")
print("-" * 80)

try:
    tick_data = xtdata.get_full_tick(test_codes)
    
    for code in test_codes:
        if code in tick_data:
            tick = tick_data[code]
            market_cap = (
                tick.get('circulatingMarketCap') or 
                tick.get('SH_FLOAT_VAL') or 
                tick.get('FLOAT_VAL') or 
                0
            )
            
            print(f"{code}:")
            print(f"  lastPrice: {tick.get('lastPrice', 0)}")
            print(f"  circulatingMarketCap: {tick.get('circulatingMarketCap', 0)}")
            print(f"  SH_FLOAT_VAL: {tick.get('SH_FLOAT_VAL', 0)}")
            print(f"  FLOAT_VAL: {tick.get('FLOAT_VAL', 0)}")
            print(f"  → 市值: {market_cap/1e8:.2f} 亿\n")
        else:
            print(f"{code}: 未获取到数据\n")
            
except Exception as e:
    print(f"❌ 获取 tick 数据失败: {e}\n")

# 方法2: 从 get_market_data 获取
print("方法2: 从 get_market_data 获取")
print("-" * 80)

try:
    financial_data = xtdata.get_market_data(
        field_list=['SH_FLOAT_VAL', 'FLOAT_VAL'],
        stock_list=test_codes,
        period='1d',
        start_time='',
        end_time='',
        dividend_type='none'
    )
    
    for code in test_codes:
        if code in financial_data:
            data = financial_data[code]
            market_cap = (
                data.get('SH_FLOAT_VAL') or 
                data.get('FLOAT_VAL') or 
                0
            )
            
            print(f"{code}:")
            print(f"  SH_FLOAT_VAL: {data.get('SH_FLOAT_VAL', 0)}")
            print(f"  FLOAT_VAL: {data.get('FLOAT_VAL', 0)}")
            print(f"  → 市值: {market_cap/1e8:.2f} 亿\n")
        else:
            print(f"{code}: 未获取到数据\n")
            
except Exception as e:
    print(f"❌ 获取 market_data 失败: {e}\n")

print("=" * 80)
print("✅ 测试完成")
print("=" * 80)