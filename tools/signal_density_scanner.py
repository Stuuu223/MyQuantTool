#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号密度扫描工具
用于在全市场范围内快速统计Halfway信号数量
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from tools.per_day_tick_runner import PerDayTickRunner
from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy


def load_hot_stocks():
    """
    加载热门股票列表
    """
    # 首先尝试从配置文件加载
    config_path = Path(__file__).parent.parent / 'config' / 'hot_stocks_codes.json'
    if config_path.exists():
        import json
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 如果配置文件格式是包含stocks数组的复杂结构
                if 'stocks' in data:
                    stocks = [item['code'] for item in data['stocks'] if 'code' in item]
                    return stocks
                # 如果是简单的{'hot_stocks': [...]}结构
                elif 'hot_stocks' in data:
                    return data['hot_stocks']
        except Exception as e:
            print(f"⚠️  读取配置文件时出错: {e}")
            pass
    
    # 如果没有配置文件或读取失败，返回一些示例股票
    print("⚠️  配置文件不存在或格式不正确，使用默认股票列表")
    return ['300997.SZ', '300986.SZ', '603697.SH']


def scan_signal_density(stocks, dates, params_list):
    """
    扫描信号密度
    
    Args:
        stocks: 股票列表
        dates: 日期列表
        params_list: 参数组合列表
    
    Returns:
        List[Dict]: 扫描结果
    """
    print(f"📊 信号密度扫描")
    print(f"📈 股票数量: {len(stocks)}")
    print(f"📅 日期数量: {len(dates)}")
    print(f"⚙️  参数组合: {len(params_list)}")
    print("=" * 80)
    
    results = []
    
    for i, stock in enumerate(stocks):
        print(f"\n📈 [{i+1}/{len(stocks)}] 扫描 {stock}")
        
        for date in dates:
            print(f"  📅 {date} ", end="", flush=True)
            
            for param_idx, params in enumerate(params_list):
                try:
                    strategy = HalfwayTickStrategy(params)
                    runner = PerDayTickRunner(
                        stock_code=stock,
                        trade_date=date,
                        strategy=strategy
                    )
                    
                    # 运行策略获取信号
                    signals = runner.run()
                    
                    # 现在tick_count已经通过run()方法设置
                    tick_count = runner.tick_count
                    
                    result = {
                        'stock_code': stock,
                        'trade_date': date,
                        'param_id': param_idx,
                        'param_desc': f"vol_{params['volatility_threshold']}_vol_surge_{params['volume_surge']}_breakout_{params['breakout_strength']}",
                        'total_signals': len(signals),
                        'tick_count': tick_count,
                        'error': None  # 确保所有结果都有error字段
                    }
                    results.append(result)
                    
                    # 根据信号数量显示状态
                    if len(signals) > 10:
                        print("🔥", end="", flush=True)  # 高信号密度
                    elif len(signals) > 0:
                        print("✅", end="", flush=True)  # 有信号
                    elif tick_count == 0:
                        print("❌", end="", flush=True)  # 无数据
                    else:
                        print("₀", end="", flush=True)  # 无信号但有数据
                        
                except Exception as e:
                    print("❌", end="", flush=True)
                    result = {
                        'stock_code': stock,
                        'trade_date': date,
                        'param_id': param_idx,
                        'param_desc': f"vol_{params['volatility_threshold']}_vol_surge_{params['volume_surge']}_breakout_{params['breakout_strength']}",
                        'total_signals': 0,
                        'tick_count': 0,
                        'error': str(e)
                    }
                    results.append(result)
    
        print()  # 换行
    
    return results


