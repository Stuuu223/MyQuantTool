"""
测试 AkShare 板块资金流排名接口
"""

import akshare as ak

print("=" * 80)
print("🧪 测试 AkShare 板块资金流排名接口")
print("=" * 80)

# 测试 1: 行业资金流排名
print("\n📊 测试 1: ak.stock_sector_fund_flow_rank (行业资金流)")
print("-" * 80)
try:
    df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前5行数据:")
    print(df.head(5))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 2: 概念资金流排名
print("\n📊 测试 2: ak.stock_sector_fund_flow_rank (概念资金流)")
print("-" * 80)
try:
    df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前5行数据:")
    print(df.head(5))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 3: 查找特定板块
print("\n📊 测试 3: 查找半导体板块")
print("-" * 80)
try:
    df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
    semiconductor_row = df[df['名称'] == '半导体']

    if not semiconductor_row.empty:
        print(f"✅ 找到半导体板块:")
        print(semiconductor_row.iloc[0])
    else:
        print(f"⚠️  未找到半导体板块")
        print(f"可用板块: {df['名称'].head(10).tolist()}")
except Exception as e:
    print(f"❌ 查找失败: {e}")

# 测试 4: 性能测试
print("\n📊 测试 4: 性能测试")
print("-" * 80)
import time

try:
    t_start = time.time()
    df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
    t_cost = time.time() - t_start

    print(f"✅ 获取全市场行业资金流排名")
    print(f"  - 板块数量: {len(df)}")
    print(f"  - 耗时: {t_cost:.3f}秒")

    # 测试查询性能
    t_start = time.time()
    semiconductor_row = df[df['名称'] == '半导体']
    t_cost = time.time() - t_start

    print(f"✅ 查询单个板块")
    print(f"  - 耗时: {t_cost:.6f}秒")
except Exception as e:
    print(f"❌ 性能测试失败: {e}")

print("\n" + "=" * 80)
print("✅ 测试完成")
print("=" * 80)