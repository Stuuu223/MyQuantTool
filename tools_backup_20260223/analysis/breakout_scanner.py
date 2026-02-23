#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO纠偏版V2】高潮窗口自动扫描器 - 极简版

核心任务：
1. 志特新材12.31 - 自动扫描全天，找出真正推动+8.97%的高潮窗口
2. 志特新材01.05 - 扫描接力加速日
3. 对比网宿科技、超捷股份
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from xtquant import xtdata

FLOAT_VOLUMES = {
    '300017.SZ': 2306141629.0,
    '301005.SZ': 836269091.0,
    '300986.SZ': 246000000.0,
}


def get_tick_data(stock_code, date):
    """获取tick数据"""
    try:
        result = xtdata.get_local_data(
            field_list=['time', 'volume', 'lastPrice'],
            stock_list=[stock_code],
            period='tick',
            start_time=date,
            end_time=date
        )
        if result and stock_code in result:
            df = result[stock_code].copy()
            if not df.empty:
                # UTC+8转换
                df.loc[:, 'dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
                df = df[df['lastPrice'] > 0].copy()
                return df
        return None
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None


def calculate_baseline(stock_code, target_date):
    """计算历史基准"""
    float_vol = FLOAT_VOLUMES.get(stock_code, 1e9)
    
    end_date = datetime.strptime(target_date, '%Y%m%d')
    dates = []
    current = end_date - timedelta(days=1)
    while len(dates) < 60:
        if current.weekday() < 5:
            dates.append(current.strftime('%Y%m%d'))
        current -= timedelta(days=1)
        if (end_date - current).days > 120:
            break
    
    turnovers = []
    for date in dates:
        df = get_tick_data(stock_code, date)
        if df is not None and not df.empty:
            df_sorted = df.sort_values('dt')
            df_sorted.loc[:, 'vol_delta'] = df_sorted['volume'].diff().fillna(df_sorted['volume'].iloc[0])
            df_sorted.loc[:, 'vol_delta'] = df_sorted['vol_delta'].clip(lower=0)
            
            # 5分钟聚合
            df_sorted = df_sorted.set_index('dt')
            resampled = df_sorted.resample('5min', label='left', closed='left').agg({
                'vol_delta': 'sum',
                'lastPrice': 'mean'
            })
            
            for _, row in resampled.iterrows():
                if row['vol_delta'] > 0 and row['lastPrice'] > 0:
                    turnovers.append(row['vol_delta'] / float_vol)
    
    if len(turnovers) < 50:
        return None
    
    return {
        'p85': float(np.percentile(turnovers, 85)),
        'p75': float(np.percentile(turnovers, 75)),
        'count': len(turnovers)
    }


def scan_day(stock_code, date, top_n=5):
    """扫描单日高潮窗口"""
    print(f"\n{'='*60}")
    print(f"扫描 {stock_code} {date}")
    print(f"{'='*60}")
    
    float_vol = FLOAT_VOLUMES.get(stock_code, 1e9)
    
    # 历史基准
    baseline = calculate_baseline(stock_code, date)
    if not baseline:
        print("❌ 基准计算失败")
        return []
    
    print(f"历史基准: 85分位={baseline['p85']:.2e}, 样本数={baseline['count']}")
    
    # 当日数据
    df = get_tick_data(stock_code, date)
    if df is None or df.empty:
        print("❌ 当日数据为空")
        return []
    
    df_sorted = df.sort_values('dt').copy()
    day_open = df_sorted['lastPrice'].iloc[0]
    day_close = df_sorted['lastPrice'].iloc[-1]
    
    # 🔥 P6.3修复：获取昨收价计算真实涨幅
    from logic.services.data_service import data_service
    date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    pre_close = data_service.get_pre_close(stock_code, date_fmt)
    if pre_close <= 0:
        pre_close = day_open * 0.97  # 备用估算
    
    true_change = (day_close - pre_close) / pre_close * 100  # 真实涨幅（相对昨收）
    intraday_change = (day_close - day_open) / day_open * 100  # 日内涨幅（相对开盘）
    
    print(f"昨收: {pre_close:.2f}, 开盘: {day_open:.2f}, 收盘: {day_close:.2f}")
    print(f"真实涨幅: {true_change:.2f}%（相对昨收）✅, 日内涨幅: {intraday_change:.2f}%（相对开盘）")
    
    # 计算成交量增量
    df_sorted.loc[:, 'vol_delta'] = df_sorted['volume'].diff().fillna(df_sorted['volume'].iloc[0])
    df_sorted.loc[:, 'vol_delta'] = df_sorted['vol_delta'].clip(lower=0)
    
    # 5分钟聚合
    df_sorted = df_sorted.set_index('dt')
    resampled = df_sorted.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'last'
    })
    resampled = resampled.dropna()
    
    if resampled.empty:
        print("❌ 无有效窗口")
        return []
    
    # 计算每个窗口的指标
    windows = []
    prev_price = day_open
    for dt, row in resampled.iterrows():
        if row['vol_delta'] <= 0 or row['lastPrice'] <= 0:
            continue
        
        # CTO紧急修复: QMT volume单位是手，需×100转股
        amount = row['vol_delta'] * 100 * row['lastPrice']  # 成交额(元)
        turnover = row['vol_delta'] * 100 / float_vol  # 换手率 (手→股)
        price_change = (row['lastPrice'] - prev_price) / prev_price * 100 if prev_price > 0 else 0
        
        # 强度得分 = 成交额(万) × 涨幅绝对值
        intensity = amount / 10000 * abs(price_change)
        
        ratio_85 = turnover / baseline['p85'] if baseline['p85'] > 0 else 0
        
        windows.append({
            'time': dt.strftime('%H:%M'),
            'hour': dt.hour,
            'minute': dt.minute,
            'price': float(row['lastPrice']),
            'amount_wan': float(amount / 10000),
            'turnover_pct': float(turnover * 100),
            'price_change_pct': float(price_change),
            'intraday_change_pct': float((row['lastPrice'] - day_open) / day_open * 100),
            'intensity_score': float(intensity),
            'ratio_85': float(ratio_85)
        })
        
        prev_price = row['lastPrice']
    
    if not windows:
        print("❌ 无有效窗口")
        return []
    
    # 按强度排序
    windows_sorted = sorted(windows, key=lambda x: x['intensity_score'], reverse=True)
    
    print(f"\n【强度Top {top_n}窗口】")
    print(f'{"时间":<8}{"价格":<10}{"涨幅%":<10}{"资金(万)":<12}{"强度":<12}{"Ratio":<10}')
    print('-'*62)
    for w in windows_sorted[:top_n]:
        print(f"{w['time']:<8}{w['price']:<10.2f}{w['price_change_pct']:<10.2f}"
              f"{w['amount_wan']:<12.1f}{w['intensity_score']:<12.0f}{w['ratio_85']:<10.2f}")
    
    return windows_sorted


if __name__ == '__main__':
    print('='*60)
    print('【CTO纠偏版V2】高潮窗口自动扫描')
    print('='*60)
    
    results = {}
    
    # 1. 志特新材12.31
    print("\n任务1: 志特新材 2025-12-31 (团队错误地只抓到10.1万)")
    zhite_1231 = scan_day('300986.SZ', '20251231', top_n=5)
    results['zhite_20251231'] = zhite_1231
    
    # 2. 志特新材01.05
    print("\n任务2: 志特新材 2026-01-05 (接力加速日)")
    zhite_0105 = scan_day('300986.SZ', '20260105', top_n=5)
    results['zhite_20260105'] = zhite_0105
    
    # 3. 网宿科技对比
    print("\n任务3: 网宿科技 2026-01-26")
    wangsu = scan_day('300017.SZ', '20260126', top_n=3)
    results['wangsu_20260126'] = wangsu
    
    # 4. 超捷股份对比  
    print("\n任务4: 超捷股份 2025-12-05")
    chaojie = scan_day('301005.SZ', '20251205', top_n=3)
    results['chaojie_20251205'] = chaojie
    
    # 保存结果
    output = Path('data/climax_v2_results.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ 结果保存: {output}")
    print(f"{'='*60}")
