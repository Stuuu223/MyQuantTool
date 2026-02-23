#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTO整改：使用正确股本重新生成300017缓存
数据源：xtdata.FloatVolume = 23.06亿股（非市值推算）
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from xtquant import xtdata

STOCK_CODE = '300017.SZ'

# 使用xtdata权威源头：FloatVolume = 23.06亿股
CORRECT_FLOAT_VOLUME = 2306141629.0

print('='*60)
print('【CTO整改】使用正确股本重新生成300017缓存')
print('='*60)
print(f'股票代码: {STOCK_CODE}')
print(f'流通股本: {CORRECT_FLOAT_VOLUME:,.0f}股 = {CORRECT_FLOAT_VOLUME/1e8:.2f}亿股')
print(f'数据源: xtdata.get_instrument_detail()["FloatVolume"]')

def get_turnover_5min_series(tick_df, float_volume):
    if 'volume' not in tick_df.columns or float_volume <= 0:
        return []
    if 'time' in tick_df.columns:
        tick_df = tick_df.sort_values('time').reset_index(drop=True)
    tick_df = tick_df.copy()
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
    if 'time' in tick_df.columns:
        if tick_df['time'].dtype in ['int64', 'float64']:
            tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms')
        else:
            tick_df['dt'] = pd.to_datetime(tick_df['time'])
    else:
        return []
    tick_df.set_index('dt', inplace=True)
    vol_5min = tick_df['vol_delta'].resample('5min').sum()
    turnover_series = (vol_5min / float_volume).tolist()
    return [t for t in turnover_series if t > 0]

# 获取最近60个交易日
days = []
current_date = datetime.now()
while len(days) < 60 * 2:
    if current_date.weekday() < 5:
        days.append(current_date.strftime('%Y%m%d'))
    current_date -= timedelta(days=1)
candidate_dates = days[:60]

daily_peaks = []
valid_days = 0

print(f'\n开始计算最近60日每日峰值换手率...')

for date in candidate_dates:
    if valid_days >= 60:
        break
    try:
        result = xtdata.get_local_data(
            field_list=['time', 'volume'],
            stock_list=[STOCK_CODE],
            period='tick',
            start_time=date,
            end_time=date
        )
        if result is None or STOCK_CODE not in result:
            continue
        tick_df = result[STOCK_CODE]
        if tick_df is None or tick_df.empty:
            continue
        turnover_series = get_turnover_5min_series(tick_df, CORRECT_FLOAT_VOLUME)
        if not turnover_series:
            continue
        daily_peaks.append(max(turnover_series))
        valid_days += 1
    except Exception as e:
        continue

if valid_days >= 5:
    hist_median = float(pd.Series(daily_peaks).median())
    print(f'\n计算完成:')
    print(f'   hist_median = {hist_median:.2e}')
    print(f'   日峰值换手率中位数 = {hist_median*100:.4f}%')
    print(f'   有效交易日 = {valid_days}天')
    
    # 更新缓存
    cache_file = Path('data/cache/hist_median_cache.json')
    cache = {}
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    
    cache[STOCK_CODE] = {
        'hist_median': hist_median,
        'float_volume': CORRECT_FLOAT_VOLUME,
        'valid_days': valid_days,
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'data_source': 'xtdata.FloatVolume'
    }
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f'\n缓存已更新（使用正确股本）')
    print(f'   文件: {cache_file}')
else:
    print(f'\n有效数据不足: {valid_days}天')
