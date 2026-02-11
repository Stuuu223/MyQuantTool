import json

with open('data/scan_results/2026-02-06_intraday.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== 2026-02-06 11:07:57 扫描结果 ===\n")

opps = data['results']['opportunities']

print(f"机会池总数: {len(opps)} 只\n")
print("前 10 只股票:")
print("=" * 100)

for i, opp in enumerate(opps[:10], 1):
    code = opp['code']
    code_6digit = opp['code_6digit']
    risk = opp['risk_score']
    traps = opp['trap_signals']
    capital = opp['capital_type']

    trap_str = ",".join(traps) if traps else "无"

    print(f"{i}. {code} ({code_6digit})")
    print(f"   风险: L{risk:.1f} | 资金类型: {capital}")
    print(f"   诱多信号: {trap_str}")
    print()

# 搜索京华激光
print("\n=== 搜索京华激光 ===")
for opp in opps:
    if '603607' in opp['code']:
        print("找到京华激光 (603607.SH):")
        print(json.dumps(opp, indent=2, ensure_ascii=False))
        break
else:
    print("未找到京华激光")