#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
150% 死亡换手验证脚本 V2.0（复用 TrueDictionary 架构）

直接调用 TrueDictionary 获取日线数据和换手率，不再重复造轮子。
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_providers.true_dictionary import TrueDictionary
from logic.core.config_manager import get_config_manager
from logic.utils.calendar_utils import get_nth_previous_trading_day

VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 70)
    print("150% 死亡换手验证（基于 TrueDictionary 市值平替法）")
    print("=" * 70)
    
    # 连接QMT
    try:
        from xtquant import xtdata
        xtdata.connect(port=58610)
        print("✅ QMT连接成功")
    except Exception as e:
        print(f"❌ QMT连接失败: {e}")
        return
    
    # 初始化
    cfg = get_config_manager()
    truedict = TrueDictionary()
    
    # 参数
    target_date = datetime.now().strftime('%Y%m%d')
    lookback_days = 90
    start_date = get_nth_previous_trading_day(target_date, lookback_days)
    
    bucket_min = 70.0
    bucket_death = 150.0
    bucket_extreme = 200.0
    
    print(f"目标日期: {target_date}")
    print(f"回溯起点: {start_date}")
    print(f"换手率分桶: [{bucket_min},{bucket_death}), [{bucket_death},{bucket_extreme}), >={bucket_extreme}")
    print("-" * 70)
    
    # 获取全市场股票列表
    try:
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        return
    
    print(f"全市场股票数: {len(all_stocks)}")
    
    # 【CTO铁血令】先warmup TrueDictionary，加载流通股本
    print("📦 正在预热TrueDictionary...")
    warmup_result = truedict.warmup(all_stocks, target_date=target_date)
    print(f"✅ 预热完成: FloatVolume={warmup_result.get('qmt', {}).get('success', 0)}只")
    print("-" * 70)
    
    # 收集事件
    events = []
    skipped = 0
    
    for i, stock in enumerate(all_stocks, 1):
        if i % 500 == 0:
            print(f"进度: {i}/{len(all_stocks)}")
        
        try:
            # 获取5日平均换手率（TrueDictionary 封装好的）
            avg_turnover_5d = truedict.get_avg_turnover_5d(stock, target_date)
            if avg_turnover_5d is None or avg_turnover_5d < bucket_min:
                skipped += 1
                continue
            
            # 获取日线数据（用于计算forward return）
            data = xtdata.get_local_data(
                field_list=['close'],
                stock_list=[stock],
                period='1d',
                start_time=start_date,
                end_time=target_date
            )
            
            if stock not in data or data[stock] is None or len(data[stock]) < 10:
                skipped += 1
                continue
            
            df = data[stock]
            df = df.reset_index()
            df['date'] = pd.to_datetime(df['time'], unit='ms', errors='coerce')
            df = df.dropna(subset=['date'])
            
            if len(df) < 10:
                skipped += 1
                continue
            
            # 计算 forward return
            df['fwd_1d_ret'] = (df['close'].shift(-1) / df['close'] - 1.0) * 100.0
            df['fwd_3d_ret'] = (df['close'].shift(-3) / df['close'] - 1.0) * 100.0
            
            # 取最后一个交易日
            last_row = df.iloc[-1]
            if pd.isna(last_row['fwd_1d_ret']) or pd.isna(last_row['fwd_3d_ret']):
                skipped += 1
                continue
            
            # 分桶
            if avg_turnover_5d < bucket_death:
                bucket = f"{bucket_min:.0f}-{bucket_death:.0f}%"
            elif avg_turnover_5d < bucket_extreme:
                bucket = f"{bucket_death:.0f}-{bucket_extreme:.0f}%"
            else:
                bucket = f">={bucket_extreme:.0f}%"
            
            events.append({
                'stock_code': stock,
                'date': last_row['date'],
                'turnover_rate': avg_turnover_5d,
                'bucket': bucket,
                'fwd_1d_ret': last_row['fwd_1d_ret'],
                'fwd_3d_ret': last_row['fwd_3d_ret']
            })
            
        except Exception:
            skipped += 1
            continue
    
    print(f"收集事件数: {len(events)}, 跳过: {skipped}")
    
    if not events:
        print("❌ 无有效事件样本")
        return
    
    # 输出CSV
    df_events = pd.DataFrame(events)
    csv_path = VALIDATION_DIR / "death_turnover_150_events.csv"
    df_events.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # 分桶统计
    summary_lines = []
    summary_lines.append("=" * 70)
    summary_lines.append("150% 死亡换手验证 - 分桶统计")
    summary_lines.append("=" * 70)
    summary_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append(f"事件样本数: {len(df_events)}")
    summary_lines.append("")
    
    for bucket in [f"{bucket_min:.0f}-{bucket_death:.0f}%",
                   f"{bucket_death:.0f}-{bucket_extreme:.0f}%",
                   f">={bucket_extreme:.0f}%"]:
        dfb = df_events[df_events['bucket'] == bucket]
        summary_lines.append(f"[{bucket}] 样本数: {len(dfb)}")
        if len(dfb) > 0:
            for col in ['fwd_1d_ret', 'fwd_3d_ret']:
                r = dfb[col].astype(float)
                win = (r > 0).mean() * 100.0
                summary_lines.append(
                    f"  {col}: mean={r.mean():.3f}% | median={r.median():.3f}% | "
                    f"win%={win:.2f}% | p5={np.percentile(r, 5):.3f}%"
                )
        summary_lines.append("")
    
    txt_path = VALIDATION_DIR / "death_turnover_150_summary.txt"
    txt_path.write_text("\n".join(summary_lines), encoding='utf-8')
    
    print(f"✅ 输出事件明细: {csv_path}")
    print(f"✅ 输出统计摘要: {txt_path}")

if __name__ == "__main__":
    main()
