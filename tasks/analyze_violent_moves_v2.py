#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股暴力主升段反推研究 V2.0 - 科学版
方法：先筛选爆涨样本（任意N日20-300%），再反推时长与换手规律
不预设时长，让数据说话
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import json

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)


def find_all_violent_moves(df, min_days=3, max_days=30, min_return=20, max_return=300, max_dd_pct=25):
    """
    暴力扫描：找出所有【任意N日涨幅20-300%】的样本
    
    优化版本：使用向量化计算，避免嵌套循环
    """
    moves = []
    used_ranges = set()  # 避免重叠区间
    
    closes = df['close'].values
    n = len(closes)
    
    # 预计算所有可能的收益矩阵（向量化）
    # 使用累积收益计算，避免重复
    
    for start_idx in range(n - min_days):
        start_close = closes[start_idx]
        
        # 批量计算所有end_idx的收益
        for days in range(min_days, min(max_days + 1, n - start_idx)):
            end_idx = start_idx + days
            end_close = closes[end_idx]
            total_return = (end_close / start_close - 1.0) * 100.0
            
            # 快速筛选：涨幅不在范围内
            if not (min_return <= total_return <= max_return):
                continue
            
            # 检查是否与已有区间重叠
            range_key = (start_idx, end_idx)
            overlap = False
            for (s, e) in used_ranges:
                if not (end_idx < s or start_idx > e):  # 重叠
                    overlap = True
                    break
            if overlap:
                continue
            
            # 计算期间最大回撤（简化版：只检查是否有过大回撤）
            segment_closes = closes[start_idx:end_idx+1]
            cummax = np.maximum.accumulate(segment_closes)
            drawdowns = (segment_closes - cummax) / cummax * 100.0
            max_dd = abs(drawdowns.min())
            
            if max_dd > max_dd_pct:
                continue
            
            # 找到有效样本
            moves.append({
                'start_idx': int(start_idx),
                'end_idx': int(end_idx),
                'days': int(days),
                'total_return': float(total_return),
                'max_drawdown': float(max_dd),
                'start_date': df['date_str'].iloc[start_idx],
                'end_date': df['date_str'].iloc[end_idx]
            })
            used_ranges.add(range_key)
    
    return moves


def get_return_buckets():
    """涨幅分档（不限定天数）"""
    return [
        (20, 30, "20-30%"),
        (30, 40, "30-40%"),
        (40, 50, "40-50%"),
        (50, 70, "50-70%"),
        (70, 100, "70-100%"),
        (100, 150, "100-150%"),
        (150, 200, "150-200%"),
        (200, 300, "200-300%"),
        (300, 999, ">=300%"),
    ]


def get_days_buckets():
    """天数分档"""
    return [
        (3, 5, "3-5天"),
        (5, 7, "5-7天"),
        (7, 10, "7-10天"),
        (10, 15, "10-15天"),
        (15, 20, "15-20天"),
        (20, 25, "20-25天"),
        (25, 30, "25-30天"),
    ]


def analyze_ignition_features_v3(df, move, float_vol):
    """
    分析起爆日特征（简化版）
    """
    start_idx = move['start_idx']
    end_idx = move['end_idx']
    
    ignition = {}
    
    # 起爆日换手率
    ignition['ignition_turnover'] = df['volume'].iloc[start_idx] * 100.0 / float_vol * 100.0
    
    # 起爆日涨幅
    if start_idx > 0:
        prev_close = float(df['close'].iloc[start_idx - 1])
        ignition['ignition_rise_pct'] = (float(df['close'].iloc[start_idx]) - prev_close) / prev_close * 100.0
    else:
        ignition['ignition_rise_pct'] = None
    
    # 起爆前5/10/20日换手率
    for n in [5, 10, 20]:
        if start_idx >= n:
            vol_avg = df['volume'].iloc[start_idx-n:start_idx].mean()
            ignition[f'turnover_t{n}'] = vol_avg * 100.0 / float_vol * 100.0
        else:
            ignition[f'turnover_t{n}'] = None
    
    # 主升段中换手率
    segment = df.iloc[start_idx:end_idx+1]
    turnovers = segment['volume'] * 100.0 / float_vol * 100.0
    ignition['uptrend_median_turnover'] = float(turnovers.median())
    
    # 主升段中涨停板数量
    if start_idx > 0 and len(segment) > 1:
        segment_copy = segment.copy()
        segment_copy['prev_close'] = df['close'].iloc[start_idx-1:end_idx].values
        segment_copy['pct_change'] = (segment_copy['close'] - segment_copy['prev_close']) / segment_copy['prev_close'] * 100.0
        limit_up_10 = ((segment_copy['pct_change'] > 9.5) & (segment_copy['pct_change'] < 10.5)).sum()
        limit_up_20 = ((segment_copy['pct_change'] > 19) & (segment_copy['pct_change'] < 21)).sum()
        ignition['limit_up_count'] = int(limit_up_10 + limit_up_20)
    else:
        ignition['limit_up_count'] = 0
    
    return ignition


