#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连板首板研究 V3.0 - 正确架构
核心改变：废弃滑动窗口，改用连板序列检测器
保证每个事件的 T0 = 真正的首板日

CTO审计修复：
- Bug#1: 贪心策略导致连板起点偏移 → 改用连板序列检测
- Bug#2: 一字涨停被误判为"平盘" → candle_type重新分类
- Bug#3: T0下跌日 → 序列检测确保T0=首板

运行方式：
    python tasks/violent_surge_v3_fireboard.py

验证标准：
    - T-1涨停比例 < 5%
    - T0涨停比例 > 90%
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "data" / "validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def detect_limit_up_series(df: pd.DataFrame, float_vol: float, min_boards: int = 3) -> list:
    """
    连板序列检测器（代替 find_all_violent_moves 的滑动窗口）
    
    算法：
    1. 逐日扫描是否涨停（10%板/20%板/ST5%板）
    2. 连续涨停日归为同一个 series
    3. 中断即结算，记录 series_start（第1板）
    4. 只保留 ≥ min_boards 的 series
    
    保证：同一股票不会有重叠或嵌套的 series
    """
    closes = df['close'].values
    n = len(closes)
    series_list = []
    
    i = 1
    while i < n:
        # 计算今日涨幅
        pct = (closes[i] - closes[i-1]) / closes[i-1] * 100.0
        
        # 判断是否涨停（主板10%，注册制20%，ST5%）
        is_lim = ((9.5 <= pct <= 10.5) or
                  (19.0 <= pct <= 21.0) or
                  (4.5 <= pct <= 5.5))
        
        if not is_lim:
            i += 1
            continue
        
        # 找到第1板，开始计数
        series_start_idx = i
        boards = [i]
        j = i + 1
        
        while j < n:
            pct_j = (closes[j] - closes[j-1]) / closes[j-1] * 100.0
            is_lim_j = ((9.5 <= pct_j <= 10.5) or
                        (19.0 <= pct_j <= 21.0) or
                        (4.5 <= pct_j <= 5.5))
            if is_lim_j:
                boards.append(j)
                j += 1
            else:
                break  # 连板中断
        
        num_boards = len(boards)
        
        if num_boards >= min_boards:
            # 计算 series 期间换手率
            seg_vols = df['volume'].iloc[series_start_idx:j]
            seg_turnover = (seg_vols * 100.0 / float_vol * 100.0).mean()
            
            # 计算总涨幅（第1板前一天收盘到最后一板收盘）
            base_close = closes[series_start_idx - 1]
            final_close = closes[boards[-1]]
            total_return = (final_close / base_close - 1.0) * 100.0
            
            # 计算最大回撤
            segment_closes = closes[series_start_idx:boards[-1]+1]
            cummax = np.maximum.accumulate(segment_closes)
            drawdowns = (segment_closes - cummax) / cummax * 100.0
            max_dd = abs(drawdowns.min()) if len(drawdowns) > 0 else 0
            
            series_list.append({
                'series_start_idx': int(series_start_idx),    # 第1板的 idx
                'series_end_idx': int(boards[-1]),
                'num_boards': int(num_boards),
                'total_return': round(float(total_return), 4),
                'max_drawdown': round(float(max_dd), 4),
                'start_date': str(df['date_str'].iloc[series_start_idx]),
                'end_date': str(df['date_str'].iloc[boards[-1]]),
                'board_dates': [str(df['date_str'].iloc[b]) for b in boards],
                'avg_turnover_during': round(float(seg_turnover), 4),
            })
        
        # 跳过整个 series，避免重叠
        i = j
    
    return series_list


