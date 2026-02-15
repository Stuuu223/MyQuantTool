"""
详细分析36字节格式的Tick数据
"""

import struct
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

tick_file = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / 'SH' / '0' / '600007' / '20251114'

print("=" * 80)
print("详细分析36字节Tick格式")
print("=" * 80)

with open(tick_file, 'rb') as f:
    data = f.read()

record_size = 36
num_records = len(data) // record_size

print(f"文件大小: {len(data)} 字节")
print(f"记录大小: {record_size} 字节")
print(f"记录数量: {num_records}")
print()

# 解析前10条记录
print("=" * 80)
print("前10条记录的详细解析")
print("=" * 80)

for i in range(min(10, num_records)):
    offset = i * record_size
    record = data[offset:offset + record_size]

    print(f"\n记录 {i+1}:")
    print(f"  原始数据 (hex): {record.hex()}")

    # 尝试解析每个4字节块
    for j in range(0, record_size, 4):
        chunk = record[j:j+4]
        value = struct.unpack('<I', chunk)[0]

        # 尝试解释为价格
        price_100 = value / 100.0
        price_10000 = value / 10000.0

        # 检查是否可能是价格（1-1000范围）
        if 1 <= price_100 <= 1000 or 1 <= price_10000 <= 1000:
            print(f"  位置 {j}-{j+3}: 值={value:10d}, 价格(÷100)={price_100:7.2f}, 价格(÷10000)={price_10000:7.4f}")
        elif value < 1000000000:  # 忽略过大的时间戳值
            print(f"  位置 {j}-{j+3}: 值={value:10d}")

    # 尝试将前8字节作为时间戳
    timestamp = struct.unpack('<Q', record[0:8])[0]
    print(f"  时间戳(8字节): {timestamp}")
    try:
        dt = datetime.fromtimestamp(timestamp / 1000.0)  # 假设是毫秒
        print(f"  转换时间(÷1000): {dt}")
    except:
        pass

    try:
        dt = datetime.fromtimestamp(timestamp / 1000000.0)  # 假设是微秒
        print(f"  转换时间(÷1000000): {dt}")
    except:
        pass

# 统计分析
print("\n" + "=" * 80)
print("统计分析")
print("=" * 80)

# 提取所有记录的前8字节作为时间戳
timestamps = []
for i in range(num_records):
    offset = i * record_size
    record = data[offset:offset + record_size]
    timestamp = struct.unpack('<Q', record[0:8])[0]
    timestamps.append(timestamp)

# 统计时间戳
timestamps = sorted(timestamps)
print(f"\n时间戳统计:")
print(f"  最小值: {min(timestamps)}")
print(f"  最大值: {max(timestamps)}")
print(f"  前三个: {timestamps[:3]}")
print(f"  后三个: {timestamps[-3:]}")

# 尝试转换时间戳
print(f"\n时间戳转换测试:")
for ts in timestamps[:5]:
    try:
        dt_ms = datetime.fromtimestamp(ts / 1000.0)
        print(f"  {ts} -> {dt_ms} (毫秒)")
    except:
        pass

    try:
        dt_us = datetime.fromtimestamp(ts / 1000000.0)
        print(f"  {ts} -> {dt_us} (微秒)")
    except:
        pass

# 查找可能的价格字段
print(f"\n价格字段分析:")
for j in range(0, record_size, 4):
    values = []
    for i in range(num_records):
        offset = i * record_size
        record = data[offset:offset + record_size]
        value = struct.unpack('<I', record[j:j+4])[0]
        values.append(value)

    # 过滤出可能是价格的值（1-1000范围内）
    prices_100 = [v / 100.0 for v in values if 1 <= v / 100.0 <= 1000]
    prices_10000 = [v / 10000.0 for v in values if 1 <= v / 10000.0 <= 1000]

    if prices_100:
        print(f"  位置 {j}-{j+3} (除以100):")
        print(f"    数量: {len(prices_100)}")
        print(f"    范围: {min(prices_100):.2f} - {max(prices_100):.2f}")
        print(f"    示例值: {prices_100[:5]}")

    if prices_10000:
        print(f"  位置 {j}-{j+3} (除以10000):")
        print(f"    数量: {len(prices_10000)}")
        print(f"    范围: {min(prices_10000):.4f} - {max(prices_10000):.4f}")
        print(f"    示例值: {prices_10000[:5]}")

# 查找成交量字段
print(f"\n成交量字段分析（整数范围）:")
for j in range(0, record_size, 4):
    values = []
    for i in range(min(1000, num_records)):  # 只分析前1000条
        offset = i * record_size
        record = data[offset:offset + record_size]
        value = struct.unpack('<I', record[j:j+4])[0]
        values.append(value)

    # 过滤出可能是成交量的值（合理范围）
    volumes = [v for v in values if v > 0 and v < 1000000000]  # 合理的成交量范围

    if volumes:
        print(f"  位置 {j}-{j+3}:")
        print(f"    数量: {len(volumes)}")
        print(f"    范围: {min(volumes)} - {max(volumes)}")
        print(f"    示例值: {volumes[:5]}")

print()
print("=" * 80)
print("分析完成")
print("=" * 80)