#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Redis中的竞价快照数据
"""

import redis

print("=" * 80)
print("🔍 检查Redis中的竞价快照数据")
print("=" * 80)

try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print("✅ Redis连接成功")
    
    # 查询所有竞价快照
    all_keys = r.keys('auction_snapshot:*')
    print(f"\n所有竞价快照数量: {len(all_keys)}")
    
    if all_keys:
        print(f"\n最新10个竞价快照:")
        for key in all_keys[-10:]:
            data = r.get(key)
            if data:
                import json
                snapshot = json.loads(data)
                print(f"  {key}")
                print(f"    竞价量: {snapshot.get('auction_volume', 0)} 手")
                print(f"    竞价额: {snapshot.get('auction_amount', 0) / 100000000:.2f} 亿")
                print(f"    时间戳: {snapshot.get('snapshot_time', 0)}")
    
    # 检查今日数据
    from datetime import datetime
    today_str = datetime.now().strftime("%Y%m%d")
    today_keys = r.keys(f'auction_snapshot:*{today_str}*')
    print(f"\n今日竞价快照数量: {len(today_keys)}")
    
    if today_keys:
        print(f"\n今日竞价快照示例:")
        for key in today_keys[:5]:
            data = r.get(key)
            if data:
                import json
                snapshot = json.loads(data)
                print(f"  {key}")
                print(f"    竞价量: {snapshot.get('auction_volume', 0)} 手")
                print(f"    竞价额: {snapshot.get('auction_amount', 0) / 100000000:.2f} 亿")
    else:
        print("⚠️ 今日无竞价快照数据")
    
    # 检查数据库存储
    print("\n" + "=" * 80)
    print("📁 检查文件系统存储")
    print("=" * 80)
    
    from pathlib import Path
    auction_dir = Path('data/auction_snapshots')
    
    if auction_dir.exists():
        csv_files = list(auction_dir.glob('*.csv'))
        print(f"\n竞价快照目录存在: ✅")
        print(f"CSV文件数量: {len(csv_files)}")
        
        if csv_files:
            print(f"\n今日CSV文件:")
            for file in csv_files:
                if file.stat().st_mtime > (datetime.now().timestamp() - 86400):
                    print(f"  ✅ {file.name} (今日)")
                else:
                    print(f"  📄 {file.name} (历史)")
    else:
        print(f"\n竞价快照目录不存在")
        print(f"  说明: 文件系统存储未启用")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()