def compute_pre_ignition_profile(df: pd.DataFrame, series: dict,
                                 float_vol: float,
                                 lookback: int = 10) -> list:
    """
    以第1板（series_start_idx）为 T0，计算 T-lookback 到 T+3 的逐日特征
    
    修正了原脚本的两个问题：
    1. T0 现在是真正的首板日
    2. candle_type 区分了一字涨停
    """
    ignition_idx = series['series_start_idx']
    records = []
    
    # T-20 均换手（背景基准）
    bg_start = max(1, ignition_idx - 20)
    bg_vols = df['volume'].iloc[bg_start:ignition_idx]
    bg_turnover = float(bg_vols.mean()) * 100.0 / float_vol * 100.0 if len(bg_vols) > 0 else None
    
    for lag in range(-lookback, 4):
        pos = ignition_idx + lag
        if pos <= 0 or pos >= len(df):
            continue
        
        close = float(df['close'].iloc[pos])
        open_ = float(df['open'].iloc[pos])
        high = float(df['high'].iloc[pos])
        low = float(df['low'].iloc[pos])
        vol = float(df['volume'].iloc[pos])
        prev_close = float(df['close'].iloc[pos - 1])
        
        daily_ret = (close - prev_close) / prev_close * 100.0
        turnover = vol * 100.0 / float_vol * 100.0
        body_pct = (close - open_) / prev_close * 100.0
        
        # 涨停判断（基于日涨幅）
        is_limit_up = ((9.5 <= daily_ret <= 10.5) or
                       (19.0 <= daily_ret <= 21.0) or
                       (4.5 <= daily_ret <= 5.5))
        
        # ✅ 修正的 candle_type 分类
        if is_limit_up and abs(body_pct) < 0.3:
            candle_type = "一字涨停"            # open ≈ close ≈ limit price
        elif is_limit_up and body_pct >= 0.3:
            candle_type = "涨停"                # T字/阳线涨停
        elif is_limit_up and body_pct <= -0.3:
            candle_type = "涨停"                # T字涨停
        elif body_pct < -9.5:
            candle_type = "跌停"
        elif body_pct > 5:
            candle_type = "大阳"
        elif body_pct > 2:
            candle_type = "小阳"
        elif body_pct > -2:
            candle_type = "平盘"
        elif body_pct > -5:
            candle_type = "小阴"
        else:
            candle_type = "大阴"
        
        upper_shadow = (high - max(open_, close)) / prev_close * 100.0
        lower_shadow = (min(open_, close) - low) / prev_close * 100.0
        vol_ratio = turnover / bg_turnover if bg_turnover and bg_turnover > 0 else None
        
        records.append({
            'lag': int(lag),
            'date': str(df['date_str'].iloc[pos]),
            'close': round(close, 3),
            'daily_return': round(daily_ret, 4),
            'turnover': round(turnover, 4),
            'vol_ratio_vs_bg': round(vol_ratio, 3) if vol_ratio else None,
            'candle_type': candle_type,
            'is_limit_up': is_limit_up,
            'upper_shadow_pct': round(upper_shadow, 3),
            'lower_shadow_pct': round(lower_shadow, 3),
            'bg_turnover_t20': round(bg_turnover, 4) if bg_turnover else None,
        })
    
    return records


