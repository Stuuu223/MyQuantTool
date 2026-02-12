#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试AkShare数据格式"""

import akshare as ak

code = "002514"
symbol_6 = code  # 6位代码

print(f"正在获取 {code} 的K线数据...")
df = ak.stock_zh_a_hist(symbol=symbol_6, period='daily', start_date='20250101', adjust='qfq')

print(f"\n原始数据形状: {df.shape}")
print(f"列名: {df.columns.tolist()}")
print(f"\n前5行（原始顺序）:")
print(df.head())
print(f"\n后5行（原始顺序）:")
print(df.tail())

# 排序前
print(f"\n排序前，倒数第4行:")
print(df.iloc[-4])
print(f"收盘价: {df.iloc[-4]['收盘']}")

# 排序后
df_sorted = df.sort_values('日期', ascending=True)
print(f"\n排序后，前5行:")
print(df_sorted.head())
print(f"\n排序后，后5行:")
print(df_sorted.tail())
print(f"\n排序后，倒数第4行:")
print(df_sorted.iloc[-4])
print(f"收盘价: {df_sorted.iloc[-4]['收盘']}")

# 计算price_3d_change
current_price = 5.67  # 假设当前价格
ref_close = df_sorted.iloc[-4]['收盘']
price_3d_change = (current_price - ref_close) / ref_close

print(f"\n计算结果:")
print(f"当前价格: {current_price}")
print(f"3天前收盘价: {ref_close}")
print(f"price_3d_change: {price_3d_change:.4f} ({price_3d_change*100:.2f}%)")

# 检查日期
print(f"\n关键日期:")
print(f"最新日期: {df_sorted.iloc[-1]['日期']}")
print(f"倒数第2天: {df_sorted.iloc[-2]['日期']}")
print(f"倒数第3天: {df_sorted.iloc[-3]['日期']}")
print(f"倒数第4天（3天前）: {df_sorted.iloc[-4]['日期']}")