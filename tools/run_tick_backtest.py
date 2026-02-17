#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一Tick回测入口脚本
用于批量回测多只股票和多种策略
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any

from tools.per_day_tick_runner import PerDayTickRunner


def load_hot_stocks(file_path: str = None) -> List[str]:
    """
    加载热门股票列表
    
    Args:
        file_path: 股票列表文件路径
        
    Returns:
        List[str]: 股票代码列表
    """
    # 尝试从配置文件加载热门股票
    config_path = PROJECT_ROOT / 'config' / 'hot_stocks_codes.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 如果配置文件格式是包含stocks数组的复杂结构
            if 'stocks' in data:
                stocks = [item['code'] for item in data['stocks'] if 'code' in item]
                return stocks
            # 如果是简单的{'hot_stocks': [...]}结构
            elif 'hot_stocks' in data:
                return data['hot_stocks']
    
    # 如果没有配置文件，返回一些示例股票
    return ['300997.SZ', '300986.SZ', '000001.SZ', '600000.SH']


def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """
    生成日期范围
    
    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        
    Returns:
        List[str]: 日期列表，格式：YYYYMMDD
    """
    import pandas as pd
    
    # 将日期字符串转换为pandas日期范围
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # 过滤掉非交易日（这里简化处理，只过滤周末）
    trading_days = []
    for date in date_range:
        # 0=Monday, 6=Sunday
        if date.weekday() < 5:  # 周一到周五
            trading_days.append(date.strftime('%Y%m%d'))
    
    return trading_days


def create_strategy(strategy_name: str, params: Dict[str, Any]):
    """
    策略工厂函数
    
    Args:
        strategy_name: 策略名称
        params: 策略参数
        
    Returns:
        策略实例
    """
    if strategy_name.lower() == 'halfway':
        from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
        return HalfwayTickStrategy(params)
    else:
        # 默认使用Halfway策略
        from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
        return HalfwayTickStrategy(params)


def get_param_grid(strategy_name: str) -> List[Dict[str, Any]]:
    """
    获取策略参数网格
    
    Args:
        strategy_name: 策略名称
        
    Returns:
        List[Dict]: 参数网格
    """
    if strategy_name.lower() == 'halfway':
        return [
            {'volatility_threshold': 0.02, 'volume_surge': 1.3, 'breakout_strength': 0.005, 'min_history_points': 60},
            {'volatility_threshold': 0.02, 'volume_surge': 1.3, 'breakout_strength': 0.01, 'min_history_points': 60},
            {'volatility_threshold': 0.03, 'volume_surge': 1.5, 'breakout_strength': 0.005, 'min_history_points': 60},
            {'volatility_threshold': 0.03, 'volume_surge': 1.5, 'breakout_strength': 0.01, 'min_history_points': 60},
            {'volatility_threshold': 0.04, 'volume_surge': 1.8, 'breakout_strength': 0.005, 'min_history_points': 60},
            {'volatility_threshold': 0.04, 'volume_surge': 1.8, 'breakout_strength': 0.01, 'min_history_points': 60},
        ]
    else:
        # 默认返回一个参数组合
        return [{'volatility_threshold': 0.03, 'volume_surge': 1.5, 'breakout_strength': 0.01}]


