#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5日均换手率死亡信号验证 - 细粒度版
目标：验证不同5日均换手率档位的1-10日收益率
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def get_turnover_buckets():
    """换手率分桶 - 每5%一档，从5%到70%"""
    buckets = []
    for low in range(5, 70, 5):
        high = low + 5
        buckets.append((low, high, f"{low}-{high}%"))
    buckets.append((70, 999, ">70%"))
    return buckets


def main():
    print("=" * 70)
    print("5日均换手率死亡信号验证（细粒度版）")
    print("=" * 70)
    
    # 连接QMT
    try:
        from xtquant import xtdata
        xtdata.connect(port=58610)
        print("✅ QMT连接成功")
    except Exception as e:
        print(f"❌ QMT连接失败: {e}")
        return
    
    # 参数
    end_date = '20260304'
    start_date = '20240101'
    forward_days = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"观察期: 1-10日")
    print(f"5日均换手率分档: 1-5%, 5-10%, ..., 75-80%, >80%")
    print("-" * 70)
    
    # 获取股票列表
    stock_codes = xtdata.get_stock_list_in_sector('沪深A股')
    
    print(f"扫描 {len(stock_codes)} 只股票...")
    
    events = []
    
    for i, stock in enumerate(stock_codes, 1):
        if i % 500 == 0:
            print(f"  进度: {i}/{len(stock_codes)}, 已收集{len(events)}个事件")
        
        try:
            # 获取足够长的日K数据（需要计算5日均线和后续10日收益）
            data = xtdata.get_local_data(
                field_list=['time', 'close', 'volume', 'amount'],
                stock_list=[stock],
                period='1d',
                start_time='20230901',
                end_time='20260320'
            )
            
            if not data or stock not in data:
                continue
            
            df = data[stock]
            if df is None or len(df) < 30:
                continue
            
            # 获取流通股本
            detail = xtdata.get_instrument_detail(stock, False)
            if not detail:
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                continue
            
            # 计算换手率和5日均换手率
            df = df.copy()
            df['date_str'] = pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y%m%d')
            df['turnover_rate'] = df['volume'] * 100.0 / float_vol * 100.0
            df['turnover_5d_avg'] = df['turnover_rate'].rolling(window=5, min_periods=1).mean()
            
            # 建立日期索引
            date_to_idx = {d: i for i, d in enumerate(df['date_str'].values)}
            
            # 筛选目标日期范围内的事件
            target_df = df[(df['date_str'] >= start_date) & (df['date_str'] <= end_date)]
            
            for idx, row in target_df.iterrows():
                event_date = row['date_str']
                event_close = float(row['close'])
                turnover_5d_avg = row['turnover_5d_avg']
                row_idx = date_to_idx.get(event_date)
                
                if row_idx is None or pd.isna(turnover_5d_avg):
                    continue
                
                # 【本地计算】forward returns
                fwd_returns = {}
                for n in forward_days:
                    future_idx = row_idx + n
                    if future_idx < len(df):
                        future_close = float(df['close'].iloc[future_idx])
                        ret = (future_close / event_close - 1.0) * 100.0
                        fwd_returns[f'fwd_{n}d'] = round(ret, 2)
                    else:
                        fwd_returns[f'fwd_{n}d'] = None
                
                # 分桶
                bucket = None
                for low, high, label in get_turnover_buckets():
                    if low <= turnover_5d_avg < high:
                        bucket = label
                        break
                
                if bucket:
                    events.append({
                        'stock_code': stock,
                        'date': event_date,
                        'turnover_5d_avg': round(turnover_5d_avg, 2),
                        'bucket': bucket,
                        **fwd_returns
                    })
        
        except Exception:
            continue
    
    print(f"\n✅ 收集完成: {len(events)}个事件")
    
    if not events:
        print("❌ 无有效事件")
        return
    
    # 输出CSV
    df_events = pd.DataFrame(events)
    csv_path = VALIDATION_DIR / "turnover_5d_avg_returns.csv"
    df_events.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # 分桶统计
    summary = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_events': len(df_events),
        'date_range': f"{start_date} ~ {end_date}",
        'forward_days': forward_days,
        'buckets': []
    }
    
    # 表格输出
    summary_lines = []
    summary_lines.append("=" * 150)
    summary_lines.append("5日均换手率 vs 后续收益验证（1-10日）")
    summary_lines.append("=" * 150)
    summary_lines.append(f"生成时间: {summary['generated_at']}")
    summary_lines.append(f"事件总数: {len(df_events)}")
    summary_lines.append("")
    
    # 表头
    header = f"{'5日均换手':<12} {'样本数':>8}"
    for n in forward_days:
        header += f" {n}日"
    header += f" {'3日胜率':>8}"
    summary_lines.append(header)
    summary_lines.append("-" * 150)
    
    # 每个分桶
    for low, high, label in get_turnover_buckets():
        dfb = df_events[df_events['bucket'] == label]
        if len(dfb) == 0:
            continue
        
        row = f"{label:<12} {len(dfb):>8}"
        bucket_data = {
            'bucket': label,
            'sample_count': len(dfb),
            'returns': {}
        }
        
        for n in forward_days:
            col = f'fwd_{n}d'
            if col in dfb.columns:
                r = dfb[col].dropna().astype(float)
                if len(r) > 0:
                    mean_ret = r.mean()
                    row += f" {mean_ret:>+7.2f}%"
                    bucket_data['returns'][f'{n}d'] = round(mean_ret, 2)
                else:
                    row += f" {'N/A':>8}"
                    bucket_data['returns'][f'{n}d'] = None
            else:
                row += f" {'N/A':>8}"
                bucket_data['returns'][f'{n}d'] = None
        
        # 计算3日胜率
        if 'fwd_3d' in dfb.columns:
            r3 = dfb['fwd_3d'].dropna().astype(float)
            if len(r3) > 0:
                win = (r3 > 0).mean() * 100.0
                row += f" {win:>7.1f}%"
                bucket_data['win_rate_3d'] = round(win, 1)
            else:
                row += f" {'N/A':>8}"
                bucket_data['win_rate_3d'] = None
        else:
            row += f" {'N/A':>8}"
            bucket_data['win_rate_3d'] = None
        
        summary['buckets'].append(bucket_data)
        summary_lines.append(row)
    
    # 找出最佳和最差分档
    summary_lines.append("-" * 150)
    summary_lines.append("")
    
    best_bucket = None
    worst_bucket = None
    best_5d_ret = -999
    worst_5d_ret = 999
    
    for b in summary['buckets']:
        if b['sample_count'] < 100:
            continue
        ret_5d = b['returns'].get('5d')
        if ret_5d is not None:
            if ret_5d > best_5d_ret:
                best_5d_ret = ret_5d
                best_bucket = b
            if ret_5d < worst_5d_ret:
                worst_5d_ret = ret_5d
                worst_bucket = b
    
    summary['best_bucket'] = best_bucket
    summary['worst_bucket'] = worst_bucket
    
    if best_bucket:
        summary_lines.append(f"5日收益最高档: {best_bucket['bucket']} ({best_bucket['sample_count']}样本, 5日收益{best_5d_ret:+.2f}%)")
    if worst_bucket:
        summary_lines.append(f"5日收益最低档: {worst_bucket['bucket']} ({worst_bucket['sample_count']}样本, 5日收益{worst_5d_ret:+.2f}%)")
    
    # 输出JSON
    json_path = VALIDATION_DIR / "turnover_5d_avg_returns.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 输出TXT
    txt_path = VALIDATION_DIR / "turnover_5d_avg_returns_summary.txt"
    txt_path.write_text("\n".join(summary_lines), encoding='utf-8')
    
    print(f"✅ 输出CSV: {csv_path}")
    print(f"✅ 输出JSON: {json_path}")
    print(f"✅ 输出摘要: {txt_path}")
    print("\n" + "\n".join(summary_lines))


if __name__ == "__main__":
    main()