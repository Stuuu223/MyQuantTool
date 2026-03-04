#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5日均换手率死亡信号验证 - 细粒度版
目标：验证不同5日均换手率档位的1-10日收益率
新增：反向验证 - 从最高收益股票反推换手率分布
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
    """换手率分桶 - 从3%开始，每5%一档"""
    buckets = []
    buckets.append((3, 5, "3-5%"))
    for low in range(5, 70, 5):
        high = low + 5
        buckets.append((low, high, f"{low}-{high}%"))
    buckets.append((70, 999, ">70%"))
    return buckets


def extreme_analysis():
    """极端高收益样本分析：右侧起爆哲学"""
    print("\n" + "=" * 80)
    print("极端高收益样本分析：右侧起爆哲学")
    print("=" * 80)
    
    try:
        from xtquant import xtdata
        xtdata.connect(port=58610)
    except Exception as e:
        print(f"❌ QMT连接失败: {e}")
        return
    
    end_date = '20260304'
    start_date = '20240101'
    
    # 收益区间：(持有天数, 收益下限%, 收益上限%, 描述)
    return_ranges = [
        (5, 30, 50, "5天30-50%"),
        (5, 50, 80, "5天50-80%"),
        (5, 80, 999, "5天80%+"),
        (10, 50, 70, "10天50-70%"),
        (10, 70, 100, "10天70-100%"),
        (10, 100, 150, "10天100-150%"),
        (10, 150, 999, "10天150%+"),
        (20, 70, 100, "20天70-100%"),
        (20, 100, 150, "20天100-150%"),
        (20, 150, 200, "20天150-200%"),
        (20, 200, 999, "20天200%+"),
        (30, 100, 150, "30天100-150%"),
        (30, 150, 200, "30天150-200%"),
        (30, 200, 300, "30天200-300%"),
        (30, 300, 999, "30天300%+"),
    ]
    
    stock_codes = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"扫描 {len(stock_codes)} 只股票...")
    
    # 收集所有事件：{ (days, low, high): [(turnover_5d_avg, return_pct, stock, date), ...] }
    all_events = {r[:3]: [] for r in return_ranges}
    
    for i, stock in enumerate(stock_codes):
        if (i + 1) % 500 == 0:
            print(f"  进度: {i+1}/{len(stock_codes)}")
        
        try:
            result = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock],
                period='1d',
                start_time=start_date,
                end_time=end_date,
                count=-1
            )
            if result is None or stock not in result:
                continue
            df = result[stock]
            if df is None or len(df) < 35:
                continue
            
            detail = xtdata.get_instrument_detail(stock, False)
            if not detail:
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                continue
            
            df = df.copy()
            df['date_str'] = df.index.astype(str)
            df['turnover_rate'] = df['volume'] * 100.0 / float_vol * 100.0
            df['turnover_5d_avg'] = df['turnover_rate'].rolling(window=5, min_periods=1).mean()
            df = df.reset_index(drop=True)
            
            for row_idx in range(len(df) - 30):
                event_close = float(df['close'].iloc[row_idx])
                turnover_5d_avg = df['turnover_5d_avg'].iloc[row_idx]
                event_date = df['date_str'].iloc[row_idx]
                
                if pd.isna(turnover_5d_avg) or turnover_5d_avg <= 0:
                    continue
                
                # 计算各持有期收益
                for days, low_ret, high_ret, desc in return_ranges:
                    if row_idx + days >= len(df):
                        continue
                    future_close = float(df['close'].iloc[row_idx + days])
                    ret = (future_close / event_close - 1.0) * 100.0
                    if low_ret <= ret < high_ret:
                        all_events[(days, low_ret, high_ret)].append((turnover_5d_avg, ret, stock, event_date))
        except Exception:
            continue
    
    print(f"\n✅ 收集完成")
    
    # 分析结果
    results = {}
    print("\n" + "=" * 110)
    print(f"{'收益区间':<15} {'样本数':<8} {'换手均值':<10} {'换手中位':<10} {'收益均值':<12} {'主要换手分布'}")
    print("-" * 110)
    
    for days, low_ret, high_ret, desc in return_ranges:
        events = all_events[(days, low_ret, high_ret)]
        if len(events) < 10:
            continue
        
        # 按收益排序，取前200（或全部）
        events_sorted = sorted(events, key=lambda x: x[1], reverse=True)[:200]
        
        turnovers = [e[0] for e in events_sorted]
        returns = [e[1] for e in events_sorted]
        
        avg_turnover = np.mean(turnovers)
        median_turnover = np.median(turnovers)
        avg_return = np.mean(returns)
        
        # 分档统计
        bucket_counts = {}
        fine_buckets = [(1, 2, "1-2%"), (2, 3, "2-3%"), (3, 5, "3-5%"), 
                       (5, 10, "5-10%"), (10, 15, "10-15%"), (15, 20, "15-20%"), (20, 999, ">20%")]
        for low, high, label in fine_buckets:
            count = sum(1 for t in turnovers if low <= t < high)
            pct = count / len(turnovers) * 100 if turnovers else 0
            if pct > 0:
                bucket_counts[label] = round(pct, 1)
        
        results[desc] = {
            'sample_count': len(events_sorted),
            'total_candidates': len(events),
            'avg_turnover': round(avg_turnover, 2),
            'median_turnover': round(median_turnover, 2),
            'avg_return': round(avg_return, 2),
            'bucket_distribution': bucket_counts
        }
        
        # 打印
        main_buckets = sorted(bucket_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        bucket_str = ', '.join([f'{k}:{v}%' for k, v in main_buckets])
        ret_str = f"+{avg_return:.1f}%" if high_ret == 999 else f"+{avg_return:.1f}%"
        print(f"{desc:<15} {len(events_sorted):>5}     {avg_turnover:>7.2f}%    {median_turnover:>7.2f}%    {ret_str:>10}   {bucket_str}")
    
    # 保存结果
    output_path = VALIDATION_DIR / "turnover_extreme_analysis.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存: {output_path}")
    
    return results
    """反向分析：从最高收益股票反推换手率分布"""
    print("\n" + "=" * 80)
    print("反向验证：最高收益股票的换手率分布")
    print("=" * 80)
    
    try:
        from xtquant import xtdata
        xtdata.connect(port=58610)
    except Exception as e:
        print(f"❌ QMT连接失败: {e}")
        return
    
    end_date = '20260304'
    start_date = '20240101'
    forward_days_list = [1, 3, 5, 10, 20, 30]
    top_pcts = [5, 10, 20]  # 前5%、10%、20%高收益股票
    
    stock_codes = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"扫描 {len(stock_codes)} 只股票...")
    
    # 收集所有事件：{forward_day: [(turnover_5d_avg, return_pct), ...]}
    all_events = {n: [] for n in forward_days_list}
    
    for i, stock in enumerate(stock_codes):
        if (i + 1) % 500 == 0:
            print(f"  进度: {i+1}/{len(stock_codes)}, 已收集 {sum(len(v) for v in all_events.values()):,} 事件")
        
        try:
            result = xtdata.get_market_data_ex(
                field_list=['open', 'high', 'low', 'close', 'volume'],
                stock_list=[stock],
                period='1d',
                start_time=start_date,
                end_time=end_date,
                count=-1
            )
            # get_market_data_ex返回dict，需要取对应股票的DataFrame
            if result is None or stock not in result:
                continue
            df = result[stock]
            if df is None or len(df) < 35:
                continue
            
            detail = xtdata.get_instrument_detail(stock, False)
            if not detail:
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                continue
            
            df = df.copy()
            # 索引就是日期字符串（如'20240102'）
            df['date_str'] = df.index.astype(str)
            df['turnover_rate'] = df['volume'] * 100.0 / float_vol * 100.0
            df['turnover_5d_avg'] = df['turnover_rate'].rolling(window=5, min_periods=1).mean()
            
            # 重置索引以便遍历
            df = df.reset_index(drop=True)
            
            for row_idx in range(len(df) - max(forward_days_list)):
                event_close = float(df['close'].iloc[row_idx])
                turnover_5d_avg = df['turnover_5d_avg'].iloc[row_idx]
                
                if pd.isna(turnover_5d_avg) or turnover_5d_avg <= 0:
                    continue
                
                # 计算各持有期收益
                for n in forward_days_list:
                    future_idx = row_idx + n
                    future_close = float(df['close'].iloc[future_idx])
                    ret = (future_close / event_close - 1.0) * 100.0
                    all_events[n].append((turnover_5d_avg, ret))
        except Exception as e:
            continue
    
    total_collected = sum(len(v) for v in all_events.values())
    print(f"\n✅ 收集完成: 共 {total_collected:,} 事件")
    
    if total_collected == 0:
        print("❌ 无有效事件，请检查数据")
        return
    
    # 对每个持有期分析
    results = {}
    for n in forward_days_list:
        events = all_events[n]
        if not events:
            continue
        
        # 按收益排序
        events_sorted = sorted(events, key=lambda x: x[1], reverse=True)
        total = len(events_sorted)
        
        print(f"\n【{n}日持有期】总样本: {total:,}")
        print("-" * 60)
        
        results[n] = {}
        
        for top_pct in top_pcts:
            top_n = int(total * top_pct / 100)
            top_events = events_sorted[:top_n]
            
            # 统计换手率分布
            turnovers = [e[0] for e in top_events]
            avg_turnover = np.mean(turnovers)
            median_turnover = np.median(turnovers)
            
            # 分档统计
            bucket_counts = {}
            for low, high, label in get_turnover_buckets():
                count = sum(1 for t in turnovers if low <= t < high)
                pct = count / len(turnovers) * 100 if turnovers else 0
                bucket_counts[label] = {'count': count, 'pct': round(pct, 1)}
            
            results[n][f'top_{top_pct}%'] = {
                'avg_turnover': round(avg_turnover, 2),
                'median_turnover': round(median_turnover, 2),
                'avg_return': round(np.mean([e[1] for e in top_events]), 2),
                'buckets': bucket_counts
            }
            
            print(f"  前{top_pct}%高收益股 (共{top_n:,}只):")
            print(f"    平均换手率: {avg_turnover:.2f}%")
            print(f"    中位数换手率: {median_turnover:.2f}%")
            print(f"    平均收益: {np.mean([e[1] for e in top_events]):.2f}%")
            
            # 打印主要档位
            main_buckets = [(k, v) for k, v in bucket_counts.items() if v['pct'] > 5]
            main_buckets.sort(key=lambda x: x[1]['pct'], reverse=True)
            bucket_str = ', '.join([f'{k}:{v["pct"]}%' for k, v in main_buckets[:5]])
            print(f"    换手率分布: {bucket_str}")
    
    # 保存结果
    output_path = VALIDATION_DIR / "turnover_reverse_analysis.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_samples': {str(k): len(v) for k, v in all_events.items()},
            'results': results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存: {output_path}")
    
    return results


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
    print(f"5日均换手率分档: 3-5%, 5-10%, ..., 65-70%, >70%")
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
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == '--reverse':
            reverse_analysis()
        elif sys.argv[1] == '--extreme':
            extreme_analysis()
        else:
            main()
    else:
        main()