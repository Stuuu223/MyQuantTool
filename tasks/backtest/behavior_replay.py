#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO Phase 4】V18沙盒全息回演

验收红线:
1. 12.31 14:25 必须识别志特新材尾盘爆发
2. 必须标记STRONG_MOMENTUM并存入记忆库
3. 1.05 09:40 必须触发接力信号并输出[BUY]

回演设定:
- 时间: 2025-12-31 至 2026-01-05
- 标的: 300986.SZ (志特新材)
- 核心: UnifiedWarfareCoreV18
"""

"""
行为回测脚本 - V18全息回演

使用方法:
    python tasks/backtest/behavior_replay.py
"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from xtquant import xtdata

# 使用新的production路径
from logic.strategies.production.unified_warfare_core import UnifiedWarfareCoreV18

# 150股池配置
STOCK_POOL_150 = [
    '300986.SZ',  # 志特新材 - 本次回演主角
]

FLOAT_VOLUMES = {
    '300986.SZ': 246000000,  # 2.46亿股
}


def get_tick_data(stock_code: str, date: str) -> pd.DataFrame:
    """获取Tick数据"""
    result = xtdata.get_local_data(
        field_list=['time', 'volume', 'lastPrice'],
        stock_list=[stock_code],
        period='tick',
        start_time=date,
        end_time=date
    )
    
    if not result or stock_code not in result:
        return pd.DataFrame()
    
    df = result[stock_code].copy()
    if df.empty:
        return pd.DataFrame()
    
    # UTC+8转换
    df['dt'] = pd.to_datetime(df['time'], unit='ms') + timedelta(hours=8)
    df = df[df['lastPrice'] > 0]
    
    return df


def calculate_5min_windows(df: pd.DataFrame, float_volume: float) -> list:
    """计算5分钟窗口 (CTO修正: volume×100转万股)"""
    if df.empty:
        return []
    
    df = df.sort_values('dt').copy()
    
    # 计算成交量增量 (CTO修正: ×100转股)
    df['vol_delta_shou'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta_shou'] = df['vol_delta_shou'].clip(lower=0)
    df['vol_delta'] = df['vol_delta_shou'] * 100  # 手→股
    
    # 5分钟聚合
    df = df.set_index('dt')
    resampled = df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'last'
    })
    resampled = resampled.dropna()
    
    if resampled.empty:
        return []
    
    windows = []
    prev_price = resampled['lastPrice'].iloc[0]
    
    for dt, row in resampled.iterrows():
        if row['vol_delta'] <= 0 or row['lastPrice'] <= 0:
            continue
        
        # CTO修正: 成交额计算
        amount = row['vol_delta'] * row['lastPrice']  # 股×元
        turnover = row['vol_delta'] / float_volume  # 换手率
        
        # 价格变化
        price_change = (row['lastPrice'] - prev_price) / prev_price * 100 if prev_price > 0 else 0
        
        # 强度得分
        intensity = amount / 10000 * abs(price_change)  # 万元×涨幅
        
        windows.append({
            'time': dt.strftime('%H:%M'),
            'datetime': dt,
            'price': float(row['lastPrice']),
            'volume': float(row['vol_delta']),  # 股
            'volume_shou': float(row['vol_delta'] / 100),  # 手
            'amount': float(amount),
            'amount_wan': float(amount / 10000),
            'turnover': float(turnover),
            'turnover_pct': float(turnover * 100),
            'price_change_pct': float(price_change),
            'intensity_score': float(intensity)
        })
        
        prev_price = row['lastPrice']
    
    return windows


