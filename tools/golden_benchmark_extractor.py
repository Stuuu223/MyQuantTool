#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO Phase 2】黄金标杆数据提取器
- 提取三只经典Breakout的真实盘面数据
- 反推系统阈值参数
- 修正Ratio计算：直接用所有历史窗口的85分位(取消双重过滤)

黄金标杆：
1. 300986 志特新材 - 2025.12.31 ~ 2026.01.05 (两个交易日起爆)
2. 300017 网宿科技 - 2026.01.26 (早盘起爆)
3. 301005 超捷股份 - 2025.12.05 (起爆)
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from xtquant import xtdata

# === 黄金标杆配置 ===
GOLDEN_BENCHMARKS = {
    '300986.SZ': {
        'name': '志特新材',
        'trigger_dates': ['20251231', '20260105'],  # 12/31起爆，1/05连板
        'trigger_time': '09:35',  # 预估起爆时间
        'description': '两个交易日起爆连板'
    },
    '300017.SZ': {
        'name': '网宿科技',
        'trigger_dates': ['20260126'],
        'trigger_time': '09:35',
        'description': '早盘推土机起爆'
    },
    '301005.SZ': {
        'name': '超捷股份',
        'trigger_dates': ['20251205'],
        'trigger_time': '09:35',
        'description': '典型 breakout'
    }
}

# 150股池
STOCK_POOL_150 = [
    '000547.SZ', '300058.SZ', '000592.SZ', '002792.SZ', '603778.SH', '301005.SZ',
    '603516.SH', '600343.SH', '300102.SZ', '688110.SH', '002149.SZ', '600879.SH',
    '300342.SZ', '600498.SH', '300456.SZ', '300475.SZ', '002050.SZ', '300136.SZ',
    '002131.SZ', '600986.SH', '600693.SH', '002361.SZ', '002565.SZ', '002202.SZ',
    '002465.SZ', '600118.SH', '603601.SH', '600151.SH', '002837.SZ', '300986.SZ',
    '301171.SZ', '002703.SZ', '002413.SZ', '603122.SH', '001208.SZ', '002759.SZ',
    '300442.SZ', '002639.SZ', '002788.SZ', '300762.SZ', '002342.SZ', '300115.SZ',
    '300548.SZ', '300308.SZ', '603667.SH', '301308.SZ', '688270.SH', '601138.SH',
    '300300.SZ', '000559.SZ', '300604.SZ', '000681.SZ', '300394.SZ', '002009.SZ',
    '600589.SH', '300418.SZ', '300502.SZ', '300620.SZ', '000859.SZ', '301232.SZ',
    '603986.SH', '001270.SZ', '300503.SZ', '300476.SZ', '300223.SZ', '300377.SZ',
    '000070.SZ', '300017.SZ', '601933.SH', '002195.SZ', '002536.SZ', '600865.SH',
    '300182.SZ', '301123.SZ', '600783.SH', '002228.SZ', '002757.SZ', '002156.SZ',
    '002163.SZ', '002506.SZ', '300364.SZ', '000066.SZ', '601698.SH', '002044.SZ',
    '600734.SH', '002151.SZ', '600266.SH', '300346.SZ', '002400.SZ', '002931.SZ',
    '300409.SZ', '603278.SH', '002119.SZ', '002173.SZ', '300118.SZ', '601399.SH',
    '000551.SZ', '600637.SH', '603696.SH', '300065.SZ', '001330.SZ', '002347.SZ',
    '002474.SZ', '603618.SH', '001331.SZ', '300900.SZ', '301611.SZ', '920576.BJ',
    '002702.SZ', '603698.SH', '000063.SZ', '002519.SZ', '603000.SH', '002995.SZ',
    '600105.SH', '002317.SZ', '603123.SH'
]

