import json

with open('E:/MyQuantTool/data/scan_results/2026-02-11_intraday.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

opps = data['results']['opportunities']

print(f'总数: {len(opps)}')

if opps:
    first = opps[0]
    print(f'\n字段数: {len(first)}')
    print(f'字段: {list(first.keys())[:25]}')

    print(f'\n场景字段:')
    for k in ['is_tail_rally', 'is_potential_trap', 'is_potential_mainline', 'scenario_type', 'scenario_confidence', 'scenario_reasons']:
        val = first.get(k, "未找到")
        print(f'  {k}: {val}')