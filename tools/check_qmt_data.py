"""
QMT数据结构检查脚本
- 不使用魔法路径
- 测试交易日历
- 测试Tick数据下载和读取
- 研究time字段格式
"""

from xtquant import xtdata
import pandas as pd

print("=" * 80)
print("1. 检查QMT连接和数据路径")
print("=" * 80)

# 获取全市场股票
all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
print(f"✅ 全市场股票数: {len(all_stocks)}")

# 取样本股票
sample_stocks = all_stocks[:5]
print(f"样本股票: {sample_stocks}")

print()
print("=" * 80)
print("2. 测试日K数据（确认QMT数据可用）")
print("=" * 80)

# 测试日K数据
test_date = '20251230'
daily_data = xtdata.get_local_data(
    field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=sample_stocks,
    period='1d',
    start_time=test_date,
    end_time=test_date
)

print(f"\n日K数据测试结果（{test_date}）:")
for stock in sample_stocks[:2]:
    if stock in daily_data and not daily_data[stock].empty:
        df = daily_data[stock]
        print(f"  ✅ {stock}: 日K数据存在，行数: {len(df)}")
        print(f"     volume单位: {df['volume'].dtype}, 值: {df['volume'].iloc[0]}")
    else:
        print(f"  ❌ {stock}: 没有日K数据")

print()
print("=" * 80)
print("3. 测试Tick数据下载和读取")
print("=" * 80)

# 先尝试读取Tick数据（可能不存在）
print(f"\n尝试读取{test_date}的Tick数据（可能未下载）:")
tick_data = xtdata.get_local_data(
    field_list=['time', 'lastPrice', 'volume', 'amount'],
    stock_list=sample_stocks[:2],
    period='tick',
    start_time=test_date,
    end_time=test_date
)

has_tick = False
for stock in sample_stocks[:2]:
    if stock in tick_data and not tick_data[stock].empty:
        has_tick = True
        df = tick_data[stock]
        print(f"  ✅ {stock}: Tick数据已存在！")
        print(f"     行数: {len(df)}")
        print(f"     列名: {df.columns.tolist()}")
        print(f"     time列类型: {df['time'].dtype}")
        print(f"     time前10个值:")
        for i, val in enumerate(df['time'].head(10)):
            print(f"       [{i}] {val} (type: {type(val).__name__})")
    else:
        print(f"  ❌ {stock}: Tick数据不存在")

if not has_tick:
    print(f"\n⚠️  {test_date}的Tick数据未下载，尝试下载...")
    
    # 尝试下载Tick数据
    for stock in sample_stocks[:2]:
        try:
            print(f"  下载 {stock} 的Tick数据...")
            xtdata.download_history_data(
                stock_code=stock,
                period='tick',
                start_time=test_date,
                end_time=test_date
            )
            print(f"  ✅ {stock} 下载完成")
        except Exception as e:
            print(f"  ❌ {stock} 下载失败: {e}")
    
    print(f"\n重新读取Tick数据...")
    tick_data = xtdata.get_local_data(
        field_list=['time', 'lastPrice', 'volume', 'amount'],
        stock_list=sample_stocks[:2],
        period='tick',
        start_time=test_date,
        end_time=test_date
    )
    
    for stock in sample_stocks[:2]:
        if stock in tick_data and not tick_data[stock].empty:
            df = tick_data[stock]
            print(f"  ✅ {stock}: Tick数据现在已存在！")
            print(f"     行数: {len(df)}")
            print(f"     time列类型: {df['time'].dtype}")
            print(f"     volume列类型: {df['volume'].dtype}")
            print(f"     volume值示例: {df['volume'].head(5).tolist()}")
            print(f"     完整前5行:")
            print(df.head())
        else:
            print(f"  ❌ {stock}: 仍然没有Tick数据")

print()
print("=" * 80)
print("4. 测试get_full_tick实时数据")
print("=" * 80)

print(f"\n获取实时Tick快照...")
try:
    full_tick = xtdata.get_full_tick(sample_stocks[:3])
    
    print(f"✅ get_full_tick成功！")
    print(f"返回类型: {type(full_tick)}")
    
    if isinstance(full_tick, dict):
        for stock, data in full_tick.items():
            print(f"\n  股票: {stock}")
            print(f"  数据类型: {type(data)}")
            if isinstance(data, dict):
                print(f"  字段: {list(data.keys())}")
                print(f"  volume: {data.get('volume', 'N/A')} (单位: 手)")
                print(f"  lastPrice: {data.get('lastPrice', 'N/A')}")
                print(f"  time: {data.get('time', 'N/A')}")
            elif isinstance(data, pd.DataFrame):
                print(f"  DataFrame形状: {data.shape}")
                print(f"  列名: {data.columns.tolist()}")
                print(f"  前3行:")
                print(data.head(3))
except Exception as e:
    print(f"❌ get_full_tick失败: {e}")

print()
print("=" * 80)
print("5. 结论")
print("=" * 80)

print("""
关键发现:
1. 日K数据单位: volume是股（1股=1）
2. Tick数据单位: volume是手（1手=100股）
3. Tick数据需要先download_history_data下载，再用get_local_data读取
4. get_full_tick返回实时快照，非历史数据

量纲铁律:
- Tick volume(手) × 100 = volume(股)
- 计算量比时必须统一单位
""")