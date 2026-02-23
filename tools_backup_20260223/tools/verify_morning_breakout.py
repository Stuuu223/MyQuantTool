#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证300017在1月26日早盘起爆 - 基于修正后的分母
"""

from xtquant import xtdata
import pandas as pd
from datetime import timedelta

STOCK_CODE = '300017.SZ'
FLOAT_VOLUME = 2306141629.0
HIST_BASELINE = 1.66e-04  # 活跃窗口75分位

print('='*70)
print('验证300017在2026-01-26早盘起爆')
print('='*70)
print(f'分母(活跃窗口75分位): {HIST_BASELINE:.2e} ({HIST_BASELINE*100:.4f}%)')
print(f'流通股本: {FLOAT_VOLUME/1e8:.2f}亿股')

# 获取1月26日数据
result = xtdata.get_local_data(
    field_list=['time', 'volume', 'lastPrice'],
    stock_list=[STOCK_CODE],
    period='tick',
    start_time='20260126',
    end_time='20260126'
)

if result and STOCK_CODE in result:
    df = result[STOCK_CODE]
    df = df.sort_values('time').reset_index(drop=True)
    df['vol_delta'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta'] = df['vol_delta'].clip(lower=0)
    
    # UTC+8转换
    df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
    df.set_index('dt', inplace=True)
    
    # 过滤价格为0的数据
    df = df[df['lastPrice'] > 0]
    
    # 按5分钟聚合
    resampled = df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'mean'
    })
    
    print(f'\n早盘5分钟窗口分析:')
    print(f'{"时间窗口":<15} {"成交量(万)":<12} {"均价":<10} {"涨幅%":<10} {"ratio":<10}')
    print('-'*70)
    
    pre_close = 11.48  # 前收盘价
    
    for dt, row in resampled.iterrows():
        hour = dt.hour
        minute = dt.minute
        
        # 只显示早盘09:25-10:30
        if not ((hour == 9 and minute >= 25) or (hour == 10)):
            continue
        
        if row['vol_delta'] > 0 and row['lastPrice'] > 0:
            turnover = row['vol_delta'] / FLOAT_VOLUME
            ratio = turnover / HIST_BASELINE
            change_pct = (row['lastPrice'] - pre_close) / pre_close * 100
            
            time_str = f'{hour:02d}:{minute:02d}'
            vol_wan = row['vol_delta'] / 1e4
            
            marker = ''
            if ratio > 4:
                marker = '✅ 触发'
            elif ratio > 3:
                marker = '⚠️ 接近'
            
            print(f'{time_str:<15} {vol_wan:>10.0f} {row["lastPrice"]:>10.2f} {change_pct:>10.2f} {ratio:>10.2f} {marker}')

print(f'\n说明:')
print(f'  ratio = 当前5分钟换手率 / 活跃窗口75分位({HIST_BASELINE*100:.4f}%)')
print(f'  ratio > 4.0 视为触发信号')
