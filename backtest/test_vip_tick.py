# -*- coding: utf-8 -*-
"""
使用VIP Token连接QMT并读取Tick数据
"""

import sys
from pathlib import Path
from xtquant import xtdata
from xtquant import xtdatacenter as xtdc
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# VIP配置
VIP_TOKEN = '6b1446e317ed67596f13d2e808291a01e0dd9839'
DATA_DIR = PROJECT_ROOT / 'data' / 'qmt_data'

print("=" * 80)
print("使用VIP Token连接QMT读取Tick数据")
print("=" * 80)
print(f"VIP Token: {VIP_TOKEN}")
print(f"数据目录: {DATA_DIR}")
print()

# 设置数据目录
DATA_DIR.mkdir(parents=True, exist_ok=True)
xtdc.set_data_home_dir(str(DATA_DIR))

# 设置VIP Token
xtdc.set_token(VIP_TOKEN)

# 初始化
print("正在初始化QMT数据服务...")
xtdc.init()
print("✅ QMT数据服务初始化完成")
print()

# 连接到VIP站点
print("正在连接到VIP站点...")
try:
    # 尝试不同的连接方式
    # 方式1: 使用xtdatacenter连接
    session_id = xtdc.connect(port=(58620, 58630))
    print(f"✅ 通过xtdatacenter连接成功，监听端口: {session_id}")
except Exception as e:
    print(f"⚠️  xtdatacenter连接失败: {e}")
    print("尝试直接使用xtdata...")
    try:
        # 方式2: 直接使用xtdata（可能已经自动连接）
        session_id = 123456
        print(f"✅ 使用默认连接方式")
    except:
        print("❌ 连接失败")
        session_id = None

print()

# 测试股票
test_stock = '600007.SH'
test_date = '2026-02-13'

print("=" * 80)
print(f"测试股票: {test_stock}")
print(f"测试日期: {test_date}")
print("=" * 80)

# 方法1: 尝试读取tick数据
print("\n方法1: 尝试读取tick数据")
print("-" * 80)

try:
    start_time = test_date.replace('-', '') + '093000'
    end_time = test_date.replace('-', '') + '150000'

    print(f"请求参数: period='tick', start_time={start_time}, end_time={end_time}")

    tick_df = xtdata.get_market_data_ex(
        field_list=['time', 'price', 'volume', 'amount'],
        stock_list=[test_stock],
        period='tick',
        start_time=start_time,
        end_time=end_time
    )

    print(f"返回结果类型: {type(tick_df)}")
    print(f"返回结果keys: {tick_df.keys() if isinstance(tick_df, dict) else 'N/A'}")

    if isinstance(tick_df, dict) and test_stock in tick_df and not tick_df[test_stock].empty:
        df = tick_df[test_stock]
        print(f"\n✅ 成功读取tick数据!")
        print(f"数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
        print(f"索引类型: {type(df.index)}")
        print(f"索引示例: {df.index[:5].tolist()}")
        print(f"\n前10条数据:")
        print(df.head(10))
        print(f"\n数据类型:")
        print(df.dtypes)
        print(f"\n统计信息:")
        print(df.describe())
    else:
        print(f"❌ 未能读取tick数据或数据为空")
        if isinstance(tick_df, dict):
            print(f"返回的字典包含: {list(tick_df.keys())}")

except Exception as e:
    print(f"❌ 读取tick数据失败: {e}")
    import traceback
    traceback.print_exc()

# 方法2: 读取1分钟数据（对比）
print("\n\n方法2: 读取1分钟数据（对比）")
print("-" * 80)

try:
    start_time = test_date.replace('-', '') + '093000'
    end_time = test_date.replace('-', '') + '150000'

    minute_df = xtdata.get_market_data_ex(
        field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=[test_stock],
        period='1m',
        start_time=start_time,
        end_time=end_time
    )

    if isinstance(minute_df, dict) and test_stock in minute_df and not minute_df[test_stock].empty:
        df = minute_df[test_stock]
        print(f"\n✅ 成功读取分钟数据!")
        print(f"数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
        print(f"索引类型: {type(df.index)}")
        print(f"\n前10条数据:")
        print(df.head(10))
    else:
        print(f"❌ 未能读取分钟数据或数据为空")

except Exception as e:
    print(f"❌ 读取分钟数据失败: {e}")

# 方法3: 尝试下载tick数据到本地
print("\n\n方法3: 下载tick数据到本地")
print("-" * 80)

try:
    start_time = '20260213093000'
    end_time = '20260213150000'

    print(f"下载参数: period='tick', start_time={start_time}, end_time={end_time}")

    result = xtdata.download_history_data(
        stock_list=[test_stock],
        period='tick',
        start_time=start_time,
        end_time=end_time
    )

    print(f"下载结果: {result}")
    print(f"✅ tick数据下载完成")

except Exception as e:
    print(f"❌ 下载tick数据失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