def analyze_scan_results(results):
    """
    分析扫描结果
    
    Args:
        results: 扫描结果列表
    """
    print(f"\n🔍 扫描结果分析")
    print("=" * 80)
    
    # 如果没有结果，返回空DataFrame
    if not results:
        print("⚠️  没有扫描结果，创建空DataFrame")
        df = pd.DataFrame(columns=['stock_code', 'trade_date', 'param_id', 'param_desc', 'total_signals', 'tick_count', 'error'])
        output_file = f"signal_density_scan_results.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 空结果已保存到: {output_file}")
        return df
    
    df = pd.DataFrame(results)
    
    # 1. 整体统计
    total_scans = len(df)
    successful_scans = len(df[df['tick_count'] > 0])
    scans_with_signals = len(df[df['total_signals'] > 0])
    
    print(f"📊 总扫描次数: {total_scans}")
    print(f"✅ 成功获取Tick数据: {successful_scans} ({successful_scans/total_scans*100:.1f}%)")
    print(f"🎯 有Halfway信号: {scans_with_signals} ({scans_with_signals/total_scans*100:.1f}%)")
    
    # 2. 信号分布统计
    signal_dist = df['total_signals'].value_counts().sort_index()
    print(f"\n📈 信号数量分布:")
    for count, freq in list(signal_dist.items())[:10]:  # 只显示前10个
        print(f"   {count} 个信号: {freq} 次")
    
    # 3. 零信号分析
    zero_signal_df = df[df['total_signals'] == 0]
    zero_signal_with_data = zero_signal_df[zero_signal_df['tick_count'] > 0]
    print(f"\n🔍 零信号分析:")
    print(f"   有数据但零信号: {len(zero_signal_with_data)} 次")
    print(f"   无数据零信号: {len(zero_signal_df) - len(zero_signal_with_data)} 次")
    
    # 4. 高信号密度分析
    high_signal_df = df[df['total_signals'] > 5]
    if len(high_signal_df) > 0:
        print(f"\n🔥 高信号密度 (>5个信号):")
        for _, row in high_signal_df.head(10).iterrows():  # 只显示前10个
            print(f"   {row['stock_code']} {row['trade_date']} - {row['total_signals']} 个信号 ({row['param_desc']})")
    
    # 5. 按股票统计
    print(f"\n📈 按股票信号统计:")
    for stock in df['stock_code'].unique():
        stock_data = df[df['stock_code'] == stock]
        total_signals = stock_data['total_signals'].sum()
        days_with_data = len(stock_data[stock_data['tick_count'] > 0])
        days_with_signals = len(stock_data[stock_data['total_signals'] > 0])
        
        print(f"   {stock}: 总信号{total_signals}, 有数据天数{days_with_data}, 有信号天数{days_with_signals}")
    
    # 6. 错误统计
    error_df = df[df['error'].notna()]
    if len(error_df) > 0:
        print(f"\n⚠️  错误统计: {len(error_df)} 次")
        for _, row in error_df.head().iterrows():
            print(f"   {row['stock_code']} {row['trade_date']}: {row['error']}")
    
    # 保存结果
    output_file = f"signal_density_scan_results.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 扫描结果已保存到: {output_file}")
    
    return df


if __name__ == "__main__":
    print("🎯 信号密度扫描工具")
    print("=" * 80)
    
    # 使用示例股票和参数
    stocks = load_hot_stocks()[:3]  # 只取前3只进行测试
    dates = ["20251114", "20251117", "20251118"]  # 使用已知有数据的日期
    
    # 使用几组不同的参数
    params_list = [
        {'volatility_threshold': 0.05, 'volume_surge': 1.2, 'breakout_strength': 0.005, 'min_history_points': 30},
        {'volatility_threshold': 0.03, 'volume_surge': 1.5, 'breakout_strength': 0.01, 'min_history_points': 30},
    ]
    
    print(f"📋 测试配置:")
    print(f"   股票: {stocks}")
    print(f"   日期: {dates}")
    print(f"   参数组合: {len(params_list)}")
    
    # 执行扫描
    results = scan_signal_density(stocks, dates, params_list)
    
    # 分析结果
    df_results = analyze_scan_results(results)
    
    print(f"\n✅ 信号密度扫描完成")
    print("=" * 80)