#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极简版hist_median缓存构建脚本 - CTO架构定调版
统一使用xtdata.get_local_data读取QMT标准路径，不搞复杂路径映射

架构原则：
1. 所有历史Tick通过xtdata.get_local_data读取（QMT客户端标准路径）
2. 不再尝试读项目目录或其他自定义路径
3. 只用QMT客户端目录：E:/qmt/userdata_mini/datadir
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 尝试导入xtdata
try:
    from xtquant import xtdata
    print("✅ xtdata导入成功")
except ImportError:
    print("❌ 无法导入xtdata，请确保QMT客户端已安装并激活")
    sys.exit(1)

def get_last_n_trading_days(n: int) -> list[str]:
    """
    获取最近n个交易日列表（格式YYYYMMDD）
    为简化，这里用当前日期倒推估算
    """
    days = []
    current_date = datetime.now()
    while len(days) < n * 2:  # 多生成一些，排除周末
        if current_date.weekday() < 5:  # 0-4 是周一到周五
            days.append(current_date.strftime('%Y%m%d'))
        current_date -= timedelta(days=1)
    return days[:n]

def get_turnover_5min_series(tick_df: pd.DataFrame, float_volume: float) -> list[float]:
    """
    计算股票每5分钟的换手率序列
    
    Args:
        tick_df: Tick数据DataFrame
        float_volume: 流通股本（股）
    
    Returns:
        list[float]: 每个5分钟窗口的换手率
    """
    if 'volume' not in tick_df.columns or float_volume <= 0:
        return []
    
    # 确保按照时间排序
    if 'time' in tick_df.columns:
        tick_df = tick_df.sort_values('time').reset_index(drop=True)
    
    # 计算volumeDelta（逐笔成交量）
    tick_df = tick_df.copy()
    tick_df['vol_delta'] = tick_df['volume'].diff().fillna(tick_df['volume'].iloc[0])
    tick_df['vol_delta'] = tick_df['vol_delta'].clip(lower=0)  # 排除异常负值
    
    # 转换时间戳为datetime
    if 'time' in tick_df.columns:
        if tick_df['time'].dtype in ['int64', 'float64']:
            # 假设是毫秒时间戳
            tick_df['dt'] = pd.to_datetime(tick_df['time'], unit='ms')
        else:
            tick_df['dt'] = pd.to_datetime(tick_df['time'])
    else:
        return []
    
    # 按5分钟分组求和
    tick_df.set_index('dt', inplace=True)
    vol_5min = tick_df['vol_delta'].resample('5min').sum()
    
    # 换手率序列
    turnover_series = (vol_5min / float_volume).tolist()
    return [t for t in turnover_series if t > 0]  # 过滤零值窗口

def get_float_volume(stock_code: str) -> float | None:
    """
    通过xtdata获取流通股本（股）
    
    Args:
        stock_code: 带后缀的股票代码，如"000547.SZ"
    
    Returns:
        float: 流通股本（股）
        None:  获取失败
    """
    try:
        detail = xtdata.get_instrument_detail(stock_code)
        if not detail:
            return None
        fv = detail.get('FloatVolume')
        if fv is None:
            return None
        # FloatVolume是字符串，必须强制转换
        # 🔧 修正：xtdata返回的FloatVolume已经是"股"单位，不需要再转
        float_vol = float(fv)
        if float_vol <= 0:
            return None
        return float_vol  # 直接返回股单位
    except Exception as e:
        print(f"  [WARN] get_float_volume {stock_code} 失败: {e}")
        return None

