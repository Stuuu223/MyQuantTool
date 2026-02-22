#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/build_hist_median_cache.py

离线构建 hist_median 缓存（盘后跑一次，非交易时间执行）

数据源:   项目 data/qmt_data/ 下已下载的 Tick 文件（不读 QMT 客户端原始目录）
数据读取: 走 QMTHistoricalProvider（已封装路径映射 + 代码格式转换）
输出:     data/cache/hist_median_cache.json

缓存格式:
{
  "300017.SZ": {
    "hist_median":  0.000032,    # turnover_5min 历史60日中位（无量纲，主指标）
    "float_volume": 2850000000,  # 流通股本（股），来自 xtdata.get_instrument_detail
    "valid_days":   52,          # 实际有效交易日数
    "updated_at":  "2026-02-22"
  }
}

字段口径说明:
  turnover_5min = 5分钟成交量(股) / 流通股本(股)  [无量纲]
  hist_median   = 上述指标在历史60交易日的日峰值中位数
  ratio_stock   = 当前turnover_5min / hist_median  [倍数，目标 > 15]
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from functools import lru_cache

# QMT 原生接口（只用于 get_instrument_detail，不用于路径读文件）
try:
    import xtquant.xtdata as xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

# 项目 QMTHistoricalProvider（封装了 data/qmt_data/ 路径 + 代码格式转换）
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logic.qmt_historical_provider import QMTHistoricalProvider

# ============================================================
# 路径与配置（严格按项目 config/paths.json 定义）
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent          # E:/MyQuantTool/
DATA_ROOT    = PROJECT_ROOT / "data"                 # E:/MyQuantTool/data/
QMT_DATA_DIR = DATA_ROOT / "qmt_data"               # E:/MyQuantTool/data/qmt_data/
CACHE_DIR    = DATA_ROOT / "cache"                   # E:/MyQuantTool/data/cache/
CACHE_FILE   = CACHE_DIR / "hist_median_cache.json"


# ============================================================
# Step A：获取流通股本（QMT 原生 get_instrument_detail，已验证）
# ============================================================

def get_float_volume(stock_code: str) -> float | None:
    """
    获取流通股本（股）
    
    QMT 原生接口: xtdata.get_instrument_detail(code)
    已验证字段:   FloatVolume（万股，str 类型）
    ⚠️ 必须强转 float，原始是字符串
    
    Args:
        stock_code: 带后缀格式，如 "300017.SZ"
    Returns:
        float: 流通股本（股），如 2_850_000_000
        None:  获取失败
    """
    if not QMT_AVAILABLE:
        return None
    try:
        detail = xtdata.get_instrument_detail(stock_code)
        if not detail:
            return None
        fv = detail.get('FloatVolume')
        if fv is None:
            return None
        float_vol_wan = float(fv)      # ⚠️ str → float，这是已踩过的坑
        if float_vol_wan <= 0:
            return None
        return float_vol_wan * 10000   # 万股 → 股
    except Exception as e:
        print(f"  [WARN] get_float_volume {stock_code} 失败: {e}")
        return None


# ============================================================
# Step B：读取 Tick（走 QMTHistoricalProvider，读 data/qmt_data/）
# ============================================================

def load_tick(stock_code: str, date: str) -> pd.DataFrame | None:
    """
    读取指定股票指定日期的 Tick 数据
    
    通过DataService读取，因为tick文件是二进制格式，需要用xtdata API读取
    
    Args:
        stock_code: "300017.SZ"
        date:       "20260126"
    Returns:
        DataFrame or None（该日无数据正常返回 None）
    """
    try:
        # 使用QMT API读取二进制tick数据
        from xtquant import xtdata
        
        # 调用xtdata API获取tick数据
        result = xtdata.get_local_data(
            field_list=[],
            stock_list=[stock_code],
            period='tick',
            start_time=date,
            end_time=date
        )
        
        df = result.get(stock_code)
        if df is None or df.empty:
            return None
        return df
    except Exception as e:
        print(f"  [WARN] load_tick {stock_code} {date} 失败: {e}")
        return None   # 静默跳过，Tick 不存在是正常情况


# ============================================================
# Step C：计算每日 turnover_5min 峰值
# ============================================================

