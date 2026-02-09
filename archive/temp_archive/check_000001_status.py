"""检查000001.SZ的状态"""
import json

# 加载20260206快照
with open('E:/MyQuantTool/data/rebuild_snapshots/full_market_snapshot_20260206_rebuild.json', 'r', encoding='utf-8') as f:
    snap = json.load(f)

print(f"20260206数据统计:")
print(f"  股票总数: {len(snap.get('all_stocks', []))}")
print(f"  Level 1候选: {len(snap.get('level1_candidates', []))}")
print(f"  机会池: {len(snap['results']['opportunities'])}")
print(f"  观察池: {len(snap['results']['watchlist'])}")
print(f"  黑名单: {len(snap['results']['blacklist'])}")

# 检查000001.SZ是否在Level 1候选中
level1_codes = [s['code'] for s in snap.get('level1_candidates', [])]
if '000001.SZ' in level1_codes:
    print(f"\n✅ 000001.SZ在Level 1候选中")
else:
    print(f"\n❌ 000001.SZ不在Level 1候选中（被Level 1过滤）")