#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟分钟K线数据生成器 - 用于回测测试

当QMT不可用时，生成符合A股特征的模拟分钟K线数据
用于测试回测流程和策略逻辑

Author: iFlow CLI
Date: 2026-02-09
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import numpy as np

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_mock_minute_data(
    code: str,
    start_date: str = None,
    end_date: str = None,
    base_price: float = 10.0,
    trend: str = 'neutral'  # 'up', 'down', 'neutral'
) -> pd.DataFrame:
    """
    生成模拟的分钟K线数据
    
    Args:
        code: 股票代码
        start_date: 开始日期，格式 'YYYYMMDD'
        end_date: 结束日期，格式 'YYYYMMDD'
        base_price: 基础价格
        trend: 趋势方向 'up', 'down', 'neutral'
    
    Returns:
        DataFrame with columns: time, open, high, low, close, volume, amount
    """
    # 默认日期范围：过去30天
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    
    # 生成所有交易日的分钟K线
    data_rows = []
    current_date = start_dt
    
    while current_date <= end_dt:
        # 跳过周末
        if current_date.weekday() >= 5:  # 周六(5) 或 周日(6)
            current_date += timedelta(days=1)
            continue
        
        # 交易时间：9:30-11:30, 13:00-15:00
        morning_sessions = [(9, 30), (9, 31), (9, 32), ..., (11, 29), (11, 30)]
        afternoon_sessions = [(13, 0), (13, 1), (13, 2), ..., (14, 59), (15, 0)]
        
        # 简化：每分钟生成一根K线
        trading_minutes = []
        
        # 上午：9:30-11:30（120分钟）
        for hour in range(9, 12):
            for minute in range(60):
                if (hour == 9 and minute < 30) or (hour == 11 and minute > 30):
                    continue
                trading_minutes.append((hour, minute))
        
        # 下午：13:00-15:00（120分钟）
        for hour in range(13, 15):
            for minute in range(60):
                trading_minutes.append((hour, minute))
        trading_minutes.append((15, 0))  # 最后一分钟
        
        # 生成每根K线
        prev_close = base_price
        daily_drift = 0.0
        
        for hour, minute in trading_minutes:
            # 计算时间戳（毫秒）
            time_dt = current_date.replace(hour=hour, minute=minute)
            timestamp = int(time_dt.timestamp() * 1000)
            
            # 生成开盘价（基于前一根K线的收盘价）
            open_price = prev_close * (1 + np.random.normal(0, 0.001))
            
            # 添加趋势漂移
            if trend == 'up':
                daily_drift += 0.0001
            elif trend == 'down':
                daily_drift -= 0.0001
            
            # 生成高点和低点
            intraday_range = abs(open_price) * 0.01  # 1%的日内振幅
            high_price = open_price * (1 + np.random.uniform(0, 0.01)) + daily_drift
            low_price = open_price * (1 - np.random.uniform(0, 0.01)) + daily_drift
            
            # 生成收盘价
            close_price = open_price + np.random.normal(0, 0.002) * abs(open_price) + daily_drift
            
            # 确保高开低收的关系
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            # 生成成交量和成交额
            volume = np.random.randint(100000, 10000000)  # 10万到1000万股
            amount = volume * close_price  # 成交额
            
            # 添加到数据
            data_rows.append({
                'time': timestamp,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume,
                'amount': round(amount, 2)
            })
            
            prev_close = close_price
            base_price = close_price  # 更新基础价格
        
        current_date += timedelta(days=1)
    
    # 创建DataFrame
    df = pd.DataFrame(data_rows)
    df['time_str'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
    
    return df


def generate_market_mock_data(
    stock_list: List[str],
    start_date: str = None,
    end_date: str = None
) -> Dict[str, pd.DataFrame]:
    """
    生成全市场模拟数据
    
    Args:
        stock_list: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        字典，key为股票代码，value为DataFrame
    """
    print()
    print("=" * 80)
    print("🔄 生成模拟分钟K线数据（QMT不可用时的备用方案）")
    print("=" * 80)
    print()
    
    result = {}
    
    for idx, code in enumerate(stock_list):
        # 随机选择趋势
        trend = np.random.choice(['up', 'down', 'neutral'], p=[0.3, 0.3, 0.4])
        
        # 随机基础价格（5-100元）
        base_price = np.random.uniform(5, 100)
        
        # 生成数据
        df = generate_mock_minute_data(
            code=code,
            start_date=start_date,
            end_date=end_date,
            base_price=base_price,
            trend=trend
        )
        
        result[code] = df
        
        print(f"✅ {code}: {len(df)} 根K线 (趋势: {trend})")
        
        # 每10只打印一次进度
        if (idx + 1) % 10 == 0:
            print(f"   进度: {idx + 1}/{len(stock_list)}")
    
    print()
    print("=" * 80)
    print(f"✅ 生成完成: {len(result)} 只股票")
    print("=" * 80)
    
    return result


def save_mock_data(data_dict: Dict[str, pd.DataFrame], output_dir: str = 'data/minute_data_mock'):
    """保存模拟数据到CSV"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print()
    print("=" * 80)
    print("💾 保存模拟数据")
    print("=" * 80)
    
    for code, df in data_dict.items():
        file_path = output_path / f"{code}_1m.csv"
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"✅ {code} → {file_path}")
    
    print("=" * 80)


def main():
    """主函数"""
    print()
    print("=" * 80)
    print("🔧 MyQuantTool - 模拟分钟K线数据生成器")
    print("=" * 80)
    print()
    print("⚠️  警告：这是模拟数据，仅用于测试回测流程")
    print("⚠️  实际回测请使用 QMT 拉取的真实数据")
    print()
    
    # 生成过去30天的数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    print(f"📅 时间范围: {start_date_str} ~ {end_date_str} (过去30天)")
    print()
    
    # 测试股票列表
    test_stocks = [
        '600519.SH',  # 贵州茅台
        '000001.SZ',  # 平安银行
        '300997.SZ',  # 欢乐家
        '002099.SZ',  # 海翔药业
        '301150.SZ',  # 中船汉光
    ]
    
    # 生成模拟数据
    data = generate_market_mock_data(
        stock_list=test_stocks,
        start_date=start_date_str,
        end_date=end_date_str
    )
    
    # 保存数据
    save_mock_data(data, 'data/minute_data_mock')
    
    # 分析第一只股票
    if data:
        first_code = list(data.keys())[0]
        df = data[first_code]
        
        print()
        print("=" * 80)
        print(f"📊 {first_code} 模拟数据分析")
        print("=" * 80)
        print(f"📌 股票代码: {first_code}")
        print(f"📊 K线数量: {len(df)}")
        print(f"📅 时间范围: {df['time_str'].min()} ~ {df['time_str'].max()}")
        print()
        print("📈 前5根K线:")
        print(df[['time_str', 'open', 'high', 'low', 'close', 'volume']].head())
        print()
        print("📉 后5根K线:")
        print(df[['time_str', 'open', 'high', 'low', 'close', 'volume']].tail())
        print("=" * 80)
    
    print()
    print("✅ 模拟数据生成完成！")
    print()
    print("📝 下一步:")
    print("   1. 使用模拟数据进行回测测试")
    print("   2. 验证回测流程是否正常")
    print("   3. 对比真实数据，调整策略参数")


if __name__ == "__main__":
    main()