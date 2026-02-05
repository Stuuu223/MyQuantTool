# -*- coding: utf-8 -*-
"""
QMT 实时数据验证脚本

用途：诊断 QMT Tick 数据的真实情况
运行环境：必须在 venv_qmt 虚拟环境中运行

作者: iFlow CLI
日期: 2026-02-05
"""

import xtquant.xtdata as xtdata
import numpy as np
from datetime import datetime

print("=" * 80)
print("🧪 QMT 实时数据验证测试")
print("=" * 80)

# 测试代码
code = "000001.SZ"

print(f"\n📍 测试股票: {code}")
print(f"🕐 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 测试 1: 尝试订阅
print(f"\n【测试 1】尝试订阅股票...")
try:
    xtdata.subscribe_quote([code])
    print("✅ 订阅成功")
except Exception as e:
    print(f"⚠️ 订阅失败: {e}")

# 测试 2: 获取完整 Tick 数据
print(f"\n【测试 2】获取完整 Tick 数据...")
tick_data = xtdata.get_full_tick([code])
print(f"📦 返回类型: {type(tick_data)}")
print(f"📦 返回内容: {tick_data}")

if tick_data and code in tick_data:
    data = tick_data[code]
    print(f"\n📊 Tick 数据详情:")
    print(f"  类型: {type(data)}")
    print(f"  内容: {data}")
    
    # 打印所有可用字段
    if hasattr(data, '__dict__'):
        print(f"\n  所有字段:")
        for key, value in data.__dict__.items():
            print(f"    {key}: {value}")
    elif isinstance(data, dict):
        print(f"\n  所有字段:")
        for key, value in data.items():
            print(f"    {key}: {value}")
    elif isinstance(data, np.ndarray):
        print(f"\n  数组形状: {data.shape}")
        print(f"  数组内容:\n{data}")
else:
    print(f"❌ 未获取到 Tick 数据")

# 测试 3: 获取分钟线数据
print(f"\n【测试 3】获取分钟线数据...")
today = datetime.now().strftime('%Y%m%d')
try:
    # 先下载
    print(f"  📥 下载今日数据...")
    xtdata.download_history_data(code, period='1m', start_time=today, end_time=today)
    
    # 获取本地数据
    print(f"  📦 获取本地数据...")
    minute_data = xtdata.get_local_data(
        stock_list=[code],
        field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
        period='1m',
        start_time=today,
        end_time=today
    )
    
    print(f"  返回类型: {type(minute_data)}")
    print(f"  返回内容: {minute_data}")
    
    if minute_data and code in minute_data:
        data = minute_data[code]
        print(f"\n  📊 分钟线数据详情:")
        print(f"    类型: {type(data)}")
        print(f"    形状: {data.shape if hasattr(data, 'shape') else 'N/A'}")
        
        if isinstance(data, np.ndarray) and data.ndim == 2:
            print(f"    最后一条记录: {data[-1]}")
            if data.shape[1] >= 6:
                volume = data[-1][5]  # volume 在第6列
                amount = data[-1][6] if data.shape[1] > 6 else 0
                print(f"    最新成交量: {volume}")
                print(f"    最新成交额: {amount}")
                if volume > 0:
                    vwap = amount / volume
                    print(f"    VWAP: {vwap:.2f}")
        elif isinstance(data, dict):
            print(f"    内容: {data}")
except Exception as e:
    print(f"❌ 分钟线数据获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 4: 获取日线数据
print(f"\n【测试 4】获取日线数据...")
try:
    daily_data = xtdata.get_local_data(
        stock_list=[code],
        field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
        period='1d',
        start_time=today,
        end_time=today
    )
    
    print(f"  返回类型: {type(daily_data)}")
    print(f"  返回内容: {daily_data}")
    
    if daily_data and code in daily_data:
        data = daily_data[code]
        print(f"\n  📊 日线数据详情:")
        print(f"    类型: {type(data)}")
        print(f"    内容: {data}")
except Exception as e:
    print(f"❌ 日线数据获取失败: {e}")

# 测试 5: 获取市场状态
print(f"\n【测试 5】检查 QMT 连接状态...")
try:
    stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"  ✅ QMT 连接正常，获取到 {len(stock_list)} 只股票")
except Exception as e:
    print(f"  ❌ QMT 连接异常: {e}")

print(f"\n" + "=" * 80)
print("🎯 诊断结论")
print("=" * 80)
print("\n请检查以下关键信息：")
print("1. Tick 数据的 volume 字段是否为 0？")
print("2. 分钟线数据是否有成交量？")
print("3. 如果两者都为 0，说明 QMT 端可能：")
print("   - 未登录实盘/模拟盘账户")
print("   - 未正确订阅股票")
print("   - 当前时间段无成交（非交易时间）")
print("\n如果 volume > 0，说明问题在三漏斗代码的数据解析逻辑。")
print("=" * 80)
