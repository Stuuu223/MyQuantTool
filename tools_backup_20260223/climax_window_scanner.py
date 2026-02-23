#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【CTO纠偏版】高潮窗口自动扫描器

解决团队"刻舟求剑"问题：
- 不再机械套用09:35
- 自动扫描全天4800个tick
- 找出真正推动涨幅的资金高潮

志特新材案例：
- 12.31拉出+8.97%光头阳线
- 团队错误：套用09:35，只抓到10.1万
- 正确做法：扫描全天，找出真正的资金高潮窗口
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

# 流通股本配置
FLOAT_VOLUMES = {
    '300017.SZ': 2306141629.0,
    '300058.SZ': 2480000000.0,
    '000547.SZ': 1589121062.0,
    '301005.SZ': 836269091.0,
    '300986.SZ': 246000000.0,  # 志特新材 2.46亿
}

@dataclass
class ClimaxWindow:
    """高潮窗口数据结构"""
    stock_code: str
    date: str
    time: str
    
    # 价格数据
    price: float
    open_price: float
    high_price: float
    low_price: float
    change_pct: float  # 相对前收涨幅
    intraday_change_pct: float  # 日内涨幅(从开盘算起)
    
    # 资金数据
    volume: float  # 成交量(股)
    amount: float  # 成交额(元)
    turnover: float  # 换手率
    
    # 强度指标
    intensity_score: float  # 量价共振得分
    money_flow_ratio: float  # 资金流向占比(估算)
    
    # 历史对比
    ratio_vs_85th: float  # vs 60天85分位
    ratio_vs_75th: float  # vs 60天75分位
    
    # 上下文
    context_prev_3: List[Dict]  # 前3个窗口
    context_next_3: List[Dict]  # 后3个窗口


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


def calculate_historical_baseline(stock_code: str, target_date: str) -> Optional[Dict]:
    """计算历史基准(CTO修正版: 直接用所有窗口85分位)"""
    float_volume = FLOAT_VOLUMES.get(stock_code, 1e9)
    
    end_date = datetime.strptime(target_date, '%Y%m%d')
    dates = []
    current = end_date - timedelta(days=1)
    while len(dates) < 60 and current > end_date - timedelta(days=120):
        if current.weekday() < 5:
            dates.append(current.strftime('%Y%m%d'))
        current -= timedelta(days=1)
    
    all_turnovers = []
    for date in dates[:60]:
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
                    tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms') + timedelta(hours=8)
                    tick_df.set_index('dt', inplace=True)
                    tick_df = tick_df[tick_df['lastPrice'] > 0]
                    
                    if not tick_df.empty:
                        tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
                        tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
                        
                        resampled = tick_df.resample('5min', label='left', closed='left').agg({
                            'vol_delta': 'sum',
                            'lastPrice': 'mean'
                        })
                        
                        for _, row in resampled.iterrows():
                            if row['vol_delta'] > 0 and row['lastPrice'] > 0:
                                turnover = row['vol_delta'] / float_volume
                                all_turnovers.append(turnover)
        except:
            continue
    
    if len(all_turnovers) < 100:
        return None
    
    return {
        'p85': float(np.percentile(all_turnovers, 85)),
        'p75': float(np.percentile(all_turnovers, 75)),
        'p50': float(np.percentile(all_turnovers, 50)),
        'total_windows': len(all_turnovers)
    }


