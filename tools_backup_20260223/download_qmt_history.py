#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QMT历史数据下载脚本
下载指定日期的日线、分钟线、Tick数据
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from xtquant import xtdata
import time

# 配置
STOCK_LIST_FILE = Path('E:/MyQuantTool/data/scan_results/20251231_candidates_73.csv')
TRADE_DATE = '20251231'
HISTORY_DAYS = 5  # 下载前5日数据


def load_stock_list():
    """加载股票列表"""
    if not STOCK_LIST_FILE.exists():
        print(f"❌ 股票列表不存在: {STOCK_LIST_FILE}")
        return []
    
    df = pd.read_csv(STOCK_LIST_FILE)
    stock_list = df['ts_code'].tolist()
    print(f"✅ 加载股票列表: {len(stock_list)}只")
    return stock_list


def download_daily_data(stock_list, trade_date):
    """下载日线数据"""
    print("\n" + "="*80)
    print("【下载日线数据】")
    print("="*80)
    
    # 计算日期范围
    end_date = trade_date
    start_date = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d')
    
    print(f"日期范围: {start_date} 至 {end_date}")
    print(f"股票数量: {len(stock_list)}只")
    
    success_count = 0
    failed_list = []
    
    for i, stock_code in enumerate(stock_list, 1):
        try:
            print(f"\n[{i}/{len(stock_list)}] {stock_code}")
            
            # 下载日线数据
            xtdata.download_history_data(
                stock_code=stock_code,
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            # 验证下载
            data = xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'amount'],
                stock_list=[stock_code],
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            if data and stock_code in data and not data[stock_code].empty:
                count = len(data[stock_code])
                print(f"   ✅ 成功 ({count}条)")
                success_count += 1
            else:
                print(f"   ⚠️ 数据为空")
                failed_list.append(stock_code)
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            failed_list.append(stock_code)
        
        time.sleep(0.05)  # 避免限流
    
    print(f"\n✅ 日线数据下载完成: {success_count}/{len(stock_list)}")
    return success_count, failed_list


def download_minute_data(stock_list, trade_date):
    """下载1分钟线数据"""
    print("\n" + "="*80)
    print("【下载1分钟线数据】")
    print("="*80)
    
    print(f"日期: {trade_date}")
    print(f"股票数量: {len(stock_list)}只")
    
    success_count = 0
    failed_list = []
    
    for i, stock_code in enumerate(stock_list, 1):
        try:
            print(f"\n[{i}/{len(stock_list)}] {stock_code}")
            
            # 下载分钟线数据
            xtdata.download_history_data(
                stock_code=stock_code,
                period='1m',
                start_time=trade_date,
                end_time=trade_date
            )
            
            # 验证下载
            data = xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock_code],
                period='1m',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if data and stock_code in data and not data[stock_code].empty:
                count = len(data[stock_code])
                print(f"   ✅ 成功 ({count}条)")
                success_count += 1
            else:
                print(f"   ⚠️ 数据为空")
                failed_list.append(stock_code)
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            failed_list.append(stock_code)
        
        time.sleep(0.05)
    
    print(f"\n✅ 分钟线数据下载完成: {success_count}/{len(stock_list)}")
    return success_count, failed_list


def download_tick_data(stock_list, trade_date):
    """下载Tick数据"""
    print("\n" + "="*80)
    print("【下载Tick数据】")
    print("="*80)
    
    print(f"日期: {trade_date}")
    print(f"股票数量: {len(stock_list)}只")
    print("⚠️  Tick数据量大，下载时间较长...")
    
    success_count = 0
    failed_list = []
    
    for i, stock_code in enumerate(stock_list, 1):
        try:
            print(f"\n[{i}/{len(stock_list)}] {stock_code}")
            
            # 检查本地是否已有数据
            existing = xtdata.get_local_data(
                field_list=['time'],
                stock_list=[stock_code],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if existing and stock_code in existing and not existing[stock_code].empty:
                count = len(existing[stock_code])
                print(f"   ✅ 本地已存在 ({count}条)")
                success_count += 1
                continue
            
            # 下载Tick数据
            print(f"   📥 下载中...")
            xtdata.download_history_data(
                stock_code=stock_code,
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            # 验证下载
            data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume'],
                stock_list=[stock_code],
                period='tick',
                start_time=trade_date,
                end_time=trade_date
            )
            
            if data and stock_code in data and not data[stock_code].empty:
                count = len(data[stock_code])
                print(f"   ✅ 成功 ({count}条)")
                success_count += 1
            else:
                print(f"   ⚠️ 数据为空")
                failed_list.append(stock_code)
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            failed_list.append(stock_code)
        
        time.sleep(0.1)
    
    print(f"\n✅ Tick数据下载完成: {success_count}/{len(stock_list)}")
    return success_count, failed_list


def main():
    """主函数"""
    print("="*80)
    print("【QMT历史数据下载】")
    print("="*80)
    print(f"目标日期: {TRADE_DATE}")
    print(f"历史天数: {HISTORY_DAYS}日")
    print("="*80)
    
    # 加载股票列表
    stock_list = load_stock_list()
    if not stock_list:
        return
    
    # 下载日线数据
    daily_success, daily_failed = download_daily_data(stock_list, TRADE_DATE)
    
    # 下载分钟线数据
    minute_success, minute_failed = download_minute_data(stock_list, TRADE_DATE)
    
    # 下载Tick数据
    tick_success, tick_failed = download_tick_data(stock_list, TRADE_DATE)
    
    # 输出汇总
    print("\n" + "="*80)
    print("【下载汇总】")
    print("="*80)
    print(f"日线数据: {daily_success}/{len(stock_list)} 成功")
    print(f"分钟线数据: {minute_success}/{len(stock_list)} 成功")
    print(f"Tick数据: {tick_success}/{len(stock_list)} 成功")
    print("="*80)
    print("✅ QMT历史数据下载完成")
    print("="*80)


if __name__ == '__main__':
    main()