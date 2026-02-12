"""
验证多日期同步的数据
"""
import json

# 读取equity_info数据
with open("data/equity_info_tushare.json", 'r', encoding='utf-8') as f:
    equity_data = json.load(f)

# 选择几个验证样本
test_stocks = ["000592.SZ", "601869.SH", "603607.SH"]

print("=" * 70)
print("验证多日期同步数据")
print("=" * 70)

for date in ["20260205", "20260206"]:
    print(f"\n📅 {date}:")
    if date in equity_data["data"]:
        for stock in test_stocks:
            if stock in equity_data["data"][date]:
                data = equity_data["data"][date][stock]
                float_mv = data["float_mv"]
                print(f"  ✅ {stock}: {float_mv/1e8:.2f} 亿")
            else:
                print(f"  ❌ {stock}: 未找到数据")
    else:
        print(f"  ❌ 日期 {date} 未找到数据")

print("\n" + "=" * 70)
print("数据验证完成")
print("=" * 70)