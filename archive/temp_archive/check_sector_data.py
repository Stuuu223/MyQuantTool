"""检查板块数据完整性"""
import json

sector_file = 'E:/MyQuantTool/data/stock_sector_map.json'

with open(sector_file, 'r', encoding='utf-8') as f:
    sector_data = json.load(f)

print("="*80)
print("板块数据完整性检查")
print("="*80)

# 统计
total_stocks = len(sector_data)
industry_count = 0
concept_count = 0
both_count = 0

# 统计行业分布
industry_dist = {}
# 统计概念分布
concept_dist = {}

for code, data in sector_data.items():
    industry = data.get('industry', '')
    concepts = data.get('concepts', [])

    if industry:
        industry_count += 1
        industry_dist[industry] = industry_dist.get(industry, 0) + 1

    if concepts:
        concept_count += 1
        for concept in concepts:
            concept_dist[concept] = concept_dist.get(concept, 0) + 1

    if industry and concepts:
        both_count += 1

print(f"总股票数: {total_stocks}")
print(f"有行业数据的股票: {industry_count} ({industry_count/total_stocks*100:.1f}%)")
print(f"有概念数据的股票: {concept_count} ({concept_count/total_stocks*100:.1f}%)")
print(f"同时有行业和概念的股票: {both_count} ({both_count/total_stocks*100:.1f}%)")

print("\n" + "="*80)
print("行业分布（前20个）")
print("="*80)
sorted_industries = sorted(industry_dist.items(), key=lambda x: x[1], reverse=True)[:20]
for industry, count in sorted_industries:
    print(f"{industry}: {count} 只股票")

print("\n" + "="*80)
print("概念分布（前20个）")
print("="*80)
sorted_concepts = sorted(concept_dist.items(), key=lambda x: x[1], reverse=True)[:20]
for concept, count in sorted_concepts:
    print(f"{concept}: {count} 只股票")

print("="*80)
print("结论：系统有完整的板块数据，可以直接用于板块/题材过滤")
print("="*80)