def analyze_series_pattern(records: list) -> dict:
    """统计分析"""
    df = pd.DataFrame(records)
    
    summary = {
        'generated_at': datetime.now().isoformat(),
        'total_samples': len(df[['stock_code', 'ignition_date']].drop_duplicates()),
        'total_day_records': len(df),
        'by_lag': {},
        'key_findings': {},
        'integrity_check': {}
    }
    
    # 按 lag 统计
    for lag in range(-10, 4):
        sub = df[df['lag'] == lag].dropna(subset=['turnover', 'daily_return'])
        
        if len(sub) == 0:
            continue
        
        t_data = sub['turnover']
        r_data = sub['daily_return']
        vr_data = sub['vol_ratio_vs_bg'].dropna()
        
        candle_dist = sub['candle_type'].value_counts().to_dict()
        limit_up_pct = sub['is_limit_up'].mean() * 100 if len(sub) > 0 else 0
        
        summary['by_lag'][str(lag)] = {
            'n': len(sub),
            'turnover': {
                'p10': round(t_data.quantile(0.1), 3),
                'p25': round(t_data.quantile(0.25), 3),
                'median': round(t_data.median(), 3),
                'p75': round(t_data.quantile(0.75), 3),
                'mean': round(t_data.mean(), 3),
            },
            'daily_return': {
                'median': round(r_data.median(), 3),
                'mean': round(r_data.mean(), 3),
            },
            'vol_ratio_vs_bg': {
                'median': round(vr_data.median(), 3) if len(vr_data) > 0 else None,
            },
            'candle_distribution': candle_dist,
            'limit_up_pct': round(limit_up_pct, 1),
        }
    
    # 完整性检查
    lag_data = summary['by_lag']
    
    if '-1' in lag_data:
        summary['integrity_check']['T-1涨停率'] = lag_data['-1']['limit_up_pct']
    if '0' in lag_data:
        summary['integrity_check']['T0涨停率'] = lag_data['0']['limit_up_pct']
        # T0下跌率
        t0_df = df[df['lag'] == 0]
        summary['integrity_check']['T0下跌率'] = round((t0_df['daily_return'] < -1).mean() * 100, 1)
    
    # 关键发现
    if '-1' in lag_data and '0' in lag_data:
        summary['key_findings'] = {
            'T-1换手中位': lag_data['-1']['turnover']['median'],
            'T-1涨跌幅中位': lag_data['-1']['daily_return']['median'],
            'T-1涨停比例': f"{lag_data['-1']['limit_up_pct']}%",
            'T0换手中位': lag_data['0']['turnover']['median'],
            'T0涨跌幅中位': lag_data['0']['daily_return']['median'],
            'T0涨停比例': f"{lag_data['0']['limit_up_pct']}%",
        }
    
    return summary


