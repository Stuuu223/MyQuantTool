"""检查Tick数据格式"""
from xtquant import xtdata
import pandas as pd

# 检查Tick数据格式
tick_data = xtdata.get_local_data(
    field_list=['time', 'lastPrice', 'volume', 'amount'],
    stock_list=['002470.SZ'],
    period='tick',
    start_time='20260227',
    end_time='20260227'
)

if tick_data and '002470.SZ' in tick_data:
    df = tick_data['002470.SZ']
    print(f'Tick数据行数: {len(df)}')
    print(f'\n列名: {df.columns.tolist()}')
    print(f'\n前10行:')
    print(df.head(10))
    
    if 'lastPrice' in df.columns:
        prices = df['lastPrice']
        print(f'\n价格统计:')
        print(f'  min: {prices.min()}')
        print(f'  max: {prices.max()}')
        print(f'  unique: {prices.nunique()}')
        
        # 检查时间字段
        if 'time' in df.columns:
            print(f'\n时间字段类型: {df["time"].dtype}')
            print(f'时间样本: {df["time"].head(3).tolist()}')
else:
    print('无Tick数据')