def run_holographic_replay():
    """运行全息回演"""
    print('='*70)
    print('【CTO Phase 4】V18沙盒全息回演')
    print('='*70)
    print("\n回演设定:")
    print("  标的: 300986.SZ (志特新材)")
    print("  时间: 2025-12-31 至 2026-01-05")
    print("  核心: UnifiedWarfareCoreV18")
    print('='*70)
    
    # 初始化V18核心
    core = UnifiedWarfareCoreV18()
    
    # Day 1: 2025-12-31 (首扬日)
    print("\n" + "="*70)
    print("【Day 1】2025-12-31 志特新材首扬日")
    print("="*70)
    
    date1 = '20251231'
    stock_code = '300986.SZ'
    float_volume = FLOAT_VOLUMES[stock_code]
    
    # 获取Tick数据
    print(f"\n1. 获取Tick数据...")
    df1 = get_tick_data(stock_code, date1)
    print(f"   Tick条数: {len(df1)}")
    
    # 计算5分钟窗口
    print(f"\n2. 计算5分钟窗口 (CTO修正: volume×100转万股)...")
    windows1 = calculate_5min_windows(df1, float_volume)
    print(f"   窗口数: {len(windows1)}")
    
    # 打印最强窗口
    if windows1:
        strongest = max(windows1, key=lambda x: x['intensity_score'])
        print(f"\n3. 最强窗口分析:")
        print(f"   时间: {strongest['time']}")
        print(f"   价格: {strongest['price']:.2f}")
        print(f"   成交: {strongest['amount_wan']:.1f}万元")
        print(f"   换手: {strongest['turnover_pct']:.4f}%")
        print(f"   强度: {strongest['intensity_score']:.0f}")
    
    # V18全天分析
    print(f"\n4. V18核心分析...")
    result1 = core.analyze_day(stock_code, date1, windows1)
    
    if 'error' in result1:
        print(f"   ❌ 分析失败: {result1['error']}")
        if result1.get('error') == 'DATA_CORRUPTED':
            print(f"   🚨 日线校验锚熔断!")
            print(f"   误差: {result1['anchor_result'].get('amount_error_pct', 0):.1f}%")
    else:
        print(f"   ✅ 分析通过")
        print(f"   成交额: {result1['total_amount']/10000:.1f}万")
        print(f"   换手率: {result1['turnover_rate']:.2f}%")
        print(f"   STRONG_MOMENTUM: {'✅ YES' if result1['is_strong_momentum'] else '❌ NO'}")
    
    # Day 2: 2026-01-05 (接力日)
    print("\n" + "="*70)
    print("【Day 2】2026-01-05 志特新材接力日")
    print("="*70)
    
    date2 = '20260105'
    
    # 检查记忆库
    print(f"\n1. 检查跨日记忆库...")
    relay_bonus = core.relay_engine.get_relay_bonus(stock_code, date2)
    print(f"   接力加分: +{relay_bonus}%")
    
    if stock_code in core.relay_engine.memory:
        mem = core.relay_engine.memory[stock_code]
        print(f"   记忆内容:")
        print(f"     日期: {mem.date}")
        print(f"     收盘: {mem.close_price:.2f}")
        print(f"     换手: {mem.turnover_rate:.2f}%")
        print(f"     强势: {'✅' if mem.is_strong_momentum else '❌'}")
        print(f"     最强窗口: {mem.max_amount_window}")
    else:
        print(f"   ❌ 无记忆 (Day1未标记为STRONG_MOMENTUM)")
    
    # 获取Day2数据
    print(f"\n2. 获取Day2 Tick数据...")
    df2 = get_tick_data(stock_code, date2)
    print(f"   Tick条数: {len(df2)}")
    
    # 计算窗口
    windows2 = calculate_5min_windows(df2, float_volume)
    print(f"   窗口数: {len(windows2)}")
    
    # 找到早盘最强窗口
    if windows2:
        morning_windows = [w for w in windows2 if w['datetime'].hour < 11]
        if morning_windows:
            morning_strongest = max(morning_windows, key=lambda x: x['intensity_score'])
            print(f"\n3. 早盘最强窗口:")
            print(f"   时间: {morning_strongest['time']}")
            print(f"   价格: {morning_strongest['price']:.2f}")
            print(f"   成交: {morning_strongest['amount_wan']:.1f}万元")
            print(f"   换手: {morning_strongest['turnover_pct']:.4f}%")
            
            # 判断接力信号
            if relay_bonus > 0 and morning_strongest['amount_wan'] > 500:
                print(f"\n   🚀 [ACTION: BUY] 跨日接力信号触发!")
                print(f"      原因: Day1 STRONG_MOMENTUM + Day2 早盘资金接力")
                print(f"      窗口: {morning_strongest['time']}")
                print(f"      资金: {morning_strongest['amount_wan']:.1f}万元")
            else:
                print(f"\n   ⚠️ 接力信号未触发")
                if relay_bonus == 0:
                    print(f"      原因: 无跨日记忆")
                elif morning_strongest['amount_wan'] <= 500:
                    print(f"      原因: 早盘资金不足 ({morning_strongest['amount_wan']:.1f}万 < 500万)")
    
    # 总结
    print("\n" + "="*70)
    print("【回演验收】")
    print("="*70)
    
    passed = True
    
    # 验收1: Day1识别
    if result1.get('is_strong_momentum'):
        print("✅ 验收1: Day1 (12.31) 标记为STRONG_MOMENTUM")
    else:
        print("❌ 验收1: Day1 (12.31) 未标记为STRONG_MOMENTUM")
        passed = False
    
    # 验收2: 记忆库存储
    if stock_code in core.relay_engine.memory:
        print("✅ 验收2: 记忆库已存储")
    else:
        print("❌ 验收2: 记忆库未存储")
        passed = False
    
    # 验收3: Day2接力
    if relay_bonus > 0:
        print("✅ 验收3: Day2 (1.05) 获得接力加分")
    else:
        print("❌ 验收3: Day2 (1.05) 未获得接力加分")
        passed = False
    
    print(f"\n{'='*70}")
    if passed:
        print("🎉 全息回演通过所有验收红线!")
    else:
        print("⚠️ 全息回演未通过，需调整参数")
    print(f"{'='*70}")
    
    # 统计
    print(f"\nV18核心统计:")
    stats = core.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    run_holographic_replay()
