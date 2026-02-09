#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试最近交易日的分钟数据"""

import sys
sys.path.append('E:/MyQuantTool')

from xtquant import xtdata

print("=" * 60)
print("测试最近交易日分钟数据")
print("=" * 60)

# 测试股票
test_stock = '600519.SH'
test_date = '20250207'  # 假设这是一个交易日

print(f"📊 测试股票: {test_stock}")
print(f"📅 测试日期: {test_date}")

# 测试 1 分钟 K 线
print("\n📈 测试 1 分钟 K 线...")
try:
    xtdata.download_history_data(
        stock_code=test_stock,
        period='1m',
        start_time=test_date,
        end_time=test_date
    )
    print("✅ 下载成功")
    
    # 读取数据
    data = xtdata.get_local_data(
        field_list=['time', 'open', 'high', 'low', 'close', 'volume'],
        stock_list=[test_stock],
        period='1m',
        start_time=test_date,
        end_time=test_date,
        count=-1
    )
    
    if data and test_stock in data:
        df = data[test_stock]
        print(f"✅ 读取到 {len(df)} 条记录")
        if len(df) > 0:
            print(f"时间范围: {df.iloc[0]['time']} ~ {df.iloc[-1]['time']}")
            print(f"价格范围: {df['low'].min():.2f} ~ {df['high'].max():.2f}")
            print(f"最新价格: {df.iloc[-1]['close']:.2f}")
    else:
        print("❌ 无数据")
except Exception as e:
    print(f"❌ 失败: {e}")

# 测试 5 分钟 K 线
print("\n📈 测试 5 分钟 K 线...")
try:
    xtdata.download_history_data(
        stock_code=test_stock,
        period='5m',
        start_time=test_date,
        end_time=test_date
    )
    print("✅ 下载成功")
    
    # 读取数据
    data = xtdata.get_local_data(
        field_list=['time', 'open', 'high', 'low', 'close', 'volume'],
        stock_list=[test_stock],
        period='5m',
        start_time=test_date,
        end_time=test_date,
        count=-1
    )
    
    if data and test_stock in data:
        df = data[test_stock]
        print(f"✅ 读取到 {len(df)} 条记录")
    else:
        print("❌ 无数据")
except Exception as e:
    print(f"❌ 失败: {e}")

# 检查数据目录
print("\n📁 检查数据目录...")
import os
sh_1m_dir = r"E:\qmt\userdata_mini\datadir\SH\60"
sh_5m_dir = r"E:\qmt\userdata_mini\datadir\SH\300"

if os.path.exists(sh_1m_dir):
    files = [f for f in os.listdir(sh_1m_dir) if f.endswith('.DAT')]
    print(f"✅ 1分钟目录存在: {len(files)} 个文件")
else:
    print(f"❌ 1分钟目录不存在")

if os.path.exists(sh_5m_dir):
    files = [f for f in os.listdir(sh_5m_dir) if f.endswith('.DAT')]
    print(f"✅ 5分钟目录存在: {len(files)} 个文件")
else:
    print(f"❌ 5分钟目录不存在")

print("\n" + "=" * 60)