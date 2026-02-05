import json

with open('data/scan_results/2026-02-05_premarket.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"扫描时间: {data.get('scan_time', 'N/A')}")
print(f"扫描模式: {data.get('mode', 'N/A')}")
print(f"\n摘要:")
print(f"  机会池: {data['summary']['opportunities']} 只")
print(f"  观察池: {data['summary']['watchlist']} 只")
print(f"  黑名单: {data['summary']['blacklist']} 只")

evidence = data['results']['evidence_matrix']
print(f"\n证据矩阵:")
print(f"  技术面: {evidence['technical']['quality']} (质量: {evidence['technical']['quality']})")
print(f"  资金流: {evidence['fund_flow']['quality']} (错误率: {evidence['fund_flow']['error_rate']:.1%})")
print(f"  市场情绪: {evidence['market_sentiment']['quality']} (评分: {evidence['market_sentiment']['score']:.1f})")

print(f"\n机会池 TOP5:")
opportunities = data['results']['opportunities']
for i, item in enumerate(opportunities[:5], 1):
    print(f"  {i}. {item['code']} - 风险评分: {item['risk_score']:.2f} - 资金类型: {item['capital_type']}")