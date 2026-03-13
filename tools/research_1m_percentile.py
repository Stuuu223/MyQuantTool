# -*- coding: utf-8 -*-
"""
【CTO V140 全市场1m分K级分位数真理探索】

研究目标：确定全天候动态分位数阈值（88th/90th/92th/95th）
时间切片：09:35, 09:45, 10:00, 11:00, 14:00, 14:45

核心问题：
- 80th/70th太宽松，需要真实数据验证
- 真龙在下午点火时，量比到底排在前多少分位？

方法论：
1. 用QMT 1m分K数据精确计算各时间点累计成交量
2. 计算实时量比 = 累计成交量 / (5日均量 * 时间进度)
3. 分析全市场分位数分布

Author: CTO
Date: 2026-03-13
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

from xtquant import xtdata

# 时间切片（分钟格式：0930=开盘）
TIME_SLICES = {
    '09:35': '093500',
    '09:45': '094500',
    '10:00': '100000',
    '11:00': '110000',
    '14:00': '140000',
    '14:45': '144500'
}

def get_minutes_passed(time_str):
    """计算从开盘到该时间点的分钟数"""
    hour = int(time_str[:2])
    minute = int(time_str[2:4])
    
    if hour < 11 or (hour == 11 and minute <= 30):
        # 上午：从09:30开始
        return (hour - 9) * 60 + minute - 30
    else:
        # 下午：从13:00开始
        return 120 + (hour - 13) * 60 + minute

def analyze_full_market_1m(date_str, limit_up_stocks=None):
    """
    分析全市场1m分K数据
    
    Args:
        date_str: 日期 "YYYYMMDD"
        limit_up_stocks: 当日涨停股列表
    """
    print(f"\n{'='*80}")
    print(f"【CTO V140 1m分K级分位数研究】日期: {date_str}")
    print(f"{'='*80}\n")
    
    # Step 1: 获取全A股列表
    print("Step 1: 获取全A股列表...")
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"  A股数量: {len(all_stocks)}只")
    
    if limit_up_stocks is None:
        limit_up_stocks = []
    print(f"  涨停股: {len(limit_up_stocks)}只")
    
    # Step 2: 获取5日均量（日K数据）
    print("\nStep 2: 获取5日均量...")
    start_date = (datetime.strptime(date_str, '%Y%m%d') - timedelta(days=15)).strftime('%Y%m%d')
    
    # 批量获取日K
    daily_data = xtdata.get_local_data(
        field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=all_stocks,
        period='1d',
        start_time=start_date,
        end_time=date_str
    )
    
    avg_volume_5d_cache = {}
    for stock, df in daily_data.items():
        if df is not None and len(df) >= 5:
            # 最近5日成交量（手），QMT volume单位是手
            volumes = df['volume'].tail(5).values
            avg_volume_5d_cache[stock] = np.mean(volumes)
    
    print(f"  获取到{len(avg_volume_5d_cache)}只股票的5日均量")
    
    # Step 3: 获取1m分K数据
    print("\nStep 3: 获取1m分K数据...")
    minute_data = xtdata.get_local_data(
        field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=all_stocks,
        period='1m',
        start_time=date_str,
        end_time=date_str
    )
    
    print(f"  获取到{len(minute_data)}只股票的1m数据")
    
    # Step 4: 计算各时间点的量比
    print("\nStep 4: 计算各时间点量比...")
    results = []
    
    for time_name, time_code in TIME_SLICES.items():
        minutes_passed = get_minutes_passed(time_code)
        time_fraction = minutes_passed / 240.0
        
        for stock, df in minute_data.items():
            if df is None or len(df) == 0:
                continue
            
            if stock not in avg_volume_5d_cache:
                continue
            
            avg_volume_5d = avg_volume_5d_cache[stock]
            if avg_volume_5d <= 0:
                continue
            
            # 累计到该时间点的成交量
            target_time = int(date_str + time_code)
            # index可能是字符串或整数，统一转换为整数比较
            try:
                idx_values = [int(i) if isinstance(i, str) else i for i in df.index]
                mask = pd.Series(idx_values, index=df.index) <= target_time
            except:
                mask = pd.Series([str(i) for i in df.index], index=df.index) <= str(target_time)
            if not mask.any():
                continue
            
            cumulative_volume = df.loc[mask, 'volume'].sum()  # 手
            
            # 实时量比
            expected_volume = avg_volume_5d * time_fraction
            if expected_volume > 0:
                volume_ratio = cumulative_volume / expected_volume
            else:
                volume_ratio = 0
            
            results.append({
                'stock_code': stock,
                'date': date_str,
                'time_point': time_name,
                'volume_ratio': volume_ratio,
                'cumulative_volume': cumulative_volume,
                'is_limit_up': stock in limit_up_stocks
            })
    
    return pd.DataFrame(results)

def analyze_percentile_distribution(df, date_str):
    """分析分位数分布"""
    if df is None or len(df) == 0:
        print("没有有效数据！")
        return
    
    print(f"\n{'='*80}")
    print(f"【各时间点量比分位数分布】")
    print(f"{'='*80}\n")
    
    for time_name in TIME_SLICES.keys():
        subset = df[df['time_point'] == time_name]
        
        if len(subset) == 0:
            continue
        
        limit_up = subset[subset['is_limit_up'] == True]
        non_limit = subset[subset['is_limit_up'] == False]
        
        print(f"\n--- {time_name} ---")
        print(f"样本数: {len(subset)} (涨停{len(limit_up)}只)")
        
        if len(limit_up) > 0:
            vr = limit_up['volume_ratio']
            print(f"涨停股量比: P25={vr.quantile(0.25):.2f}x, P50={vr.quantile(0.50):.2f}x, P75={vr.quantile(0.75):.2f}x, P90={vr.quantile(0.90):.2f}x")
        
        if len(non_limit) > 0:
            vr = non_limit['volume_ratio']
            print(f"非涨停量比: P25={vr.quantile(0.25):.2f}x, P50={vr.quantile(0.50):.2f}x, P75={vr.quantile(0.75):.2f}x, P90={vr.quantile(0.90):.2f}x")
        
        # 全市场分位数阈值
        all_vr = subset['volume_ratio']
        print(f"全市场分位: 88th={all_vr.quantile(0.88):.2f}x, 90th={all_vr.quantile(0.90):.2f}x, 92th={all_vr.quantile(0.92):.2f}x, 95th={all_vr.quantile(0.95):.2f}x")
    
    # 统计涨停股在各分位数的覆盖率
    print(f"\n\n{'='*80}")
    print("【涨停股量比分位数覆盖率】")
    print(f"{'='*80}\n")
    
    for percentile in [88, 90, 92, 95]:
        print(f"\n--- {percentile}th分位数 ---")
        for time_name in TIME_SLICES.keys():
            subset = df[df['time_point'] == time_name]
            limit_up = subset[subset['is_limit_up'] == True]
            
            if len(limit_up) == 0:
                continue
            
            threshold = subset['volume_ratio'].quantile(percentile / 100)
            covered = (limit_up['volume_ratio'] >= threshold).sum()
            coverage = covered / len(limit_up) * 100
            
            print(f"{time_name}: 阈值{threshold:.2f}x, 覆盖{covered}/{len(limit_up)}只 ({coverage:.1f}%)")

def get_limit_up_stocks(date_str):
    """获取当日涨停股"""
    try:
        with open('data/validation/violent_samples_full.json', 'r', encoding='utf-8') as f:
            samples = json.load(f)
        
        limit_up_stocks = []
        for s in samples:
            if s['date'] == date_str and s['t0'].get('is_limit_up', False):
                limit_up_stocks.append(s['stock_code'])
        
        return list(set(limit_up_stocks))
    except:
        return []

def main():
    # 分析今天
    today = datetime.now().strftime('%Y%m%d')
    
    # 获取涨停股
    print("获取涨停股列表...")
    limit_up_stocks = get_limit_up_stocks(today)
    print(f"涨停股: {len(limit_up_stocks)}只")
    
    # 分析全市场
    df = analyze_full_market_1m(today, limit_up_stocks)
    
    if df is not None and len(df) > 0:
        # 保存结果
        output_path = f'data/research_lab/1m_percentile_{today}.csv'
        os.makedirs('data/research_lab', exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存: {output_path}")
        
        # 分析分位数
        analyze_percentile_distribution(df, today)
    
    print("\n\n【CTO结论】")
    print("="*80)
    print("基于1m分K数据的分位数研究完成。")
    print("根据涨停股覆盖率，确定全天候分位数阈值。")
    print("="*80)

if __name__ == '__main__':
    main()
