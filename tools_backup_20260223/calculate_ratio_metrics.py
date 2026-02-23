#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTO指令：资金指标无量纲化（Ratio化）处理
将原始资金流量转换为相对ratio，消除魔法数字依赖
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def calculate_stock_baseline(stock_code, lookback_days=20):
    """
    计算单票历史baseline（用于自标准化）
    从已有样本数据推算该票的typical flow水平
    """
    samples_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "samples"
    
    # 查找该票所有历史CSV
    pattern = f"{stock_code}_*.csv"
    files = list(samples_dir.glob(pattern))
    
    if not files:
        return None
    
    all_flows = []
    for f in files:
        df = pd.read_csv(f)
        if 'flow_5min' in df.columns:
            # 取该日所有非零5分钟流
            flows = df[df['flow_5min'] != 0]['flow_5min'].abs()
            all_flows.extend(flows.tolist())
    
    if not all_flows:
        return None
    
    return {
        'median_5min': np.median(all_flows),
        'p75_5min': np.percentile(all_flows, 75),
        'p90_5min': np.percentile(all_flows, 90),
        'max_5min': np.max(all_flows)
    }


def calculate_day_baseline(df):
    """
    计算当日baseline（用于日标准化）
    """
    if 'flow_5min' not in df.columns or df.empty:
        return None
    
    valid_flows = df[df['flow_5min'] != 0]['flow_5min'].abs()
    
    if len(valid_flows) == 0:
        return None
    
    return {
        'median_5min_day': valid_flows.median(),
        'mean_5min_day': valid_flows.mean(),
        'std_5min_day': valid_flows.std()
    }


def add_ratio_metrics(csv_file):
    """
    为单个CSV文件添加ratio指标
    """
    df = pd.read_csv(csv_file)
    
    if df.empty or 'flow_5min' not in df.columns:
        return None
    
    # 提取股票代码
    stock_code = Path(csv_file).stem.split('_')[0]
    
    # 1. 计算该票历史baseline
    stock_baseline = calculate_stock_baseline(stock_code)
    
    # 2. 计算当日baseline
    day_baseline = calculate_day_baseline(df)
    
    # 3. 添加ratio指标
    if stock_baseline and stock_baseline['median_5min'] > 0:
        df['flow_5min_ratio_stock'] = df['flow_5min'].abs() / stock_baseline['median_5min']
        df['flow_5min_ratio_stock_p75'] = df['flow_5min'].abs() / stock_baseline['p75_5min']
    else:
        df['flow_5min_ratio_stock'] = np.nan
        df['flow_5min_ratio_stock_p75'] = np.nan
    
    if day_baseline and day_baseline['median_5min_day'] > 0:
        df['flow_5min_ratio_day'] = df['flow_5min'].abs() / day_baseline['median_5min_day']
    else:
        df['flow_5min_ratio_day'] = np.nan
    
    # 4. 计算sustain_ratio (15min/5min)
    if 'flow_15min' in df.columns:
        df['sustain_ratio'] = np.where(
            df['flow_5min'].abs() > 0,
            df['flow_15min'].abs() / df['flow_5min'].abs(),
            np.nan
        )
    
    # 5. 计算价格效率指标 (每单位资金推动的价格变化)
    if 'price' in df.columns:
        df['price_change'] = df['price'].diff()
        df['flow_efficiency'] = np.where(
            df['flow_5min'].abs() > 0,
            df['price_change'] / (df['flow_5min'].abs() / 1e6),  # 每百万资金的价格变化
            np.nan
        )
    
    return df


