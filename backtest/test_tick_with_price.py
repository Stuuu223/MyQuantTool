# -*- coding: utf-8 -*-
"""
测试tick数据价格计算
"""

import sys
from pathlib import Path
from xtquant import xtdata
from xtquant import xtdatacenter as xtdc
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# VIP配置
VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'
DATA_DIR = PROJECT_ROOT / 'data' / 'qmt_data'

# 设置数据目录
DATA_DIR.mkdir(parents=True, exist_ok=True)
xtdc.set_data_home_dir(str(DATA_DIR))
xtdc.set_token(VIP_TOKEN)
xtdc.init()

print("=" * 80)
print("测试Tick数据价格获取")
print("=" * 80)

test_stock = '600007.SH'
test_date = '2026-02-13'

start_time = test_date.replace('-', '') + '093000'
end_time = test_date.replace('-', '') + '150000'

# 读取tick数据
tick_df = xtdata.get_market_data_ex(
    field_list=['time', 'price', 'volume', 'amount'],
    stock_list=[test_stock],
    period='tick',
    start_time=start_time,
    end_time=end_time
)

if test_stock in tick_df:
    df = tick_df[test_stock]

    print(f"\n原始tick数据（前10条）:")
    print(df.head(10))
    print(f"\nprice字段统计:")
    print(df['price'].describe())
    print(f"\nprice字段非空值数量: {df['price'].notna().sum()}")

    # 尝试计算价格
    print("\n" + "=" * 80)
    print("尝试从成交额/成交量计算价格")
    print("=" * 80)

    # 计算均价 = 成交额 / 成交量
    df['calc_price'] = df['amount'] / df['volume']

    print(f"\n计算后的价格（前10条）:")
    print(df[['time', 'volume', 'amount', 'calc_price']].head(10))

    print(f"\n计算价格统计:")
    print(df['calc_price'].describe())

    print(f"\n价格范围: {df['calc_price'].min():.2f} - {df['calc_price'].max():.2f}")

    # 对比分钟数据的价格
    print("\n" + "=" * 80)
    print("对比分钟数据")
    print("=" * 80)

    minute_df = xtdata.get_market_data_ex(
        field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=[test_stock],
        period='1m',
        start_time=start_time,
        end_time=end_time
    )

    if test_stock in minute_df:
        min_df = minute_df[test_stock]
        print(f"\n分钟数据价格范围: {min_df['low'].min():.2f} - {min_df['high'].max():.2f}")
        print(f"分钟数据开盘价: {min_df['open'].iloc[0]:.2f}")
        print(f"分钟数据收盘价: {min_df['close'].iloc[-1]:.2f}")

        # 检查tick计算的价格是否在分钟数据范围内
        in_range = (df['calc_price'] >= min_df['low'].min()) & (df['calc_price'] <= min_df['high'].max())
        print(f"\nTick计算价格在分钟数据范围内的比例: {in_range.sum()}/{len(df)} ({in_range.mean()*100:.1f}%)")

    # 尝试使用其他字段
    print("\n" + "=" * 80)
    print("尝试获取更多tick字段")
    print("=" * 80)

    # 尝试获取更多字段
    tick_df_full = xtdata.get_market_data_ex(
        field_list=['time', 'price', 'lastPrice', 'open', 'high', 'low', 'close', 'volume', 'amount', 'askPrice1', 'bidPrice1'],
        stock_list=[test_stock],
        period='tick',
        start_time=start_time,
        end_time=end_time
    )

    if test_stock in tick_df_full:
        df_full = tick_df_full[test_stock]
        print(f"\n完整字段列表: {df_full.columns.tolist()}")
        print(f"\n数据形状: {df_full.shape}")
        print(f"\n前5条数据:")
        print(df_full.head())

        # 检查哪些字段有有效数据
        print(f"\n各字段非空值数量:")
        for col in df_full.columns:
            non_null = df_full[col].notna().sum()
            print(f"  {col}: {non_null}/{len(df_full)}")

        # 如果有lastPrice字段，使用它
        if 'lastPrice' in df_full.columns and df_full['lastPrice'].notna().sum() > 0:
            print(f"\n✅ 发现lastPrice字段！")
            print(f"lastPrice统计:")
            print(df_full['lastPrice'].describe())
            print(f"\nlastPrice前10条:")
            print(df_full['lastPrice'].head(10))

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)