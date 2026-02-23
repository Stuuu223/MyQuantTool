#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO分层动态Ratio系统】
高频票(300017/300058): 90分位基准, ratio阈值2.0
低频票(000547/603778): 75分位基准, ratio阈值5.0
+ 横向相对强度排名(150股池Top 2%)
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from xtquant import xtdata

# === 股票流动性分层配置 ===
TIERED_CONFIG = {
    'high_freq': {  # 高频活跃票
        'stocks': ['300017.SZ', '300058.SZ', '000592.SZ'],
        'baseline_percentile': 90,  # 90分位
        'ratio_threshold': 2.0,      # 阈值2.0
        'description': '平时上蹿下跳，用极端活跃基准'
    },
    'mid_freq': {  # 中频票
        'stocks': ['002792.SZ', '603778.SH', '301005.SZ'],
        'baseline_percentile': 80,
        'ratio_threshold': 3.0,
        'description': '中等活跃度'
    },
    'low_freq': {  # 低频冷门票
        'stocks': ['000547.SZ', '603516.SH'],
        'baseline_percentile': 75,  # 75分位
        'ratio_threshold': 5.0,      # 阈值5.0
        'description': '平时一潭死水，爆发时ratio容易达到5+'
    }
}

# 流通股本配置
FLOAT_VOLUMES = {
    '300017.SZ': 2306141629.0,   # 23.06亿股
    '300058.SZ': 2480000000.0,   # 24.8亿股
    '000547.SZ': 1589121062.0,   # 15.89亿股
    '002792.SZ': 1231174354.0,
    '603778.SH': 671280000.0,
    '301005.SZ': 836269091.0,
    '000592.SZ': 1938784000.0,
    '603516.SH': 2032682790.0,
}

def get_turnover_series(tick_df, float_volume):
    """计算5分钟换手率序列 - UTC+8修正"""
    if tick_df.empty or float_volume <= 0:
        return []
    
    tick_df = tick_df.copy()
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
    
    # UTC+8转换
    tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms') + timedelta(hours=8)
    tick_df.set_index('dt', inplace=True)
    
    # 过滤价格为0的数据
    tick_df = tick_df[tick_df['lastPrice'] > 0]
    
    if tick_df.empty:
        return []
    
    # 5分钟聚合
    resampled = tick_df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'mean'
    })
    
    result = []
    for dt, row in resampled.iterrows():
        if row['vol_delta'] > 0 and row['lastPrice'] > 0:
            turnover = row['vol_delta'] / float_volume
            amount = row['vol_delta'] * row['lastPrice']
            result.append({
                'time': dt,
                'turnover': turnover,
                'amount': amount,
                'hour': dt.hour,
                'minute': dt.minute
            })
    return result

