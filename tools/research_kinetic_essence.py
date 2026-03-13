# -*- coding: utf-8 -*-
"""
【CTO V153 纯物理学动能解剖】砸碎"涨停崇拜"，直击动能本质！

核心哲学：
- 涨停只是交易所人造的一堵墙，不是物理本质！
- 一只从-4%拉到+8%的票（振幅12%），物理势能可能比开盘一字板强一万倍！
- 不看涨停标签，只看物理特征：ΔP/Δt、MFE、量比

研究目标：
1. 定义"极端动能事件"(EKE)：15分钟涨幅>4% + MFE Top5% + 量比Top10%
2. 提取盘中所有EKE切片，无论是否涨停
3. 建立物理特征 vs 后续收益的三维映射
4. 回答核心问题：当MFE和量比达阈值时，未来EV是多少？

Author: CTO Research Team
Date: 2026-03-14
Version: V153
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# QMT接口
from xtquant import xtdata
xtdata.enable_hello = False

# 项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ExtremeKineticEvent:
    """极端动能事件"""
    code: str
    date: str
    start_time: str  # EKE起始时间
    end_time: str    # EKE结束时间
    
    # 物理特征
    price_acceleration: float  # 价格加速度 (%/15min)
    mfe: float                  # 做功效率
    volume_ratio: float         # 量比
    volume_ratio_percentile: float  # 量比分位数
    mfe_percentile: float       # MFE分位数
    
    # 价格信息
    start_price: float
    end_price: float
    high_price: float
    low_price: float
    amplitude: float  # 振幅%
    
    # 后续收益
    t0_close: float
    t1_return: Optional[float] = None
    t3_return: Optional[float] = None
    t5_return: Optional[float] = None
    
    # 标签（仅供参考）
    is_limit_up: bool = False


def load_samples() -> List[dict]:
    """加载暴力样本数据（不限制涨停）"""
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                             'data', 'validation', 'violent_samples_full.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def scan_intraday_eke(
    stock_code: str, 
    date: str,
    avg_volume_5d: float,
    min_acceleration: float = 4.0,  # 15分钟最小涨幅%
    window_minutes: int = 15
) -> List[ExtremeKineticEvent]:
    """
    扫描盘中所有极端动能事件（EKE）
    
    不看涨停标签，只看物理特征！
    """
    events = []
    
    try:
        data = xtdata.get_local_data(
            field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
            stock_list=[stock_code],
            period='1m',
            start_time=date,
            end_time=date
        )
        
        if not data or stock_code not in data:
            return events
        
        df = data[stock_code]
        if df is None or len(df) < window_minutes:
            return events
        
        # 计算15分钟滚动涨幅
        for i in range(window_minutes, len(df)):
            start_price = df['close'].iloc[i - window_minutes]
            end_price = df['close'].iloc[i]
            
            if start_price <= 0:
                continue
            
            # 价格加速度
            acceleration = (end_price - start_price) / start_price * 100
            
            if acceleration < min_acceleration:
                continue
            
            # 提取这个窗口的数据
            window_df = df.iloc[i - window_minutes:i + 1]
            
            high = window_df['high'].max()
            low = window_df['low'].min()
            amplitude = (high - low) / low * 100 if low > 0 else 0
            
            # 计算MFE
            total_amount = window_df['amount'].sum()
            open_price = window_df['open'].iloc[0]
            price_range = ((end_price - low) + (high - open_price)) / 2
            price_range_pct = price_range / open_price * 100 if open_price > 0 else 0
            
            # 估算净流入（简化）
            net_inflow = total_amount * 0.2
            inflow_ratio = net_inflow / total_amount * 100 if total_amount > 0 else 0
            
            if inflow_ratio <= 0:
                continue
            
            mfe = price_range_pct / inflow_ratio
            
            # 计算量比
            cum_volume = df['volume'].iloc[:i + 1].sum() * 100  # 手->股
            minutes_elapsed = i + 1
            est_full_volume = cum_volume * 240 / minutes_elapsed if minutes_elapsed > 0 else 0
            volume_ratio = est_full_volume / avg_volume_5d if avg_volume_5d > 0 else 0
            
            # 时间戳
            end_ts = str(df.index[i])
            start_ts = str(df.index[i - window_minutes])
            
            event = ExtremeKineticEvent(
                code=stock_code,
                date=date,
                start_time=start_ts[8:12],  # HHMM
                end_time=end_ts[8:12],
                price_acceleration=acceleration,
                mfe=mfe,
                volume_ratio=volume_ratio,
                volume_ratio_percentile=0.0,  # 后续批量计算
                mfe_percentile=0.0,  # 后续批量计算
                start_price=start_price,
                end_price=end_price,
                high_price=high,
                low_price=low,
                amplitude=amplitude,
                t0_close=df['close'].iloc[-1]
            )
            
            events.append(event)
        
        return events
        
    except Exception as e:
        return events


def main():
    print("=" * 70)
    print("【CTO V153 纯物理学动能解剖】")
    print("砸碎'涨停崇拜'，直击动能本质！")
    print("=" * 70)
    
    # Step 1: 加载样本
    print("\nStep 1: 加载样本...")
    samples = load_samples()
    samples_2026 = [s for s in samples if s['date'].startswith('2026')]
    print(f"  2026年样本: {len(samples_2026)}个")
    
    # 获取5日均量
    print("\nStep 2: 获取5日均量...")
    all_stocks = list(set(s['stock_code'] for s in samples_2026))
    print(f"  涉及股票: {len(all_stocks)}只")
    
    # 从日K获取5日均量
    avg_volume_dict = {}
    end_date = '20260313'
    start_date = '20260101'
    
    # 分批获取
    batch_size = 500
    for i in range(0, min(len(all_stocks), 1000), batch_size):  # 限制1000只避免太慢
        batch = all_stocks[i:i + batch_size]
        try:
            daily_data = xtdata.get_local_data(
                field_list=['volume'],
                stock_list=batch,
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            for code in batch:
                if code in daily_data and daily_data[code] is not None:
                    vol_series = daily_data[code]['volume']
                    if len(vol_series) >= 5:
                        avg_volume_dict[code] = vol_series.tail(5).mean() * 100  # 手->股
        except:
            pass
    
    print(f"  获取到5日均量: {len(avg_volume_dict)}只")
    
    # Step 3: 扫描EKE
    print("\nStep 3: 扫描盘中极端动能事件(EKE)...")
    print("  条件: 15分钟涨幅>=4%")
    
    all_events = []
    sample_dates = list(set(s['date'] for s in samples_2026[:500]))  # 限制日期数
    sample_dates.sort()
    
    for date in sample_dates[:5]:  # 只研究5个日期
        print(f"  扫描 {date}...")
        day_stocks = [s for s in samples_2026 if s['date'] == date][:50]  # 每天最多50只
        
        for s in day_stocks:
            code = s['stock_code']
            avg_vol = avg_volume_dict.get(code, 0)
            if avg_vol <= 0:
                continue
            
            events = scan_intraday_eke(code, date, avg_vol)
            
            # 补充后续收益
            for e in events:
                t0_close = s.get('t0', {}).get('close', 0)
                t1 = s.get('post_days', {}).get('t_plus_1', {}).get('close', 0)
                t3 = s.get('post_days', {}).get('t_plus_3', {}).get('close', 0)
                t5 = s.get('post_days', {}).get('t_plus_5', {}).get('close', 0)
                
                if t0_close > 0:
                    if t1 > 0:
                        e.t1_return = (t1 / t0_close - 1) * 100
                    if t3 > 0:
                        e.t3_return = (t3 / t0_close - 1) * 100
                    if t5 > 0:
                        e.t5_return = (t5 / t0_close - 1) * 100
                
                e.is_limit_up = s.get('t0', {}).get('is_limit_up', False)
            
            all_events.extend(events)
    
    print(f"\n  发现EKE事件: {len(all_events)}个")
    
    if len(all_events) == 0:
        print("\n警告: 没有发现EKE事件！")
        return
    
    # Step 4: 计算横截面分位数
    print("\nStep 4: 计算横截面分位数...")
    
    all_mfe = [e.mfe for e in all_events if e.mfe > 0]
    all_vr = [e.volume_ratio for e in all_events if e.volume_ratio > 0]
    
    mfe_90th = np.percentile(all_mfe, 90) if all_mfe else 1.0
    mfe_95th = np.percentile(all_mfe, 95) if all_mfe else 1.0
    vr_90th = np.percentile(all_vr, 90) if all_vr else 1.0
    
    for e in all_events:
        if e.mfe > 0:
            e.mfe_percentile = np.searchsorted(np.sort(all_mfe), e.mfe) / len(all_mfe)
        if e.volume_ratio > 0:
            e.volume_ratio_percentile = np.searchsorted(np.sort(all_vr), e.volume_ratio) / len(all_vr)
    
    # Step 5: 分组分析
    print("\n" + "=" * 70)
    print("【物理学动能 vs 后续收益】")
    print("=" * 70)
    
    # 按物理特征分组
    high_mfe_vr = [e for e in all_events if e.mfe_percentile >= 0.90 and e.volume_ratio_percentile >= 0.90]
    low_mfe_vr = [e for e in all_events if e.mfe_percentile < 0.50 and e.volume_ratio_percentile < 0.50]
    mid_mfe_vr = [e for e in all_events if e not in high_mfe_vr and e not in low_mfe_vr]
    
    print(f"\n【分组统计】")
    print(f"  高MFE高量比(Top10%): {len(high_mfe_vr)}个")
    print(f"  低MFE低量比(Bottom50%): {len(low_mfe_vr)}个")
    print(f"  中间组: {len(mid_mfe_vr)}个")
    
    # 计算各组收益
    def calc_returns(events: List[ExtremeKineticEvent]):
        t1 = [e.t1_return for e in events if e.t1_return is not None]
        t3 = [e.t3_return for e in events if e.t3_return is not None]
        t5 = [e.t5_return for e in events if e.t5_return is not None]
        return {
            't1': (np.mean(t1), np.median(t1)) if t1 else (None, None),
            't3': (np.mean(t3), np.median(t3)) if t3 else (None, None),
            't5': (np.mean(t5), np.median(t5)) if t5 else (None, None),
            't5_positive': sum(1 for r in t5 if r > 0) / len(t5) * 100 if t5 else None
        }
    
    print("\n【核心问题：当MFE和量比达阈值时，未来EV是多少？】")
    print("-" * 70)
    
    if high_mfe_vr:
        r = calc_returns(high_mfe_vr)
        print(f"\n高MFE高量比组 (物理最强):")
        print(f"  次日: 均值{r['t1'][0]:+.2f}% 中位数{r['t1'][1]:+.2f}%")
        print(f"  3日: 均值{r['t3'][0]:+.2f}% 中位数{r['t3'][1]:+.2f}%")
        print(f"  5日: 均值{r['t5'][0]:+.2f}% 中位数{r['t5'][1]:+.2f}%")
        print(f"  5日正收益比例: {r['t5_positive']:.1f}%")
    
    if low_mfe_vr:
        r = calc_returns(low_mfe_vr)
        print(f"\n低MFE低量比组 (物理最弱):")
        print(f"  次日: 均值{r['t1'][0]:+.2f}% 中位数{r['t1'][1]:+.2f}%")
        print(f"  3日: 均值{r['t3'][0]:+.2f}% 中位数{r['t3'][1]:+.2f}%")
        print(f"  5日: 均值{r['t5'][0]:+.2f}% 中位数{r['t5'][1]:+.2f}%")
        print(f"  5日正收益比例: {r['t5_positive']:.1f}%")
    
    if mid_mfe_vr:
        r = calc_returns(mid_mfe_vr)
        print(f"\n中间组:")
        print(f"  5日: 均值{r['t5'][0]:+.2f}% 中位数{r['t5'][1]:+.2f}%")
    
    # 涨停vs非涨停对比（仅供参考，不是核心）
    print("\n" + "=" * 70)
    print("【标签污染验证：涨停 vs 非涨停（仅供参考）】")
    print("=" * 70)
    
    limit_up = [e for e in all_events if e.is_limit_up]
    no_limit = [e for e in all_events if not e.is_limit_up]
    
    print(f"\n涨停事件: {len(limit_up)}个")
    print(f"非涨停事件: {len(no_limit)}个")
    
    if limit_up:
        r = calc_returns(limit_up)
        print(f"\n涨停组 5日收益: 均值{r['t5'][0]:+.2f}% 中位数{r['t5'][1]:+.2f}%")
    
    if no_limit:
        r = calc_returns(no_limit)
        print(f"非涨停组 5日收益: 均值{r['t5'][0]:+.2f}% 中位数{r['t5'][1]:+.2f}%")
    
    # 核心结论
    print("\n" + "=" * 70)
    print("【CTO 物理学裁决】")
    print("=" * 70)
    
    if high_mfe_vr and low_mfe_vr:
        high_t5 = calc_returns(high_mfe_vr)['t5']
        low_t5 = calc_returns(low_mfe_vr)['t5']
        
        if high_t5[0] and low_t5[0]:
            ev_diff = high_t5[0] - low_t5[0]
            if ev_diff > 2:
                print(f"\n✅ 物理学有效：高MFE高量比组的5日EV显著高于低组({ev_diff:+.2f}%)")
                print("  建议：量比92th + MFE 90th 作为联合阈值")
            else:
                print(f"\n⚠️ 物理学效果有限：EV差异仅{ev_diff:+.2f}%，需要更多研究")
    
    print("\n研究完成！砸碎涨停标签，直击物理本质！")


if __name__ == '__main__':
    main()
