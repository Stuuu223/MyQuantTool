#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证竞价快照数据

Author: MyQuantTool Team
Date: 2026-02-10
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logic.auction_snapshot_manager import AuctionSnapshotManager
from logic.database_manager import DatabaseManager

db_manager = DatabaseManager()
db_manager._init_redis()  # 🔧 强制初始化Redis
snapshot_manager = AuctionSnapshotManager(db_manager)

# 检查几只热门股票
test_codes = ['000001.SZ', '600000.SH', '300059.SZ', '688001.SH']

print("=" * 60)
print("🔍 验证竞价快照数据")
print("=" * 60)

for code in test_codes:
    snapshot = snapshot_manager.load_auction_snapshot(code)
    if snapshot:
        volume = snapshot.get('auction_volume', 0)
        amount = snapshot.get('auction_amount', 0)
        print(f"✅ {code}: 竞价量={volume}, 竞价额={amount/1e8:.2f}亿")
    else:
        print(f"❌ {code}: 无竞价数据")

print("=" * 60)