def calculate_tiered_baseline(stock_code, tier_config, lookback_days=60):
    """计算分层动态基准"""
    print(f'\n{"="*60}')
    print(f'计算 {stock_code} 的分层基准')
    print(f'分层: {tier_config["description"]}')
    print(f'分位点: {tier_config["baseline_percentile"]}th')
    print(f'Ratio阈值: {tier_config["ratio_threshold"]}')
    
    float_volume = FLOAT_VOLUMES.get(stock_code)
    if not float_volume:
        print(f'❌ 未找到 {stock_code} 的流通股本配置')
        return None
    
    # 获取最近60个交易日
    days = []
    current_date = datetime.now()
    while len(days) < lookback_days * 2:
        if current_date.weekday() < 5:
            days.append(current_date.strftime('%Y%m%d'))
        current_date -= timedelta(days=1)
    candidate_dates = days[:lookback_days]
    
    all_turnovers = []
    valid_days = 0
    
    for date in candidate_dates:
        try:
            result = xtdata.get_local_data(
                field_list=['time', 'volume', 'lastPrice'],
                stock_list=[stock_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if result and stock_code in result:
                tick_df = result[stock_code]
                if not tick_df.empty:
                    windows = get_turnover_series(tick_df, float_volume)
                    if windows:
                        turnovers = [w['turnover'] for w in windows]
                        all_turnovers.extend(turnovers)
                        valid_days += 1
        except:
            continue
    
    if not all_turnovers or valid_days < 5:
        print(f'❌ 有效数据不足')
        return None
    
    # 计算分位数基准
    baseline = np.percentile(all_turnovers, tier_config['baseline_percentile'])
    median = np.percentile(all_turnovers, 50)
    
    print(f'✅ 计算完成:')
    print(f'   有效交易日: {valid_days}天')
    print(f'   总窗口数: {len(all_turnovers)}')
    print(f'   {tier_config["baseline_percentile"]}分位基准: {baseline:.2e} ({baseline*100:.4f}%)')
    print(f'   中位数: {median:.2e} ({median*100:.4f}%)')
    
    return {
        'baseline': float(baseline),
        'median': float(median),
        'ratio_threshold': tier_config['ratio_threshold'],
        'baseline_percentile': tier_config['baseline_percentile'],
        'valid_days': valid_days
    }

def verify_morning_breakout(stock_code, date, config):
    """验证早盘起爆"""
    print(f'\n{"="*60}')
    print(f'验证 {stock_code} 在 {date} 早盘起爆')
    print(f'{"="*60}')
    
    float_volume = FLOAT_VOLUMES.get(stock_code)
    if not float_volume:
        return
    
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice'],
        stock_list=[stock_code],
        period='tick',
        start_time=date,
        end_time=date
    )
    
    if not result or stock_code not in result:
        print('❌ 未找到数据')
        return
    
    tick_df = result[stock_code]
    windows = get_turnover_series(tick_df, float_volume)
    
    if not windows:
        print('❌ 无有效窗口')
        return
    
    # 计算当日活跃基准
    day_avg = np.mean([w['amount'] for w in windows])
    active_windows = [w for w in windows if w['amount'] > day_avg]
    
    if not active_windows:
        print('❌ 无活跃窗口')
        return
    
    # 使用配置的分位点计算基准
    baseline = np.percentile(
        [w['turnover'] for w in active_windows],
        config['baseline_percentile']
    )
    
    print(f'当日活跃窗口数: {len(active_windows)}')
    print(f'动态基准({config["baseline_percentile"]}分位): {baseline:.2e}')
    print(f'Ratio阈值: {config["ratio_threshold"]}')
    
    print(f'\n早盘窗口分析:')
    print(f'{"时间":<12} {"涨幅%":<10} {"ratio":<10} {"状态":<15}')
    print('-'*50)
    
    pre_close = 11.48 if '300017' in stock_code else 26.91  # 简化处理
    
    triggered = False
    for w in windows:
        if not (9 <= w['hour'] <= 10):
            continue
        
        ratio = w['turnover'] / baseline if baseline > 0 else 0
        change_pct = (w['amount'] / w['turnover'] / float_volume - pre_close) / pre_close * 100
        
        time_str = f'{w["hour"]:02d}:{w["minute"]:02d}'
        
        status = ''
        if ratio >= config['ratio_threshold']:
            status = '✅ 触发信号'
            triggered = True
        elif ratio >= config['ratio_threshold'] * 0.7:
            status = '⚠️ 接近阈值'
        
        print(f'{time_str:<12} {change_pct:>8.2f} {ratio:>10.2f} {status:<15}')
    
    return triggered

def cross_sectional_ranking(target_stock, date, top_pct=0.02):
    """横向相对强度排名 - 150股池Top 2%"""
    print(f'\n{"="*60}')
    print(f'【横向相对强度排名】{target_stock} 在 {date}')
    print(f'目标: 排名前 {top_pct*100:.1f}% (约{int(150*top_pct)}只股)')
    print(f'{"="*60}')
    
    # 获取300017在09:35的数据
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice'],
        stock_list=[target_stock],
        period='tick',
        start_time=date,
        end_time=date
    )
    
    if not result or target_stock not in result:
        print('❌ 未找到目标股数据')
        return
    
    tick_df = result[target_stock]
    windows = get_turnover_series(tick_df, FLOAT_VOLUMES.get(target_stock, 1))
    
    # 找到09:35窗口
    target_window = None
    for w in windows:
        if w['hour'] == 9 and w['minute'] == 35:
            target_window = w
            break
    
    if not target_window:
        print('❌ 未找到09:35窗口')
        return
    
    target_amount = target_window['amount']
    print(f'\n目标股 {target_stock} 09:35资金: {target_amount/10000:.2f}万')
    
    # 模拟150股池数据（用于演示，实际应从数据库/配置读取）
    # 基于历史经验，300017的量能通常在前10%
    simulated_pool = generate_simulated_pool(date, target_amount)
    
    # 排名计算
    all_amounts = [s['amount'] for s in simulated_pool]
    all_amounts.append(target_amount)
    all_amounts.sort(reverse=True)
    
    rank = all_amounts.index(target_amount) + 1
    total = len(all_amounts)
    percentile = (rank / total) * 100
    
    print(f'\n在{total}只股中排名: 第{rank}名 (前{percentile:.1f}%)')
    
    if percentile <= top_pct * 100:
        print(f'✅ 进入Top {top_pct*100:.0f}%！横向强度达标！')
        return True
    else:
        print(f'⚠️ 未进入Top {top_pct*100:.0f}%，横向强度不足')
        return False

def generate_simulated_pool(date, target_amount):
    """生成模拟股池数据用于排名测试"""
    # 基于经验数据的模拟
    pool = [
        {'code': '300XXX.SZ', 'amount': target_amount * 2.5},   # 更高
        {'code': '002XXX.SZ', 'amount': target_amount * 1.8},
        {'code': '600XXX.SH', 'amount': target_amount * 1.5},
        {'code': '301XXX.SZ', 'amount': target_amount * 1.3},
        {'code': '603XXX.SH', 'amount': target_amount * 1.2},
        {'code': '000XXX.SZ', 'amount': target_amount * 1.1},
    ]
    
    # 添加一些比目标低的
    for i in range(20):
        pool.append({'code': f'模拟{i:03d}', 'amount': target_amount * (0.95 - i*0.04)})
    
    return pool

if __name__ == '__main__':
    print('='*70)
    print('【CTO分层动态Ratio系统】验证')
    print('='*70)
    
    # 测试300017(高频票) - 分层基准
    config_300017 = calculate_tiered_baseline('300017.SZ', TIERED_CONFIG['high_freq'])
    if config_300017:
        verify_morning_breakout('300017.SZ', '20260126', config_300017)
    
    # 测试300017 - 横向排名
    cross_sectional_ranking('300017.SZ', '20260126', top_pct=0.02)
    
    # 测试000547(低频票) - 分层基准
    config_000547 = calculate_tiered_baseline('000547.SZ', TIERED_CONFIG['low_freq'])
    if config_000547:
        verify_morning_breakout('000547.SZ', '20260120', config_000547)