def generate_report(summary: dict, output_path: Path) -> None:
    """生成报告"""
    
    lag_data = summary.get('by_lag', {})
    findings = summary.get('key_findings', {})
    integrity = summary.get('integrity_check', {})
    
    lines = [
        "# 连板首板研究报告 V3.0",
        f"\n**生成时间**: {summary['generated_at']}",
        f"**样本量**: {summary['total_samples']} 个连板事件（≥3连板）",
        "",
        "---",
        "",
        "## 完整性检查",
        "",
        f"- T-1涨停率: {integrity.get('T-1涨停率', 'N/A')}%（应<5%）",
        f"- T0涨停率: {integrity.get('T0涨停率', 'N/A')}%（应>90%）",
        f"- T0下跌率: {integrity.get('T0下跌率', 'N/A')}%（应<5%）",
        "",
        "---",
        "",
        "## 逐日换手率画像",
        "",
        "| T日 | 换手P25 | 换手中位 | 换手P75 | 涨幅中位 | K线TOP1 | 涨停比例 |",
        "|-----|---------|---------|---------|---------|--------|--------|",
    ]
    
    for lag in range(-10, 4):
        k = str(lag)
        if k not in lag_data:
            continue
        d = lag_data[k]
        t = d['turnover']
        r = d['daily_return']
        candle_top = max(d['candle_distribution'], key=d['candle_distribution'].get) if d['candle_distribution'] else '-'
        
        label = f"T{lag}" if lag <= -1 else ("T0" if lag == 0 else f"T+{lag}")
        lines.append(
            f"| {label} | {t['p25']}% | **{t['median']}%** | {t['p75']}% | "
            f"{r['median']}% | {candle_top} | {d['limit_up_pct']}% |"
        )
    
    if findings:
        lines += [
            "",
            "---",
            "",
            "## 核心结论",
            "",
            f"- **T-1换手率中位**: {findings.get('T-1换手中位', 'N/A')}%",
            f"- **T-1涨跌幅中位**: {findings.get('T-1涨跌幅中位', 'N/A')}%",
            f"- **T-1涨停比例**: {findings.get('T-1涨停比例', 'N/A')}",
            f"- **T0换手率中位**: {findings.get('T0换手中位', 'N/A')}%",
            f"- **T0涨停比例**: {findings.get('T0涨停比例', 'N/A')}",
        ]
    
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    print("=" * 60)
    print("连板首板研究 V3.0 启动")
    print("核心改变：废弃滑动窗口，改用连板序列检测器")
    print("=" * 60)
    
    # 连接QMT
    from xtquant import xtdata
    xtdata.connect(port=58610)
    print("QMT连接成功")
    
    # 获取股票池
    stock_codes = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"股票池: {len(stock_codes)} 只")
    
    # 扫描所有股票
    all_series = []
    all_records = []
    
    for i, stock in enumerate(stock_codes, 1):
        if i % 200 == 0:
            print(f"  进度: {i}/{len(stock_codes)}, 已发现 {len(all_series)} 个连板事件")
        
        try:
            result = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock],
                period='1d',
                start_time='20240101',
                end_time='20260305',
                count=-1
            )
            
            if result is None or stock not in result:
                continue
            
            df = result[stock]
            if df is None or len(df) < 50:
                continue
            
            df = df.copy()
            df['date_str'] = df.index.astype(str)
            df = df.reset_index(drop=True)
            df = df[df['volume'] > 0].copy()
            
            # 获取流通股本
            detail = xtdata.get_instrument_detail(stock, False)
            if not detail:
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                continue
            
            # 检测连板序列
            series_list = detect_limit_up_series(df, float_vol, min_boards=3)
            
            for series in series_list:
                series['stock_code'] = stock
                series['ignition_date'] = series['start_date']
                all_series.append(series)
                
                # 计算逐日特征
                records = compute_pre_ignition_profile(df, series, float_vol)
                for rec in records:
                    rec['stock_code'] = stock
                    rec['ignition_date'] = series['start_date']
                    rec['num_boards'] = series['num_boards']
                    rec['total_return'] = series['total_return']
                all_records.extend(records)
            
            time.sleep(0.05)
            
        except Exception:
            continue
    
    print(f"\n发现 {len(all_series)} 个连板事件")
    
    if not all_series:
        print("无样本")
        return
    
    # 保存连板事件清单
    series_df = pd.DataFrame(all_series)
    series_csv = OUTPUT_DIR / "violent_surge_v3_series.csv"
    series_df.to_csv(series_csv, index=False, encoding="utf-8-sig")
    print(f"连板事件清单: {series_csv}")
    
    # 保存逐日特征
    detail_df = pd.DataFrame(all_records)
    detail_csv = OUTPUT_DIR / "violent_surge_v3_detailed.csv"
    detail_df.to_csv(detail_csv, index=False, encoding="utf-8-sig")
    print(f"逐日特征: {detail_csv} ({len(detail_df)} 行)")
    
    # 统计分析
    summary = analyze_series_pattern(all_records)
    
    # 保存JSON
    summary_json = OUTPUT_DIR / "violent_surge_v3_pattern.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"统计摘要: {summary_json}")
    
    # 生成报告
    report_path = OUTPUT_DIR / "REPORT_VIOLENT_SURGE_V3.md"
    generate_report(summary, report_path)
    print(f"报告: {report_path}")
    
    # 完整性检查结果
    print("\n" + "=" * 60)
    print("完整性检查：")
    integrity = summary.get('integrity_check', {})
    t1_lim = integrity.get('T-1涨停率', 999)
    t0_lim = integrity.get('T0涨停率', 0)
    
    if t1_lim < 5:
        print(f"  ✅ T-1涨停率: {t1_lim}% (<5%)")
    else:
        print(f"  ❌ T-1涨停率: {t1_lim}% (>=5%, 不合格)")
    
    if t0_lim > 90:
        print(f"  ✅ T0涨停率: {t0_lim}% (>90%)")
    else:
        print(f"  ⚠️ T0涨停率: {t0_lim}% (<90%, 需检查)")
    
    print("=" * 60)
    print("V3 完成！")


if __name__ == "__main__":
    main()
