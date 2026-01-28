#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 QMT 历史数据获取功能（简化版）
直接使用 xtdata 接口，绕过 qmt_manager
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 动态加载 xtdata
import importlib.util

# 添加 xtquant 目录到 Python 路径
xtquant_path = os.path.join(project_root, 'xtquant')
if xtquant_path not in sys.path:
    sys.path.insert(0, xtquant_path)

# 加载 xtbson 模块
xtbson_spec = importlib.util.spec_from_file_location(
    "xtquant.xtbson",
    os.path.join(xtquant_path, "xtbson", "__init__.py")
)
xtbson_module = importlib.util.module_from_spec(xtbson_spec)
xtbson_spec.loader.exec_module(xtbson_module)
sys.modules['xtquant.xtbson'] = xtbson_module

# 加载 xtdata_config 模块
xtdata_config_spec = importlib.util.spec_from_file_location(
    "xtquant.xtdata_config",
    os.path.join(xtquant_path, "xtdata_config.py")
)
xtdata_config_module = importlib.util.module_from_spec(xtdata_config_spec)
xtdata_config_spec.loader.exec_module(xtdata_config_module)
sys.modules['xtquant.xtdata_config'] = xtdata_config_module

# 加载 IPythonApiClient 模块
ipython_api_spec = importlib.util.spec_from_file_location(
    "xtquant.IPythonApiClient",
    os.path.join(xtquant_path, "IPythonApiClient.py")
)
ipython_api_module = importlib.util.module_from_spec(ipython_api_spec)
ipython_api_spec.loader.exec_module(ipython_api_module)
sys.modules['xtquant.IPythonApiClient'] = ipython_api_module

# 加载 xtdata 模块
xtdata_spec = importlib.util.spec_from_file_location(
    "xtquant.xtdata",
    os.path.join(xtquant_path, "xtdata.py")
)
xtdata = importlib.util.module_from_spec(xtdata_spec)
xtdata_spec.loader.exec_module(xtdata)
sys.modules['xtquant.xtdata'] = xtdata

print("=" * 70)
print("🧪 测试 QMT 历史数据获取功能（简化版）")
print("=" * 70)
print()

# 测试股票代码
test_stocks = ['000001.SZ', '600519.SH', '000858.SZ']

print("-" * 70)
print("📊 开始测试历史数据获取...")
print("-" * 70)
print()

for stock_code in test_stocks:
    print(f"📍 测试股票: {stock_code}")

    try:
        # 获取历史数据
        data = xtdata.get_market_data_ex(
            stock_list=[stock_code],
            period='1d',
            start_time='20240101',
            end_time='',
            count=-1,
            dividend_type='front',
            fill_data=True
        )

        # 检查数据
        if data and stock_code in data and data[stock_code] is not None:
            df = data[stock_code]

            print(f"  ✅ 成功获取 {len(df)} 条历史数据")

            # 显示最新数据
            df.reset_index(inplace=True)
            if 'time' in df.columns:
                print(f"  - 时间范围: {df['time'].iloc[0]} 到 {df['time'].iloc[-1]}")
            if 'close' in df.columns:
                print(f"  - 最新收盘价: {df['close'].iloc[-1]:.2f}")
            print(f"  - 数据列: {list(df.columns)}")
        else:
            print(f"  ❌ 获取失败：数据为空")

    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
        import traceback
        traceback.print_exc()

    print()

print("-" * 70)
print("✅ 测试完成")
print("-" * 70)
print()
print("📝 说明：")
print("  - 如果所有股票都成功获取数据，说明 QMT 接口工作正常")
print("  - 速度应该很快（0.1秒以内）")
print()