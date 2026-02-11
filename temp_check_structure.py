import json

with open('data/scan_results/2026-02-06_093027_intraday.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

opp = data['results']['opportunities'][0]
print("机会池第一条数据结构:")
print(json.dumps(opp, indent=2, ensure_ascii=False)[:1000])