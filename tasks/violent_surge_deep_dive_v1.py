#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暴力拉升型深度研究 V1.0 - 连板起爆前操盘画像
目标：挖掘 T-5 到 T-1 的逐日暗流特征
样本：连板暴力型（≥3涨停板，3-5天，日K）

运行方式：
    python tasks/violent_surge_deep_dive_v1.py

输出文件：
    data/validation/violent_surge_samples_detailed.csv   - 逐日特征明细
    data/validation/violent_surge_pre_pattern.json       - 统计摘要
    data/validation/violent_surge_report.md              - 分析报告
"""

import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "data" / "validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime) [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def load_violent_samples(csv_path: Path) -> pd.DataFrame:
    """筛选连板暴力型样本"""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    
    violent = df[
        (df['days'] <= 5) &
        (df['total_return'] >= 30) &
        (df['limit_up_count'] >= 3)
    ].copy()
    
    log.info(f"连板暴力型样本: {len(violent)} 个")
    log.info(f"涨停板分布:\n{violent['limit_up_count'].value_counts().sort_index()}")
    
    return violent


def fetch_kline_window(stock_code: str, start_date: str, xtdata, 
                       lookback_days: int = 25, lookahead_days: int = 6) -> pd.DataFrame | None:
    """获取股票在起爆日前后的日K数据窗口"""
    dt = datetime.strptime(start_date, "%Y%m%d")
    fetch_start = (dt - timedelta(days=lookback_days + 15)).strftime("%Y%m%d")
    fetch_end = (dt + timedelta(days=lookahead_days + 5)).strftime("%Y%m%d")
    
    try:
        result = xtdata.get_market_data_ex(
            stock_list=[stock_code],
            field_list=["open", "high", "low", "close", "volume"],
            period="1d",
            start_time=fetch_start,
            end_time=fetch_end,
            count=-1
        )
        
        if result is None or stock_code not in result:
            return None
        
        df = result[stock_code].copy()
        df['date_str'] = df.index.astype(str)
        df = df.reset_index(drop=True)
        df = df[df['volume'] > 0].copy()
        
        return df
        
    except Exception as e:
        log.error(f"  {stock_code} 获取K线失败: {e}")
        return None


def compute_day_features(kline_df: pd.DataFrame, ignition_date: str, 
                         float_vol: float, window: int = 10) -> list:
    """以起爆日为基准，计算 T-N 到 T+3 的逐日特征"""
    
    # 找起爆日位置
    try:
        ign_pos = None
        for i, d in enumerate(kline_df['date_str'].values):
            if d == ignition_date:
                ign_pos = i
                break
            elif d > ignition_date:
                ign_pos = i  # 取最接近的
                break
        
        if ign_pos is None or ign_pos >= len(kline_df):
            return []
    except:
        return []
    
    features = []
    
    # 计算背景换手率（T-20均）
    t20_start = max(0, ign_pos - 20)
    t20_vols = kline_df['volume'].iloc[t20_start:ign_pos]
    bg_vol_avg = t20_vols.mean() if len(t20_vols) > 0 else np.nan
    bg_turnover = bg_vol_avg * 100.0 / float_vol * 100.0 if float_vol > 0 and bg_vol_avg > 0 else np.nan
    
    # T-window 到 T+3
    for lag in range(-window, 4):
        pos = ign_pos + lag
        if pos < 0 or pos >= len(kline_df):
            continue
        
        row = kline_df.iloc[pos]
        prev_pos = pos - 1
        
        close = float(row['close'])
        open_ = float(row['open'])
        high = float(row['high'])
        low = float(row['low'])
        vol = float(row['volume'])
        
        # 换手率
        turnover = vol * 100.0 / float_vol * 100.0 if float_vol > 0 else np.nan
        
        # 涨跌幅
        if prev_pos >= 0:
            prev_close = float(kline_df['close'].iloc[prev_pos])
            daily_return = (close - prev_close) / prev_close * 100.0
        else:
            prev_close = np.nan
            daily_return = np.nan
        
        # 换手率相对背景的倍数
        vol_ratio = turnover / bg_turnover if bg_turnover and bg_turnover > 0 else np.nan
        
        # K线形态分类
        if not np.isnan(prev_close) and prev_close > 0:
            body_pct = (close - open_) / prev_close * 100.0
            if body_pct > 9.5:
                candle_type = "涨停"
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
        else:
            candle_type = "未知"
            body_pct = np.nan
        
        # 是否涨停
        is_limit_up = (9.5 <= daily_return <= 10.5) or (19 <= daily_return <= 21) if not np.isnan(daily_return) else False
        
        features.append({
            'lag': lag,
            'date': kline_df['date_str'].iloc[pos],
            'close': round(close, 3),
            'turnover': round(turnover, 4) if not np.isnan(turnover) else None,
            'daily_return': round(daily_return, 4) if not np.isnan(daily_return) else None,
            'vol_ratio_vs_bg': round(vol_ratio, 3) if not np.isnan(vol_ratio) else None,
            'candle_type': candle_type,
            'is_limit_up': is_limit_up,
            'bg_turnover_t20': round(bg_turnover, 4) if not np.isnan(bg_turnover) else None,
        })
    
    return features


def process_all_samples(violent_df: pd.DataFrame, xtdata, max_samples: int = None) -> list:
    """批量处理所有样本"""
    samples = violent_df if max_samples is None else violent_df.head(max_samples)
    
    all_records = []
    failed_count = 0
    
    for idx, row in samples.iterrows():
        stock_code = row['stock_code']
        start_date = str(int(row['start_date']))
        total_return = row['total_return']
        days = row['days']
        limit_ups = row['limit_up_count']
        return_bucket = row['return_bucket']
        
        log.info(f"[{idx+1}/{len(samples)}] {stock_code} | 起爆日:{start_date} | {days}天涨{total_return:.1f}% | {limit_ups}板")
        
        # 获取流通股本
        try:
            detail = xtdata.get_instrument_detail(stock_code, False)
            if detail is None:
                failed_count += 1
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                failed_count += 1
                continue
        except:
            failed_count += 1
            continue
        
        # 获取K线
        kline_df = fetch_kline_window(stock_code, start_date, xtdata)
        if kline_df is None or len(kline_df) < 10:
            failed_count += 1
            continue
        
        # 计算逐日特征
        day_features = compute_day_features(kline_df, start_date, float_vol)
        
        if not day_features:
            failed_count += 1
            continue
        
        # 附加样本元信息
        for feat in day_features:
            feat.update({
                'stock_code': stock_code,
                'ignition_date': start_date,
                'sample_days': days,
                'sample_return': round(total_return, 2),
                'sample_limit_ups': limit_ups,
                'return_bucket': return_bucket,
            })
        
        all_records.extend(day_features)
        time.sleep(0.1)
    
    log.info(f"处理完成: {len(samples) - failed_count} 成功 / {failed_count} 失败")
    log.info(f"生成逐日特征记录: {len(all_records)} 条")
    
    return all_records


def analyze_pre_ignition_pattern(records: list) -> dict:
    """对 T-10 到 T0 的逐日特征做统计分析"""
    df = pd.DataFrame(records)
    
    summary = {
        'generated_at': datetime.now().isoformat(),
        'total_samples': df[['stock_code', 'ignition_date']].drop_duplicates().shape[0],
        'total_day_records': len(df),
        'by_lag': {},
        'key_findings': {}
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
                'p10': round(r_data.quantile(0.1), 3),
                'p25': round(r_data.quantile(0.25), 3),
                'median': round(r_data.median(), 3),
                'p75': round(r_data.quantile(0.75), 3),
                'mean': round(r_data.mean(), 3),
            },
            'vol_ratio_vs_bg': {
                'median': round(vr_data.median(), 3) if len(vr_data) > 0 else None,
            },
            'candle_distribution': candle_dist,
            'limit_up_pct': round(limit_up_pct, 1),
        }
    
    # 关键发现
    lag_data = summary['by_lag']
    if '-1' in lag_data and '0' in lag_data:
        summary['key_findings'] = {
            'T-1换手中位': lag_data['-1']['turnover']['median'],
            'T-1涨跌幅中位': lag_data['-1']['daily_return']['median'],
            'T0换手中位': lag_data['0']['turnover']['median'],
            'T0涨跌幅中位': lag_data['0']['daily_return']['median'],
            'T0涨停比例': f"{lag_data['0']['limit_up_pct']}%",
            'T-1K线分布': lag_data['-1']['candle_distribution'],
        }
    
    return summary


def generate_report(summary: dict, output_path: Path) -> None:
    """生成 Markdown 格式分析报告"""
    
    lag_data = summary.get('by_lag', {})
    findings = summary.get('key_findings', {})
    
    lines = [
        "# 暴力拉升型深度研究报告 V1.0",
        f"\n**生成时间**: {summary['generated_at']}",
        f"**样本量**: {summary['total_samples']} 个连板暴力事件（≥3涨停板，3-5天）",
        "",
        "---",
        "",
        "## 一、逐日换手率画像",
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
            "## 二、核心结论",
            "",
            f"- **T-1换手率中位**: {findings.get('T-1换手中位', 'N/A')}%",
            f"- **T-1涨跌幅中位**: {findings.get('T-1涨跌幅中位', 'N/A')}%",
            f"- **T0换手率中位**: {findings.get('T0换手中位', 'N/A')}%",
            f"- **T0涨停比例**: {findings.get('T0涨停比例', 'N/A')}",
        ]
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"报告已写入: {output_path}")


def main():
    log.info("=" * 60)
    log.info("暴力拉升型深度研究 V1.0 启动")
    log.info("=" * 60)
    
    # Step 1: 加载现有样本
    csv_path = PROJECT_ROOT / "data" / "validation" / "violent_moves_v2.csv"
    if not csv_path.exists():
        log.error(f"样本文件不存在: {csv_path}")
        sys.exit(1)
    
    violent_df = load_violent_samples(csv_path)
    
    # Step 2: 连接 QMT
    log.info("连接 QMT...")
    try:
        from xtquant import xtdata
        xtdata.connect(port=58610)
        log.info("QMT连接成功")
    except Exception as e:
        log.error(f"QMT连接失败: {e}")
        sys.exit(1)
    
    # Step 3: 批量处理（全量）
    records = process_all_samples(
        violent_df=violent_df,
        xtdata=xtdata,
        max_samples=None,  # 全量
    )
    
    if not records:
        log.error("未获取到任何逐日特征数据")
        sys.exit(1)
    
    # Step 4: 保存明细 CSV
    detail_df = pd.DataFrame(records)
    detail_csv = OUTPUT_DIR / "violent_surge_samples_detailed.csv"
    detail_df.to_csv(detail_csv, index=False, encoding="utf-8-sig")
    log.info(f"明细已保存: {detail_csv} ({len(detail_df)} 行)")
    
    # Step 5: 统计分析
    summary = analyze_pre_ignition_pattern(records)
    
    # 保存 JSON
    summary_json = OUTPUT_DIR / "violent_surge_pre_pattern.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info(f"统计摘要已保存: {summary_json}")
    
    # Step 6: 生成报告
    report_path = OUTPUT_DIR / "violent_surge_report.md"
    generate_report(summary, report_path)
    
    # Step 7: 控制台预览
    log.info("")
    log.info("=" * 60)
    log.info("核心发现预览：")
    
    lag_data = summary.get('by_lag', {})
    for lag in [-5, -4, -3, -2, -1, 0, 1, 2]:
        k = str(lag)
        if k not in lag_data:
            continue
        d = lag_data[k]
        label = f"T{lag}" if lag <= -1 else ("T0" if lag == 0 else f"T+{lag}")
        log.info(
            f"  {label:6s} | 换手中位:{d['turnover']['median']:6.2f}% | "
            f"涨幅中位:{d['daily_return']['median']:+6.2f}% | "
            f"涨停:{d['limit_up_pct']}%"
        )
    
    log.info("=" * 60)
    log.info("全部完成！")


if __name__ == "__main__":
    main()
