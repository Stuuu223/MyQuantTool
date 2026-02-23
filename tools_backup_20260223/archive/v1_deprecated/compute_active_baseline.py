#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【老板指令】方案B：活跃窗口75分位分母计算
验证：打印时间分布直方图，确保样本不过度集中在开盘前10分钟
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from xtquant import xtdata

STOCK_CODE = '300017.SZ'
CORRECT_FLOAT_VOLUME = 2306141629.0  # 23.06亿股
PERCENTILE = 75  # 75分位

print('='*70)
print('【老板指令】方案B：活跃窗口75分位分母计算')
print('='*70)
print(f'股票代码: {STOCK_CODE}')
print(f'流通股本: {CORRECT_FLOAT_VOLUME:,.0f}股 = {CORRECT_FLOAT_VOLUME/1e8:.2f}亿股')
print(f'分位点: {PERCENTILE}th percentile')
print(f'活跃定义: 5分钟成交额 > 当日5分钟成交额均值')

def get_turnover_5min_series(tick_df, float_volume):
    """计算5分钟换手率序列，返回[(time, turnover, amount), ...]"""
    if 'volume' not in tick_df.columns or float_volume <= 0:
        return []
    
    tick_df = tick_df.sort_values('time').reset_index(drop=True)
    tick_df = tick_df.copy()
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
    
    if tick_df['time'].dtype in ['int64', 'float64']:
        tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms')
    else:
        tick_df['dt'] = pd.to_datetime(tick_df['time'])
    
    tick_df.set_index('dt', inplace=True)
    
    # 计算5分钟聚合
    resampled = tick_df.resample('5min').agg({
        'vol_delta': 'sum',
        'lastPrice': 'mean'
    })
    
    result = []
    for dt, row in resampled.iterrows():
        if row['vol_delta'] > 0 and pd.notna(row['lastPrice']):
            turnover = row['vol_delta'] / float_volume
            amount = row['vol_delta'] * row['lastPrice']  # 成交额（元）
            result.append({
                'time': dt,
                'turnover': turnover,
                'amount': amount,
                'hour': dt.hour,
                'minute': dt.minute
            })
    
    return result

# 获取最近60个交易日
days = []
current_date = datetime.now()
while len(days) < 60 * 2:
    if current_date.weekday() < 5:
        days.append(current_date.strftime('%Y%m%d'))
    current_date -= timedelta(days=1)
candidate_dates = days[:60]

all_windows = []  # 所有窗口
active_windows = []  # 活跃窗口

print(f'\n开始计算最近60日5分钟窗口...')

for date in candidate_dates:
    try:
        result = xtdata.get_local_data(
            field_list=['time', 'volume', 'lastPrice'],
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
        
        windows = get_turnover_5min_series(tick_df, CORRECT_FLOAT_VOLUME)
        if not windows:
            continue
        
        # 计算当日平均成交额
        day_avg_amount = np.mean([w['amount'] for w in windows])
        
        for w in windows:
            w['date'] = date
            w['day_avg_amount'] = day_avg_amount
            w['is_active'] = w['amount'] > day_avg_amount
            all_windows.append(w)
            
            if w['is_active']:
                active_windows.append(w)
        
    except Exception as e:
        continue

print(f'\n✅ 数据收集完成:')
print(f'   总窗口数: {len(all_windows)}')
print(f'   活跃窗口数: {len(active_windows)} ({len(active_windows)/len(all_windows)*100:.1f}%)')

# 时间分布直方图（老板要求验证）
print(f'\n【时间分布验证 - 老板要求】')
print(f'活跃窗口时间分布:')

time_buckets = {
    '09:30-09:40': 0,
    '09:40-10:00': 0,
    '10:00-10:30': 0,
    '10:30-11:30': 0,
    '11:30-13:00': 0,
    '13:00-14:00': 0,
    '14:00-14:30': 0,
    '14:30-15:00': 0
}

for w in active_windows:
    h, m = w['hour'], w['minute']
    time_str = f'{h:02d}:{m:02d}'
    
    if h == 9 and m >= 30 and m < 40:
        time_buckets['09:30-09:40'] += 1
    elif h == 9 and m >= 40:
        time_buckets['09:40-10:00'] += 1
    elif h == 10 and m < 30:
        time_buckets['10:00-10:30'] += 1
    elif (h == 10 and m >= 30) or h == 11:
        time_buckets['10:30-11:30'] += 1
    elif h == 11 and m >= 30:
        time_buckets['11:30-13:00'] += 1
    elif h == 13:
        time_buckets['13:00-14:00'] += 1
    elif h == 14 and m < 30:
        time_buckets['14:00-14:30'] += 1
    else:
        time_buckets['14:30-15:00'] += 1

for bucket, count in time_buckets.items():
    pct = count / len(active_windows) * 100 if active_windows else 0
    bar = '█' * int(pct / 2)
    print(f'   {bucket}: {count:4d} ({pct:5.1f}%) {bar}')

# 计算75分位分母
if active_windows:
    active_turnovers = [w['turnover'] for w in active_windows]
    hist_baseline = np.percentile(active_turnovers, PERCENTILE)
    
    print(f'\n✅ 分母计算完成:')
    print(f'   活跃窗口换手率75分位: {hist_baseline:.2e}')
    print(f'   换算为百分比: {hist_baseline*100:.4f}%')
    
    # 保存新缓存
    cache_file = Path('data/cache/hist_median_cache_active75.json')
    cache = {
        STOCK_CODE: {
            'hist_baseline': float(hist_baseline),
            'float_volume': CORRECT_FLOAT_VOLUME,
            'method': 'active_window_75p',
            'active_window_count': len(active_windows),
            'total_window_count': len(all_windows),
            'updated_at': datetime.now().strftime('%Y-%m-%d')
        }
    }
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 新缓存已保存: {cache_file}')
    
    # 验证：300017在1月26日早盘的ratio预期
    print(f'\n【预期验证】300017 2026-01-26早盘:')
    print(f'   09:35-09:40 turnover: ~0.0204% (旧分母0.02%)')
    print(f'   新分母: {hist_baseline*100:.4f}%')
    print(f'   预期ratio: {0.0204/hist_baseline:.2f}')
    
else:
    print(f'\n⚠️ 活跃窗口不足，无法计算分母')
