#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
参数热力图分析作业
生成不同参数组合的回测表现热力图
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
import json
import argparse


def generate_param_grid():
    """
    生成参数网格
    """
    volatility_thresholds = [0.01, 0.02, 0.03, 0.04, 0.05]
    volume_surge_values = [1.1, 1.2, 1.3, 1.5, 1.8]
    breakout_strength_values = [0.001, 0.003, 0.005, 0.008, 0.01]
    
    param_grid = []
    for vol in volatility_thresholds:
        for vol_surge in volume_surge_values:
            for breakout in breakout_strength_values:
                param_grid.append({
                    'volatility_threshold': vol,
                    'volume_surge': vol_surge,
                    'breakout_strength': breakout,
                    'min_history_points': 30
                })
    
    return param_grid


def run_param_heatmap_analysis(
    stock_code: str, 
    start_date: str, 
    end_date: str,
    param_grid: List[Dict],
    sample_size: int = 5
) -> List[Dict]:
    """
    运行参数热力图分析
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        param_grid: 参数网格
        sample_size: 采样天数
        
    Returns:
        List[Dict]: 分析结果
    """
    print(f"📊 参数热力图分析: {stock_code}")
    print(f"📅 日期范围: {start_date} ~ {end_date}")
    print(f"⚙️  参数组合数: {len(param_grid)}")
    print(f"📊 采样天数: {sample_size}")
    print("=" * 80)
    
    # 获取交易日列表（模拟）
    import pandas as pd
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    trading_days = []
    for date in date_range:
        if date.weekday() < 5:  # 周一到周五
            trading_days.append(date.strftime('%Y-%m-%d'))
    
    # 采样交易日
    sample_days = trading_days[:sample_size]
    print(f"🗓️  采样交易日: {sample_days}")
    
    results = []
    
    print("\n🏃 开始参数网格搜索...")
    for i, params in enumerate(param_grid):
        print(f"\r   进度: {i+1}/{len(param_grid)}", end="", flush=True)
        
        try:
            # 这里我们模拟使用策略进行回测
            # 在实际应用中，这应该连接到真实的回测引擎
            from tools.per_day_tick_runner import PerDayTickRunner
            from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
            
            total_signals = 0
            total_return_5min = 0
            total_return_count_5min = 0
            
            for trade_date in sample_days:
                try:
                    strategy = HalfwayTickStrategy(params)
                    runner = PerDayTickRunner(
                        stock_code=stock_code,
                        trade_date=trade_date.replace('-', ''),  # 转换为YYYYMMDD格式
                        strategy=strategy
                    )
                    
                    signals = runner.run()
                    stats = runner.get_statistics()
                    
                    total_signals += stats['total_signals']
                    
                    # 累加收益
                    if stats['total_returns']['5min'] > 0:
                        total_return_5min += stats['avg_return']['5min'] * stats['total_returns']['5min']
                        total_return_count_5min += stats['total_returns']['5min']
                        
                except Exception:
                    continue  # 跳过有问题的日期
            
            # 计算平均值
            avg_signals = total_signals / len(sample_days) if sample_days else 0
            avg_return_5min = total_return_5min / total_return_count_5min if total_return_count_5min > 0 else 0
            
            result = {
                'volatility_threshold': params['volatility_threshold'],
                'volume_surge': params['volume_surge'],
                'breakout_strength': params['breakout_strength'],
                'total_signals': total_signals,
                'avg_signals_per_day': avg_signals,
                'avg_return_5min': avg_return_5min,
                'total_return_count': total_return_count_5min
            }
            results.append(result)
            
        except Exception as e:
            print(f"\n   ❌ 参数组合{i+1}处理失败: {e}")
            continue
    
    print(f"\n✅ 参数网格搜索完成")
    
    return results


