import json

with open('data/scan_results/2026-02-06_093027_intraday.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("快照中的所有顶层字段:")
for key in data.keys():
    print(f"  - {key}")

print("\nresults 中的所有字段:")
for key in data['results'].keys():
    print(f"  - {key}")

print("\nlevel1_candidates 是否存在:")
print(f"  - level1_candidates: {'level1_candidates' in data['results']}")

if 'level1_candidates' in data['results'] and data['results']['level1_candidates']:
    print("\nlevel1_candidates 第一条数据:")
    print(json.dumps(data['results']['level1_candidates'][0], indent=2, ensure_ascii=False)[:500])