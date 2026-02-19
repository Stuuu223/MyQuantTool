#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Per-Day Tick Runner (重构版 - TickProvider迁移)
用于对单个股票的单个交易日进行Tick回放测试

功能：
1. 按时间顺序迭代Tick数据
2. 接受策略接口，支持多种策略
3. 记录信号和后续收益
4. 生成简单的统计报告

使用TickProvider统一封装类管理QMT连接

Author: iFlow CLI (T4迁移)
Date: 2026-02-19
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
from typing import Dict, List, Optional, Tuple
import numpy as np

# 🔥 T4迁移：使用TickProvider管理连接，QMTHistoricalProvider使用TickProvider
from logic.data_providers.tick_provider import TickProvider
from logic.qmt_historical_provider import QMTHistoricalProvider
from logic.strategies.tick_strategy_interface import ITickStrategy, TickData, Signal


class PerDayTickRunner:
    """
    每日Tick回放运行器 (重构版 - TickProvider版)
    
    用于测试策略在单个股票单个交易日中的表现
    支持多种策略接口
    """
    
    def __init__(
        self, 
        stock_code: str, 
        trade_date: str, 
        strategy: ITickStrategy,
        tick_provider: TickProvider = None
    ):
        """
        初始化
        
        Args:
            stock_code: 股票代码
            trade_date: 交易日期，格式：YYYYMMDD
            strategy: 策略实例
            tick_provider: TickProvider实例（可选，不传则自动创建）
        """
        self.stock_code = stock_code
        self.trade_date = trade_date
        self.strategy = strategy  # 策略实例
        
        # 🔥 T4迁移：使用TickProvider管理连接
        self._tick_provider = tick_provider
        self._owns_provider = tick_provider is None
        
        # 状态变量
        self.tick_count = 0  # Tick计数
        
        # 信号记录
        self.signals = []
        
        # 初始化历史数据提供者（传入TickProvider）
        start_time = f"{trade_date}093000"
        end_time = f"{trade_date}150000"
        self.tick_provider_hist = QMTHistoricalProvider(
            stock_code=stock_code,
            start_time=start_time,
            end_time=end_time,
            period="tick",
            tick_provider=self._tick_provider
        )
    
    def _ensure_connection(self):
        """确保QMT连接可用"""
        if self._tick_provider is None:
            self._tick_provider = TickProvider()
            self._owns_provider = True
        
        if not self._tick_provider.is_connected():
            if not self._tick_provider.connect():
                raise RuntimeError("无法连接到QMT行情服务")
    
    def run(self) -> List[Dict]:
        """
        运行回放
        
        Returns:
            List[Dict]: 所有信号及其相关信息
        """
        # 🔥 T4迁移：确保连接
        self._ensure_connection()
        
        print(f"🏃 开始回放: {self.stock_code} {self.trade_date} ({self.strategy.get_strategy_name()})")
        
        # 遍历Tick数据
        self.tick_count = 0
        for tick in self.tick_provider_hist.iter_ticks():
            self.tick_count += 1
            
            # 将tick数据转换为策略接口需要的格式
            tick_data = TickData(
                time=tick['time'],
                last_price=tick['last_price'],
                volume=tick['volume'],
                amount=tick['amount'],
                bid_price=tick.get('bid_price', 0),
                ask_price=tick.get('ask_price', 0),
                bid_vol=tick.get('bid_vol', 0),
                ask_vol=tick.get('ask_vol', 0)
            )
            
            # 处理Tick
            signals = self.strategy.on_tick(tick_data)
            for signal in signals:
                # 记录信号
                signal_info = {
                    'time': signal.time,
                    'price': signal.price,
                    'signal_type': signal.signal_type,
                    'params': signal.params,
                    'strength': signal.strength,
                    'extra_info': signal.extra_info
                }
                self.signals.append(signal_info)
                
                # 打印信号信息
                signal_time = datetime.fromtimestamp(signal.time/1000).strftime('%H:%M:%S')
                print(f"🚨 {signal_time} 信号触发: {signal.signal_type}, 价格={signal.price:.2f}, "
                      f"强度={signal.strength:.2f}")
        
        print(f"📊 处理完成: {self.tick_count}条Tick, {len(self.signals)}个信号")
        
        # 为每个信号计算后续收益
        if self.signals:
            self._calculate_signal_outcomes()
        
        return self.signals
    
    def _calculate_signal_outcomes(self):
        """
        计算每个信号的后续收益
        """
        if not self.signals:
            return
        
        # 重新获取价格历史用于计算收益
        price_history = []
        for tick in self.tick_provider_hist.iter_ticks():
            price_history.append((tick['time'], tick['last_price']))
        
        # 按时间排序价格历史
        sorted_prices = sorted(price_history, key=lambda x: x[0])
        
        for signal in self.signals:
            signal_time = signal['time']
            
            # 找到信号发生后1分钟、5分钟、10分钟的价格
            target_times = {
                '1min': signal_time + 60 * 1000,    # 1分钟后的价格
                '5min': signal_time + 5 * 60 * 1000,  # 5分钟后的价格
                '10min': signal_time + 10 * 60 * 1000  # 10分钟后的价格
            }
            
            outcomes = {}
            for period, target_time in target_times.items():
                # 找到最接近目标时间的价格
                target_price = None
                for i in range(len(sorted_prices)):
                    if sorted_prices[i][0] >= target_time:
                        target_price = sorted_prices[i][1]
                        break
                
                if target_price and signal['price'] > 0:
                    return_rate = (target_price - signal['price']) / signal['price']
                    outcomes[period] = {
                        'price': target_price,
                        'return_rate': return_rate
                    }
                else:
                    outcomes[period] = {
                        'price': None,
                        'return_rate': None
                    }
            
            signal['outcomes'] = outcomes
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        if not self.signals:
            return {
                'total_signals': 0,
                'winning_counts': {
                    '1min': 0,
                    '5min': 0,
                    '10min': 0
                },
                'win_rate': {
                    '1min': 0.0,
                    '5min': 0.0,
                    '10min': 0.0
                },
                'avg_return': {
                    '1min': 0.0,
                    '5min': 0.0,
                    '10min': 0.0
                },
                'total_returns': {
                    '1min': 0,
                    '5min': 0,
                    '10min': 0
                }
            }
        
        # 计算收益率统计
        returns_1min = [s['outcomes']['1min']['return_rate'] for s in self.signals 
                       if s['outcomes']['1min']['return_rate'] is not None]
        returns_5min = [s['outcomes']['5min']['return_rate'] for s in self.signals 
                       if s['outcomes']['5min']['return_rate'] is not None]
        returns_10min = [s['outcomes']['10min']['return_rate'] for s in self.signals 
                        if s['outcomes']['10min']['return_rate'] is not None]
        
        # 计算胜率（正收益比例）
        winning_1min = len([r for r in returns_1min if r is not None and r > 0])
        winning_5min = len([r for r in returns_5min if r is not None and r > 0])
        winning_10min = len([r for r in returns_10min if r is not None and r > 0])
        
        stats = {
            'total_signals': len(self.signals),
            'winning_counts': {
                '1min': winning_1min,
                '5min': winning_5min,
                '10min': winning_10min
            },
            'win_rate': {
                '1min': winning_1min / len(returns_1min) if returns_1min else 0.0,
                '5min': winning_5min / len(returns_5min) if returns_5min else 0.0,
                '10min': winning_10min / len(returns_10min) if returns_10min else 0.0
            },
            'avg_return': {
                '1min': np.mean(returns_1min) if returns_1min else 0.0,
                '5min': np.mean(returns_5min) if returns_5min else 0.0,
                '10min': np.mean(returns_10min) if returns_10min else 0.0
            },
            'total_returns': {
                '1min': len(returns_1min),
                '5min': len(returns_5min),
                '10min': len(returns_10min)
            }
        }
        
        return stats
    
    def close(self):
        """关闭连接"""
        # 🔥 T4迁移：如果owns_provider，则关闭连接
        if self._owns_provider and self._tick_provider:
            self._tick_provider.close()
            self._tick_provider = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False