def build_hist_median_cache(
    stock_codes: list[str],
    lookback_days: int = 60
) -> dict:
    """
    构建hist_median缓存
    
    Args:
        stock_codes: 股票代码列表（带后缀格式，如["000547.SZ", "300017.SZ"]）
        lookback_days: 回溯天数，默认60
    
    Returns:
        dict: 缓存数据
    """
    cache = {}
    candidate_dates = get_last_n_trading_days(lookback_days)

    for i, code in enumerate(stock_codes):
        print(f"\n[{i+1}/{len(stock_codes)}] {code}")

        # 1. 获取流通股本
        float_vol = get_float_volume(code)
        if float_vol is None:
            print(f"  ⚠️ 流通股本获取失败，跳过")
            continue
        print(f"  流通股本: {float_vol/1e8:.2f}亿股")

        # 2. 遍历历史日期，计算每日峰值换手
        daily_peaks = []
        valid_days = 0

        for date in candidate_dates:
            if valid_days >= lookback_days:
                break

            # 直接使用xtdata.get_local_data读取QMT标准路径数据
            try:
                result = xtdata.get_local_data(
                    field_list=['time', 'volume'],
                    stock_list=[code],
                    period='tick',
                    start_time=date,
                    end_time=date
                )
                
                if result is None or code not in result:
                    continue  # 该日无数据（节假日/停牌），正常跳过
                
                tick_df = result[code]
                if tick_df is None or tick_df.empty:
                    continue
                
                # 计算该日换手率峰值
                turnover_series = get_turnover_5min_series(tick_df, float_vol)
                if not turnover_series:
                    continue

                # 用当日峰值代表"当日最活跃5分钟换手水平"
                daily_peaks.append(max(turnover_series))
                valid_days += 1
            except Exception as e:
                # 静默跳过，可能是该日无数据或权限问题
                continue

        if valid_days < 5:  # 少于5日有效数据，不可靠
            print(f"  ⚠️ 有效数据不足 {valid_days} 日（需>=5），跳过")
            continue

        hist_median = float(pd.Series(daily_peaks).median())
        print(f"  ✅ hist_median={hist_median:.6f}，有效={valid_days}日")
        print(f"     (解读：日峰值换手率中位={hist_median*100:.4f}%/5min)")

        cache[code] = {
            "hist_median": hist_median,
            "float_volume": float_vol,
            "valid_days": valid_days,
            "updated_at": datetime.now().strftime('%Y-%m-%d')
        }

    # 3. 写入缓存文件
    cache_dir = PROJECT_ROOT / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / "hist_median_cache.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 缓存写入完成: {len(cache)}/{len(stock_codes)} 只 → {cache_file}")
    return cache


if __name__ == "__main__":
    print("="*60)
    print("极简版hist_median缓存构建脚本 - CTO架构定调版")
    print("="*60)
    
    # 验证用的股票池（从顽主研究中提取的）
    VERIFY_CODES = [
        "300017.SZ",   # 网宿科技（AB对照核心）
        "000547.SZ",   # 航天发展
        "300058.SZ",   # 蓝色光标
        "000592.SZ",   # 平潭发展
        "002792.SZ",   # 通宇通讯
        "603778.SH",   # 国晟科技
        "301005.SZ",   # 超捷股份
        "603516.SH",   # 淳中科技
    ]

    print(f"开始构建缓存，股票数量: {len(VERIFY_CODES)}")
    print(f"回溯天数: 60日")
    print(f"数据源: QMT客户端标准路径 (E:/qmt/userdata_mini/datadir)")
    
    result = build_hist_median_cache(VERIFY_CODES, lookback_days=60)
    
    # 快速验证：打印300017.SZ结果供人工核对
    entry = result.get("300017.SZ")
    if entry:
        print(f"\n--- 验证 300017.SZ ---")
        print(f"  hist_median  = {entry['hist_median']:.6f}")
        print(f"  float_volume = {entry['float_volume']/1e8:.2f}亿股")
        print(f"  valid_days   = {entry['valid_days']}")
        print(f"  预期 ratio_stock 量级:")
        print(f"    1-26 高峰时 flow_5min≈587M，price≈13.78")
        vol_est = 587e6 / 13.78          # 约 4259万股
        t5_est  = vol_est / entry['float_volume']
        ratio_est = t5_est / entry['hist_median']
        print(f"    vol_5min≈{vol_est/1e4:.0f}万股 → turnover≈{t5_est:.4f}")
        print(f"    ratio_stock≈{ratio_est:.1f}（目标>15）")
    
    print(f"\n缓存文件位置: {PROJECT_ROOT / 'data' / 'cache' / 'hist_median_cache.json'}")
    print("="*60)