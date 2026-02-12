import json

data = json.load(open('data/scan_results/2026-02-06_093027_intraday.json', 'r', encoding='utf-8'))
opps = data['results']['opportunities']

print(f'机会池数量: {len(opps)}')

if opps:
    print(f'第一只股票的字段:')
    for key in opps[0].keys():
        print(f'  - {key}')