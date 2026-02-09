"""检查快照日期"""
import json

with open('E:/MyQuantTool/data/rebuild_snapshots/full_market_snapshot_20260121_rebuild.json', 'r', encoding='utf-8') as f:
    snap = json.load(f)

print(f"trade_date: {snap['trade_date']}")
print(f"scan_time: {snap.get('scan_time', 'N/A')}")

opps = snap['results']['opportunities']
opp = [o for o in opps if o['code']=='000006.SZ']
print(f"000006.SZ in opportunities: {len(opp)>0}")
if opp:
    print(f"000006.SZ price: {opp[0]['price']['close']}")