# 流通股本(从wanzhu数据提取)
FLOAT_VOLUMES = {
    '300017.SZ': 2306141629.0,
    '300058.SZ': 2480000000.0,
    '000547.SZ': 1589121062.0,
    '002792.SZ': 1231174354.0,
    '603778.SH': 671280000.0,
    '301005.SZ': 836269091.0,
    '300986.SZ': 246000000.0,  # 志特新材 约2.46亿流通股
    '600343.SH': 500000000.0,
    '300102.SZ': 800000000.0,
}

@dataclass
class BreakoutMetrics:
    """起爆时刻的核心指标"""
    stock_code: str
    stock_name: str
    date: str
    time: str
    
    # 基础数据
    price: float
    change_pct: float
    volume_5min: float  # 5分钟成交量(股)
    amount_5min: float  # 5分钟成交额(元)
    
    # Ratio指标(修正后)
    ratio_60d_85th: float  # 60天所有窗口85分位Ratio
    ratio_60d_75th: float  # 60天所有窗口75分位Ratio
    
    # 换手率指标(老板关注的)
    turnover_5min: float  # 5分钟换手率
    turnover_cumulative: float  # 当日累计换手
    
    # 横向排名(150股池)
    cross_section_rank: int  # 资金排名
    cross_section_total: int  # 总股数
    cross_section_percentile: float  # 排名百分比
    
    # Sustain指标
    sustain_ratio: float  # flow_15min / flow_5min
    
    # 波段数据(用于真实波幅比)
    wave_amplitude: float  # 起爆波段振幅
    atr_5d: float  # 5日平均真实振幅
    price_volatility_ratio: float  # 真实波幅比 = wave_amplitude / atr_5d


def get_tick_data(stock_code: str, date: str) -> Optional[pd.DataFrame]:
    """获取tick数据"""
    try:
        result = xtdata.get_local_data(
            field_list=['time', 'volume', 'lastPrice', 'open', 'high', 'low'],
            stock_list=[stock_code],
            period='tick',
            start_time=date,
            end_time=date
        )
        if result and stock_code in result:
            return result[stock_code]
        return None
    except Exception as e:
        print(f"❌ 获取{stock_code} {date}数据失败: {e}")
        return None


def calculate_historical_baseline_all_windows(
    stock_code: str,
    target_date: str,
    lookback_days: int = 60,
    percentiles: List[int] = [75, 85, 90]
) -> Dict:
    """
    CTO修正：用所有历史窗口计算基准(取消双重过滤)
    直接用过去60天所有5分钟窗口的指定分位
    """
    float_volume = FLOAT_VOLUMES.get(stock_code, 1e9)
    
    # 获取历史日期(排除目标日期)
    end_date = datetime.strptime(target_date, '%Y%m%d')
    dates = []
    current = end_date - timedelta(days=1)
    while len(dates) < lookback_days and current > end_date - timedelta(days=120):
        if current.weekday() < 5:
            dates.append(current.strftime('%Y%m%d'))
        current -= timedelta(days=1)
    
    all_turnovers = []
    valid_days = 0
    
    print(f"  计算{stock_code}历史基准(取消双重过滤)...")
    print(f"  回看{lookback_days}个交易日, 从{dates[-1]}到{dates[0]}")
    
    for date in dates[:lookback_days]:
        tick_df = get_tick_data(stock_code, date)
        if tick_df is None or tick_df.empty:
            continue
        
        # UTC+8转换
        tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms') + timedelta(hours=8)
        tick_df.set_index('dt', inplace=True)
        
        # 过滤无效数据
        tick_df = tick_df[tick_df['lastPrice'] > 0]
        if tick_df.empty:
            continue
        
        # 计算5分钟成交量
        tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
        tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
        
        # 5分钟聚合
        resampled = tick_df.resample('5min', label='left', closed='left').agg({
            'vol_delta': 'sum',
            'lastPrice': 'mean'
        })
        
        for _, row in resampled.iterrows():
            if row['vol_delta'] > 0 and row['lastPrice'] > 0:
                turnover = row['vol_delta'] / float_volume
                all_turnovers.append(turnover)
        
        valid_days += 1
    
    if not all_turnovers:
        return None
    
    # 直接计算所有窗口的分位数(CTO修正: 取消活跃窗口过滤)
    baselines = {}
    for p in percentiles:
        baselines[f'p{p}'] = float(np.percentile(all_turnovers, p))
    
    print(f"  ✅ 有效交易日:{valid_days}, 总窗口数:{len(all_turnovers)}")
    print(f"  基准(85分位): {baselines['p85']:.4e} ({baselines['p85']*100:.4f}%)")
    print(f"  基准(75分位): {baselines['p75']:.4e} ({baselines['p75']*100:.4f}%)")
    
    return {
        'baselines': baselines,
        'total_windows': len(all_turnovers),
        'valid_days': valid_days,
        'median': float(np.percentile(all_turnovers, 50)),
        'mean': float(np.mean(all_turnovers))
    }


