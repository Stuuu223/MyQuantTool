"""验证修复后的资金流数据"""
import sys
sys.path.insert(0, 'E:\\\\MyQuantTool')

from logic.fund_flow_analyzer import FundFlowAnalyzer
from datetime import datetime

print("="*80)
print("验证修复后的资金流数据")
print("="*80)

# 测试股票
test_codes = ['000050', '000001', '000002']

analyzer = FundFlowAnalyzer()

for code in test_codes:
    print(f"\n{code}:")
    print("-"*80)

    try:
        # 获取5天数据
        data = analyzer.get_fund_flow(code, days=5)

        if "error" in data:
            print(f"❌ 错误: {data['error']}")
            continue

        records = data.get('records', [])
        latest = data.get('latest')

        print(f"获取到 {len(records)} 条记录")
        print(f"最新日期: {latest['date']}")
        print(f"主力净流入: {latest['main_net_inflow']/1e4:.1f} 万")

        # 检查日期是否递增
        dates = [r['date'] for r in records]
        print(f"日期范围: {dates[0]} 到 {dates[-1]}")

        # 验证日期是否正确（应该是最近5天）
        if latest['date'] == dates[-1]:
            print("✅ latest 指向最新数据")
        else:
            print(f"❌ latest 错误：应该指向 {dates[-1]}，实际是 {latest['date']}")

        # 检查日期是否递增
        is_increasing = all(dates[i] < dates[i+1] for i in range(len(dates)-1))
        if is_increasing:
            print("✅ 日期顺序正确（从旧到新）")
        else:
            print("❌ 日期顺序错误")

        # 打印所有数据
        print("\n详细数据:")
        for i, r in enumerate(records):
            latest_flag = " ← 最新" if i == len(records)-1 else ""
            print(f"  {r['date']}: 主力={r['main_net_inflow']/1e4:8.1f}万{latest_flag}")

    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()

print("\n"+"="*80)
print("验证完成")
print("="*80)