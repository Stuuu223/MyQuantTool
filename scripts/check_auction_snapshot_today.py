#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查今日竞价快照数据
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.database_manager import DatabaseManager
from logic.auction_snapshot_manager import AuctionSnapshotManager

print("=" * 80)
print("🔍 检查今日竞价快照数据")
print("=" * 80)

# 初始化
db = DatabaseManager()
manager = AuctionSnapshotManager(db)

# 检查Redis连接
print(f"\n1. Redis连接状态:")
print(f"   可用: {'✅ 是' if manager.is_available else '❌ 否'}")

if manager.is_available:
    # 获取今日竞价快照数量
    redis = db._redis_client
    pattern = f"auction_snapshot:*{manager.get_today_str()}*"
    keys = redis.keys(pattern)
    
    print(f"\n2. 今日竞价快照数量（Redis）:")
    print(f"   总数: {len(keys)}")
    
    if keys:
        print(f"\n3. 今日竞价快照示例（前5条）:")
        for i, key in enumerate(keys[:5], 1):
            data = redis.get(key)
            if data:
                import json
                snapshot = json.loads(data)
                print(f"   [{i}] {key.decode() if isinstance(key, bytes) else key}")
                print(f"      竞价量: {snapshot.get('auction_volume', 0)} 手")
                print(f"      竞价额: {snapshot.get('auction_amount', 0) / 100000000:.2f} 亿")
    
    print(f"\n4. 文件系统存储:")
    import os
    auction_dir = Path('data/auction_snapshots')
    
    if auction_dir.exists():
        files = list(auction_dir.glob('*.csv'))
        print(f"   目录存在: ✅")
        print(f"   CSV文件数量: {len(files)}")
        
        if files:
            print(f"\n5. 今日CSV文件示例:")
            for file in files[:5]:
                print(f"   - {file.name}")
    else:
        print(f"   目录存在: ❌")
        print(f"   说明: 文件系统存储未启用或未创建")
else:
    print(f"\n⚠️ Redis不可用，无法检查竞价快照数据")

print("\n" + "=" * 80)