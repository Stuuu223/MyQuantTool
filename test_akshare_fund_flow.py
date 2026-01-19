"""
测试 AkShare 资金流接口（详细）
"""

import akshare as ak

print("=" * 80)
print("🧪 测试 AkShare 资金流接口（详细）")
print("=" * 80)

# 测试 1: 个股资金流
print("\n📊 测试 1: ak.stock_individual_fund_flow")
print("-" * 80)
try:
    df = ak.stock_individual_fund_flow(stock="000001", market="sh")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 2: 个股资金流（无参数）
print("\n📊 测试 2: ak.stock_individual_fund_flow(stock='000001')")
print("-" * 80)
try:
    df = ak.stock_individual_fund_flow(stock="000001")
    print(f"✅ 接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前3行数据:")
    print(df.head(3))
except Exception as e:
    print(f"❌ 接口不可用: {e}")

# 测试 3: 板块成分股资金流聚合
print("\n📊 测试 3: 获取板块成分股并聚合资金流")
print("-" * 80)
try:
    # 获取银行板块成分股
    df = ak.stock_board_industry_cons_em(symbol="银行")
    print(f"✅ 银行板块成分股接口可用！")
    print(f"列名: {df.columns.tolist()}")
    print(f"数据形状: {df.shape}")
    print(f"前5只股票:")
    print(df.head(5))

    # 获取成分股的资金流并聚合
    if '代码' in df.columns or 'item' in df.columns:
        code_col = '代码' if '代码' in df.columns else 'item'
        stock_codes = df[code_col].head(3).tolist()

        total_inflow = 0
        for code in stock_codes:
            try:
                fund_df = ak.stock_individual_fund_flow(stock=code)
                if not fund_df.empty:
                    # 尝试获取净流入数据
                    for col in ['净流入', '主力净流入', 'net_inflow']:
                        if col in fund_df.columns:
                            total_inflow += fund_df[col].iloc[0]
                            break
            except:
                pass

        print(f"\n💰 板块资金流聚合（前3只股票）:")
        print(f"  总净流入: {total_inflow/100000000:.2f}亿")
except Exception as e:
    print(f"❌ 接口不可用: {e}")

print("\n" + "=" * 80)
print("✅ 测试完成")
print("=" * 80)