def run_batch_backtest(stocks: List[str], dates: List[str], strategy_name: str, 
                      output_file: str = None):
    """
    运行批量回测
    
    Args:
        stocks: 股票代码列表
        dates: 日期列表
        strategy_name: 策略名称
        output_file: 输出文件路径
    """
    print("=" * 100)
    print(f"🚀 批量回测启动")
    print(f"📊 股票数量: {len(stocks)}")
    print(f"📅 日期范围: {len(dates)} 天")
    print(f"🎯 策略名称: {strategy_name}")
    print("=" * 100)
    
    # 获取参数网格
    param_grid = get_param_grid(strategy_name)
    print(f"⚙️  参数组合: {len(param_grid)} 种")
    
    results = []
    
    # 遍历股票
    for i, stock in enumerate(stocks):
        print(f"\n📈 [{i+1}/{len(stocks)}] 正在回测 {stock}")
        
        # 遍历日期
        for date in dates:
            print(f"  📅 {date} ", end="", flush=True)
            
            # 遍历参数组合
            for param_idx, params in enumerate(param_grid):
                try:
                    # 根据策略名称创建策略实例
                    strategy = create_strategy(strategy_name, params)
                    
                    # 创建runner并运行
                    runner = PerDayTickRunner(
                        stock_code=stock,
                        trade_date=date,
                        strategy=strategy
                    )
                    
                    signals = runner.run()
                    stats = runner.get_statistics()
                    
                    # 记录结果
                    result = {
                        'stock_code': stock,
                        'trade_date': date,
                        'strategy': strategy_name,
                        'param_id': param_idx,
                        'params': str(params),
                        'tick_count': runner.tick_count,
                        'total_signals': stats['total_signals'],
                        'win_rate_1min': stats['win_rate']['1min'],
                        'win_rate_5min': stats['win_rate']['5min'],
                        'win_rate_10min': stats['win_rate']['10min'],
                        'avg_return_1min': stats['avg_return']['1min'],
                        'avg_return_5min': stats['avg_return']['5min'],
                        'avg_return_10min': stats['avg_return']['10min'],
                        'total_returns_1min': stats['total_returns']['1min'],
                        'total_returns_5min': stats['total_returns']['5min'],
                        'total_returns_10min': stats['total_returns']['10min']
                    }
                    results.append(result)
                    
                    # 简单的进度指示
                    if stats['total_signals'] > 0:
                        print("✅", end="", flush=True)
                    else:
                        print("❌", end="", flush=True)
                        
                except Exception as e:
                    print(f"❌(E)", end="", flush=True)
                    # 记录错误
                    result = {
                        'stock_code': stock,
                        'trade_date': date,
                        'strategy': strategy_name,
                        'param_id': param_idx,
                        'params': str(params),
                        'tick_count': 0,
                        'total_signals': 0,
                        'win_rate_1min': 0.0,
                        'win_rate_5min': 0.0,
                        'win_rate_10min': 0.0,
                        'avg_return_1min': 0.0,
                        'avg_return_5min': 0.0,
                        'avg_return_10min': 0.0,
                        'total_returns_1min': 0,
                        'total_returns_5min': 0,
                        'total_returns_10min': 0,
                        'error': str(e)
                    }
                    results.append(result)
            
            print()  # 换行
    
    # 创建结果DataFrame
    df_results = pd.DataFrame(results)
    
    # 保存结果
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"batch_backtest_results_{strategy_name}_{timestamp}.csv"
    
    df_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 结果已保存到: {output_file}")
    
    # 打印统计信息
    print(f"\n📊 回测统计:")
    print(f"   总回测次数: {len(df_results)}")
    print(f"   总信号数: {df_results['total_signals'].sum()}")
    print(f"   平均信号数: {df_results['total_signals'].mean():.2f}")
    print(f"   有信号的比例: {(df_results['total_signals'] > 0).mean():.2%}")
    print(f"   平均5分钟胜率: {df_results['win_rate_5min'].mean():.2%}")
    print(f"   平均5分钟收益率: {df_results['avg_return_5min'].mean():.4f}")
    
    print(f"\n✅ 批量回测完成！")
    print("=" * 100)
    
    return df_results


def main():
    parser = argparse.ArgumentParser(description='统一Tick回测入口脚本')
    parser.add_argument('--stock-list', type=str, default=None,
                        help='股票列表文件路径 (默认使用配置文件)')
    parser.add_argument('--date-start', type=str, default='2025-11-14',
                        help='开始日期 (YYYY-MM-DD格式)')
    parser.add_argument('--date-end', type=str, default='2025-11-20',
                        help='结束日期 (YYYY-MM-DD格式)')
    parser.add_argument('--strategy', type=str, default='halfway',
                        help='策略名称 (halfway等)')
    parser.add_argument('--output', type=str, default=None,
                        help='输出文件路径')
    
    args = parser.parse_args()
    
    # 加载股票列表
    stocks = load_hot_stocks(args.stock_list)
    
    # 生成日期范围
    dates = generate_date_range(args.date_start, args.date_end)
    
    # 运行批量回测
    run_batch_backtest(
        stocks=stocks,
        dates=dates,
        strategy_name=args.strategy,
        output_file=args.output
    )


if __name__ == "__main__":
    main()