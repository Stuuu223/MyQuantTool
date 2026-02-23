#!/usr/bin/env python3
"""检查QMT volume字段单位"""

from xtquant import xtdata
import pandas as pd
from datetime import timedelta

# 检查志特新材tick数据
result = xtdata.get_local_data(
    field_list=['time', 'volume', 'lastPrice'],
    stock_list=['300986.SZ'],
    period='tick',
    start_time='20251231',
    end_time='20251231'
)

df = result['300986.SZ']
print('原始volume字段示例:')
print(df[['time', 'volume', 'lastPrice']].head(10))
print(f'\n首行volume: {df.iloc[0]["volume"]}')
print(f'末行volume: {df.iloc[-1]["volume"]}')
print(f'差值: {df.iloc[-1]["volume"] - df.iloc[0]["volume"]}')
print(f'\n数据类型: {df["volume"].dtype}')

# 对比日线
result_day = xtdata.get_local_data(
    field_list=['volume'],
    stock_list=['300986.SZ'],
    period='1d',
    start_time='20251231',
    end_time='20251231'
)

if result_day and '300986.SZ' in result_day:
    day_volume = result_day['300986.SZ'].iloc[0]['volume']
    print(f'\n日线volume: {day_volume}')
    print(f'Tick累加volume: {df.iloc[-1]["volume"] - df.iloc[0]["volume"]}')
    print(f'比值: {day_volume / (df.iloc[-1]["volume"] - df.iloc[0]["volume"])}')