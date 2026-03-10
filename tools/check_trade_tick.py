"""检查交易时段Tick数据"""
from xtquant import xtdata
import pandas as pd

tick_data = xtdata.get_local_data(
    field_list=['time', 'lastPrice', 'volume', 'amount'],
    stock_list=['002470.SZ'],
    period='tick',
    start_time='20260227',
    end_time='20260227'
)

if tick_data and '002470.SZ' in tick_data:
    df = tick_data['002470.SZ']
    
    # 转换时间戳
    df['datetime'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
    df['time_str'] = df['datetime'].dt.strftime('%H:%M:%S')
    
    print(f'总行数: {len(df)}')
    
    # 过滤交易时段
    trade_df = df[df['lastPrice'] > 0]
    print(f'有价格数据行数: {len(trade_df)}')
    
    # 按时间段统计
    morning_df = trade_df[(trade_df['time_str'] >= '09:30:00') & (trade_df['time_str'] <= '11:30:00')]
    afternoon_df = trade_df[(trade_df['time_str'] >= '13:00:00') & (trade_df['time_str'] <= '15:00:00')]
    
    print(f'\n上午时段(09:30-11:30): {len(morning_df)}行')
    print(f'\n下午时段(13:00-15:00): {len(afternoon_df)}行')
    
    if len(trade_df) > 0:
        print(f'\n交易时段价格统计:')
        print(f'  开盘价(第一笔有价格): {trade_df["lastPrice"].iloc[0]}')
        print(f'  收盘价(最后一笔): {trade_df["lastPrice"].iloc[-1]}')
        print(f'  最高价: {trade_df["lastPrice"].max()}')
        print(f'  最低价: {trade_df["lastPrice"].min()}')
        print(f'  unique价格数: {trade_df["lastPrice"].nunique()}')
        
        # 查看前几笔交易
        print(f'\n前10笔交易:')
        print(trade_df[['time_str', 'lastPrice', 'volume', 'amount']].head(10))