def scan_climax_windows(
    stock_code: str,
    date: str,
    top_n: int = 5
) -> List[ClimaxWindow]:
    """
    自动扫描全天的"高潮窗口"
    
    策略：
    1. 计算每个5分钟窗口的资金量
    2. 计算每个窗口对全天涨幅的贡献
    3. 计算量价共振得分 = 资金量 × 涨幅贡献
    4. 返回得分最高的Top N窗口
    """
    print(f"\n{'='*70}")
    print(f"【高潮窗口扫描】{stock_code} - {date}")
    print(f"{'='*70}")
    
    float_volume = FLOAT_VOLUMES.get(stock_code, 1e9)
    
    # 1. 获取历史基准
    baseline = calculate_historical_baseline(stock_code, date)
    if not baseline:
        print("❌ 无法计算历史基准")
        return []
    
    print(f"历史基准: 85分位={baseline['p85']:.4e}, 75分位={baseline['p75']:.4e}")
    
    # 2. 获取当日tick数据
    tick_df = get_tick_data(stock_code, date)
    if tick_df is None or tick_df.empty:
        print("❌ 无法获取当日数据")
        return []
    
    # UTC+8转换
    tick_df = tick_df.copy()
    tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms') + timedelta(hours=8)
    tick_df.set_index('dt', inplace=True)
    tick_df = tick_df[tick_df['lastPrice'] > 0]
    
    if tick_df.empty:
        print("❌ 当日无有效价格数据")
        return []
    
    # 获取开盘价和收盘价
    day_open = tick_df['lastPrice'].iloc[0]
    day_high = tick_df['lastPrice'].max()
    day_close = tick_df['lastPrice'].iloc[-1]
    day_change_pct = (day_close - day_open) / day_open * 100
    
    print(f"\n全天概况:")
    print(f"  开盘: {day_open:.2f}, 收盘: {day_close:.2f}")
    print(f"  最高: {day_high:.2f}")
    print(f"  日内涨幅: {day_change_pct:.2f}%")
    
    # 3. 计算5分钟窗口
    tick_df = tick_df.copy()
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)
    
    resampled = tick_df.resample('5min', label='left', closed='left').agg({
        'vol_delta': 'sum',
        'lastPrice': ['first', 'last', 'max', 'min']
    })
    
    # 扁平化列名
    resampled.columns = ['volume', 'open', 'close', 'high', 'low']
    
    # 4. 计算每个窗口的指标
    windows = []
    for dt, row in resampled.iterrows():
        if row['volume'] <= 0 or row['close'] <= 0:
            continue
        
        amount = row['volume'] * row['close']
        turnover = row['volume'] / float_volume
        
        # 日内涨幅贡献(从该窗口开盘到收盘)
        window_change_pct = (row['close'] - row['open']) / row['open'] * 100 if row['open'] > 0 else 0
        
        # 相对开盘的涨幅
        intraday_change_pct = (row['close'] - day_open) / day_open * 100
        
        # 量价共振得分 = 成交额 × 涨幅贡献的绝对值
        # 正向放量上涨得分高，负向放量下跌得分也高(但我们会筛选)
        intensity_score = amount / 10000 * abs(window_change_pct)
        
        windows.append({
            'time': dt,
            'hour': dt.hour,
            'minute': dt.minute,
            'price': row['close'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'volume': row['volume'],
            'amount': amount,
            'turnover': turnover,
            'window_change_pct': window_change_pct,
            'intraday_change_pct': intraday_change_pct,
            'intensity_score': intensity_score
        })
    
    if not windows:
        print("❌ 无有效窗口")
        return []
    
    # 5. 按强度得分排序
    windows_df = pd.DataFrame(windows)
    windows_df = windows_df.sort_values('intensity_score', ascending=False)
    
    print(f"\n全天共{len(windows)}个5分钟窗口")
    print(f"\n【资金强度Top {top_n}窗口】")
    print(f'{"时间":<8} {"价格":<8} {"涨幅%":<8} {"资金(万)":<12} {"强度得分":<12} {"Ratio85":<10}')
    print('-'*70)
    
    climax_windows = []
    for idx, row in windows_df.head(top_n).iterrows():
        ratio_85 = row['turnover'] / baseline['p85'] if baseline['p85'] > 0 else 0
        ratio_75 = row['turnover'] / baseline['p75'] if baseline['p75'] > 0 else 0
        
        time_str = f"{row['hour']:02d}:{row['minute']:02d}"
        print(f"{time_str:<8} {row['price']:<8.2f} {row['window_change_pct']:<8.2f} "
              f"{row['amount']/10000:<12.1f} {row['intensity_score']:<12.0f} {ratio_85:<10.2f}")
        
        # 构建上下文(前3后3窗口)
        context_prev = []
        context_next = []
        current_idx = windows_df.index.get_loc(idx)
        
        climax_windows.append(ClimaxWindow(
            stock_code=stock_code,
            date=date,
            time=time_str,
            price=row['price'],
            open_price=row['open'],
            high_price=row['high'],
            low_price=row['low'],
            change_pct=row['window_change_pct'],
            intraday_change_pct=row['intraday_change_pct'],
            volume=row['volume'],
            amount=row['amount'],
            turnover=row['turnover'],
            intensity_score=row['intensity_score'],
            money_flow_ratio=0,  # 待计算
            ratio_vs_85th=ratio_85,
            ratio_vs_75th=ratio_75,
            context_prev_3=context_prev,
            context_next_3=context_next
        ))
    
    return climax_windows


def analyze_two_day_continuation(
    stock_code: str,
    day1_date: str,
    day2_date: str
) -> Dict:
    """
    分析两日接力特征
    
    志特新材案例：
    - 12.31: 强势首扬 +8.97%
    - 01.05: 加速拉板
    """
    print(f"\n{'='*70}")
    print(f"【两日接力分析】{stock_code}")
    print(f"Day1: {day1_date} | Day2: {day2_date}")
    print(f"{'='*70}")
    
    # 扫描两天的数据
    day1_windows = scan_climax_windows(stock_code, day1_date, top_n=3)
    day2_windows = scan_climax_windows(stock_code, day2_date, top_n=3)
    
    if not day1_windows or not day2_windows:
        print("❌ 数据不足")
        return {}
    
    # Day1最强窗口
    day1_best = day1_windows[0]
    # Day2最强窗口
    day2_best = day2_windows[0]
    
    print(f"\n【Day1 {day1_date} 特征】")
    print(f"  时间: {day1_best.time}")
    print(f"  价格: {day1_best.price:.2f}")
    print(f"  涨幅: {day1_best.change_pct:.2f}%")
    print(f"  资金: {day1_best.amount/10000:.1f}万")
    print(f"  Ratio: {day1_best.ratio_vs_85th:.2f}")
    
    print(f"\n【Day2 {day2_date} 特征】")
    print(f"  时间: {day2_best.time}")
    print(f"  价格: {day2_best.price:.2f}")
    print(f"  涨幅: {day2_best.change_pct:.2f}%")
    print(f"  资金: {day2_best.amount/10000:.1f}万")
    print(f"  Ratio: {day2_best.ratio_vs_85th:.2f}")
    
    # 接力特征
    price_jump = (day2_best.price - day1_best.price) / day1_best.price * 100
    money_jump = (day2_best.amount - day1_best.amount) / day1_best.amount * 100
    
    print(f"\n【接力特征】")
    print(f"  价格跳升: {price_jump:.2f}%")
    print(f"  资金变化: {money_jump:.1f}%")
    
    return {
        'day1_best': asdict(day1_best),
        'day2_best': asdict(day2_best),
        'price_jump_pct': price_jump,
        'money_jump_pct': money_jump
    }


if __name__ == '__main__':
    print('='*70)
    print('【CTO纠偏版】高潮窗口自动扫描')
    print('='*70)
    
    # 1. 重新扫描志特新材12.31 (自动寻找高潮窗口，不机械套用09:35)
    print("\n" + "="*70)
    print("任务1: 重新扫描志特新材12.31全天资金结构")
    print("="*70)
    climax_1231 = scan_climax_windows('300986.SZ', '20251231', top_n=5)
    
    # 2. 扫描志特新材01.05接力日
    print("\n" + "="*70)
    print("任务2: 扫描志特新材01.05接力加速日")
    print("="*70)
    climax_0105 = scan_climax_windows('300986.SZ', '20260105', top_n=5)
    
    # 3. 两日接力分析
    print("\n" + "="*70)
    print("任务3: 分析12.31 -> 01.05接力特征")
    print("="*70)
    continuation = analyze_two_day_continuation('300986.SZ', '20251231', '20260105')
    
    # 4. 对比网宿科技和超捷股份
    print("\n" + "="*70)
    print("任务4: 黄金标杆对比验证")
    print("="*70)
    wangsu = scan_climax_windows('300017.SZ', '20260126', top_n=3)
    chaojie = scan_climax_windows('301005.SZ', '20251205', top_n=3)
    
    # 保存结果
    results = {
        'zhite_1231': [asdict(w) for w in climax_1231],
        'zhite_0105': [asdict(w) for w in climax_0105],
        'continuation_analysis': continuation,
        'wangsu_0126': [asdict(w) for w in wangsu],
        'chaojie_1205': [asdict(w) for w in chaojie]
    }
    
    output_file = Path('data/climax_window_analysis.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n{'='*70}")
    print(f"✅ 分析完成，结果保存: {output_file}")
    print(f"{'='*70}")
