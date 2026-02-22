#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查原始Tick数据时间范围 - 验证早盘数据是否存在
"""

from xtquant import xtdata
import pandas as pd

print('检查300017.SZ最近几日的Tick数据时间范围...')

# 检查最近3个交易日
dates = ['20260221', '20260220', '20260219']

for date in dates:
    print(f'\n{"="*60}')
    print(f'日期: {date}')
    print(f'{"="*60}')
    
    try:
        result = xtdata.get_local_data(
            field_list=['time', 'volume', 'lastPrice'],
            stock_list=['300017.SZ'],
            period='tick',
            start_time=date,
            end_time=date
        )
        
        if result and '300017.SZ' in result:
            df = result['300017.SZ']
            if not df.empty:
                # 转换时间戳
                df['dt'] = pd.to_datetime(df['time'], unit='ms')
                print(f'  数据条数: {len(df)}')
                print(f'  时间范围: {df["dt"].min()} ~ {df["dt"].max()}')
                
                # 检查早盘数据（09:30-10:00）
                morning_mask = (df['dt'].dt.hour == 9) & (df['dt'].dt.minute >= 30) | \
                              (df['dt'].dt.hour == 10) & (df['dt'].dt.minute < 30)
                morning_data = df[morning_mask]
                print(f'  早盘数据条数(09:30-10:00): {len(morning_data)}')
                
                if len(morning_data) > 0:
                    print(f'  早盘时间范围: {morning_data["dt"].min()} ~ {morning_data["dt"].max()}')
                else:
                    print(f'  ⚠️ 警告: 无早盘数据！')
                    
                # 打印前5条和后5条
                print(f'\n  前5条:')
                for i in range(min(5, len(df))):
                    print(f'    {df["dt"].iloc[i]} price={df["lastPrice"].iloc[i]}')
                    
            else:
                print('  数据为空')
        else:
            print('  未找到数据')
            
    except Exception as e:
        print(f'  错误: {e}')
