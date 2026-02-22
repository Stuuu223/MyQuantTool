#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查1月26日时间分布
"""

from xtquant import xtdata
import pandas as pd

print('检查300017.SZ 2026-01-26时间分布...')

result = xtdata.get_local_data(
    field_list=['time', 'volume', 'lastPrice'],
    stock_list=['300017.SZ'],
    period='tick',
    start_time='20260126',
    end_time='20260126'
)

if result and '300017.SZ' in result:
    df = result['300017.SZ']
    df['dt'] = pd.to_datetime(df['time'], unit='ms')
    
    print(f'总数据条数: {len(df)}')
    print(f'时间范围: {df["dt"].min()} ~ {df["dt"].max()}')
    
    # 按小时统计
    df['hour'] = df['dt'].dt.hour
    df['minute'] = df['dt'].dt.minute
    
    hourly = df.groupby('hour').size()
    print(f'\n每小时数据条数:')
    for hour, count in hourly.items():
        print(f'  {hour:02d}:00 - {count:4d}条')
    
    # 检查09:30数据
    morning_0930 = df[(df['hour'] == 9) & (df['minute'] == 30)]
    print(f'\n09:30数据条数: {len(morning_0930)}')
    if len(morning_0930) > 0:
        print(f'09:30时间范围: {morning_0930["dt"].min()} ~ {morning_0930["dt"].max()}')
    
    # 打印前10条
    print(f'\n前10条数据:')
    for i in range(min(10, len(df))):
        print(f'  {df["dt"].iloc[i]} price={df["lastPrice"].iloc[i]}')
