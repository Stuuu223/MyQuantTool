"""
Debug eastmoney data source with detailed logging
"""

import sys
sys.path.append('E:/MyQuantTool')

from logic.moneyflow_data_source import EastmoneyMoneyflowSource
import json
import os

# Test with 603607.SH
eastmoney_source = EastmoneyMoneyflowSource()

# Debug: Find the file
data_dir = "E:/MyQuantTool/data/scan_results"
snapshot_files = []
for file in os.listdir(data_dir):
    if file.endswith("_intraday.json") and "test" not in file.lower():
        snapshot_files.append(os.path.join(data_dir, file))

print(f"Found {len(snapshot_files)} snapshot files (excluding test files)")

# Use the latest snapshot file (by modification time)
latest_file = max(snapshot_files, key=os.path.getmtime)
print(f"Using file: {os.path.basename(latest_file)}")

# Load the file
with open(latest_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find 603607.SH
opportunities = data.get('results', {}).get('opportunities', [])
for opp in opportunities:
    if opp.get('code') == '603607.SH':
        flow_data = opp.get('flow_data', {})
        records = flow_data.get('records', [])
        print(f"Found 603607.SH with {len(records)} flow records")
        
        # Check date range
        if records:
            first_date = records[0]['date'].replace('-', '')
            last_date = records[-1]['date'].replace('-', '')
            print(f"Date range: {first_date} to {last_date}")
            
            # Test date matching
            start_date = '20250812'
            end_date = '20250922'
            
            matched_records = []
            for record in records:
                record_date = record['date'].replace('-', '')
                if start_date <= record_date <= end_date:
                    matched_records.append(record)
            
            print(f"Matched {len(matched_records)} records in range {start_date} to {end_date}")
        
        break

# Test the actual method
snapshots = eastmoney_source.get_moneyflow(
    ts_code='603607.SH',
    start_date='20250812',
    end_date='20250922'
)

print(f"\nMethod returned {len(snapshots)} snapshots")