#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查扫描结果时间戳"""

import json

with open('data/scan_results/2026-02-09_intraday.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Scan time: {data.get('scan_time')}")
print(f"Opportunities: {data.get('summary', {}).get('opportunities')}")
print(f"Watchlist: {data.get('summary', {}).get('watchlist')}")
print(f"Blacklist: {data.get('summary', {}).get('blacklist')}")