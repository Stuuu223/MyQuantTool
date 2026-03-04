#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高换手率死亡信号验证 - 优化版（本地数据一次性获取）
目标：验证不同换手率档位的后续表现
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.core.config_manager import get_config_manager

VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def get_turnover_buckets():
    """换手率分桶 - 每5%一档"""
    buckets = []
    for low in range(5, 80, 5):
        high = low + 5
        buckets.append((low, high, f"{low}-{high}%"))
    buckets.append((80, 999, ">80%"))
    return buckets


def main():
    print("=" * 70)
    print("高换手率死亡信号验证（本地数据优化版）")
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
    print(f"换手率分档: 5-10%, 10-15%, ..., 75-80%, >80%")
    print("-" * 70)
    
    # 获取股票列表
    stock_codes = xtdata.get_stock_list_in_sector('沪深A股')
    
    print(f"扫描 {len(stock_codes)} 只股票...")
    
    events = []
    
    for i, stock in enumerate(stock_codes, 1):
        if i % 500 == 0:
            print(f"  进度: {i}/{len(stock_codes)}, 已收集{len(events)}个事件")
        
        try:
            # 【优化】一次性获取所有日K数据（包含足够的时间窗口计算forward returns）
            data = xtdata.get_local_data(
                field_list=['time', 'close', 'volume', 'amount'],
                stock_list=[stock],
                period='1d',
                start_time='20230901',  # 提前开始，确保有历史数据
                end_time='20260320'     # 延后结束，确保能计算forward returns
            )
            
            if not data or stock not in data:
                continue
            
            df = data[stock]
            if df is None or len(df) < 30:
                continue
            
            # 获取流通股本（只调用一次）
            detail = xtdata.get_instrument_detail(stock, False)
            if not detail:
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                continue
            
            # 【本地计算】计算换手率和forward returns
            df = df.copy()
            df['date_str'] = pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y%m%d')
            df['turnover_rate'] = df['volume'] * 100.0 / float_vol * 100.0
            
            # 建立日期索引
            date_to_idx = {d: i for i, d in enumerate(df['date_str'].values)}
            
            # 找出高换手事件
            high_turnover = df[(df['turnover_rate'] >= 5.0) & (df['date_str'] >= start_date) & (df['date_str'] <= end_date)]
            
            for idx, row in high_turnover.iterrows():
                event_date = row['date_str']
                event_close = float(row['close'])
                turnover = row['turnover_rate']
                row_idx = date_to_idx.get(event_date)
                
                if row_idx is None:
                    continue
                
                # 【本地计算】forward returns - 直接从df中取
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
                    if low <= turnover < high:
                        bucket = label
                        break
                
                if bucket:
                    events.append({
                        'stock_code': stock,
                        'date': event_date,
                        'turnover_rate': turnover,
                        'bucket': bucket,
                        **fwd_returns
                    })
        
        except Exception as e:
            continue
    
    print(f"\n✅ 收集完成: {len(events)}个高换手事件")
    
    if not events:
        print("❌ 无有效事件")
        return
    
    # 输出CSV
    df_events = pd.DataFrame(events)
    csv_path = VALIDATION_DIR / "turnover_death_signal.csv"
    df_events.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # 分桶统计 - 表格格式
    summary_lines = []
    summary_lines.append("=" * 140)
    summary_lines.append("高换手率死亡信号验证 - 细粒度版（换手率每5%分档，收益1-10日）")
    summary_lines.append("=" * 140)
    summary_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append(f"事件总数: {len(df_events)}")
    summary_lines.append("")
    
    # 表头
    header = f"{'换手率档位':<12} {'样本数':>8}"
    for n in forward_days:
        header += f" {n}日收益"
    header += f" {'3日胜率':>8}"
    summary_lines.append(header)
    summary_lines.append("-" * 140)
    
    # 每个分桶
    for low, high, label in get_turnover_buckets():
        dfb = df_events[df_events['bucket'] == label]
        if len(dfb) == 0:
            continue
        
        row = f"{label:<12} {len(dfb):>8}"
        
        for n in forward_days:
            col = f'fwd_{n}d'
            if col in dfb.columns:
                r = dfb[col].dropna().astype(float)
                if len(r) > 0:
                    mean_ret = r.mean()
                    row += f" {mean_ret:>+10.2f}%"
                else:
                    row += f" {'N/A':>10}"
            else:
                row += f" {'N/A':>10}"
        
        # 计算综合胜率（使用3日收益）
        if 'fwd_3d' in dfb.columns:
            r3 = dfb['fwd_3d'].dropna().astype(float)
            if len(r3) > 0:
                win = (r3 > 0).mean() * 100.0
                row += f" {win:>7.1f}%"
            else:
                row += f" {'N/A':>8}"
        else:
            row += f" {'N/A':>8}"
        
        summary_lines.append(row)
    
    # 添加汇总
    summary_lines.append("-" * 140)
    summary_lines.append("")
    summary_lines.append("【关键发现】")
    summary_lines.append("")
    
    # 找出胜率最高和最低的分档
    best_bucket = None
    worst_bucket = None
    best_win = -999
    worst_win = 999
    
    for low, high, label in get_turnover_buckets():
        dfb = df_events[df_events['bucket'] == label]
        if len(dfb) < 10:
            continue
        if 'fwd_3d' in dfb.columns:
            r = dfb['fwd_3d'].dropna().astype(float)
            if len(r) > 0:
                win = (r > 0).mean() * 100.0
                if win > best_win:
                    best_win = win
                    best_bucket = (label, len(dfb), win)
                if win < worst_win:
                    worst_win = win
                    worst_bucket = (label, len(dfb), win)
    
    if best_bucket:
        summary_lines.append(f"胜率最高档: {best_bucket[0]} ({best_bucket[1]}样本, 胜率{best_bucket[2]:.1f}%)")
    if worst_bucket:
        summary_lines.append(f"胜率最低档: {worst_bucket[0]} ({worst_bucket[1]}样本, 胜率{worst_bucket[2]:.1f}%)")
    
    txt_path = VALIDATION_DIR / "turnover_death_signal_summary.txt"
    txt_path.write_text("\n".join(summary_lines), encoding='utf-8')
    
    print(f"✅ 输出明细: {csv_path}")
    print(f"✅ 输出摘要: {txt_path}")
    print("\n" + "\n".join(summary_lines))


if __name__ == "__main__":
    main()