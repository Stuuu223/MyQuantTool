#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 QMT 接口和数据目录"""

import sys
sys.path.append('E:/MyQuantTool')

print("测试 QMT 接口")
print("=" * 50)

# 测试 1: 加载 QMT
try:
    from xtquant import xtdata
    print("✅ QMT 接口加载成功")
except ImportError as e:
    print(f"❌ QMT 接口加载失败: {e}")
    print("\n请确保:")
    print("  1. QMT 客户端已安装")
    print("  2. xtquant 库已正确安装")
    print("  3. QMT 客户端正在运行")
    sys.exit(1)

# 测试 2: 获取数据目录
print("\n" + "=" * 50)
print("检查 QMT 数据目录")
print("=" * 50)
try:
    data_dir = xtdata.get_data_dir()
    print(f"📁 数据目录: {data_dir}")
    
    import os
    if os.path.exists(data_dir):
        print("✅ 数据目录存在")
        
        # 检查目录大小
        total_size = 0
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
        
        print(f"📊 目录大小: {total_size / (1024*1024):.2f} MB")
        
        # 列出部分文件
        files_found = []
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                files_found.append(os.path.join(root, file))
                if len(files_found) >= 10:
                    break
            if len(files_found) >= 10:
                break
        
        if files_found:
            print(f"\n📁 部分文件:")
            for file in files_found[:10]:
                print(f"  - {file}")
            if len(files_found) > 10:
                print(f"  ... 还有 {len(files_found) - 10} 个文件")
    else:
        print("❌ 数据目录不存在")
except Exception as e:
    print(f"❌ 获取数据目录失败: {e}")

# 测试 3: 测试数据下载（小范围）
print("\n" + "=" * 50)
print("测试数据下载")
print("=" * 50)

test_stock = "600519.SH"
test_period = "1d"
test_start = "20240101"
test_end = "20240110"

print(f"测试股票: {test_stock}")
print(f"测试周期: {test_period}")
print(f"测试时间: {test_start} - {test_end}")

try:
    from logic.code_converter import CodeConverter
    code_converter = CodeConverter()
    
    qmt_code = code_converter.to_qmt(test_stock)
    print(f"QMT 代码: {qmt_code}")
    
    # 下载数据
    print("\n📥 开始下载数据...")
    xtdata.download_history_data(
        stock_code=qmt_code,
        period=test_period,
        start_time=test_start,
        end_time=test_end
    )
    print("✅ 下载成功")
    
    # 验证数据
    print("\n🔍 验证数据...")
    data = xtdata.get_local_data(
        field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=[qmt_code],
        period=test_period,
        start_time=test_start,
        end_time=test_end,
        count=-1
    )
    
    if data and qmt_code in data:
        df = data[qmt_code]
        print(f"✅ 验证成功: {len(df)} 条记录")
        print("\n数据预览:")
        print(df.head())
    else:
        print("❌ 验证失败: 数据为空")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
