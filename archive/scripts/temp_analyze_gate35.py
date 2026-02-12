
"""
Analyze snapshot data to find samples with "3-day price up but capital not following"
"""
import json
from pathlib import Path

snapshot_file = Path("data/scan_results/2026-02-06_094521_intraday.json")

with open(snapshot_file, 'r', encoding='utf-8') as f:
    snapshot = json.load(f)

results = snapshot.get('results', {})
opportunities = results.get('opportunities', [])
watchlist = results.get('watchlist', [])
blacklist = results.get('blacklist', [])

all_stocks = opportunities + watchlist + blacklist

print("=" * 80)
print("Analyze capital flow in snapshot data")
print("=" * 80)

candidates = []

for stock in all_stocks:
    code = stock.get('code')
    name = stock.get('name', '')
    decision_tag = stock.get('decision_tag', 'UNKNOWN')
    ratio = stock.get('ratio', None)
    
    # Get capital flow records
    flow_data = stock.get('flow_data', {})
    records = flow_data.get('records', [])
    
    if len(records) >= 3:
        # Calculate capital 3-day net sum
        capital_3d_net_sum = sum(record.get('main_net_inflow', 0) for record in records[:3])
        
        # Display capital flow analysis
        print(f"\n{code} {name}")
        print(f"  Decision tag: {decision_tag}")
        print(f"  ratio: {ratio:.4f}%" if ratio else "  ratio: None")
        print(f"  Capital 3d net sum: {capital_3d_net_sum/10000:.2f} Wan")
        
        # Display daily capital inflow
        print(f"  Daily main net inflow:")
        for i, record in enumerate(records[:5]):  # Show first 5 days
            date = record.get('date', 'N/A')
            net_inflow = record.get('main_net_inflow', 0) / 10000
            print(f"    {date}: {net_inflow:.2f} Wan")
        
        candidates.append({
            'code': code,
            'name': name,
            'decision_tag': decision_tag,
            'ratio': ratio,
            'capital_3d_net_sum': capital_3d_net_sum,
            'records': records[:3]
        })

print("\n" + "=" * 80)
print("Candidate stocks analysis")
print("=" * 80)

# Find stocks with "capital not following"
capital_not_follow_stocks = []
for stock in candidates:
    capital_3d_net_sum = stock['capital_3d_net_sum']
    # Capital 3-day net sum <= 0
    if capital_3d_net_sum <= 0:
        capital_not_follow_stocks.append(stock)
        print(f"\n{stock['code']} {stock['name']} - 3-day capital net sum is negative")
        print(f"  Capital net sum: {capital_3d_net_sum/10000:.2f} Wan")
        print(f"  ratio: {stock['ratio']:.4f}%" if stock['ratio'] else "  ratio: None")
        print(f"  Decision tag: {stock['decision_tag']}")

print("\n" + "=" * 80)
print("Statistics")
print("=" * 80)
print(f"Total stocks: {len(candidates)}")
print(f"Stocks with negative 3-day capital net sum: {len(capital_not_follow_stocks)}")
print(f"Stocks with ratio < 1% among them: {len([s for s in capital_not_follow_stocks if s.get('ratio') and s['ratio'] < 1])}")