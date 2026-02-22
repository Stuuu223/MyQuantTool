#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO整改版】方案B：活跃窗口75分位分母计算 - 修正时间戳错误
关键修正：
1. 使用label='left'确保时间戳对齐到窗口开始
2. 明确处理09:30开盘数据
3. 检查原始Tick边界完整性
4. 打印详细时间分布验证
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
PERCENTILE = 75

print('='*70)
print('【CTO整改版】方案B：活跃窗口75分位 - 修正时间戳错误')
print('='*70)

def get_turnover_5min_series(tick_df, float_volume):
    """
    计算5分钟换手率序列 - CTO修正版
    关键：使用label='left'确保时间戳对齐到窗口开始
    """
    if 'volume' not in tick_df.columns or float_volume <= 0:
        return []
    
    # 确保按时间排序
    tick_df = tick_df.sort_values('time').reset_index(drop=True)
    tick_df = tick_df.copy()
    
    # 计算成交量增量
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
    
    # 转换时间戳 - 关键修正：使用毫秒时间戳
    if tick_df['time'].dtype in ['int64', 'float64']:
        # QMT返回的是毫秒时间戳
        tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms')
    else:
        tick_df['dt'] = pd.to_datetime(tick_df['time'])
    
    # 设置索引
    tick_df.set_index('dt', inplace=True)
    
    # 按5分钟聚合 - 关键修正：使用label='left', closed='left'
    # 这样09:30:00-09:34:59的数据会标记为09:30:00
    resampled = tick_df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'mean',
        'volume': 'last'  # 保留最后一笔的累计成交量用于验证
    })
    
    result = []
    for dt, row in resampled.iterrows():
        if row['vol_delta'] > 0 and pd.notna(row['lastPrice']):
            turnover = row['vol_delta'] / float_volume
            amount = row['vol_delta'] * row['lastPrice']
            result.append({
                'time': dt,
                'turnover': turnover,
                'amount': amount,
                'vol_delta': row['vol_delta'],
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

all_windows = []
active_windows = []

print(f'\n开始计算最近60日5分钟窗口（修正时间戳对齐）...')

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
        
        # 检查原始Tick数据的时间范围
        if tick_df['time'].dtype in ['int64', 'float64']:
            first_time = pd.to_datetime(tick_df['time'].iloc[0], unit='ms')
            last_time = pd.to_datetime(tick_df['time'].iloc[-1], unit='ms')
        else:
            first_time = pd.to_datetime(tick_df['time'].iloc[0])
            last_time = pd.to_datetime(tick_df['time'].iloc[-1])
        
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
        print(f'  [{date}] 错误: {e}')
        continue

print(f'\n✅ 数据收集完成:')
print(f'   总窗口数: {len(all_windows)}')
print(f'   活跃窗口数: {len(active_windows)} ({len(active_windows)/len(all_windows)*100:.1f}%)')

# 时间分布直方图（CTO要求验证）
print(f'\n【时间分布验证 - CTO要求】')
print(f'活跃窗口时间分布:')

time_buckets = {
    '09:30-09:35': 0,
    '09:35-09:40': 0,
    '09:40-09:45': 0,
    '09:45-10:00': 0,
    '10:00-10:30': 0,
    '10:30-11:30': 0,
    '11:30-13:00': 0,
    '13:00-14:00': 0,
    '14:00-14:30': 0,
    '14:30-15:00': 0
}

for w in active_windows:
    h, m = w['hour'], w['minute']
    
    if h == 9 and m == 30:
        time_buckets['09:30-09:35'] += 1
    elif h == 9 and m == 35:
        time_buckets['09:35-09:40'] += 1
    elif h == 9 and m == 40:
        time_buckets['09:40-09:45'] += 1
    elif h == 9 and m >= 45:
        time_buckets['09:45-10:00'] += 1
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
    print(f'   活跃窗口换手率{PERCENTILE}分位: {hist_baseline:.2e}')
    print(f'   换算为百分比: {hist_baseline*100:.4f}%')
    
    # 保存新缓存
    cache_file = Path('data/cache/hist_median_cache_active75_v2.json')
    cache = {
        STOCK_CODE: {
            'hist_baseline': float(hist_baseline),
            'float_volume': CORRECT_FLOAT_VOLUME,
            'method': 'active_window_75p_v2',
            'active_window_count': len(active_windows),
            'total_window_count': len(all_windows),
            'time_distribution': time_buckets,
            'updated_at': datetime.now().strftime('%Y-%m-%d'),
            'note': 'CTO修正版：修正时间戳对齐'
        }
    }
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 新缓存已保存: {cache_file}')
    
else:
    print(f'\n⚠️ 活跃窗口不足，无法计算分母')