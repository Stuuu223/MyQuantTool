#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高换手率死亡信号验证 - 简化版
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
from logic.utils.calendar_utils import get_nth_previous_trading_day

VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def get_turnover_buckets():
    """换手率分桶"""
    return [
        (30, 50, "30-50%"),
        (50, 70, "50-70%"),
        (70, 100, "70-100%"),
        (100, 999, ">100%")
    ]


def calculate_forward_returns(stock_code: str, event_date: str, event_close: float, forward_days: list) -> dict:
    """计算事件后N日收益"""
    from xtquant import xtdata
    from logic.utils.calendar_utils import get_next_trading_day
    
    returns = {}
    
    for n in forward_days:
        try:
            # 逐日找下一个交易日，重复n次
            future_date = event_date
            for _ in range(n):
                future_date = get_next_trading_day(future_date)
                if future_date is None:
                    raise ValueError("No next trading day")
            
            future_data = xtdata.get_local_data(
                field_list=['close'],
                stock_list=[stock_code],
                period='1d',
                start_time=future_date,
                end_time=future_date
            )
            
            if future_data and stock_code in future_data and len(future_data[stock_code]) > 0:
                future_close = float(future_data[stock_code]['close'].iloc[-1])
                ret = (future_close / event_close - 1.0) * 100.0
                returns[f'fwd_{n}d'] = round(ret, 2)
            else:
                returns[f'fwd_{n}d'] = None
        except:
            returns[f'fwd_{n}d'] = None
    
    return returns


def main():
    print("=" * 70)
    print("高换手率死亡信号验证（简化版）")
    print("=" * 70)
    
    # 连接QMT
    try:
        from xtquant import xtdata
        xtdata.connect(port=58610)
        print("✅ QMT连接成功")
    except Exception as e:
        print(f"❌ QMT连接失败: {e}")
        return
    
    # 参数 - 扩大时间范围
    end_date = '20260304'
    start_date = '20240101'  # 扩大到2024年
    forward_days = [1, 3, 5, 10]
    
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"观察期: 次日、3日、5日、10日")
    print("-" * 70)
    
    # 获取股票列表
    stock_codes = xtdata.get_stock_list_in_sector('沪深A股')
    
    print(f"扫描 {len(stock_codes)} 只股票...")
    
    events = []
    
    for i, stock in enumerate(stock_codes, 1):
        if i % 500 == 0:
            print(f"  进度: {i}/{len(stock_codes)}, 已收集{len(events)}个事件")
        
        try:
            # 获取日K数据
            data = xtdata.get_local_data(
                field_list=['time', 'close', 'volume', 'amount'],
                stock_list=[stock],
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            if not data or stock not in data:
                continue
            
            df = data[stock]
            if df is None or len(df) < 5:
                continue
            
            # 获取流通股本
            detail = xtdata.get_instrument_detail(stock, False)
            if not detail:
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                continue
            
            # 计算换手率（volume是手，乘100转股）
            df = df.copy()
            df['date'] = pd.to_datetime(df['time'], unit='ms')
            df['turnover_rate'] = df['volume'] * 100.0 / float_vol * 100.0
            
            # 找出高换手事件（>=30%）
            high_turnover = df[df['turnover_rate'] >= 30.0]
            
            for _, row in high_turnover.iterrows():
                event_date = row['date'].strftime('%Y%m%d')
                event_close = float(row['close'])
                turnover = row['turnover_rate']
                
                # 计算forward return
                fwd_returns = calculate_forward_returns(stock, event_date, event_close, forward_days)
                
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
        
        except:
            continue
    
    print(f"\n✅ 收集完成: {len(events)}个高换手事件")
    
    if not events:
        print("❌ 无有效事件")
        return
    
    # 输出CSV
    df_events = pd.DataFrame(events)
    csv_path = VALIDATION_DIR / "turnover_death_signal.csv"
    df_events.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # 分桶统计
    summary_lines = []
    summary_lines.append("=" * 70)
    summary_lines.append("高换手率死亡信号验证 - 简化版（1/3/5/10日）")
    summary_lines.append("=" * 70)
    summary_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append(f"事件总数: {len(df_events)}")
    summary_lines.append("")
    
    for _, _, label in get_turnover_buckets():
        dfb = df_events[df_events['bucket'] == label]
        summary_lines.append(f"[{label}] 样本数: {len(dfb)}")
        
        if len(dfb) > 0:
            for col in ['fwd_1d', 'fwd_3d', 'fwd_5d', 'fwd_10d']:
                if col in dfb.columns:
                    r = dfb[col].dropna().astype(float)
                    if len(r) > 0:
                        win = (r > 0).mean() * 100.0
                        summary_lines.append(
                            f"  {col}: mean={r.mean():.2f}% | median={r.median():.2f}% | "
                            f"win={win:.1f}% | max={r.max():.2f}% | min={r.min():.2f}%"
                        )
        summary_lines.append("")
    
    txt_path = VALIDATION_DIR / "turnover_death_signal_summary.txt"
    txt_path.write_text("\n".join(summary_lines), encoding='utf-8')
    
    print(f"✅ 输出明细: {csv_path}")
    print(f"✅ 输出摘要: {txt_path}")
    print("\n" + "\n".join(summary_lines))


if __name__ == "__main__":
    main()