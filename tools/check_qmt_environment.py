"""检查QMT真实环境连接状态"""
import sys
sys.path.insert(0, '.')

from xtquant import xtdata
import pandas as pd

print("=" * 70)
print("QMT真实环境检查")
print("=" * 70)

# 测试1：检查是否能获取股票列表
print("\n1. 检查股票列表获取...")
try:
    stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"✅ 成功获取股票列表：{len(stock_list)} 只")
except Exception as e:
    print(f"❌ 获取股票列表失败：{e}")
    print("⚠️ 可能原因：QMT未登录或无行情权限")
    sys.exit(1)

# 测试2：检查历史K线数据
print("\n2. 检查历史K线数据...")
test_code = '600519.SH'
try:
    hist_data = xtdata.get_market_data(
        stock_list=[test_code],
        period='1d',
        count=5
    )

    if hist_data and 'volume' in hist_data:
        volume_df = hist_data['volume']
        print(f"✅ 成功获取历史K线数据")
        print(f"   DataFrame结构：{volume_df.shape}")
        print(f"   列名：{list(volume_df.columns)}")
        print(f"   索引：{list(volume_df.index)}")

        if test_code in volume_df.columns:
            volumes = volume_df[test_code]
            print(f"   成交量数据：{volumes.tolist()}")
        else:
            print(f"⚠️ {test_code} 不在列中")
    else:
        print(f"❌ 历史K线数据为空")
        print("⚠️ 可能原因：无历史数据权限")
        sys.exit(1)
except Exception as e:
    print(f"❌ 获取历史K线失败：{e}")
    sys.exit(1)

# 测试3：检查实时行情
print("\n3. 检查实时行情...")
try:
    tick_data = xtdata.get_full_tick([test_code])
    if tick_data and test_code in tick_data:
        data = tick_data[test_code]
        print(f"✅ 成功获取实时行情")
        print(f"   lastPrice: {data.get('lastPrice', 'N/A')}")
        print(f"   lastClose: {data.get('lastClose', 'N/A')}")
        print(f"   volume: {data.get('volume', 'N/A')}")
    else:
        print(f"⚠️ 实时行情为空（可能不在交易时段）")
except Exception as e:
    print(f"❌ 获取实时行情失败：{e}")

print("\n" + "=" * 70)
print("检查完成")
print("=" * 70)
print("\n如果所有测试通过，说明QMT环境满足真实环境条件")
print("可以执行：python tasks/collect_auction_snapshot.py --date 2026-02-11")