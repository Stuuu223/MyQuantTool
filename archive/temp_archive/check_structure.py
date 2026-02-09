import json

data = json.load(open('data/scan_results/2026-02-06_094521_intraday.json', 'r', encoding='utf-8'))
print('顶层键:', list(data.keys()))
print('results顶层键:', list(data.get('results', {}).keys()))
print('results.opportunities数量:', len(data.get('results', {}).get('opportunities', [])))
if data.get('results', {}).get('opportunities'):
    print('第一个机会的字段:', list(data['results']['opportunities'][0].keys()))
    print('第一个机会是否有trade_date:', 'trade_date' in data['results']['opportunities'][0])