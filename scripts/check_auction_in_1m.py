#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查1分钟K线数据是否包含竞价时间段"""

import pandas as pd

df = pd.read_csv('data/minute_data/000001.SZ_1m.csv')

print('时间范围:')
print(f'开始: {df["time_str"].min()}')
print(f'结束: {df["time_str"].max()}')
print(f'总行数: {len(df)}')

print('\n前5行:')
print(df[['time_str', 'volume']].head())

print('\n检查竞价时间段数据 (09:15-09:30):')
auction_data = df[df['time_str'].str.contains('09:1[5-9]')]
print(f'竞价时间段数据行数: {len(auction_data)}')

if len(auction_data) > 0:
    print('\n竞价时间段数据示例:')
    print(auction_data[['time_str', 'volume']])
else:
    print('❌ 没有竞价时间段数据')