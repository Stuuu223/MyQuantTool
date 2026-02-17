#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
参数热力图生成工具
用于分析不同参数组合在单一股票上的表现
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
from itertools import product
from tools.per_day_tick_runner import PerDayTickRunner
from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy


def generate_param_grid():
    """
    生成参数网格
    """
    volatility_thresholds = [0.01, 0.02, 0.03, 0.04, 0.05]
    volume_surge_values = [1.1, 1.2, 1.3, 1.4, 1.5]
    breakout_strength_values = [0.001, 0.003, 0.005, 0.008, 0.01]
    
    param_grid = []
    for vol, vol_surge, breakout in product(volatility_thresholds, volume_surge_values, breakout_strength_values):
        param_grid.append({
            'volatility_threshold': vol,
            'volume_surge': vol_surge,
            'breakout_strength': breakout,
            'min_history_points': 30
        })
    
    return param_grid


def run_param_heatmap_analysis(stock_code: str, start_date: str, end_date: str, sample_size: int = 5):
    """
    运行参数热力图分析
    
    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        sample_size: 采样天数
    """
    print(f"📊 参数热力图分析: {stock_code}")
    print(f"📅 日期范围: {start_date} ~ {end_date}")
    print(f"📊 采样天数: {sample_size}")
    print("=" * 80)
    
    # 获取交易日列表（模拟）
    # 实际使用时应从QMT获取真实的交易日历
    import pandas as pd
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    trading_days = []
    for date in date_range:
        if date.weekday() < 5:  # 周一到周五
            trading_days.append(date.strftime('%Y%m%d'))
    
    # 采样交易日
    sample_days = trading_days[:sample_size]
    print(f"🗓️  采样交易日: {sample_days}")
    
    # 生成参数网格
    param_grid = generate_param_grid()
    print(f"⚙️  参数组合总数: {len(param_grid)}")
    
    # 只取前25个参数组合进行演示（避免计算量过大）
    param_grid = param_grid[:25]
    print(f"⚙️  实际测试参数组合: {len(param_grid)} (前25个)")
    
    results = []
    
    print("\n🏃 开始参数网格搜索...")
    for i, params in enumerate(param_grid):
        print(f"\r   进度: {i+1}/{len(param_grid)}", end="", flush=True)
        
        total_signals = 0
        total_return_5min = 0
        total_return_count_5min = 0
        
        for trade_date in sample_days:
            try:
                strategy = HalfwayTickStrategy(params)
                runner = PerDayTickRunner(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    strategy=strategy
                )
                
                signals = runner.run()
                stats = runner.get_statistics()
                
                total_signals += stats['total_signals']
                
                # 累加收益
                if stats['total_returns']['5min'] > 0:
                    total_return_5min += stats['avg_return']['5min'] * stats['total_returns']['5min']
                    total_return_count_5min += stats['total_returns']['5min']
                    
            except Exception as e:
                print(f"\n   ❌ 日期{trade_date}处理失败: {e}")
                continue
        
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
    
    print(f"\n✅ 参数网格搜索完成")
    
    # 转换为DataFrame
    df_results = pd.DataFrame(results)
    
    # 保存详细结果
    output_file = f"param_heatmap_results_{stock_code.replace('.', '_')}_{start_date}_{end_date}.csv"
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"💾 详细结果已保存: {output_file}")
    
    # 创建热力图所需的数据
    # 使用volatility_threshold和volume_surge作为x,y轴，以breakout_strength为切片
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # 为每个breakout_strength值创建子图
    unique_breakout = sorted(df_results['breakout_strength'].unique())[:3]  # 取前3个值
    
    for idx, breakout_val in enumerate(unique_breakout):
        subset = df_results[df_results['breakout_strength'] == breakout_val]
        
        if len(subset) == 0:
            continue
            
        # 创建透视表
        pivot = subset.pivot_table(
            values='avg_return_5min',
            index='volume_surge',
            columns='volatility_threshold',
            fill_value=0
        )
        
        sns.heatmap(
            pivot,
            annot=True,
            fmt='.4f',
            cmap='RdYlGn',
            center=0,
            ax=axes[idx],
            cbar_kws={'label': '5分钟平均收益'}
        )
        axes[idx].set_title(f'突破强度={breakout_val}\n5分钟平均收益热力图')
        axes[idx].set_xlabel('波动率阈值')
        axes[idx].set_ylabel('量能放大倍数')
    
    # 隐藏多余的子图
    for idx in range(len(unique_breakout), 3):
        axes[idx].set_visible(False)
    
    plt.tight_layout()
    heatmap_file = f"param_heatmap_{stock_code.replace('.', '_')}_{start_date}_{end_date}.png"
    plt.savefig(heatmap_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"🖼️  热力图已保存: {heatmap_file}")
    
    # 打印统计信息
    print(f"\n📈 统计信息:")
    print(f"   总测试组合: {len(df_results)}")
    print(f"   信号总数范围: {df_results['total_signals'].min()} ~ {df_results['total_signals'].max()}")
    print(f"   平均每日信号范围: {df_results['avg_signals_per_day'].min():.3f} ~ {df_results['avg_signals_per_day'].max():.3f}")
    print(f"   5分钟平均收益范围: {df_results['avg_return_5min'].min():.4f} ~ {df_results['avg_return_5min'].max():.4f}")
    
    # 找出表现最好的参数组合
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
    
    return df_results


if __name__ == "__main__":
    print("🎯 参数热力图生成工具")
    print("=" * 80)
    
    # 使用300997.SZ进行测试
    results = run_param_heatmap_analysis(
        stock_code="300997.SZ",
        start_date="2025-11-01",
        end_date="2025-12-01",
        sample_size=3  # 使用3个交易日进行演示
    )
    
    print(f"\n✅ 参数热力图分析完成")
    print("=" * 80)
