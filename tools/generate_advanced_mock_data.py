#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级模拟数据生成器 (Advanced Mock Data Generator)

功能：
生成包含特定市场特征的分钟K线数据，用于压力测试和策略验证。
支持场景：
1. 正常波动 (Normal)
2. 诱多陷阱 (Pump and Dump)
3. 涨停封板 (Limit Up)
4. 跌停封板 (Limit Down)
5. 剧烈震荡 (High Volatility)

Author: MyQuantTool Team
Date: 2026-02-09
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import random

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def generate_trade_times(date_str: str) -> list:
    """生成单日的交易时间序列（分钟级）"""
    date = datetime.strptime(date_str, "%Y%m%d")
    times = []
    
    # 上午 9:30 - 11:30
    current = date.replace(hour=9, minute=30)
    end_am = date.replace(hour=11, minute=30)
    while current <= end_am:
        times.append(current)
        current += timedelta(minutes=1)
        
    # 下午 13:00 - 15:00
    current = date.replace(hour=13, minute=0)
    end_pm = date.replace(hour=15, minute=0)
    while current <= end_pm:
        times.append(current)
        current += timedelta(minutes=1)
        
    return times

def apply_scenario(price_series: np.array, volume_series: np.array, scenario: str):
    """应用特定场景特征"""
    length = len(price_series)
    
    if scenario == 'pump_and_dump':
        # 诱多：前1/3拉升，中间1/3高位震荡，后1/3急跌
        phase1 = int(length * 0.3)
        phase2 = int(length * 0.6)
        
        # 拉升期：价格+5%，量能放大
        price_series[:phase1] *= np.linspace(1.0, 1.05, phase1)
        volume_series[:phase1] *= np.linspace(1.0, 3.0, phase1)
        
        # 震荡期：价格波动，量能维持高位
        price_series[phase1:phase2] = price_series[phase1-1] * (1 + np.random.normal(0, 0.005, phase2-phase1))
        volume_series[phase1:phase2] *= 2.0
        
        # 急跌期：价格-8%，量能萎缩或放大（出货完成）
        price_series[phase2:] = price_series[phase2-1] * np.linspace(1.0, 0.92, length-phase2)
        volume_series[phase2:] *= 1.5 # 恐慌盘
        
    elif scenario == 'limit_up':
        # 涨停：开盘不久封板，之后一条直线，量能极度萎缩
        lock_time = int(length * 0.2) # 20%时间点封板
        limit_price = price_series[0] * 1.10 # 10%涨停
        
        # 封板前拉升
        price_series[:lock_time] = np.linspace(price_series[0], limit_price, lock_time)
        volume_series[:lock_time] *= 2.0 # 抢筹
        
        # 封板后
        price_series[lock_time:] = limit_price
        volume_series[lock_time:] = volume_series[0] * 0.1 # 缩量封单
        
    elif scenario == 'limit_down':
        # 跌停：开盘不久跌停
        lock_time = int(length * 0.2)
        limit_price = price_series[0] * 0.90
        
        price_series[:lock_time] = np.linspace(price_series[0], limit_price, lock_time)
        volume_series[:lock_time] *= 2.5 # 恐慌出逃
        
        price_series[lock_time:] = limit_price
        volume_series[lock_time:] = volume_series[0] * 0.05
        
    elif scenario == 'high_volatility':
        # 剧烈震荡：增加随机噪声幅度
        noise = np.random.normal(0, 0.02, length) # 2%标准差
        price_series *= (1 + noise)
        volume_series *= (1 + np.abs(noise) * 5) # 波动大成交量大

    return price_series, volume_series

def generate_mock_data(
    code: str, 
    scenario: str = 'normal',
    days: int = 5,
    base_price: float = 10.0
) -> pd.DataFrame:
    """生成指定场景的模拟数据"""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days*2) # 多取几天防周末
    
    all_dfs = []
    generated_days = 0
    current_date = start_date
    
    while generated_days < days and current_date <= end_date:
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
            
        date_str = current_date.strftime("%Y%m%d")
        times = generate_trade_times(date_str)
        n = len(times)
        
        # 基础游走
        returns = np.random.normal(0, 0.001, n) # 0.1% 每分钟波动
        price_path = base_price * np.exp(np.cumsum(returns))
        
        # 基础成交量
        base_volume = 1000 + np.random.randint(0, 500, n)
        
        # 应用场景特征（仅在最后一天应用特殊场景，前面几天正常）
        daily_scenario = scenario if generated_days == days - 1 else 'normal'
        price_path, volume = apply_scenario(price_path, base_volume, daily_scenario)
        
        # 构造OHLC
        opens = price_path
        closes = np.roll(price_path, -1); closes[-1] = closes[-2]
        highs = np.maximum(opens, closes) * (1 + np.random.rand(n) * 0.001)
        lows = np.minimum(opens, closes) * (1 - np.random.rand(n) * 0.001)
        
        # 构造DataFrame
        df = pd.DataFrame({
            'time_str': [t.strftime("%Y-%m-%d %H:%M:%S") for t in times],
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volume.astype(int),
            'amount': volume * closes
        })
        
        # QMT 格式通常包含 time 毫秒时间戳
        df['time'] = [int(t.timestamp() * 1000) for t in times]
        
        all_dfs.append(df)
        base_price = closes[-1] #这一天的收盘价是下一天的参考
        generated_days += 1
        current_date += timedelta(days=1)
        
    return pd.concat(all_dfs, ignore_index=True)

def main():
    output_dir = Path("data/minute_data_mock_advanced")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🚀 高级模拟数据生成器启动")
    print("=" * 60)
    
    scenarios = {
        '300999.SZ': ('pump_and_dump', '诱多陷阱'),
        '600111.SH': ('limit_up', '涨停封板'),
        '002222.SZ': ('limit_down', '跌停封板'),
        '300000.SZ': ('high_volatility', '剧烈震荡'),
        '601398.SH': ('normal', '正常波动')
    }
    
    for code, (scenario, desc) in scenarios.items():
        print(f"生成 {code} [{desc}]...", end=" ")
        df = generate_mock_data(code, scenario=scenario, days=10)
        
        file_path = output_dir / f"{code}_1m.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"✅ 完成 ({len(df)} bars)")
        
    print("-" * 60)
    print(f"📁 数据已保存至: {output_dir}")
    print("💡 建议使用 tools/run_backtest_1m.py 测试这些数据")

if __name__ == "__main__":
    main()
