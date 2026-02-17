#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tick数据回测作业
使用统一的backtestengine运行Tick策略
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from datetime import datetime
from typing import List, Dict
import json
import argparse

from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
from logic.strategies.tick_strategy_adapter import create_tick_backtest_strategy, TickDataFeed
from logic.strategies.backtest_engine import BacktestEngine


def run_tick_backtest(
    stock_codes: List[str], 
    start_date: str, 
    end_date: str, 
    strategy_params: Dict,
    initial_capital: float = 100000
):
    """
    运行Tick数据回测
    
    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        strategy_params: 策略参数
        initial_capital: 初始资金
        
    Returns:
        Dict: 回测结果
    """
    print(f"🚀 开始Tick数据回测")
    print(f"📊 股票: {len(stock_codes)} 只")
    print(f"📅 日期: {start_date} ~ {end_date}")
    print(f"💰 初始资金: {initial_capital:,.2f}")
    print(f"⚙️  策略参数: {strategy_params}")
    print("-" * 60)
    
    # 创建策略
    halfway_strategy = HalfwayTickStrategy(strategy_params)
    strategy_func = create_tick_backtest_strategy(halfway_strategy, strategy_params)
    
    # 创建回测引擎
    engine = BacktestEngine(initial_capital=initial_capital)
    
    # 运行回测
    result = engine.run_backtest(
        strategy_func=strategy_func,
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        strategy_params=strategy_params
    )
    
    return result


def run_param_grid_search(
    stock_codes: List[str],
    start_date: str,
    end_date: str,
    param_grid: List[Dict],
    initial_capital: float = 100000
):
    """
    运行参数网格搜索
    
    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        param_grid: 参数网格
        initial_capital: 初始资金
        
    Returns:
        List[Dict]: 所有参数组合的回测结果
    """
    print(f"🔍 开始参数网格搜索")
    print(f"📊 参数组合数: {len(param_grid)}")
    print(f"📈 股票数: {len(stock_codes)}")
    print("-" * 60)
    
    results = []
    
    for i, params in enumerate(param_grid):
        print(f"[{i+1}/{len(param_grid)}] 测试参数: {params}")
        
        try:
            result = run_tick_backtest(
                stock_codes=stock_codes,
                start_date=start_date,
                end_date=end_date,
                strategy_params=params,
                initial_capital=initial_capital
            )
            
            if result['success']:
                result['params'] = params
                result['param_id'] = i
                results.append(result)
                print(f"  ✅ 成功 - 总收益率: {result['metrics']['total_return']:.2f}%")
            else:
                print(f"  ❌ 失败 - {result.get('error', '未知错误')}")
                
        except Exception as e:
            print(f"  ❌ 异常 - {str(e)}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Tick数据回测作业')
    parser.add_argument('--stocks', nargs='+', help='股票代码列表')
    parser.add_argument('--start-date', type=str, required=True, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--initial-capital', type=float, default=100000, help='初始资金')
    parser.add_argument('--mode', choices=['single', 'grid'], default='single', help='运行模式')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    
    # 半路策略参数
    parser.add_argument('--volatility-threshold', type=float, default=0.03, help='波动率阈值')
    parser.add_argument('--volume-surge', type=float, default=1.5, help='量能放大倍数')
    parser.add_argument('--breakout-strength', type=float, default=0.01, help='突破强度')
    
    args = parser.parse_args()
    
    # 加载股票列表（如果未指定）
    if not args.stocks:
        # 从配置文件加载热门股票
        hot_stocks_path = PROJECT_ROOT / 'config' / 'hot_stocks_codes.json'
        if hot_stocks_path.exists():
            import json
            with open(hot_stocks_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'stocks' in data:
                    args.stocks = [item['code'] for item in data['stocks'][:20]]  # 限制为前20只
                else:
                    args.stocks = ['300997.SZ', '300986.SZ', '603697.SH']  # 默认股票
        else:
            args.stocks = ['300997.SZ', '300986.SZ', '603697.SH']  # 默认股票
    
    # 单独运行模式
    if args.mode == 'single':
        strategy_params = {
            'volatility_threshold': args.volatility_threshold,
            'volume_surge': args.volume_surge,
            'breakout_strength': args.breakout_strength
        }
        
        result = run_tick_backtest(
            stock_codes=args.stocks,
            start_date=args.start_date,
            end_date=args.end_date,
            strategy_params=strategy_params,
            initial_capital=args.initial_capital
        )
        
        if result['success']:
            metrics = result['metrics']
            print("\n" + "="*60)
            print("📊 回测结果")
            print("="*60)
            print(f"初始资金: ¥{metrics['initial_capital']:,.2f}")
            print(f"最终权益: ¥{metrics['final_equity']:,.2f}")
            print(f"总收益率: {metrics['total_return']:.2f}%")
            print(f"年化收益率: {metrics['annual_return']:.2f}%")
            print(f"最大回撤: {metrics['max_drawdown']:.2f}%")
            print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"胜率: {metrics['win_rate']:.2f}%")
            print(f"交易次数: {metrics['total_trades']}")
            print(f"盈亏比: {metrics['profit_loss_ratio']:.2f}")
            
            # 保存结果
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                print(f"\n💾 结果已保存: {output_path}")
        
    # 网格搜索模式
    elif args.mode == 'grid':
        # 定义参数网格
        param_grid = [
            {
                'volatility_threshold': 0.02,
                'volume_surge': 1.3,
                'breakout_strength': 0.005
            },
            {
                'volatility_threshold': 0.03,
                'volume_surge': 1.5,
                'breakout_strength': 0.01
            },
            {
                'volatility_threshold': 0.05,
                'volume_surge': 1.2,
                'breakout_strength': 0.003
            },
            {
                'volatility_threshold': 0.01,
                'volume_surge': 1.8,
                'breakout_strength': 0.015
            }
        ]
        
        results = run_param_grid_search(
            stock_codes=args.stocks,
            start_date=args.start_date,
            end_date=args.end_date,
            param_grid=param_grid,
            initial_capital=args.initial_capital
        )
        
        # 分析最佳参数
        if results:
            best_result = max(results, key=lambda x: x['metrics']['total_return'])
            print(f"\n🏆 最佳参数组合:")
            print(f"参数: {best_result['params']}")
            print(f"总收益率: {best_result['metrics']['total_return']:.2f}%")
            print(f"最大回撤: {best_result['metrics']['max_drawdown']:.2f}%")
            print(f"胜率: {best_result['metrics']['win_rate']:.2f}%")
            
            # 保存所有结果
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
                print(f"\n💾 网格搜索结果已保存: {output_path}")


if __name__ == "__main__":
    main()
