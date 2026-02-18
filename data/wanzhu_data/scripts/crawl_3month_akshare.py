#!/usr/bin/env python3
"""
AkShare 近3个月涨停数据采集
优势：可以获取历史数据，不需要手机抓包
防封策略：3-5秒随机延时，模拟正常访问
"""

import akshare as ak
import pandas as pd
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def get_trade_dates(start_date, end_date):
    """获取交易日历（简化版，实际应该用akshare的trade日历接口）"""
    dates = []
    current = start_date
    while current <= end_date:
        # 跳过周末
        if current.weekday() < 5:
            dates.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    return dates

def crawl_zt_for_date(date_str):
    """
    采集指定日期的涨停数据
    date_str: 'YYYYMMDD'
    """
    try:
        print(f"  正在采集 {date_str}...")
        
        # 随机延时 3-5秒（防封）
        sleep_time = random.uniform(3, 5)
        time.sleep(sleep_time)
        
        # 获取涨停数据
        df = ak.stock_zt_pool_em(date=date_str)
        
        if df is not None and len(df) > 0:
            # 标准化字段
            result = pd.DataFrame()
            result['code'] = df['代码']
            result['name'] = df['名称']
            result['price'] = df['最新价']
            result['change_pct'] = df['涨跌幅']
            result['sector'] = df['所属行业']
            result['limit_up_days'] = df['连板数']
            result['first_time'] = df['首次封板时间']
            result['last_time'] = df['最后封板时间']
            result['open_count'] = df['炸板次数']
            result['date'] = date_str
            result['source'] = 'akshare_em'
            
            print(f"  ✓ 获取到 {len(result)} 条涨停数据")
            return result
        else:
            print(f"  - 该日期无涨停数据（可能非交易日）")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return pd.DataFrame()

def save_data(df, date_str):
    """保存数据"""
    if df is None or len(df) == 0:
        return
    
    # 保存日文件
    daily_file = BASE_DIR / f"stock_zt_{date_str}.csv"
    df.to_csv(daily_file, index=False, encoding='utf-8-sig')
    
    # 合并历史数据
    all_files = sorted(BASE_DIR.glob("stock_zt_*.csv"))
    if len(all_files) > 0:
        all_dfs = []
        for f in all_files:
            try:
                tdf = pd.read_csv(f)
                all_dfs.append(tdf)
            except:
                continue
        
        if all_dfs:
            hist = pd.concat(all_dfs, ignore_index=True)
            hist = hist.drop_duplicates(subset=['date', 'code'], keep='last')
            
            hist_file = BASE_DIR / "stock_zt_history.csv"
            hist.to_csv(hist_file, index=False, encoding='utf-8-sig')
            print(f"  ✓ 历史数据更新: {len(hist)} 条记录")

def crawl_history_days(days=90):
    """
    采集近N天的数据
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"开始采集 {start_date.strftime('%Y%m%d')} 到 {end_date.strftime('%Y%m%d')} 的涨停数据")
    print(f"预计采集 {days} 天，每请求间隔3-5秒，预计耗时 {days * 4 // 60} 分钟\n")
    
    # 获取所有日期
    all_dates = get_trade_dates(start_date, end_date)
    print(f"共 {len(all_dates)} 个交易日（已过滤周末）")
    
    success_count = 0
    fail_count = 0
    total_zt = 0
    
    for i, date_str in enumerate(all_dates):
        print(f"\n[{i+1}/{len(all_dates)}] {date_str}")
        
        df = crawl_zt_for_date(date_str)
        
        if df is not None:
            if len(df) > 0:
                save_data(df, date_str)
                total_zt += len(df)
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n{'='*50}")
    print(f"采集完成!")
    print(f"  成功: {success_count} 天")
    print(f"  失败: {fail_count} 天")
    print(f"  总涨停记录: {total_zt} 条")
    print(f"  数据保存: {BASE_DIR}/stock_zt_history.csv")

if __name__ == "__main__":
    import sys
    
    # 默认采集近90天（3个月）
    days = 90
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    
    crawl_history_days(days)