def create_heatmap_visualization(results_df: pd.DataFrame, output_file: str):
    """
    创建热力图可视化
    
    Args:
        results_df: 结果DataFrame
        output_file: 输出文件路径
    """
    if len(results_df) == 0:
        print("⚠️  没有数据可生成热力图")
        return
    
    # 创建热力图
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. 信号数量热力图 (volatility_threshold vs volume_surge)
    pivot_signals = results_df.pivot_table(
        values='avg_signals_per_day',
        index='volume_surge',
        columns='volatility_threshold',
        aggfunc='mean',
        fill_value=0
    )
    
    sns.heatmap(
        pivot_signals,
        annot=True,
        fmt='.3f',
        cmap='YlOrRd',
        ax=axes[0, 0],
        cbar_kws={'label': '平均每日信号数'}
    )
    axes[0, 0].set_title('平均每日信号数热力图')
    axes[0, 0].set_xlabel('波动率阈值')
    axes[0, 0].set_ylabel('量能放大倍数')
    
    # 2. 收益率热力图 (volatility_threshold vs volume_surge)
    pivot_returns = results_df.pivot_table(
        values='avg_return_5min',
        index='volume_surge',
        columns='volatility_threshold',
        aggfunc='mean',
        fill_value=0
    )
    
    sns.heatmap(
        pivot_returns,
        annot=True,
        fmt='.4f',
        cmap='RdYlGn',
        center=0,
        ax=axes[0, 1],
        cbar_kws={'label': '5分钟平均收益'}
    )
    axes[0, 1].set_title('5分钟平均收益率热力图')
    axes[0, 1].set_xlabel('波动率阈值')
    axes[0, 1].set_ylabel('量能放大倍数')
    
    # 3. 按突破强度分组的收益热力图
    # 创建一个按breakout_strength分组的图
    unique_breakout = sorted(results_df['breakout_strength'].unique())
    if len(unique_breakout) > 0:
        breakout_val = unique_breakout[min(1, len(unique_breakout)-1)]  # 取第二个值
        subset = results_df[results_df['breakout_strength'] == breakout_val]
        
        if len(subset) > 0:
            pivot_breakout = subset.pivot_table(
                values='avg_return_5min',
                index='volume_surge',
                columns='volatility_threshold',
                aggfunc='mean',
                fill_value=0
            )
            
            sns.heatmap(
                pivot_breakout,
                annot=True,
                fmt='.4f',
                cmap='RdYlGn',
                center=0,
                ax=axes[1, 0],
                cbar_kws={'label': '5分钟平均收益'}
            )
            axes[1, 0].set_title(f'突破强度={breakout_val}时的收益率热力图')
            axes[1, 0].set_xlabel('波动率阈值')
            axes[1, 0].set_ylabel('量能放大倍数')
    
    # 4. 参数重要性分析
    # 计算各参数与收益率的相关性
    if len(results_df) > 1:
        param_cols = ['volatility_threshold', 'volume_surge', 'breakout_strength']
        correlations = {}
        for col in param_cols:
            corr = results_df[col].corr(results_df['avg_return_5min'])
            correlations[col] = corr
        
        # 绘制相关性柱状图
        axes[1, 1].bar(correlations.keys(), correlations.values())
        axes[1, 1].set_title('参数与收益率相关性')
        axes[1, 1].set_ylabel('相关系数')
        axes[1, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"🖼️  热力图已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='参数热力图分析作业')
    parser.add_argument('--stock', type=str, default='300997.SZ', help='股票代码')
    parser.add_argument('--start-date', type=str, default='2025-11-01', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2025-12-01', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--sample-size', type=int, default=3, help='采样天数')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    
    args = parser.parse_args()
    
    # 生成参数网格
    param_grid = generate_param_grid()
    print(f"⚙️  生成参数网格: {len(param_grid)} 个组合")
    
    # 限制参数网格大小以避免运行时间过长
    param_grid = param_grid[:25]  # 只测试前25个组合
    print(f"⚙️  实际测试参数组合: {len(param_grid)} 个")
    
    # 运行分析
    results = run_param_heatmap_analysis(
        stock_code=args.stock,
        start_date=args.start_date,
        end_date=args.end_date,
        param_grid=param_grid,
        sample_size=args.sample_size
    )
    
    if not results:
        print("❌ 没有获得任何结果")
        return
    
    # 转换为DataFrame
    df_results = pd.DataFrame(results)
    
    # 保存详细结果
    if args.output:
        output_path = Path(args.output)
        results_path = output_path.parent / f"{output_path.stem}_results.csv"
        df_results.to_csv(results_path, index=False, encoding='utf-8-sig')
        print(f"💾 详细结果已保存: {results_path}")
        
        # 创建热力图
        heatmap_path = output_path.parent / f"{output_path.stem}_heatmap.png"
        create_heatmap_visualization(df_results, str(heatmap_path))
    
    # 打印统计信息
    print(f"\n📈 统计信息:")
    print(f"   总测试组合: {len(df_results)}")
    print(f"   信号总数范围: {df_results['total_signals'].min()} ~ {df_results['total_signals'].max()}")
    print(f"   平均每日信号范围: {df_results['avg_signals_per_day'].min():.3f} ~ {df_results['avg_signals_per_day'].max():.3f}")
    print(f"   5分钟平均收益范围: {df_results['avg_return_5min'].min():.4f} ~ {df_results['avg_return_5min'].max():.4f}")
    
    # 找出表现最好的参数组合
    if len(df_results) > 0:
        best_by_signals = df_results.loc[df_results['total_signals'].idxmax()]
        best_by_return = df_results.loc[df_results['avg_return_5min'].idxmax()]
        
        print(f"\n🏆 表现最佳参数组合:")
        print(f"   信号最多: vol={best_by_signals['volatility_threshold']}, "
              f"vol_surge={best_by_signals['volume_surge']}, "
              f"breakout={best_by_signals['breakout_strength']}, "
              f"信号数={best_by_signals['total_signals']}")
        print(f"   收益最好: vol={best_by_return['volatility_threshold']}, "
              f"vol_surge={best_by_return['volume_surge']}, "
              f"breakout={best_by_return['breakout_strength']}, "
              f"收益={best_by_return['avg_return_5min']:.4f}")
    
    print(f"\n✅ 参数热力图分析完成")


if __name__ == "__main__":
    main()
