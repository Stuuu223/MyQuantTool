#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
志特新材1月5日右侧起爆深度分析
验证09:40开火信号

⚠️ 紧急修复说明：
- 修复前：使用 (价格 - 开盘价) / 开盘价 计算涨幅（日内涨幅）❌
- 修复后：使用 (价格 - 昨收价) / 昨收价 计算涨幅（真实涨幅）✅
- 志特新材是创业板，正确涨幅应接近20%涨停
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from xtquant import xtdata

# 导入数据服务
from logic.services.data_service import data_service

def analyze_zhitexincai_0105():
    """分析志特新材1月5日表现"""
    
    stock_code = '300986.SZ'
    date = '20260105'
    date_fmt = '2026-01-05'  # 用于DataService的日期格式
    
    print('='*80)
    print('【志特新材 1月5日 右侧起爆分析】')
    print('='*80)
    print(f'股票代码: {stock_code}')
    print(f'分析日期: {date}')
    print()
    
    # 🔥 修复：获取昨收价（正确涨幅基准）
    print('【数据准备】')
    pre_close = data_service.get_pre_close(stock_code, date_fmt)
    if pre_close <= 0:
        print(f'❌ 无法获取昨收价，使用默认估算')
        # 备用：尝试从tick数据估算
        temp_result = xtdata.get_local_data(
            field_list=['time', 'lastPrice'],
            stock_list=[stock_code],
            period='tick',
            start_time=date,
            end_time=date
        )
        if temp_result and stock_code in temp_result and not temp_result[stock_code].empty:
            # 用第一分钟最低价的98%作为昨收估算
            first_min = temp_result[stock_code]['lastPrice'].iloc[:100].min()
            pre_close = first_min * 0.98
        else:
            pre_close = 20.0  # 默认估算
    
    print(f'昨收价: {pre_close:.2f}（涨幅计算基准）')
    print()
    
    # 获取Tick数据
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice', 'amount'],
        stock_list=[stock_code],
        period='tick',
        start_time=date,
        end_time=date
    )
    
    if not result or stock_code not in result:
        print('❌ 无法获取Tick数据')
        return
    
    df = result[stock_code].copy()
    if df.empty:
        print('❌ Tick数据为空')
        return
    
    # UTC+8转换
    df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
    df = df[df['lastPrice'] > 0]
    
    print(f'✅ Tick记录数: {len(df)}')
    print(f'时间范围: {df["dt"].min()} ~ {df["dt"].max()}')
    print()
    
    # 计算成交量增量 (手→股)
    df['vol_delta_shou'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta_shou'] = df['vol_delta_shou'].clip(lower=0)
    df['vol_delta'] = df['vol_delta_shou'] * 100  # 手→股
    
    # 计算成交额
    df['amount_delta'] = df['vol_delta'] * df['lastPrice']
    
    # 09:30开盘数据
    morning_start = df[df['dt'].dt.time >= pd.Timestamp('09:30:00').time()]
    if morning_start.empty:
        print('❌ 无早盘数据')
        return
    
    open_price = morning_start['lastPrice'].iloc[0]
    # 🔥 修复：计算高开溢价（相对于昨收）
    open_gap = (open_price - pre_close) / pre_close * 100
    print(f'开盘价: {open_price:.2f}')
    print(f'高开溢价: {open_gap:+.2f}%（相对昨收{pre_close:.2f}）')
    
    # 09:40数据分析
    time_0940 = pd.Timestamp(f'{date[:4]}-{date[4:6]}-{date[6:]} 09:40:00')
    df_0940 = df[df['dt'] <= time_0940]
    
    if df_0940.empty:
        print('❌ 无09:40前数据')
        return
    
    price_0940 = df_0940['lastPrice'].iloc[-1]
    volume_0940 = df_0940['vol_delta'].sum()
    amount_0940 = df_0940['amount_delta'].sum()
    # 🔥 修复：使用昨收价计算真实涨幅
    change_pct_0940 = (price_0940 - pre_close) / pre_close * 100
    # 保留日内涨幅用于参考
    intraday_change_0940 = (price_0940 - open_price) / open_price * 100
    
    print()
    print('-'*80)
    print('【09:40关键指标】')
    print('-'*80)
    print(f'昨收价: {pre_close:.2f}')
    print(f'开盘价: {open_price:.2f}')
    print(f'09:40价格: {price_0940:.2f}')
    print(f'09:40真实涨幅: {change_pct_0940:+.2f}%（相对昨收）✅')
    print(f'09:40日内涨幅: {intraday_change_0940:+.2f}%（相对开盘）')
    print(f'09:40前成交量: {volume_0940/10000:.1f}万股')
    print(f'09:40前成交额: {amount_0940/10000:.1f}万元')
    print()
    
    # 5分钟窗口分析
    df = df.set_index('dt')
    resampled = df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'amount_delta': 'sum',
        'lastPrice': 'last'
    }).dropna()
    
    print('-'*80)
    print('【早盘5分钟窗口】')
    print('-'*80)
    
    morning_windows = resampled[resampled.index.time <= pd.Timestamp('10:30:00').time()]
    for idx, row in morning_windows.head(6).iterrows():
        time_str = idx.strftime('%H:%M')
        vol_wan = row['vol_delta'] / 10000
        amount_wan = row['amount_delta'] / 10000
        price = row['lastPrice']
        print(f'{time_str} - 量:{vol_wan:6.1f}万股 额:{amount_wan:8.1f}万元 价:{price:.2f}')
    
    # 全天统计
    print()
    print('-'*80)
    print('【全天统计】')
    print('-'*80)
    
    total_volume = df['vol_delta'].sum()
    total_amount = df['amount_delta'].sum()
    close_price = df['lastPrice'].iloc[-1]
    high_price = df['lastPrice'].max()
    low_price = df['lastPrice'].min()
    # 🔥 修复：使用昨收价计算真实涨幅
    day_change = (close_price - pre_close) / pre_close * 100
    # 保留日内涨幅用于参考
    intraday_change = (close_price - open_price) / open_price * 100
    # 计算涨停状态（创业板20%）
    is_limit_up = day_change >= 19.5
    
    print(f'全天成交量: {total_volume/10000:.1f}万股')
    print(f'全天成交额: {total_amount/10000:.1f}万元')
    print(f'最高价: {high_price:.2f}')
    print(f'最低价: {low_price:.2f}')
    print(f'收盘价: {close_price:.2f}')
    print(f'昨收价: {pre_close:.2f}')
    print(f'全天真实涨幅: {day_change:+.2f}%（相对昨收）{"🚀 涨停!" if is_limit_up else ""}✅')
    print(f'全天日内涨幅: {intraday_change:+.2f}%（相对开盘）')
    print()
    
    # 信号判断
    print('-'*80)
    print('【右侧起爆信号判断】')
    print('-'*80)
    
    signals = []
    
    # 信号1: 09:40前放量
    if volume_0940 > 1000000:  # 100万股
        signals.append('✅ 09:40前放量 > 100万股')
    else:
        signals.append('❌ 09:40前放量不足')
    
    # 信号2: 09:40前上涨（使用真实涨幅）
    if change_pct_0940 > 2:
        signals.append(f'✅ 09:40前真实涨幅 {change_pct_0940:+.2f}% > 2%')
    elif change_pct_0940 > 0:
        signals.append(f'⚠️ 09:40前小幅上涨 {change_pct_0940:+.2f}%')
    else:
        signals.append(f'❌ 09:40前下跌 {change_pct_0940:+.2f}%')
    
    # 信号3: 全天强势（使用真实涨幅）
    if day_change > 15:  # 创业板强势标准
        signals.append(f'✅ 全天强势上涨 {day_change:+.2f}% > 15%（涨停附近）')
    elif day_change > 5:
        signals.append(f'✅ 全天上涨 {day_change:+.2f}% > 5%')
    elif day_change > 0:
        signals.append(f'⚠️ 全天小幅上涨 {day_change:+.2f}%')
    else:
        signals.append(f'❌ 全天下跌 {day_change:+.2f}%')
    
    for sig in signals:
        print(sig)
    
    print()
    print('='*80)
    
    # 综合判断
    bullish_signals = sum(1 for s in signals if s.startswith('✅'))
    if bullish_signals >= 2:
        print('🚀 【右侧起爆确认】志特新材1月5日符合右侧起爆特征！')
    elif bullish_signals >= 1:
        print('⚠️ 【信号一般】志特新材1月5日有起爆迹象但不够强烈')
    else:
        print('❌ 【无起爆信号】志特新材1月5日表现平淡')
    
    print('='*80)
    
    return {
        'stock_code': stock_code,
        'date': date,
        'pre_close': pre_close,  # 🔥 新增：昨收价
        'open_price': open_price,
        'open_gap': open_gap,  # 🔥 新增：高开溢价
        'price_0940': price_0940,
        'change_pct_0940': change_pct_0940,  # 🔥 修复：真实涨幅（相对昨收）
        'intraday_change_0940': intraday_change_0940,  # 🔥 新增：日内涨幅（相对开盘）
        'volume_0940': volume_0940,
        'amount_0940': amount_0940,
        'close_price': close_price,
        'day_change': day_change,  # 🔥 修复：真实涨幅（相对昨收）
        'intraday_change': intraday_change,  # 🔥 新增：日内涨幅（相对开盘）
        'is_limit_up': is_limit_up,  # 🔥 新增：是否涨停
        'bullish_signals': bullish_signals
    }

if __name__ == '__main__':
    result = analyze_zhitexincai_0105()
