"""调试UniverseBuilder数据获取问题"""
import sys
sys.path.insert(0, r'E:\MyQuantTool')

from xtquant import xtdata

# 连接QMT
xtdata.connect()
print("=" * 60)
print("UniverseBuilder调试脚本")
print("=" * 60)

# 1. 获取股票列表
all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
print(f"\n1. 全市场股票数: {len(all_stocks)}")
print(f"   前5只: {all_stocks[:5]}")

# 2. 检查get_stock_name
print("\n2. 测试get_stock_name:")
for stock in all_stocks[:10]:
    name = xtdata.get_stock_name(stock)
    print(f"   {stock}: {name}")

# 3. 检查get_instrument_detail
print("\n3. 测试get_instrument_detail:")
for stock in all_stocks[:5]:
    try:
        detail = xtdata.get_instrument_detail(stock)
        float_vol = detail.get('FloatVolume', 0) if detail else 0
        print(f"   {stock}: FloatVolume={float_vol:,.0f}")
    except Exception as e:
        print(f"   {stock}: 错误={e}")

# 4. 检查get_local_data (tick)
print("\n4. 测试get_local_data (tick) - 20251231:")
test_stocks = all_stocks[:5]
tick_data = xtdata.get_local_data(
    field_list=['volume', 'amount'],
    stock_list=test_stocks,
    period='tick',
    start_time='20251231',
    end_time='20251231'
)
for stock in test_stocks:
    if tick_data and stock in tick_data and len(tick_data[stock]) > 0:
        df = tick_data[stock]
        print(f"   {stock}: tick数据有{len(df)}条")
    else:
        print(f"   {stock}: 无tick数据")

# 5. 检查get_local_data (1d)
print("\n5. 测试get_local_data (1d) - 20251231:")
daily_data = xtdata.get_local_data(
    field_list=['volume', 'amount', 'open', 'high', 'low', 'close'],
    stock_list=test_stocks,
    period='1d',
    start_time='20251231',
    end_time='20251231'
)
for stock in test_stocks:
    if daily_data and stock in daily_data and len(daily_data[stock]) > 0:
        df = daily_data[stock]
        print(f"   {stock}: 日K数据有{len(df)}条, volume={df['volume'].values[-1] if 'volume' in df.columns else 'N/A'}")
    else:
        print(f"   {stock}: 无日K数据")

# 6. 检查交易日期
print("\n6. 检查交易日期:")
trading_dates = xtdata.get_trading_dates('20251201', '20251231')
print(f"   2025年12月交易日: {trading_dates}")

print("\n" + "=" * 60)
print("调试完成")
