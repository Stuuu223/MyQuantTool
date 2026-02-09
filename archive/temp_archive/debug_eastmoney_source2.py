"""
Debug eastmoney data source - check multiple files
"""

import json
import os

data_dir = "E:/MyQuantTool/data/scan_results"

# Find snapshot files
snapshot_files = []
for file in os.listdir(data_dir):
    if file.endswith("_intraday.json"):
        snapshot_files.append(os.path.join(data_dir, file))

print(f"Found {len(snapshot_files)} snapshot files")

# Check each file
for file_path in snapshot_files:
    print(f"\n{'='*60}")
    print(f"File: {os.path.basename(file_path)}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    opportunities = data.get('results', {}).get('opportunities', [])
    
    for opp in opportunities:
        code = opp.get('code')
        flow_data = opp.get('flow_data', {})
        records = flow_data.get('records', [])
        
        if records:
            print(f"  {code}: {len(records)} flow records")
            print(f"    First record date: {records[0].get('date')}")
            print(f"    Last record date: {records[-1].get('date')}")