def main():
    print("=" * 100, flush=True)
    print("A股暴力主升段反推研究 V2.0 - 科学版（不预设天数）", flush=True)
    print("=" * 100, flush=True)
    
    # 参数配置
    try:
        from logic.utils.calendar_utils import get_nth_previous_trading_day
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = get_nth_previous_trading_day(end_date, 250 * 3)  # 3年
    except:
        start_date = '20230301'
        end_date = '20260304'
    
    print(f"时间窗口: {start_date} ~ {end_date} (约3年)", flush=True)
    print(f"筛选条件: 任意3-30日涨幅20-300%, 回撤<25%", flush=True)
    print(f"方法: 先筛选样本，再反推规律", flush=True)
    print("-" * 100, flush=True)
    
    # 连接QMT
    try:
        from xtquant import xtdata
        xtdata.connect(port=58610)
        print("✅ QMT连接成功", flush=True)
    except Exception as e:
        print(f"❌ QMT连接失败: {e}", flush=True)
        return
    
    # 获取股票池
    stock_codes = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"股票池: {len(stock_codes)} 只\n", flush=True)
    
    # 收集所有暴力拉升样本
    all_moves = []
    
    for i, stock in enumerate(stock_codes, 1):
        if i % 100 == 0:
            print(f"  进度: {i}/{len(stock_codes)}, 已收集 {len(all_moves):,} 个样本", flush=True)
        
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
            if df is None or len(df) < 260:
                continue
            
            # 获取流通股本
            detail = xtdata.get_instrument_detail(stock, False)
            if not detail:
                continue
            
            float_vol = float(detail.get('FloatVolume', 0) if hasattr(detail, 'get') else getattr(detail, 'FloatVolume', 0))
            if float_vol <= 0:
                continue
            
            df = df.copy()
            df['date_str'] = df.index.astype(str)
            df = df.reset_index(drop=True)
            
            # 找出所有暴力拉升（不限定天数）
            moves = find_all_violent_moves(df, min_days=3, max_days=30, min_return=20, max_return=300)
            
            for move in moves:
                # 分析起爆特征
                ignition = analyze_ignition_features_v3(df, move, float_vol)
                
                # 合并数据
                full_record = {
                    'stock_code': stock,
                    **move,
                    **ignition
                }
                
                all_moves.append(full_record)
        
        except Exception:
            continue
    
    print(f"\n✅ 识别完成: {len(all_moves):,} 个暴力拉升样本", flush=True)
    
    if not all_moves:
        print("❌ 无样本")
        return
    
    # 转DataFrame
    df_moves = pd.DataFrame(all_moves)
    
    # 添加分桶标签
    def get_return_bucket(ret):
        for low, high, label in get_return_buckets():
            if low <= ret < high:
                return label
        return None
    
    def get_days_bucket(days):
        for low, high, label in get_days_buckets():
            if low <= days < high:
                return label
        return None
    
    df_moves['return_bucket'] = df_moves['total_return'].apply(get_return_bucket)
    df_moves['days_bucket'] = df_moves['days'].apply(get_days_bucket)
    
    # 输出明细CSV
    csv_path = VALIDATION_DIR / "violent_moves_v2.csv"
    df_moves.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"✅ 明细CSV: {csv_path}")
    
    # === 反推分析 ===
    summary = {
        'generated_at': datetime.now().isoformat(),
        'date_range': f"{start_date}~{end_date}",
        'total_samples': len(all_moves),
        'by_return': {},  # 按涨幅分析
        'by_days': {},    # 按天数分析
        'cross_analysis': {}  # 交叉分析
    }
    
    # 1. 按涨幅分组统计
    print("\n" + "=" * 100)
    print("反推分析1：不同涨幅档位的天数分布")
    print("=" * 100)
    
    for low, high, label in get_return_buckets():
        dfr = df_moves[(df_moves['total_return'] >= low) & (df_moves['total_return'] < high)]
        
        if len(dfr) == 0:
            continue
        
        stats = {
            'count': len(dfr),
            'pct': len(dfr) / len(df_moves) * 100.0,
            'days_avg': float(dfr['days'].mean()),
            'days_median': float(dfr['days'].median()),
            'days_mode': int(dfr['days'].mode()[0]) if len(dfr['days'].mode()) > 0 else None,
            'days_distribution': dfr['days_bucket'].value_counts().to_dict(),
            'ignition_turnover_median': float(dfr['ignition_turnover'].median()),
            'pre_turnover_t20_median': float(dfr['turnover_t20'].median()) if 'turnover_t20' in dfr.columns and dfr['turnover_t20'].notna().any() else None,
            'uptrend_turnover_median': float(dfr['uptrend_median_turnover'].median()),
        }
        
        summary['by_return'][label] = stats
        
        print(f"\n【{label}】样本: {stats['count']:,} ({stats['pct']:.2f}%)")
        print(f"  天数: 均值{stats['days_avg']:.1f}, 中位{stats['days_median']:.1f}, 众数{stats['days_mode']}")
        print(f"  起爆日换手中位: {stats['ignition_turnover_median']:.2f}%")
        print(f"  天数分布TOP3:")
        top3 = sorted(stats['days_distribution'].items(), key=lambda x: x[1], reverse=True)[:3]
        for k, v in top3:
            print(f"    {k}: {v}个 ({v/stats['count']*100:.1f}%)")
    
    # 2. 按天数分组统计
    print("\n" + "=" * 100)
    print("反推分析2：不同天数档位的涨幅分布")
    print("=" * 100)
    
    for low, high, label in get_days_buckets():
        dfd = df_moves[(df_moves['days'] >= low) & (df_moves['days'] < high)]
        
        if len(dfd) == 0:
            continue
        
        stats = {
            'count': len(dfd),
            'pct': len(dfd) / len(df_moves) * 100.0,
            'return_avg': float(dfd['total_return'].mean()),
            'return_median': float(dfd['total_return'].median()),
            'return_p75': float(dfd['total_return'].quantile(0.75)),
            'return_p90': float(dfd['total_return'].quantile(0.90)),
            'return_distribution': dfd['return_bucket'].value_counts().to_dict(),
            'ignition_turnover_median': float(dfd['ignition_turnover'].median()),
            'limit_up_count_avg': float(dfd['limit_up_count'].mean()) if 'limit_up_count' in dfd.columns else None,
        }
        
        summary['by_days'][label] = stats
        
        print(f"\n【{label}】样本: {stats['count']:,} ({stats['pct']:.2f}%)")
        print(f"  涨幅: 均值{stats['return_avg']:.1f}%, 中位{stats['return_median']:.1f}%, P75={stats['return_p75']:.1f}%, P90={stats['return_p90']:.1f}%")
        print(f"  起爆日换手中位: {stats['ignition_turnover_median']:.2f}%")
        print(f"  涨幅分布TOP3:")
        top3 = sorted(stats['return_distribution'].items(), key=lambda x: x[1], reverse=True)[:3]
        for k, v in top3:
            print(f"    {k}: {v}个 ({v/stats['count']*100:.1f}%)")
    
    # 3. 交叉分析（热力图数据）
    cross_matrix = df_moves.groupby(['return_bucket', 'days_bucket']).size().unstack(fill_value=0)
    summary['cross_analysis'] = {
        'matrix': cross_matrix.to_dict(),
        'total': len(df_moves)
    }
    
    # 输出JSON
    json_path = VALIDATION_DIR / "violent_moves_summary_v2.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 摘要JSON: {json_path}")
    
    print("\n" + "=" * 100)
    print("数据已保存，可用于制图和config调整")
    print("=" * 100)


if __name__ == "__main__":
    main()
