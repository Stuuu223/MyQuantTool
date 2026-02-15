"""
分析真实的QMT Tick数据文件
"""

import struct
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 选择一个股票的tick文件（600007.SH在20251114的数据）
tick_file = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / 'SH' / '0' / '600007' / '20251114'

if not tick_file.exists():
    print(f"❌ 文件不存在: {tick_file}")
    # 尝试找其他文件
    tick_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / 'SH' / '0'
    if tick_dir.exists():
        stock_dir = list(tick_dir.iterdir())[0]
        if stock_dir.is_dir():
            files = list(stock_dir.iterdir())
            if files:
                tick_file = files[0]
                print(f"✅ 使用替代文件: {tick_file}")
            else:
                print("❌ 没有找到tick数据文件")
                exit(1)
    else:
        exit(1)

print("=" * 80)
print("分析真实的Tick数据文件")
print("=" * 80)
print(f"文件路径: {tick_file}")
print(f"文件大小: {tick_file.stat().st_size} 字节")
print()

with open(tick_file, 'rb') as f:
    data = f.read()

print(f"读取了 {len(data)} 字节")
print()

# 显示前256字节的hex dump
print("=" * 80)
print("前256字节（Hex Dump）")
print("=" * 80)

hex_data = data[:256]
for i in range(0, len(hex_data), 16):
    hex_str = ' '.join(f'{b:02x}' for b in hex_data[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in hex_data[i:i+16])
    print(f"{i:04x}: {hex_str:<48} {ascii_str}")

print()

# 尝试不同的记录大小
print("=" * 80)
print("尝试不同的记录大小")
print("=" * 80)

# 常见的tick数据记录大小
possible_sizes = [16, 20, 24, 28, 32, 36, 40, 48, 64]

for record_size in possible_sizes:
    if len(data) % record_size == 0:
        num_records = len(data) // record_size
        print(f"\n记录大小: {record_size} 字节 -> {num_records} 条记录")

        # 显示前3条记录的hex
        for i in range(min(3, num_records)):
            offset = i * record_size
            record = data[offset:offset + record_size]
            print(f"  记录{i+1}: {record.hex()[:record_size*2]}")

# 分析QMT可能使用的格式
print("\n" + "=" * 80)
print("尝试解析QMT tick格式")
print("=" * 80)

# QMT tick数据通常的格式猜测
# 参考：QMT的tick数据通常包含：时间、价格、成交量、买卖方向等

# 尝试20字节格式
record_size = 20
if len(data) >= record_size:
    print(f"\n尝试 {record_size} 字节格式:")
    for i in range(min(5, len(data) // record_size)):
        offset = i * record_size
        record = data[offset:offset + record_size]

        # 尝试多种解析方式
        print(f"\n  记录{i+1} (hex: {record.hex()})")

        # 方式1: 时间(8) + 价格(4) + 成交量(4) + 其他(4)
        try:
            time_ms = struct.unpack('<Q', record[0:8])[0]
            price_int = struct.unpack('<I', record[8:12])[0]
            volume = struct.unpack('<I', record[12:16])[0]
            direction = struct.unpack('<I', record[16:20])[0]

            # 价格可能需要除以100或10000
            price1 = price_int / 100.0
            price2 = price_int / 10000.0

            print(f"    方式1: 时间戳={time_ms}, 价格={price1:.2f}(除100)或{price2:.4f}(除10000), "
                  f"成交量={volume}, 方向={direction}")
        except:
            pass

        # 方式2: 时间(4) + 毫秒(2) + 价格(4) + 成交量(4) + 其他(6)
        try:
            time_s = struct.unpack('<I', record[0:4])[0]
            time_ms = struct.unpack('<H', record[4:6])[0]
            price_int = struct.unpack('<I', record[6:10])[0]
            volume = struct.unpack('<I', record[10:14])[0]

            dt = datetime.fromtimestamp(time_s)
            price = price_int / 100.0

            print(f"    方式2: 时间={dt}.{time_ms:03d}, 价格={price:.2f}, 成交量={volume}")
        except:
            pass

# 尝试32字节格式（原始代码使用的）
record_size = 32
if len(data) >= record_size and len(data) % record_size == 0:
    print(f"\n尝试 {record_size} 字节格式（原始代码使用的）:")
    for i in range(min(3, len(data) // record_size)):
        offset = i * record_size
        record = data[offset:offset + record_size]

        print(f"\n  记录{i+1} (hex: {record.hex()[:64]})")

        # 原始代码的解析方式
        try:
            timestamp_ms = struct.unpack('<Q', record[0:8])[0]
            volume = struct.unpack('<I', record[8:12])[0]
            amount = struct.unpack('<I', record[12:16])[0]
            price_raw = struct.unpack('<I', record[16:20])[0]
            direction = struct.unpack('<B', record[20:21])[0]

            price = price_raw / 10000.0

            print(f"    原始解析: 时间戳={timestamp_ms}, 价格={price:.2f}, "
                  f"成交量={volume}, 成交额={amount}, 方向={direction}")
        except:
            pass

        # 尝试另一种32字节解析
        try:
            time_s = struct.unpack('<I', record[0:4])[0]
            time_ms = struct.unpack('<I', record[4:8])[0]
            price_raw = struct.unpack('<I', record[8:12])[0]
            volume = struct.unpack('<I', record[12:16])[0]
            amount = struct.unpack('<Q', record[16:24])[0]

            price = price_raw / 100.0

            dt = datetime.fromtimestamp(time_s)
            print(f"    新解析方式: 时间={dt}.{time_ms:06d}, 价格={price:.2f}, "
                  f"成交量={volume}, 成交额={amount}")
        except:
            pass

# 查看是否有重复的模式
print("\n" + "=" * 80)
print("查找数据模式")
print("=" * 80)

# 查找可能的价格范围（通常股票价格在1-1000之间）
print("\n查找可能的价格字段（1-1000范围）:")

# 尝试将数据解释为4字节整数
for i in range(0, min(100, len(data)), 4):
    try:
        value = struct.unpack('<I', data[i:i+4])[0]
        price1 = value / 100.0
        price2 = value / 10000.0

        if 1 <= price1 <= 1000:
            print(f"  位置{i-8}到{i-1}: 值={value}, 价格(除100)={price1:.2f}")
        elif 1 <= price2 <= 1000:
            print(f"  位置{i-8}到{i-1}: 值={value}, 价格(除10000)={price2:.4f}")
    except:
        pass

print()
print("=" * 80)
print("分析完成")
print("=" * 80)