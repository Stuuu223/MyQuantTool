"""
分析QMT Tick数据文件的原始格式
"""

import struct
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 选择一个股票的tick文件
tick_file = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / 'quotetimeinfo'

if not tick_file.exists():
    print(f"❌ 文件不存在: {tick_file}")
    exit(1)

print("=" * 80)
print("分析Tick数据文件格式")
print("=" * 80)
print(f"文件路径: {tick_file}")
print(f"文件大小: {tick_file.stat().st_size} 字节")
print()

with open(tick_file, 'rb') as f:
    data = f.read()

print(f"读取了 {len(data)} 字节")
print()

# 尝试不同的解析方式
print("=" * 80)
print("方式1: 假设每条记录32字节（原始代码的假设）")
print("=" * 80)

record_size = 32
num_records = len(data) // record_size

print(f"记录数量: {num_records}")
print()

if num_records > 0:
    print("前5条记录:")
    for i in range(min(5, num_records)):
        offset = i * record_size
        record = data[offset:offset + record_size]

        # 按原始代码的格式解析
        timestamp_ms = struct.unpack('<Q', record[0:8])[0]
        volume = struct.unpack('<I', record[8:12])[0]
        amount = struct.unpack('<I', record[12:16])[0]
        price_raw = struct.unpack('<I', record[16:20])[0]
        price = price_raw / 10000.0
        direction = struct.unpack('<B', record[20:21])[0]

        print(f"  记录{i+1}:")
        print(f"    时间戳(ms): {timestamp_ms}")
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
            print(f"    转换时间: {dt}")
        except:
            print(f"    转换时间: 无效时间戳")
        print(f"    成交量: {volume}")
        print(f"    成交额: {amount}")
        print(f"    价格原始值: {price_raw}")
        print(f"    价格: {price}")
        print(f"    方向: {direction}")
        print(f"    原始字节(hex): {record[:24].hex()}")
        print()

print("=" * 80)
print("方式2: 分析原始字节的十六进制")
print("=" * 80)

# 显示前256字节的hex dump
hex_data = data[:256]
print("前256字节（Hex Dump）:")
for i in range(0, len(hex_data), 16):
    hex_str = ' '.join(f'{b:02x}' for b in hex_data[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in hex_data[i:i+16])
    print(f"{i:04x}: {hex_str:<48} {ascii_str}")

print()

print("=" * 80)
print("方式3: 尝试解析为QMT的tick格式（可能的不同格式）")
print("=" * 80)

# QMT可能有多种tick格式，尝试其他可能性
print("尝试其他可能的格式...")

# 格式1: 20字节格式
record_size_20 = 20
if len(data) >= record_size_20:
    print("\n格式A - 20字节记录:")
    for i in range(min(3, len(data) // record_size_20)):
        offset = i * record_size_20
        record = data[offset:offset + record_size_20]

        # 尝试解析
        try:
            time_ms = struct.unpack('<Q', record[0:8])[0]
            price_int = struct.unpack('<I', record[8:12])[0]
            volume = struct.unpack('<I', record[12:16])[0]
            # price = price_int / 100.0  # 尝试除以100

            print(f"  记录{i+1}: 时间={datetime.fromtimestamp(time_ms/1000)}, "
                  f"价格={price_int}, 成交量={volume}, hex={record.hex()[:40]}")
        except:
            pass

# 格式2: 16字节格式
record_size_16 = 16
if len(data) >= record_size_16:
    print("\n格式B - 16字节记录:")
    for i in range(min(3, len(data) // record_size_16)):
        offset = i * record_size_16
        record = data[offset:offset + record_size_16]

        try:
            time_ms = struct.unpack('<Q', record[0:8])[0]
            price_int = struct.unpack('<I', record[8:12])[0]
            volume = struct.unpack('<I', record[12:16])[0]

            print(f"  记录{i+1}: 时间={datetime.fromtimestamp(time_ms/1000)}, "
                  f"价格={price_int}, 成交量={volume}, hex={record.hex()}")
        except:
            pass

# 查看是否有其他文件结构
print("\n" + "=" * 80)
print("查找其他tick数据文件")
print("=" * 80)

tick_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir'

# 查找SH和SZ目录下的tick文件
for market in ['SH', 'SZ']:
    market_dir = tick_dir / market / '0'
    if market_dir.exists():
        print(f"\n{market}目录下的股票:")
        stock_dirs = list(market_dir.iterdir())[:3]  # 只看前3个
        for stock_dir in stock_dirs:
            if stock_dir.is_dir():
                files = list(stock_dir.iterdir())
                print(f"  {stock_dir.name}: {len(files)} 个文件")
                if files:
                    print(f"    示例文件: {files[0].name}, 大小: {files[0].stat().st_size} 字节")

print()
print("=" * 80)
print("分析完成")
print("=" * 80)