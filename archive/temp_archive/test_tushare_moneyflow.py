#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试Tushare moneyflow接口"""

import tushare as ts

# 初始化Tushare
ts_api = ts.pro_api('1430dca9cc3419b91928e162935065bcd3531fa82976fee8355d550b')

# 测试：获取20260206的资金流数据
trade_date = '20260206'

print("=" * 60)
print(f"测试Tushare moneyflow接口 - {trade_date}")
print("=" * 60)

try:
    # 获取前5只股票的资金流（测试）
    test_codes = ['000001.SZ', '000002.SZ', '600000.SH', '600519.SH', '603607.SH']
    
    df = ts_api.moneyflow(trade_date=trade_date)
    
    if df is not None and len(df) > 0:
        print(f"✅ 获取到 {len(df)} 条资金流数据")
        print(f"字段: {list(df.columns)}")
        print("\n前5条数据:")
        print(df.head())
        
        # 检查测试股票
        print("\n测试股票的资金流:")
        for code in test_codes:
            stock_data = df[df['ts_code'] == code]
            if len(stock_data) > 0:
                row = stock_data.iloc[0]
                print(f"{code}: 主力净流入 = {row['buy_elg_vol'] - row['sell_elg_vol']:.2f}")
            else:
                print(f"{code}: 无数据")
    else:
        print(f"❌ 无数据")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)