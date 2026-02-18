#!/usr/bin/env python3
"""
顽主杯生产环境采集脚本
基于真实API配置，自动采集每日热门买入股票
"""

import requests
import pandas as pd
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "wanzhu_api_config.json"

def load_config():
    """加载API配置"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_wanzhu_data(trade_date, page=1, page_size=100):
    """
    采集指定日期的顽主杯数据
    trade_date: '2026-02-12' 格式
    """
    cfg = load_config()
    url = cfg['base_url']
    headers = cfg['headers']
    params = cfg['default_params'].copy()
    
    # 设置日期和分页
    params['stock_date'] = trade_date
    params['page'] = page
    params['page_size'] = page_size
    
    try:
        # 随机延时防封（3-5秒）
        time.sleep(random.uniform(3, 5))
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data
        
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
        return None

def parse_wanzhu_data(data, trade_date):
    """解析顽主杯数据为DataFrame"""
    if not data or not isinstance(data, dict):
        return None
    
    # 检查返回状态
    if data.get('errno') != 0 and data.get('code') != 0:
        print(f"  - API返回错误: {data.get('errmsg', '未知错误')}")
        return None
    
    # 获取数据列表
    result_data = data.get('data', {})
    records = result_data.get('list', [])
    total = result_data.get('total', 0)
    
    if not records:
        print(f"  - 未找到数据记录")
        return None
    
    print(f"  找到 {total} 条记录，当前页 {len(records)} 条")
    
    df = pd.DataFrame(records)
    
    # 标准化字段
    column_mapping = {
        'stock_code': 'code',
        'stock_name': 'name',
        'stock_desc': 'description',
        'count': 'buy_count',
        'yes_count': 'yesterday_count',
        'total_fund': 'total_fund',
        'comments_count': 'comments_count',
        'choice_count': 'choice_count',
        'id': 'id',
    }
    
    df = df.rename(columns=column_mapping)
    
    # 补全股票代码为6位（API返回的数字格式会丢失前导零）
    df['code'] = df['code'].astype(str).str.zfill(6)
    
    df['date'] = trade_date.replace('-', '')
    df['source'] = 'wanzhu_api'
    
    return df

def save_data(df, trade_date):
    """保存数据"""
    if df is None or len(df) == 0:
        return
    
    date_str = trade_date.replace('-', '')
    
    # 保存日文件
    daily_file = BASE_DIR / f"wanzhu_{date_str}.csv"
    df.to_csv(daily_file, index=False, encoding='utf-8-sig')
    print(f"  ✓ 日文件保存: {daily_file} ({len(df)} 条)")
    
    # 合并历史数据
    all_files = sorted(BASE_DIR.glob("wanzhu_*.csv"))
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
            
            hist_file = BASE_DIR / "wanzhu_history.csv"
            hist.to_csv(hist_file, index=False, encoding='utf-8-sig')
            print(f"  ✓ 历史数据更新: {hist_file} ({len(hist)} 条)")

def crawl_date(trade_date):
    """采集单日数据"""
    print(f"\n[{trade_date}] 开始采集...")
    
    data = fetch_wanzhu_data(trade_date)
    
    if data:
        df = parse_wanzhu_data(data, trade_date)
        if df is not None and len(df) > 0:
            save_data(df, trade_date)
            print(f"  ✓ 成功采集 {len(df)} 条数据")
            return True
    
    return False

def crawl_range(start_date, end_date):
    """采集日期范围数据"""
    print(f"采集范围: {start_date} 到 {end_date}")
    
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    success_count = 0
    fail_count = 0
    
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        
        if crawl_date(date_str):
            success_count += 1
        else:
            fail_count += 1
        
        current += timedelta(days=1)
    
    print(f"\n{'='*60}")
    print(f"采集完成: 成功 {success_count} 天, 失败 {fail_count} 天")
    print(f"数据文件: {BASE_DIR}/wanzhu_history.csv")

def crawl_recent_days(days=30):
    """采集最近N天"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    crawl_range(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        # 指定日期范围
        crawl_range(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        # 最近N天
        crawl_recent_days(int(sys.argv[1]))
    else:
        # 默认最近30天
        crawl_recent_days(30)