def analyze_wangsu_comparison():
    """
    CTO指令：以网宿1.26 vs 2.13为典型，建立ratio直觉映射
    """
    samples_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "samples"
    
    print("="*80)
    print("CTO指令：网宿科技典型正反例Ratio分析")
    print("="*80)
    
    # 读取真起爆日
    wangsu_true = samples_dir / "300017_2026-01-26_true.csv"
    wangsu_trap = samples_dir / "300017_2026-02-13_trap.csv"
    
    if not wangsu_true.exists() or not wangsu_trap.exists():
        print("❌ 网宿数据文件缺失")
        return
    
    # 添加ratio指标
    df_true = add_ratio_metrics(wangsu_true)
    df_trap = add_ratio_metrics(wangsu_trap)
    
    # 提取关键时段（10:00-14:30，排除开盘和尾盘）
    df_true_focus = df_true[(df_true['time'] >= '10:00:00') & (df_true['time'] <= '14:30:00')]
    df_trap_focus = df_trap[(df_trap['time'] >= '10:00:00') & (df_trap['time'] <= '14:30:00')]
    
    print("\n【真起爆日 2026-01-26】关键指标分布")
    print("-"*60)
    print(f"样本数: {len(df_true_focus)}")
    if 'flow_5min_ratio_stock' in df_true_focus.columns:
        print(f"flow_5min_ratio_stock: 均值={df_true_focus['flow_5min_ratio_stock'].mean():.2f}, 中位数={df_true_focus['flow_5min_ratio_stock'].median():.2f}, 最大值={df_true_focus['flow_5min_ratio_stock'].max():.2f}")
    if 'flow_5min_ratio_day' in df_true_focus.columns:
        print(f"flow_5min_ratio_day: 均值={df_true_focus['flow_5min_ratio_day'].mean():.2f}, 中位数={df_true_focus['flow_5min_ratio_day'].median():.2f}, 最大值={df_true_focus['flow_5min_ratio_day'].max():.2f}")
    if 'sustain_ratio' in df_true_focus.columns:
        print(f"sustain_ratio: 均值={df_true_focus['sustain_ratio'].mean():.2f}, 中位数={df_true_focus['sustain_ratio'].median():.2f}")
    if 'flow_efficiency' in df_true_focus.columns:
        print(f"flow_efficiency: 均值={df_true_focus['flow_efficiency'].mean():.4f} (每百万资金价格变化)")
    
    print("\n【骗炮日 2026-02-13】关键指标分布")
    print("-"*60)
    print(f"样本数: {len(df_trap_focus)}")
    if 'flow_5min_ratio_stock' in df_trap_focus.columns:
        print(f"flow_5min_ratio_stock: 均值={df_trap_focus['flow_5min_ratio_stock'].mean():.2f}, 中位数={df_trap_focus['flow_5min_ratio_stock'].median():.2f}, 最大值={df_trap_focus['flow_5min_ratio_stock'].max():.2f}")
    if 'flow_5min_ratio_day' in df_trap_focus.columns:
        print(f"flow_5min_ratio_day: 均值={df_trap_focus['flow_5min_ratio_day'].mean():.2f}, 中位数={df_trap_focus['flow_5min_ratio_day'].median():.2f}, 最大值={df_trap_focus['flow_5min_ratio_day'].max():.2f}")
    if 'sustain_ratio' in df_trap_focus.columns:
        print(f"sustain_ratio: 均值={df_trap_focus['sustain_ratio'].mean():.2f}, 中位数={df_trap_focus['sustain_ratio'].median():.2f}")
    if 'flow_efficiency' in df_trap_focus.columns:
        print(f"flow_efficiency: 均值={df_trap_focus['flow_efficiency'].mean():.4f} (每百万资金价格变化)")
    
    print("\n【对比分析】")
    print("-"*60)
    
    # 计算ratio差异
    if 'flow_5min_ratio_stock' in df_true_focus.columns and 'flow_5min_ratio_stock' in df_trap_focus.columns:
        true_mean = df_true_focus['flow_5min_ratio_stock'].mean()
        trap_mean = df_trap_focus['flow_5min_ratio_stock'].mean()
        print(f"flow_5min_ratio_stock: 真起爆({true_mean:.2f}) vs 骗炮({trap_mean:.2f}), 差异={true_mean-trap_mean:.2f}")
    
    if 'sustain_ratio' in df_true_focus.columns and 'sustain_ratio' in df_trap_focus.columns:
        true_sustain = df_true_focus['sustain_ratio'].mean()
        trap_sustain = df_trap_focus['sustain_ratio'].mean()
        print(f"sustain_ratio: 真起爆({true_sustain:.2f}) vs 骗炮({trap_sustain:.2f}), 差异={true_sustain-trap_sustain:.2f}")
    
    # 保存ratio化后的文件
    output_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "samples_ratio"
    output_dir.mkdir(exist_ok=True)
    
    df_true.to_csv(output_dir / "300017_2026-01-26_true_ratio.csv", index=False)
    df_trap.to_csv(output_dir / "300017_2026-02-13_trap_ratio.csv", index=False)
    
    print(f"\n✅ Ratio化文件已保存: {output_dir}")
    print("="*80)


