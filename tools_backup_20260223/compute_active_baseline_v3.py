#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO最终整改版】方案B：活跃窗口75分位 - 修正UTC时间戳转换
关键修正：UTC时间 + 8小时 = 北京时间
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from xtquant import xtdata

STOCK_CODE = '300017.SZ'
CORRECT_FLOAT_VOLUME = 2306141629.0
PERCENTILE = 75

print('='*70)
print('【CTO最终整改版】方案B：修正UTC+8时间戳转换')
print('='*70)

def get_turnover_5min_series(tick_df, float_volume):
    """计算5分钟换手率序列 - 修正UTC+8"""
    if 'volume' not in tick_df.columns or float_volume <= 0:
        return []
    
    tick_df = tick_df.sort_values('time').reset_index(drop=True)
    tick_df = tick_df.copy()
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
    
    # 关键修正：UTC + 8小时 = 北京时间
    if tick_df['time'].dtype in ['int64', 'float64']:
        tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms') + timedelta(hours=8)
    else:
        tick_df['dt'] = pd.to_datetime(tick_df['time']) + timedelta(hours=8)
    
    tick_df.set_index('dt', inplace=True)
    
    # 过滤掉价格为0的数据（盘前/盘后）
    tick_df = tick_df[tick_df['lastPrice'] > 0]
    
    if tick_df.empty:
        return []
    
    # 按5分钟聚合
    resampled = tick_df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'mean'
    })
    
    result = []
    for dt, row in resampled.iterrows():
        if row['vol_delta'] > 0 and pd.notna(row['lastPrice']) and row['lastPrice'] > 0:
            turnover = row['vol_delta'] / float_volume
            amount = row['vol_delta'] * row['lastPrice']
            result.append({
                'time': dt,
                'turnover': turnover,
                'amount': amount,
                'hour': dt.hour,
                'minute': dt.minute
            })
    
    return result

# 只检查1月26日数据（有数据的一天）
date = '20260126'
print(f'\n检查日期: {date}')

try:
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice'],
        stock_list=[STOCK_CODE],
        period='tick',
        start_time=date,
        end_time=date
    )
    
    if result and STOCK_CODE in result:
        tick_df = result[STOCK_CODE]
        print(f'原始数据条数: {len(tick_df)}')
        
        windows = get_turnover_5min_series(tick_df, CORRECT_FLOAT_VOLUME)
        print(f'有效5分钟窗口数: {len(windows)}')
        
        if windows:
            # 计算当日平均
            day_avg_amount = np.mean([w['amount'] for w in windows])
            print(f'当日平均成交额/5min: {day_avg_amount/1e4:.0f}万')
            
            # 标记活跃窗口
            for w in windows:
                w['is_active'] = w['amount'] > day_avg_amount
            
            active_windows = [w for w in windows if w['is_active']]
            print(f'活跃窗口数: {len(active_windows)}')
            
            # 时间分布
            print(f'\n【时间分布 - 修正UTC+8后】')
            morning_count = sum(1 for w in active_windows if 9 <= w['hour'] < 10)
            afternoon_count = sum(1 for w in active_windows if 13 <= w['hour'] < 15)
            print(f'  早盘(09:00-10:00): {morning_count}个')
            print(f'  下午(13:00-15:00): {afternoon_count}个')
            
            if active_windows:
                active_turnovers = [w['turnover'] for w in active_windows]
                hist_baseline = np.percentile(active_turnovers, PERCENTILE)
                print(f'\n✅ 分母计算完成:')
                print(f'   活跃窗口换手率{PERCENTILE}分位: {hist_baseline:.2e} ({hist_baseline*100:.4f}%)')
            
            # 打印早盘窗口详情
            morning_windows = [w for w in windows if 9 <= w['hour'] < 10]
            if morning_windows:
                print(f'\n早盘窗口详情:')
                for w in morning_windows[:5]:
                    status = '活跃' if w['is_active'] else '普通'
                    print(f'  {w["hour"]:02d}:{w["minute"]:02d} - 成交{w["amount"]/1e4:.0f}万 - {status}')
        else:
            print('⚠️ 无有效窗口')
    else:
        print('未找到数据')
        
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