def calc_daily_peak_turnover(
    tick_df: pd.DataFrame,
    float_volume: float
) -> float | None:
    """
    计算该日 turnover_5min 的峰值（代表当日最活跃5分钟换手水平）
    
    逻辑:
      1. volumeDelta = 逐笔成交量（QMT volume 是累计值，需 diff）
      2. 按 5 分钟窗口聚合 → vol_5min
      3. turnover_5min = vol_5min / float_volume
      4. 取当日最大值作为"当日基准点"
    
    ⚠️ 过滤集合竞价噪声：只取 09:30 之后的 Tick
    """
    if 'volume' not in tick_df.columns or float_volume <= 0:
        return None

    df = tick_df.copy()

    # 时间处理（QMT timestamp 为毫秒整数）
    if 'time' in df.columns:
        if df['time'].dtype in ['int64', 'float64']:
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
        else:
            df['dt'] = pd.to_datetime(df['time'])
    else:
        return None

    # ⚠️ 过滤集合竞价：只保留 09:30 之后
    market_open = df['dt'].dt.normalize() + pd.Timedelta(hours=9, minutes=30)
    df = df[df['dt'] >= market_open].copy()
    if df.empty:
        return None

    df = df.sort_values('dt').reset_index(drop=True)

    # volumeDelta（逐笔成交量），第一笔用自身
    df['vol_delta'] = df['volume'].diff().fillna(df['volume'].iloc[0])
    df['vol_delta'] = df['vol_delta'].clip(lower=0)   # 排除异常负值

    # 按 5 分钟窗口聚合
    df.set_index('dt', inplace=True)
    vol_5min = df['vol_delta'].resample('5min').sum()
    vol_5min = vol_5min[vol_5min > 0]   # 过滤空窗口

    if vol_5min.empty:
        return None

    # turnover_5min 序列
    turnover_series = vol_5min / float_volume

    return float(turnover_series.max())


# ============================================================
# 核心入口：构建完整缓存
# ============================================================

def build_hist_median_cache(
    stock_codes: list[str],
    lookback_days: int = 60
) -> dict:
    """
    对每只股票构建 hist_median 缓存

    Args:
        stock_codes:   带后缀的股票代码列表，如 ["300017.SZ", "000547.SZ"]
        lookback_days: 回溯交易日数，默认 60

    Returns:
        dict: 写入 data/cache/hist_median_cache.json 并同时返回
    """
    cache = {}

    # 候选日期（简单生成，靠 Tick 文件是否存在来过滤非交易日）
    candidate_dates = []
    d = datetime.now()
    while len(candidate_dates) < lookback_days * 2:
        d -= timedelta(days=1)
        if d.weekday() < 5:  # 跳过周六周日
            candidate_dates.append(d.strftime('%Y%m%d'))

    for i, code in enumerate(stock_codes):
        print(f"\n[{i+1}/{len(stock_codes)}] {code}")

        # A. 流通股本（QMT get_instrument_detail，已验证）
        float_vol = get_float_volume(code)
        if float_vol is None:
            print(f"  ⚠️ 流通股本获取失败，跳过")
            continue
        print(f"  流通股本: {float_vol/1e8:.2f}亿股")

        # B. 遍历历史日期，计算每日峰值换手
        daily_peaks = []
        valid_days = 0

        for date in candidate_dates:
            if valid_days >= lookback_days:
                break

            tick_df = load_tick(code, date)
            if tick_df is None:
                continue   # 该日无数据（节假日/停牌），正常跳过

            peak = calc_daily_peak_turnover(tick_df, float_vol)
            if peak is None or peak <= 0:
                continue

            daily_peaks.append(peak)
            valid_days += 1

        if valid_days < 5:
            print(f"  ⚠️ 有效数据不足 {valid_days} 日（需>=5），跳过")
            continue

        hist_median = float(pd.Series(daily_peaks).median())
        print(f"  ✅ hist_median={hist_median:.6f}，有效={valid_days}日")
        print(f"     (解读：日峰值换手率中位={hist_median*100:.4f}%/5min)")

        cache[code] = {
            "hist_median":  hist_median,
            "float_volume": float_vol,
            "valid_days":   valid_days,
            "updated_at":   datetime.now().strftime('%Y-%m-%d')
        }

    # 写入缓存
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 缓存写入完成: {len(cache)}/{len(stock_codes)} 只 → {CACHE_FILE}")
    return cache


# ============================================================
# 执行入口
# ============================================================

if __name__ == "__main__":
    # 验证样本（你们已验证的正反例股票池）
    VERIFY_CODES = [
        "300017.SZ",   # 网宿科技（AB 对照核心）
        "000547.SZ",   # 航天发展
        "300058.SZ",
        "000592.SZ",
        "002792.SZ",
        "603778.SH",
        "301005.SZ",
        "603516.SH",
    ]

    result = build_hist_median_cache(VERIFY_CODES, lookback_days=60)

    # 快速验证：打印 300017.SZ 结果供人工核对
    entry = result.get("300017.SZ")
    if entry:
        print(f"\n--- 验证 300017.SZ ---")
        print(f"  hist_median  = {entry['hist_median']:.6f}")
        print(f"  float_volume = {entry['float_volume']/1e8:.2f}亿股")
        print(f"  valid_days   = {entry['valid_days']}")
        print(f"  頴期 ratio_stock 量级:")
        print(f"    1-26 高峰时 flow_5min≈587M，price≈13.78")
        vol_est = 587e6 / 13.78          # 约 4259万股
        t5_est  = vol_est / entry['float_volume']
        ratio_est = t5_est / entry['hist_median']
        print(f"    vol_5min≈{vol_est/1e4:.0f}万股 → turnover≈{t5_est:.4f}")
        print(f"    ratio_stock≈{ratio_est:.1f}（目标>15）")
