"""
Debug eastmoney data source
"""

import json
import os

data_dir = "E:/MyQuantTool/data/scan_results"

# Find snapshot files
snapshot_files = []
for file in os.listdir(data_dir):
    if file.endswith("_intraday.json"):
        snapshot_files.append(os.path.join(data_dir, file))

print(f"Found {len(snapshot_files)} snapshot files:")
for f in snapshot_files:
    print(f"  - {f}")

# Use the latest snapshot file
if snapshot_files:
    latest_file = sorted(snapshot_files)[-1]
    print(f"\nUsing latest file: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check structure
    print(f"\nTop-level keys: {list(data.keys())}")
    
    # Check results structure
    results = data.get('results', {})
    print(f"\nResults keys: {list(results.keys())}")
    
    # Check opportunities
    opportunities = results.get('opportunities', [])
    print(f"\nNumber of opportunities: {len(opportunities)}")
    
    # Find 603607.SH
    for i, opp in enumerate(opportunities[:3]):  # Show first 3
        print(f"\nOpportunity {i+1}:")
        print(f"  code: {opp.get('code')}")
        print(f"  flow_data keys: {list(opp.get('flow_data', {}).keys()) if opp.get('flow_data') else 'None'}")
        
        if opp.get('code') == '603607.SH':
            print(f"\nFound 603607.SH!")
            flow_data = opp.get('flow_data', {})
            records = flow_data.get('records', [])
            print(f"  Number of flow records: {len(records)}")
            if records:
                print(f"  First record: {records[0]}")