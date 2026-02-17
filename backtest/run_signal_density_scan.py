#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
信号密度扫描作业
分析Halfway策略在不同股票和日期上的信号分布
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from typing import List, Dict
import json
import argparse


def load_hot_stocks() -> List[str]:
    """
    加载热门股票列表
    """
    config_path = PROJECT_ROOT / 'config' / 'hot_stocks_codes.json'
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


def run_signal_density_scan(
    stocks: List[str], 
    dates: List[str], 
    params: Dict
) -> List[Dict]:
    """
    运行信号密度扫描
    
    Args:
        stocks: 股票列表
        dates: 日期列表
        params: 策略参数
        
    Returns:
        List[Dict]: 扫描结果
    """
    print(f"📊 信号密度扫描")
    print(f"📈 股票数量: {len(stocks)}")
    print(f"📅 日期数量: {len(dates)}")
    print(f"⚙️  策略参数: {params}")
    print("=" * 80)
    
    results = []
    
    for i, stock in enumerate(stocks):
        print(f"\n📈 [{i+1}/{len(stocks)}] 扫描 {stock}")
        
        for date in dates:
            print(f"  📅 {date} ", end="", flush=True)
            
            try:
                # 这里我们模拟使用策略进行信号检测
                # 在实际应用中，这应该连接到真实的策略执行器
                from tools.per_day_tick_runner import PerDayTickRunner
                from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
                
                strategy = HalfwayTickStrategy(params)
                runner = PerDayTickRunner(
                    stock_code=stock,
                    trade_date=date.replace('-', ''),  # 转换为YYYYMMDD格式
                    strategy=strategy
                )
                
                # 运行回放获取信号
                signals = runner.run()
                
                result = {
                    'stock_code': stock,
                    'trade_date': date,
                    'param_desc': f"vol_{params['volatility_threshold']}_vol_surge_{params['volume_surge']}_breakout_{params['breakout_strength']}",
                    'total_signals': len(signals),
                    'tick_count': runner.tick_count,
                    'error': None
                }
                results.append(result)
                
                # 根据信号数量显示状态
                if len(signals) > 10:
                    print("🔥", end="", flush=True)  # 高信号密度
                elif len(signals) > 0:
                    print("✅", end="", flush=True)  # 有信号
                elif runner.tick_count == 0:
                    print("❌", end="", flush=True)  # 无数据
                else:
                    print("₀", end="", flush=True)  # 无信号但有数据
                    
            except Exception as e:
                print("❌", end="", flush=True)
                result = {
                    'stock_code': stock,
                    'trade_date': date,
                    'param_desc': f"vol_{params['volatility_threshold']}_vol_surge_{params['volume_surge']}_breakout_{params['breakout_strength']}",
                    'total_signals': 0,
                    'tick_count': 0,
                    'error': str(e)
                }
                results.append(result)
    
        print()  # 换行
    
    return results


def analyze_scan_results(results: List[Dict]) -> Dict:
    """
    分析扫描结果
    
    Args:
        results: 扫描结果列表
        
    Returns:
        Dict: 分析结果
    """
    df = pd.DataFrame(results)
    
    print(f"\n🔍 扫描结果分析")
    print("=" * 80)
    
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
    
    # 4. 按股票统计
    print(f"\n📈 按股票信号统计:")
    for stock in df['stock_code'].unique():
        stock_data = df[df['stock_code'] == stock]
        total_signals = stock_data['total_signals'].sum()
        days_with_data = len(stock_data[stock_data['tick_count'] > 0])
        days_with_signals = len(stock_data[stock_data['total_signals'] > 0])
        
        print(f"   {stock}: 总信号{total_signals}, 有数据天数{days_with_data}, 有信号天数{days_with_signals}")
    
    # 5. 错误统计
    error_df = df[df['error'].notna()]
    if len(error_df) > 0:
        print(f"\n⚠️  错误统计: {len(error_df)} 次")
        for _, row in error_df.head().iterrows():
            print(f"   {row['stock_code']} {row['trade_date']}: {row['error']}")
    
    return {
        'summary': {
            'total_scans': total_scans,
            'successful_scans': successful_scans,
            'scans_with_signals': scans_with_signals,
            'success_rate': successful_scans / total_scans if total_scans > 0 else 0,
            'signal_rate': scans_with_signals / total_scans if total_scans > 0 else 0
        },
        'detailed_results': results
    }


def main():
    parser = argparse.ArgumentParser(description='信号密度扫描作业')
    parser.add_argument('--stocks', nargs='+', help='股票代码列表')
    parser.add_argument('--dates', nargs='+', help='日期列表 (YYYY-MM-DD)')
    parser.add_argument('--volatility-threshold', type=float, default=0.03, help='波动率阈值')
    parser.add_argument('--volume-surge', type=float, default=1.5, help='量能放大倍数')
    parser.add_argument('--breakout-strength', type=float, default=0.01, help='突破强度')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    
    args = parser.parse_args()
    
    # 加载股票列表
    if not args.stocks:
        stocks = load_hot_stocks()[:10]  # 限制为前10只进行测试
    else:
        stocks = args.stocks
    
    # 加载日期列表（如果没有指定，使用最近的几个交易日）
    if not args.dates:
        # 使用最近的3个交易日进行测试
        import pandas as pd
        from datetime import datetime, timedelta
        # 生成最近3个交易日的日期（假设今天是交易日）
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]
        args.dates = dates
    
    # 构建策略参数
    params = {
        'volatility_threshold': args.volatility_threshold,
        'volume_surge': args.volume_surge,
        'breakout_strength': args.breakout_strength,
        'min_history_points': 30
    }
    
    # 运行扫描
    results = run_signal_density_scan(
        stocks=stocks,
        dates=args.dates,
        params=params
    )
    
    # 分析结果
    analysis = analyze_scan_results(results)
    
    # 保存结果
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 扫描结果已保存: {output_path}")
    
    print(f"\n✅ 信号密度扫描完成")


if __name__ == "__main__":
    main()
