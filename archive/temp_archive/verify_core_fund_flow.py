"""验证核心系统的资金流数据单位"""
import akshare as ak

# 测试000050的资金流数据（东方财富接口）
code = "000050"
market = "sz"

print("="*60)
print("验证核心系统资金流数据单位")
print("="*60)

try:
    df = ak.stock_individual_fund_flow(stock=code, market=market)

    if df.empty:
        print("❌ 未获取到数据")
    else:
        print(f"✅ 获取到 {len(df)} 条数据")
        print("\n字段列表:")
        print(df.columns.tolist())

        print("\n最新一条数据（2026-01-09）:")
        latest = df.iloc[0]
        print(f"  日期: {latest['日期']}")
        print(f"  超大单净流入-净额: {latest['超大单净流入-净额']:,} 元")
        print(f"  大单净流入-净额: {latest['大单净流入-净额']:,} 元")
        print(f"  中单净流入-净额: {latest['中单净流入-净额']:,} 元")
        print(f"  小单净流入-净额: {latest['小单净流入-净额']:,} 元")

        # 计算主力净流入
        main_net = latest['超大单净流入-净额'] + latest['大单净流入-净额']
        print(f"\n主力净流入（超大单+大单）: {main_net:,} 元 = {main_net/1e4:.1f}万")

        # 对比Tushare数据（之前验证的）
        print("\n对比Tushare数据（2026-01-09）:")
        print("  Tushare主力净流入: 1365.8万")
        print(f"  AkShare主力净流入: {main_net/1e4:.1f}万")

        if abs(main_net/1e4 - 1365.8) < 100:  # 允许100万误差
            print("  ✅ 数据基本一致（差异在合理范围内）")
        else:
            print(f"  ⚠️  数据差异较大: {abs(main_net/1e4 - 1365.8):.1f}万")

except Exception as e:
    print(f"❌ 获取数据失败: {e}")

print("="*60)