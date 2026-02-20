"""
验证问题股票的真实tick列名
作为AI项目总监，我需要确认xtdata返回的实际字段结构差异
"""
from xtquant import xtdata
import pandas as pd

print("="*80)
print("AI项目总监：验证问题股票的真实tick列名")
print("目的：确认002792.SZ等股票的tick数据实际包含哪些列")
print("="*80)

# 测试几个"问题股票"和一个"正常股票"作为对比
problem_stocks = ["002792.SZ", "600343.SH", "002131.SZ", "002565.SZ"]
normal_stock = "000547.SZ"

date_str = "2026-01-22"
start_time = "20260122093000"
end_time = "20260122150000"

# 先测试正常股票作为基准
print(f"\n基准测试 - 正常股票 {normal_stock}:")
print("-" * 60)

tick_df = xtdata.get_market_data_ex(
    field_list=[],  # 传空列表获取默认字段
    stock_list=[normal_stock],
    period='tick',
    start_time=start_time,
    end_time=end_time
)

if normal_stock in tick_df and not tick_df[normal_stock].empty:
    df = tick_df[normal_stock]
    print(f"DataFrame形状: {df.shape}")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据类型: {dict(df.dtypes)}")
    print(f"前2行数据:")
    print(df.head(2))
else:
    print(f"  无数据或为空")

# 测试问题股票
print(f"\n" + "="*80)
print("问题股票测试:")
print("="*80)

for stock_code in problem_stocks:
    print(f"\n{stock_code}:")
    print("-" * 40)
    
    # 获取默认字段（传空列表）
    tick_df = xtdata.get_market_data_ex(
        field_list=[],
        stock_list=[stock_code],
        period='tick',
        start_time=start_time,
        end_time=end_time
    )
    
    if stock_code not in tick_df:
        print(f"  ❌ 返回数据中不包含{stock_code}")
        print(f"  返回数据: {type(tick_df)}")
        if isinstance(tick_df, dict):
            print(f"  包含的股票: {list(tick_df.keys())}")
        continue
    
    df = tick_df[stock_code]
    
    if df is None:
        print(f"  ❌ DataFrame为None")
        continue
    
    if df.empty:
        print(f"  ❌ DataFrame为空 (形状: {df.shape})")
        continue
    
    print(f"  ✅ DataFrame形状: {df.shape}")
    print(f"  列名: {df.columns.tolist()}")
    print(f"  数据类型: {dict(df.dtypes)}")
    
    # 检查关键字段是否存在
    key_fields = ['lastPrice', 'close', 'volume', 'time']
    missing_fields = [field for field in key_fields if field not in df.columns]
    
    if missing_fields:
        print(f"  ⚠️  缺失关键字段: {missing_fields}")
    
    # 显示前2行数据
    print(f"  前2行数据:")
    print(df.head(2))

print(f"\n" + "="*80)
print("AI项目总监分析结论:")
print("="*80)

# 额外测试：使用我们代码中实际使用的field_list
print(f"\n测试实际代码中使用的field_list:")
field_list = ['time', 'lastPrice', 'volume', 'amount', 'bidPrice', 'askPrice']

for stock_code in [normal_stock] + problem_stocks[:2]:
    print(f"\n{stock_code} 使用field_list={field_list}:")
    
    tick_df = xtdata.get_market_data_ex(
        field_list=field_list,
        stock_list=[stock_code],
        period='tick',
        start_time=start_time,
        end_time=end_time
    )
    
    if stock_code in tick_df and not tick_df[stock_code].empty:
        df = tick_df[stock_code]
        print(f"  返回列名: {df.columns.tolist()}")
        print(f"  缺失字段: {[f for f in field_list if f not in df.columns]}")
    else:
        print(f"  无数据返回")