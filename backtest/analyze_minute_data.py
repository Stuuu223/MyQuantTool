"""
分析分钟数据文件格式
"""

import struct
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 选择一个股票的分钟数据文件
minute_file = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / 'SH' / '60' / '600000.DAT'

print("=" * 80)
print("分析分钟数据文件格式")
print("=" * 80)
print(f"文件路径: {minute_file}")
print(f"文件大小: {minute_file.stat().st_size} 字节")
print()

with open(minute_file, 'rb') as f:
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

# 常见的分钟数据记录大小
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

# 尝试32字节格式（常见的分钟数据格式）
record_size = 32
if len(data) % record_size == 0:
    print("\n" + "=" * 80)
    print(f"尝试解析 {record_size} 字节分钟数据格式")
    print("=" * 80)

    num_records = len(data) // record_size

    # 解析前10条记录
    for i in range(min(10, num_records)):
        offset = i * record_size
        record = data[offset:offset + record_size]

        print(f"\n记录 {i+1} (hex: {record.hex()})")

        # 尝试多种解析方式

        # 方式1: 时间(4) + 毫秒(2) + 开(4) + 高(4) + 低(4) + 收(4) + 量(4) + 额(4)
        try:
            time_s = struct.unpack('<I', record[0:4])[0]
            time_ms = struct.unpack('<H', record[4:6])[0]
            open_p = struct.unpack('<I', record[6:10])[0] / 100.0
            high_p = struct.unpack('<I', record[10:14])[0] / 100.0
            low_p = struct.unpack('<I', record[14:18])[0] / 100.0
            close_p = struct.unpack('<I', record[18:22])[0] / 100.0
            volume = struct.unpack('<I', record[22:26])[0]
            amount = struct.unpack('<I', record[26:30])[0]

            dt = datetime.fromtimestamp(time_s)
            print(f"  方式1: {dt}.{time_ms:03d}, O={open_p:.2f}, H={high_p:.2f}, "
                  f"L={low_p:.2f}, C={close_p:.2f}, V={volume}, A={amount}")
        except:
            pass

        # 方式2: 时间(4) + 开(4) + 高(4) + 低(4) + 收(4) + 量(4) + 额(4) + 其他(4)
        try:
            time_s = struct.unpack('<I', record[0:4])[0]
            open_p = struct.unpack('<I', record[4:8])[0] / 100.0
            high_p = struct.unpack('<I', record[8:12])[0] / 100.0
            low_p = struct.unpack('<I', record[12:16])[0] / 100.0
            close_p = struct.unpack('<I', record[16:20])[0] / 100.0
            volume = struct.unpack('<I', record[20:24])[0]
            amount = struct.unpack('<I', record[24:28])[0]

            dt = datetime.fromtimestamp(time_s)
            print(f"  方式2: {dt}, O={open_p:.2f}, H={high_p:.2f}, "
                  f"L={low_p:.2f}, C={close_p:.2f}, V={volume}, A={amount}")
        except:
            pass

        # 方式3: 时间(8) + 开(4) + 高(4) + 低(4) + 收(4) + 量(4) + 额(4)
        try:
            time_ms = struct.unpack('<Q', record[0:8])[0]
            open_p = struct.unpack('<I', record[8:12])[0] / 100.0
            high_p = struct.unpack('<I', record[12:16])[0] / 100.0
            low_p = struct.unpack('<I', record[16:20])[0] / 100.0
            close_p = struct.unpack('<I', record[20:24])[0] / 100.0
            volume = struct.unpack('<I', record[24:28])[0]
            amount = struct.unpack('<I', record[28:32])[0]

            dt = datetime.fromtimestamp(time_ms / 1000.0)
            print(f"  方式3: {dt}, O={open_p:.2f}, H={high_p:.2f}, "
                  f"L={low_p:.2f}, C={close_p:.2f}, V={volume}, A={amount}")
        except:
            pass

print()
print("=" * 80)
print("分析完成")
print("=" * 80)