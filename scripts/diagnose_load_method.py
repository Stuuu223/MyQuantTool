#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断load_auction_snapshot方法

Author: MyQuantTool Team
Date: 2026-02-10
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logic.database_manager import DatabaseManager
from logic.auction_snapshot_manager import AuctionSnapshotManager
from datetime import datetime

print("=" * 80)
print("🔍 诊断load_auction_snapshot方法")
print("=" * 80)

db_manager = DatabaseManager()
db_manager._init_redis()

# 直接从Redis获取原始数据
test_code = '000001.SZ'
today = datetime.now().strftime("%Y%m%d")
key = f"auction:{today}:{test_code}"

print(f"\n📌 测试Key: {key}")

# 步骤1：直接从Redis获取
print("\n步骤1: 直接从Redis获取原始数据")
raw_data = db_manager._redis_client.get(key)
print(f"   原始数据类型: {type(raw_data)}")
if raw_data:
    print(f"   原始数据: {raw_data[:100]}")

# 步骤2：通过DatabaseManager.redis_get获取
print("\n步骤2: 通过DatabaseManager.redis_get获取")
manager_data = db_manager.redis_get(key)
print(f"   返回数据类型: {type(manager_data)}")
if manager_data:
    print(f"   返回数据: {manager_data[:100] if isinstance(manager_data, str) else manager_data}")

# 步骤3：尝试解析
print("\n步骤3: 尝试解析JSON")
try:
    if isinstance(manager_data, str):
        parsed = json.loads(manager_data)
        print(f"   ✅ 解析成功: {parsed}")
    elif isinstance(manager_data, dict):
        print(f"   ❌ 数据已经是dict: {manager_data}")
    else:
        print(f"   ❌ 数据类型未知: {type(manager_data)}")
except Exception as e:
    print(f"   ❌ 解析失败: {e}")

# 步骤4：通过AuctionSnapshotManager加载
print("\n步骤4: 通过AuctionSnapshotManager.load_auction_snapshot加载")
snapshot_manager = AuctionSnapshotManager(db_manager)
result = snapshot_manager.load_auction_snapshot(test_code)
if result:
    print(f"   ✅ 加载成功: {result}")
else:
    print(f"   ❌ 加载失败")

print("=" * 80)