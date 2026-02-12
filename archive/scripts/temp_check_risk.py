import json

with open('data/scan_results/2026-02-06_093027_intraday.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

opps = data['results']['opportunities']
print(f'机会池数量: {len(opps)}')
print('\n风险评分分布:')
for opp in opps:
    risk = opp.get('risk_score', 0)
    print(f"{opp['code']} ({opp.get('name', '')}): 风险={risk:.2f}")