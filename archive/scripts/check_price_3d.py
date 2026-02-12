#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查扫描结果中的price_3d_change值"""

import json

with open('data/scan_results/2026-02-09_intraday.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

blacklist = data.get('results', {}).get('blacklist', [])

print(f"Blacklist count: {len(blacklist)}")
print("\n前5只股票的price_3d_change值:")
for i, stock in enumerate(blacklist[:5]):
    code = stock.get('code')
    price_3d = stock.get('price_3d_change')
    print(f"{i+1}. {code} - price_3d_change={price_3d}")