def analyze_all_samples():
    """
    对所有样本进行ratio分析
    """
    samples_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "samples"
    output_dir = PROJECT_ROOT / "data" / "wanzhu_data" / "samples_ratio"
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "="*80)
    print("批量处理所有样本的Ratio指标")
    print("="*80)
    
    csv_files = list(samples_dir.glob("*.csv"))
    csv_files = [f for f in csv_files if not f.name.endswith("_summary.csv")]
    
    summary_data = []
    
    for csv_file in csv_files:
        print(f"\n处理: {csv_file.name}")
        df = add_ratio_metrics(csv_file)
        
        if df is None:
            continue
        
        # 保存ratio化文件
        output_file = output_dir / f"{csv_file.stem}_ratio.csv"
        df.to_csv(output_file, index=False)
        
        # 提取关键时段统计
        df_focus = df[(df['time'] >= '10:00:00') & (df['time'] <= '14:30:00')]
        
        if len(df_focus) == 0:
            continue
        
        # 提取股票代码和日期
        parts = csv_file.stem.split('_')
        stock_code = parts[0]
        date = parts[1] if len(parts) > 1 else "unknown"
        label = parts[2] if len(parts) > 2 else "unknown"
        
        # 汇总统计
        summary = {
            'code': stock_code,
            'date': date,
            'label': label,
            'max_ratio_stock': df_focus['flow_5min_ratio_stock'].max() if 'flow_5min_ratio_stock' in df_focus.columns else np.nan,
            'max_ratio_day': df_focus['flow_5min_ratio_day'].max() if 'flow_5min_ratio_day' in df_focus.columns else np.nan,
            'max_sustain_ratio': df_focus['sustain_ratio'].max() if 'sustain_ratio' in df_focus.columns else np.nan,
            'mean_sustain_ratio': df_focus['sustain_ratio'].mean() if 'sustain_ratio' in df_focus.columns else np.nan,
        }
        
        summary_data.append(summary)
        
        print(f"  max_ratio_stock: {summary['max_ratio_stock']:.2f}")
        print(f"  max_ratio_day: {summary['max_ratio_day']:.2f}")
        print(f"  mean_sustain_ratio: {summary['mean_sustain_ratio']:.2f}")
    
    # 保存汇总
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(output_dir / "ratio_summary.csv", index=False)
        
        print("\n" + "="*80)
        print("Ratio汇总统计")
        print("="*80)
        
        # 按标签分组统计
        if 'label' in summary_df.columns:
            for label in summary_df['label'].unique():
                if pd.isna(label):
                    continue
                subset = summary_df[summary_df['label'] == label]
                print(f"\n【{label}】样本数: {len(subset)}")
                print(f"  max_ratio_stock: 均值={subset['max_ratio_stock'].mean():.2f}, 中位数={subset['max_ratio_stock'].median():.2f}")
                print(f"  max_ratio_day: 均值={subset['max_ratio_day'].mean():.2f}, 中位数={subset['max_ratio_day'].median():.2f}")
                print(f"  mean_sustain_ratio: 均值={subset['mean_sustain_ratio'].mean():.2f}, 中位数={subset['mean_sustain_ratio'].median():.2f}")
    
    print(f"\n✅ 所有Ratio化文件已保存: {output_dir}")
    print("="*80)


if __name__ == "__main__":
    # 先分析网宿典型正反例
    analyze_wangsu_comparison()
    
    # 再批量处理所有样本
    analyze_all_samples()
