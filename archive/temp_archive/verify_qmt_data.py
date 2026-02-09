#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证 QMT 下载数据"""

import sys
sys.path.append('E:/MyQuantTool')

from xtquant import xtdata
from logic.code_converter import CodeConverter

# 测试股票
test_stocks = ["600519.SH", "000001.SZ", "600000.SH"]
periods = ["1d", "1m", "5m"]

code_converter = CodeConverter()

print("=" * 60)
print("验证 QMT 下载数据")
print("=" * 60)

for stock_code in test_stocks:
    qmt_code = code_converter.to_qmt(stock_code)
    print(f"\n📊 股票: {stock_code} (QMT: {qmt_code})")
    print("-" * 60)
    
    for period in periods:
        try:
            # 读取本地数据
            data = xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[qmt_code],
                period=period,
                start_time='20240101',
                end_time='20251231',
                count=-1
            )
            
            if data and qmt_code in data:
                df = data[qmt_code]
                print(f"  ✅ {period}: {len(df)} 条记录")
                
                if len(df) > 0:
                    # 显示时间范围
                    print(f"     时间范围: {df.iloc[0]['time']} ~ {df.iloc[-1]['time']}")
                    # 显示最新数据
                    print(f"     最新价格: {df.iloc[-1]['close']:.2f}")
            else:
                print(f"  ❌ {period}: 无数据")
        except Exception as e:
            print(f"  ❌ {period}: 读取失败 - {e}")

print("\n" + "=" * 60)