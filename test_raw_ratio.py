#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
烟雾测试脚本 - 纯Pandas直接计算ratio
验证000547在2026-01-26的真实资金流入和ratio计算

CTO指令：
1. 直接用QMTHistoricalProvider读原始Tick
2. 毫秒时间戳必须除以1000转换
3. 计算9:35-9:40的5分钟净流入
4. 排查单位错配问题
"""

import sys
import json
from pathlib import Path
import pandas as pd
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.qmt_historical_provider import QMTHistoricalProvider

# 测试参数
STOCK_CODE = '300017.SZ'
TEST_DATE = '20260126'
# ✅ 使用xtdata正确股本：23.06亿股（FloatVolume）
# 流通市值519.34亿仅用于验证，不参与计算

def load_hist_median_cache():
    """加载hist_median缓存"""
    cache_file = PROJECT_ROOT / "data" / "cache" / "hist_median_cache.json"
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def test_raw_calculation():
    """
    纯Pandas直接计算测试
    """
    print("="*70)
    print("烟雾测试 - 纯Pandas直接计算ratio")
    print("="*70)
    print(f"\n测试标的: {STOCK_CODE}")
    print(f"测试日期: {TEST_DATE}")
    
    # 1. 加载hist_median缓存
    cache = load_hist_median_cache()
    cache_entry = cache.get(STOCK_CODE, {})
    hist_median = cache_entry.get('hist_median', 0)
    float_volume = cache_entry.get('float_volume', 0)
    
    print(f"\n【缓存数据】")
    print(f"  hist_median: {hist_median:.2e}")
    print(f"  float_volume: {float_volume/1e8:.2f}亿股 ({float_volume:,.0f}股)")
    print(f"  解读: 历史60日换手率峰值中位数={hist_median*100:.6f}%/5min")
    
    # 2. 读取原始Tick数据
    print(f"\n【读取原始Tick数据】")
    provider = QMTHistoricalProvider(
        stock_code=STOCK_CODE,
        start_time=TEST_DATE,
        end_time=TEST_DATE
    )
    df = provider.get_raw_ticks()
    
    if df is None or df.empty:
        print("  ❌ 无数据")
        return
    
    print(f"  ✅ 读取成功: {len(df)}条Tick")
    print(f"  列名: {list(df.columns)}")
    
    # 3. 时间戳转换（毫秒->秒）
    print(f"\n【时间戳转换】")
    if 'time' in df.columns:
        # 检查时间戳单位
        sample_ts = df['time'].iloc[0]
        print(f"  原始时间戳样例: {sample_ts}")
        
        # 毫秒转秒（如果数值过大）
        if sample_ts > 1e12:  # 毫秒级时间戳
            df['time_sec'] = df['time'] / 1000
            print(f"  ✅ 毫秒转秒: {sample_ts} -> {sample_ts/1000}")
        else:
            df['time_sec'] = df['time']
            print(f"  时间戳已是秒级")
        
        # 转换为datetime（手动+8小时转为北京时间，避免时区问题）
        df['datetime'] = pd.to_datetime(df['time_sec'] + 8*3600, unit='s')
        print(f"  时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
    
    # 4. 计算早盘9:30-10:10的每个5分钟切片（CTO指定分析时段）
    print(f"\n【早盘5分钟切片分析 - CTO指定时段 09:30-10:10】")
    
    # CTO指定：分析9:30-10:10的每个5分钟切片
    print(f"  数据实际时间范围: {df['datetime'].min()} ~ {df['datetime'].max()}")
    
    # 确保volume_delta已计算
    df = df.sort_values('datetime').reset_index(drop=True)
    df['volume_delta'] = df['volume'].diff().fillna(0)
    df['volume_delta'] = df['volume_delta'].clip(lower=0)
    
    # 获取早盘价格基准（9:30开盘价）
    morning_start = "2026-01-26 09:30:00"
    morning_mask = df['datetime'] >= morning_start
    morning_df = df[morning_mask]
    
    if len(morning_df) > 0:
        open_price = morning_df['lastPrice'].iloc[0]
        print(f"\n  早盘开盘价(9:30): {open_price:.2f}元")
    
    # 分析每个5分钟窗口
    print(f"\n  【5分钟切片详细数据 - 9:30-10:10】")
    print(f"  {'时间窗口':<20} {'成交量(万股)':<15} {'换手率(%)':<12} {'均价':<10} {'涨幅(%)':<10} {'ratio_stock'}")
    print(f"  {'-'*90}")
    
    time_windows = [
        ("09:30:00", "09:35:00"),
        ("09:35:00", "09:40:00"),
        ("09:40:00", "09:45:00"),
        ("09:45:00", "09:50:00"),
        ("09:50:00", "09:55:00"),
        ("09:55:00", "10:00:00"),
        ("10:00:00", "10:05:00"),
        ("10:05:00", "10:10:00"),
    ]
    
    morning_ratios = []
    for start_str, end_str in time_windows:
        window_mask = (df['datetime'] >= f"2026-01-26 {start_str}") & (df['datetime'] < f"2026-01-26 {end_str}")
        window_df = df[window_mask].copy()
        
        if len(window_df) == 0:
            continue
        
        # 计算指标
        vol_5min = window_df['volume_delta'].sum()
        turnover_5min = vol_5min / float_volume if float_volume > 0 else 0
        avg_price = window_df['lastPrice'].mean() if len(window_df) > 0 else 0
        
        # 计算涨幅（相对昨收）
        change_pct = ((avg_price - open_price) / open_price * 100) if open_price > 0 else 0
        
        # 计算ratio
        ratio_stock = turnover_5min / hist_median if hist_median > 0 else 0
        morning_ratios.append({
            'window': f"{start_str}-{end_str}",
            'vol': vol_5min,
            'turnover': turnover_5min,
            'price': avg_price,
            'change': change_pct,
            'ratio': ratio_stock
        })
        
        print(f"  {start_str}-{end_str:<9} {vol_5min/1e4:>10.2f}    {turnover_5min*100:>10.4f}  {avg_price:>8.2f}   {change_pct:>+7.2f}    {ratio_stock:>8.2f}")
    
    # 找出最大ratio窗口
    if morning_ratios:
        max_ratio_window = max(morning_ratios, key=lambda x: x['ratio'])
        print(f"\n  ✅ 早盘最大ratio窗口: {max_ratio_window['window']}")
        print(f"     ratio_stock={max_ratio_window['ratio']:.2f}, 涨幅={max_ratio_window['change']:+.2f}%")
        print(f"     换手率={max_ratio_window['turnover']*100:.4f}%, 成交量={max_ratio_window['vol']/1e4:.2f}万股")
    
    # 7. 单位错配排查
    print(f"\n【单位错配排查】")
    print(f"  hist_median单位: 换手率(无量纲) = 成交量(股) / 流通股本(股)")
    print(f"  turnover_5min单位: 换手率(无量纲)")
    print(f"  ratio_stock单位: 倍数(无量纲)")
    print(f"  ")
    print(f"  检查: turnover_5min({turnover_5min:.2e}) 和 hist_median({hist_median:.2e})")
    print(f"  两者是否同单位? {'✅ 是' if turnover_5min/hist_median < 1e6 else '❌ 可能单位不匹配'}")
    
    # 8. 扫描全天，找出最大ratio时段
    print(f"\n【全天扫描 - 找出最大ratio时段】")
    print(f"  扫描5分钟滑动窗口...")
    
    max_ratio = 0
    max_window = None
    
    # 每5分钟一个窗口
    df_sorted = df.sort_values('datetime').reset_index(drop=True)
    for i in range(0, len(df_sorted) - 100, 50):  # 步长50（约5分钟）
        window = df_sorted.iloc[i:i+100]
        if len(window) < 10:
            continue
        
        # 计算该窗口的换手率
        window = window.copy()
        window['vol_delta'] = window['volume'].diff().fillna(0).clip(lower=0)
        vol_5min = window['vol_delta'].sum()
        turnover_5min = vol_5min / float_volume if float_volume > 0 else 0
        
        # 计算ratio
        if hist_median > 0:
            ratio = turnover_5min / hist_median
            if ratio > max_ratio:
                max_ratio = ratio
                max_window = window
    
    if max_window is not None:
        print(f"\n  ✅ 最大ratio窗口:")
        print(f"    时间: {max_window['datetime'].iloc[0]} ~ {max_window['datetime'].iloc[-1]}")
        print(f"    ratio_stock: {max_ratio:.2f}")
        
        vol_max = max_window['vol_delta'].sum() if 'vol_delta' in max_window.columns else 0
        print(f"    成交量: {vol_max/1e4:.2f}万股")
        
        if max_ratio >= 15:
            print(f"    🔥 触发阈值! (ratio >= 15)")
        else:
            print(f"    ❌ 未触发阈值 (需要>=15)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    test_raw_calculation()
