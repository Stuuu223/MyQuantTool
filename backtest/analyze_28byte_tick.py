"""
详细分析28字节Tick数据格式
"""

import struct
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

minute_file = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / 'SH' / '60' / '600000.DAT'

print("=" * 80)
print("详细分析28字节Tick数据格式")
print("=" * 80)

with open(minute_file, 'rb') as f:
    data = f.read()

record_size = 28
num_records = len(data) // record_size

print(f"文件大小: {len(data)} 字节")
print(f"记录大小: {record_size} 字节")
print(f"记录数量: {num_records}")
print()

# 解析前20条记录
print("=" * 80)
print("前20条记录的详细解析")
print("=" * 80)

for i in range(min(20, num_records)):
    offset = i * record_size
    record = data[offset:offset + record_size]

    print(f"\n记录 {i+1}:")
    print(f"  原始数据 (hex): {record.hex()}")

    # 尝试解析
    # 基于hex dump的模式：feffffffffffff7f e803ac67 96280000 96280000 8c280000 8c280000 00000000
    # 可能的格式：
    # 位置0-7: 8字节（可能是时间戳或其他标识）
    # 位置8-11: 4字节整数
    # 位置12-15: 4字节整数
    # 位置16-19: 4字节整数
    # 位置20-23: 4字节整数
    # 位置24-27: 4字节整数

    try:
        # 前8字节
        val0_7 = struct.unpack('<Q', record[0:8])[0]
        print(f"  位置0-7: {val0_7}")

        # 尝试解释为时间戳
        try:
            dt = datetime.fromtimestamp(val0_7 / 1000.0)
            print(f"    -> 时间(÷1000): {dt}")
        except:
            pass

        # 后面4字节字段
        val8_11 = struct.unpack('<I', record[8:12])[0]
        val12_15 = struct.unpack('<I', record[12:16])[0]
        val16_19 = struct.unpack('<I', record[16:20])[0]
        val20_23 = struct.unpack('<I', record[20:24])[0]
        val24_27 = struct.unpack('<I', record[24:28])[0]

        print(f"  位置8-11: {val8_11}")
        print(f"  位置12-15: {val12_15}")
        print(f"  位置16-19: {val16_19}")
        print(f"  位置20-23: {val20_23}")
        print(f"  位置24-27: {val24_27}")

        # 尝试解释为价格（除以100）
        if 1 <= val8_11 / 100.0 <= 10000:
            print(f"    -> 价格(÷100): {val8_11 / 100.0:.2f}")
        if 1 <= val12_15 / 100.0 <= 10000:
            print(f"    -> 价格(÷100): {val12_15 / 100.0:.2f}")
        if 1 <= val16_19 / 100.0 <= 10000:
            print(f"    -> 价格(÷100): {val16_19 / 100.0:.2f}")
        if 1 <= val20_23 / 100.0 <= 10000:
            print(f"    -> 价格(÷100): {val20_23 / 100.0:.2f}")

        # 尝试解释为成交量
        if 0 < val8_11 < 100000000:
            print(f"    -> 成交量: {val8_11}")
        if 0 < val12_15 < 100000000:
            print(f"    -> 成交量: {val12_15}")

    except Exception as e:
        print(f"  解析错误: {e}")

# 统计分析
print("\n" + "=" * 80)
print("统计分析")
print("=" * 80)

# 分析第一个字段（0-7字节）
timestamps = []
for i in range(num_records):
    offset = i * record_size
    record = data[offset:offset + record_size]
    val = struct.unpack('<Q', record[0:8])[0]
    timestamps.append(val)

timestamps = sorted(timestamps)
print(f"\n位置0-7字段统计:")
print(f"  最小值: {min(timestamps)}")
print(f"  最大值: {max(timestamps)}")
print(f"  前五个: {timestamps[:5]}")
print(f"  后五个: {timestamps[-5:]}")

# 尝试转换为时间
print(f"\n时间转换测试:")
for ts in timestamps[:10]:
    try:
        dt = datetime.fromtimestamp(ts / 1000.0)
        print(f"  {ts} -> {dt} (毫秒)")
    except:
        try:
            dt = datetime.fromtimestamp(ts / 1000000.0)
            print(f"  {ts} -> {dt} (微秒)")
        except:
            pass

# 分析价格字段
print(f"\n价格字段分析（位置8-11, 除以100）:")
prices = []
for i in range(num_records):
    offset = i * record_size
    record = data[offset:offset + record_size]
    val = struct.unpack('<I', record[8:12])[0]
    price = val / 100.0
    if 1 <= price <= 10000:
        prices.append(price)

if prices:
    print(f"  有效价格数量: {len(prices)}")
    print(f"  价格范围: {min(prices):.2f} - {max(prices):.2f}")
    print(f"  前10个: {prices[:10]}")
    print(f"  后10个: {prices[-10:]}")

# 分析成交量字段
print(f"\n成交量字段分析（位置12-15）:")
volumes = []
for i in range(num_records):
    offset = i * record_size
    record = data[offset:offset + record_size]
    val = struct.unpack('<I', record[12:16])[0]
    if 0 < val < 100000000:
        volumes.append(val)

if volumes:
    print(f"  有效成交量数量: {len(volumes)}")
    print(f"  成交量范围: {min(volumes)} - {max(volumes)}")
    print(f"  前10个: {volumes[:10]}")
    print(f"  后10个: {volumes[-10:]}")

print()
print("=" * 80)
print("分析完成")
print("=" * 80)