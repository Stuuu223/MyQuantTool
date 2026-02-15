使用QMT API读取tick数据
"""

import sys
from pathlib import Path
import pandas as pd
from xtquant import xtdata

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

print("=" * 80)
print("使用QMT API读取Tick数据")
print("=" * 80)

# 测试股票
test_stock = '600007.SH'
test_date = '2026-02-13'

print(f"\n测试股票: {test_stock}")
print(f"测试日期: {test_date}")

# 方法1: 尝试直接读取tick数据
print("\n" + "=" * 80)
print("方法1: 尝试直接读取tick数据")
print("=" * 80)

try:
    start_time = test_date.replace('-', '') + '093000'
    end_time = test_date.replace('-', '') + '150000'

    tick_df = xtdata.get_market_data_ex(
        field_list=['time', 'price', 'volume', 'amount'],
        stock_list=[test_stock],
        period='tick',
        start_time=start_time,
        end_time=end_time
    )

    if test_stock in tick_df and not tick_df[test_stock].empty:
        df = tick_df[test_stock]
        print(f"\n✅ 成功读取tick数据!")
        print(f"数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
        print(f"索引类型: {type(df.index)}")
        print(f"\n前10条数据:")
        print(df.head(10))
        print(f"\n数据类型:")
        print(df.dtypes)
    else:
        print("❌ 未能读取tick数据或数据为空")

except Exception as e:
    print(f"❌ 读取tick数据失败: {e}")
    import traceback
    traceback.print_exc()

# 方法2: 读取1分钟数据（作为对比）
print("\n" + "=" * 80)
print("方法2: 读取1分钟数据（作为对比）")
print("=" * 80)

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

    if test_stock in minute_df and not minute_df[test_stock].empty:
        df = minute_df[test_stock]
        print(f"\n✅ 成功读取分钟数据!")
        print(f"数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
        print(f"索引类型: {type(df.index)}")
        print(f"\n前10条数据:")
        print(df.head(10))
    else:
        print("❌ 未能读取分钟数据或数据为空")

except Exception as e:
    print(f"❌ 读取分钟数据失败: {e}")

# 方法3: 尝试从本地文件读取
print("\n" + "=" * 80)
print("方法3: 尝试从本地文件读取")
print("=" * 80)

try:
    tick_file = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir' / 'SH' / '0' / '600007' / test_date.replace('-', '')

    if tick_file.exists():
        print(f"\n✅ 找到本地tick文件: {tick_file}")
        print(f"文件大小: {tick_file.stat().st_size} 字节")

        # 尝试使用xtdata读取本地文件
        tick_df = xtdata.get_local_data(
            field_list=['time', 'price', 'volume', 'amount'],
            stock_list=[test_stock],
            period='tick',
            start_time=test_date.replace('-', '')
        )

        if tick_df and not tick_df.empty:
            print(f"\n✅ 成功从本地文件读取tick数据!")
            print(f"数据形状: {tick_df.shape}")
            print(f"列名: {tick_df.columns.tolist()}")
            print(f"\n前10条数据:")
            print(tick_df.head(10))
        else:
            print("❌ 从本地文件读取失败")
    else:
        print(f"❌ 未找到本地tick文件: {tick_file}")

except Exception as e:
    print(f"❌ 从本地文件读取失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