def analyze_breakout_moment(
    stock_code: str,
    date: str,
    trigger_time: str = '09:35'
) -> Optional[BreakoutMetrics]:
    """分析起爆时刻的完整指标"""
    config = GOLDEN_BENCHMARKS.get(stock_code)
    if not config:
        return None
    
    print(f"\n{'='*70}")
    print(f"【黄金标杆】{stock_code} {config['name']} - {date}")
    print(f"描述: {config['description']}")
    print(f"{'='*70}")
    
    # 1. 计算历史基准(CTO修正版)
    baseline_data = calculate_historical_baseline_all_windows(stock_code, date)
    if not baseline_data:
        print("❌ 无法计算历史基准")
        return None
    
    # 2. 获取当日tick数据
    tick_df = get_tick_data(stock_code, date)
    if tick_df is None or tick_df.empty:
        print("❌ 无法获取当日tick数据")
        return None
    
    # UTC+8转换
    tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms') + timedelta(hours=8)
    tick_df.set_index('dt', inplace=True)
    tick_df = tick_df[tick_df['lastPrice'] > 0]
    
    if tick_df.empty:
        print("❌ 当日无有效价格数据")
        return None
    
    # 3. 计算5分钟窗口
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
    
    resampled = tick_df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': 'last',
        'open': 'first',
        'high': 'max',
        'low': 'min'
    })
    
    float_volume = FLOAT_VOLUMES.get(stock_code, 1e9)
    
    # 4. 找到起爆时刻窗口
    target_hour = int(trigger_time.split(':')[0])
    target_minute = int(trigger_time.split(':')[1])
    
    breakout_window = None
    for dt, row in resampled.iterrows():
        if dt.hour == target_hour and dt.minute == target_minute:
            if row['vol_delta'] > 0 and row['lastPrice'] > 0:
                breakout_window = {
                    'time': dt,
                    'volume': row['vol_delta'],
                    'price': row['lastPrice'],
                    'amount': row['vol_delta'] * row['lastPrice'],
                    'turnover': row['vol_delta'] / float_volume
                }
                break
    
    if not breakout_window:
        print(f"❌ 未找到{trigger_time}窗口")
        # 打印可用窗口供参考
        print("\n可用窗口:")
        for dt, row in resampled.head(10).iterrows():
            print(f"  {dt.strftime('%H:%M')}: 量{row['vol_delta']/10000:.1f}万, 价{row['lastPrice']:.2f}")
        return None
    
    print(f"\n起爆窗口 ({trigger_time}):")
    print(f"  价格: {breakout_window['price']:.2f}")
    print(f"  5分钟量: {breakout_window['volume']/10000:.1f}万股")
    print(f"  5分钟额: {breakout_window['amount']/10000:.1f}万元")
    print(f"  5分钟换手: {breakout_window['turnover']*100:.4f}%")
    
    # 5. 计算Ratio(CTO修正: 用所有窗口的85分位)
    ratio_85th = breakout_window['turnover'] / baseline_data['baselines']['p85'] if baseline_data['baselines']['p85'] > 0 else 0
    ratio_75th = breakout_window['turnover'] / baseline_data['baselines']['p75'] if baseline_data['baselines']['p75'] > 0 else 0
    
    print(f"\n【CTO修正后Ratio】(取消双重过滤)")
    print(f"  vs 60天85分位: {ratio_85th:.2f}")
    print(f"  vs 60天75分位: {ratio_75th:.2f}")
    
    # 6. 计算Sustain (15分钟/5分钟)
    sustain = calculate_sustain(resampled, target_hour, target_minute)
    print(f"\nSustain (15min/5min): {sustain:.2f}")
    
    # 返回结果
    return BreakoutMetrics(
        stock_code=stock_code,
        stock_name=config['name'],
        date=date,
        time=trigger_time,
        price=breakout_window['price'],
        change_pct=0,  # 需要前收盘价计算
        volume_5min=breakout_window['volume'],
        amount_5min=breakout_window['amount'],
        ratio_60d_85th=ratio_85th,
        ratio_60d_75th=ratio_75th,
        turnover_5min=breakout_window['turnover'],
        turnover_cumulative=0,  # 需计算
        cross_section_rank=0,  # 需150股池数据
        cross_section_total=150,
        cross_section_percentile=0,
        sustain_ratio=sustain,
        wave_amplitude=0,  # 需计算
        atr_5d=0,
        price_volatility_ratio=0
    )


