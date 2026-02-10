#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速诊断QMT竞价数据格式

Author: MyQuantTool Team
Date: 2026-02-10
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from xtquant import xtdata

# 获取几只热门股票的Tick数据
test_codes = ['000001.SZ', '600000.SH', '300059.SZ']

print("=" * 60)
print("🔍 诊断QMT竞价数据格式")
print("=" * 60)

tick_data = xtdata.get_full_tick(test_codes)

for code in test_codes:
    tick = tick_data.get(code, {})
    print(f"\n📊 {code}:")
    print(f"   数据类型: {type(tick)}")
    
    if isinstance(tick, dict) and tick:
        print(f"   所有字段: {list(tick.keys())}")
        
        # 打印关键字段
        print(f"   lastPrice: {tick.get('lastPrice', 'N/A')}")
        print(f"   lastClose: {tick.get('lastClose', 'N/A')}")
        print(f"   amount: {tick.get('amount', 'N/A')}")
        print(f"   volume: {tick.get('volume', 'N/A')}")
        print(f"   totalVolume: {tick.get('totalVolume', 'N/A')}")
        print(f"   total_volume: {tick.get('total_volume', 'N/A')}")
        print(f"   turnoverVolume: {tick.get('turnoverVolume', 'N/A')}")
        print(f"   turnover_volume: {tick.get('turnover_volume', 'N/A')}")
        
        # 尝试其他可能的字段
        print(f"   其他字段:")
        for key in ['auctionVolume', 'auction_volume', 'bidVolume', 'askVolume', 'bid_vol', 'ask_vol']:
            if key in tick:
                print(f"     {key}: {tick[key]}")
    else:
        print(f"   ❌ 无数据")

print("\n" + "=" * 60)