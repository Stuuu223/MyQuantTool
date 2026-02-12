import json

data = json.load(open('data/scan_results/2026-02-06_093027_intraday.json', 'r', encoding='utf-8'))
opps = data['results']['opportunities']

if opps:
    first = opps[0]
    print(f'第一只股票数据:')
    print(json.dumps(first, ensure_ascii=False, indent=2))