def calculate_sustain(resampled_df: pd.DataFrame, hour: int, minute: int) -> float:
    """计算Sustain比率: 15分钟资金 / 5分钟资金"""
    target_idx = None
    for i, (dt, _) in enumerate(resampled_df.iterrows()):
        if dt.hour == hour and dt.minute == minute:
            target_idx = i
            break
    
    if target_idx is None or target_idx < 2:
        return 0.0
    
    # 5分钟资金(当前窗口)
    flow_5min = resampled_df.iloc[target_idx]['vol_delta'] * resampled_df.iloc[target_idx]['lastPrice']
    
    # 15分钟资金(前3个窗口累积)
    start_idx = max(0, target_idx - 2)
    flow_15min = 0
    for i in range(start_idx, target_idx + 1):
        if resampled_df.iloc[i]['vol_delta'] > 0:
            flow_15min += resampled_df.iloc[i]['vol_delta'] * resampled_df.iloc[i]['lastPrice']
    
    if flow_5min <= 0:
        return 0.0
    
    return flow_15min / flow_5min


if __name__ == '__main__':
    print('='*70)
    print('【CTO Phase 2】黄金标杆数据提取')
    print('='*70)
    
    results = []
    
    # 标杆1: 网宿科技 (01-26)
    result = analyze_breakout_moment('300017.SZ', '20260126', '09:35')
    if result:
        results.append(asdict(result))
    
    # 标杆2: 超捷股份 (12-05)
    result = analyze_breakout_moment('301005.SZ', '20251205', '09:35')
    if result:
        results.append(asdict(result))
    
    # 标杆3: 志特新材 (12-31起爆)
    result = analyze_breakout_moment('300986.SZ', '20251231', '09:35')
    if result:
        results.append(asdict(result))
    
    # 汇总输出
    print(f"\n{'='*70}")
    print('【黄金标杆汇总】')
    print(f"{'='*70}")
    
    for r in results:
        print(f"\n{r['stock_code']} {r['stock_name']} - {r['date']}")
        print(f"  Ratio(85分位): {r['ratio_60d_85th']:.2f}")
        print(f"  Ratio(75分位): {r['ratio_60d_75th']:.2f}")
        print(f"  Sustain: {r['sustain_ratio']:.2f}")
        print(f"  5min换手: {r['turnover_5min']*100:.4f}%")
        print(f"  5min资金: {r['amount_5min']/10000:.1f}万")
    
    # 保存结果
    output_file = Path('data/golden_benchmarks.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 结果已保存: {output_file}")
