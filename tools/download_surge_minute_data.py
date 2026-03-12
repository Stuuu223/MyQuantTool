# -*- coding: utf-8 -*-
"""
CTO V111 分K数据批量下载器

下载violent_surge样本的完整上升周期分K数据
"""

import os
import sys
import time
from datetime import datetime, timedelta
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import xtquant.xtdata as xtdata
except ImportError:
    print("[ERROR] 无法导入xtquant，请确保在venv_qmt环境中运行")
    sys.exit(1)


def main():
    print("="*70)
    print("CTO V111 分K数据批量下载器")
    print("="*70)
    
    # 读取violent_surge样本
    samples_path = os.path.join(ROOT, 'data', 'validation', 'recent_samples_2025_2026.csv')
    df = pd.read_csv(samples_path)
    surge = df[df['label'] == 1].copy()
    
    # 获取所有样本的日期范围
    dates = surge['date'].unique()
    min_date = str(min(dates))
    max_date = str(max(dates))
    
    print(f"\n[样本范围] {min_date} ~ {max_date}")
    print(f"[样本数量] {len(surge)}条, {len(surge['stock_code'].unique())}只股票")
    
    # 按股票分组，获取每只股票的日期范围
    stock_dates = surge.groupby('stock_code').agg({
        'date': ['min', 'max', 'count']
    }).reset_index()
    stock_dates.columns = ['stock_code', 'min_date', 'max_date', 'count']
    
    # 扩展日期范围（前后各加3天）
    stock_dates['download_start'] = stock_dates['min_date'].apply(
        lambda x: (datetime.strptime(str(x), '%Y%m%d') - timedelta(days=3)).strftime('%Y%m%d')
    )
    stock_dates['download_end'] = stock_dates['max_date'].apply(
        lambda x: (datetime.strptime(str(x), '%Y%m%d') + timedelta(days=3)).strftime('%Y%m%d')
    )
    
    print(f"\n[下载计划] {len(stock_dates)}只股票的分K数据")
    
    # 批量下载
    success_count = 0
    fail_count = 0
    
    for idx, row in stock_dates.iterrows():
        stock_code = row['stock_code']
        start_date = row['download_start']
        end_date = row['download_end']
        
        print(f"\r[下载中] {stock_code} {start_date}~{end_date} ({idx+1}/{len(stock_dates)}) 成功:{success_count}", end='', flush=True)
        
        try:
            # 下载1分钟K线（注意：QMT API第一个参数是字符串，不是列表）
            xtdata.download_history_data(
                stock_code,  # 字符串，不是列表
                period='1m', 
                start_time=start_date, 
                end_time=end_date
            )
            
            # 下载日K（确保有日K）
            xtdata.download_history_data(
                stock_code,
                period='1d', 
                start_time=start_date, 
                end_time=end_date
            )
            
            success_count += 1
            
            # 每20只暂停一下
            if (idx + 1) % 20 == 0:
                print(f"\n  [暂停] 已下载{idx+1}只，休息2秒...")
                time.sleep(2)
                
        except Exception as e:
            print(f"\n  [ERROR] {stock_code}: {e}")
            fail_count += 1
    
    print(f"\n\n[下载完成] 成功:{success_count} 失败:{fail_count}")
    
    # 验证下载结果
    print("\n[验证分K数据]")
    valid_count = 0
    
    for idx, row in stock_dates.head(20).iterrows():
        stock_code = row['stock_code']
        date = str(row['min_date'])
        
        try:
            minute_data = xtdata.get_local_data(
                field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=[stock_code],
                period='1m',
                start_time=date,
                end_time=date
            )
            
            if minute_data and stock_code in minute_data:
                df = minute_data[stock_code]
                if df is not None and len(df) > 0:
                    valid_count += 1
                    print(f"  ✓ {stock_code} {date}: {len(df)}根分K")
                else:
                    print(f"  ✗ {stock_code} {date}: 数据为空")
            else:
                print(f"  ✗ {stock_code} {date}: 无数据")
        except Exception as e:
            print(f"  ✗ {stock_code} {date}: {e}")
    
    print(f"\n[验证结果] 有效数据: {valid_count}/20")


if __name__ == '__main__':
    main()