def run_sample_test():
    """
    运行样本测试
    """
    print("=" * 80)
    print("🧪 Per-Day Tick Runner 样本测试 (TickProvider版)")
    print("=" * 80)
    print("🔧 使用TickProvider统一封装类管理QMT连接")
    
    # 导入Halfway策略
    from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
    
    # 测试参数组合
    test_params = {
        'volatility_threshold': 0.03,  # 平台波动率阈值
        'volume_surge': 1.5,           # 量能放大倍数
        'breakout_strength': 0.01      # 突破强度
    }
    
    # 创建策略实例
    strategy = HalfwayTickStrategy(test_params)
    
    # 测试股票和日期
    test_stock = "300997.SZ"
    test_dates = ["20251114", "20251117", "20251118"]  # 选择几个交易日
    
    all_results = []
    
    # 🔥 T4迁移：使用TickProvider上下文管理器
    with TickProvider() as tick_provider:
        print(f"\n✅ QMT连接成功")
        
        for trade_date in test_dates:
            print(f"\n📊 测试 {test_stock} {trade_date}")
            print("-" * 60)
            
            runner = PerDayTickRunner(
                stock_code=test_stock,
                trade_date=trade_date,
                strategy=strategy,
                tick_provider=tick_provider  # 共享TickProvider
            )
            
            # 运行回放
            signals = runner.run()
            
            # 获取统计信息
            stats = runner.get_statistics()
            
            print(f"📈 信号统计:")
            print(f"   总信号数: {stats['total_signals']}")
            print(f"   1分钟胜率: {stats['win_rate']['1min']:.2%} ({stats['winning_counts']['1min']}/{stats['total_returns']['1min']})")
            print(f"   5分钟胜率: {stats['win_rate']['5min']:.2%} ({stats['winning_counts']['5min']}/{stats['total_returns']['5min']})")
            print(f"   10分钟胜率: {stats['win_rate']['10min']:.2%} ({stats['winning_counts']['10min']}/{stats['total_returns']['10min']})")
            print(f"   1分钟平均收益率: {stats['avg_return']['1min']:.4f}")
            print(f"   5分钟平均收益率: {stats['avg_return']['5min']:.4f}")
            print(f"   10分钟平均收益率: {stats['avg_return']['10min']:.4f}")
            
            # 记录结果
            result = {
                'stock': test_stock,
                'date': trade_date,
                'strategy': strategy.get_strategy_name(),
                'params': test_params,
                'signals': signals,
                'stats': stats
            }
            all_results.append(result)
    
    print("\n" + "=" * 80)
    print("📋 综合测试结果")
    print("=" * 80)
    
    total_signals = sum([r['stats']['total_signals'] for r in all_results])
    total_dates = len(all_results)
    
    print(f"股票: {test_stock}")
    print(f"策略: {strategy.get_strategy_name()}")
    print(f"测试天数: {total_dates}")
    print(f"总信号数: {total_signals}")
    
    if total_signals > 0:
        # 计算平均胜率
        avg_win_rate_1min = np.mean([r['stats']['win_rate']['1min'] for r in all_results])
        avg_win_rate_5min = np.mean([r['stats']['win_rate']['5min'] for r in all_results])
        avg_win_rate_10min = np.mean([r['stats']['win_rate']['10min'] for r in all_results])
        
        # 计算平均收益率
        avg_return_1min = np.mean([r['stats']['avg_return']['1min'] for r in all_results])
        avg_return_5min = np.mean([r['stats']['avg_return']['5min'] for r in all_results])
        avg_return_10min = np.mean([r['stats']['avg_return']['10min'] for r in all_results])
        
        print(f"平均1分钟胜率: {avg_win_rate_1min:.2%}")
        print(f"平均5分钟胜率: {avg_win_rate_5min:.2%}")
        print(f"平均10分钟胜率: {avg_win_rate_10min:.2%}")
        print(f"平均1分钟收益率: {avg_return_1min:.4f}")
        print(f"平均5分钟收益率: {avg_return_5min:.4f}")
        print(f"平均10分钟收益率: {avg_return_10min:.4f}")
    else:
        print("⚠️  没有触发任何信号，请调整参数")
    
    print("\n✅ Per-Day Tick Runner 测试完成")
    print("=" * 80)
    
    return all_results


if __name__ == "__main__":
    results = run_sample_test()
