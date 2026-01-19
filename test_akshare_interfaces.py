"""
测试 AkShare 资金流接口
"""

import akshare as ak

print("=" * 80)
print("🧪 测试 AkShare 资金流接口")
print("=" * 80)

# 测试 1: 行业板块资金流排名
print("\n📊 测试 1: ak.stock_board_industry_fund_flow_rank_em")
print("-" * 80)
try:
    df = ak.stock_board_industry_fund_flow_rank_em()
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 2: 行业板块资金流排名（带参数）
print("\n📊 测试 2: ak.stock_board_industry_fund_flow_rank_em(symbol='当日')")
print("-" * 80)
try:
    df = ak.stock_board_industry_fund_flow_rank_em(symbol="当日")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 3: 概念板块资金流排名
print("\n📊 测试 3: ak.stock_board_concept_fund_flow_rank_em")
print("-" * 80)
try:
    df = ak.stock_board_concept_fund_flow_rank_em()
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 4: 概念板块资金流排名（带参数）
print("\n📊 测试 4: ak.stock_board_concept_fund_flow_rank_em(symbol='当日')")
print("-" * 80)
try:
    df = ak.stock_board_concept_fund_flow_rank_em(symbol="当日")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 5: 板块历史数据（可能包含资金流）
print("\n📊 测试 5: ak.stock_board_industry_hist_em(symbol='银行')")
print("-" * 80)
try:
    df = ak.stock_board_industry_hist_em(symbol="银行", period="daily", start_date="20260101", end_date="20260119")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 6: 个股资金流
print("\n📊 测试 6: ak.stock_individual_fund_flow(stock='000001', indicator='今日')")
print("-" * 80)
try:
    df = ak.stock_individual_fund_flow(stock="000001", indicator="今日")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

print("\n" + "=" * 80)
print("✅ 测试完成")
print("=" * 80)