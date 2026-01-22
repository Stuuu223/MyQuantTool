#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞价快照手动保存脚本

用于手动保存竞价快照，可以在竞价期间（9:15-9:30）运行
"""

from logic.auction_snapshot_saver import AuctionSnapshotSaver
from datetime import datetime

print("=" * 80)
print("🚀 竞价快照手动保存")
print("=" * 80)

# 显示当前时间
now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print(f"\n🕐 当前时间: {current_time}")

# 创建竞价快照保存器
saver = AuctionSnapshotSaver()

# 检查竞价快照管理器是否可用
if not saver.snapshot_manager or not saver.snapshot_manager.is_available:
    print("\n❌ 竞价快照管理器不可用")
    print("💡 请检查Redis是否启动")
    exit(1)

# 检查是否在竞价时间
if saver.is_auction_time():
    print("✅ 当前在竞价时间（9:15-9:30）")
    
    # 询问是否保存
    print("\n开始保存竞价快照...")
    print("⏳ 这可能需要一些时间，请耐心等待...")
    
    result = saver.save_auction_snapshot_for_stocks()
    
    if result['success']:
        print(f"\n✅ 保存成功！")
        print(f"   成功: {result['saved_count']} 只")
        print(f"   失败: {result['failed_count']} 只")
        if 'total_count' in result:
            print(f"   总计: {result['total_count']} 只")
        print(f"\n💡 竞价快照已保存到Redis，可以在UI中查看")
    else:
        print(f"\n❌ 保存失败: {result.get('error', '未知错误')}")
else:
    print("⚠️ 当前不在竞价时间（9:15-9:30）")
    print("💡 请在竞价期间运行此程序")
    print("\n📅 竞价时间说明:")
    print("   - 9:15-9:25: 集合竞价（可以接受委托）")
    print("   - 9:25-9:30: 竞价真空期（不能委托，但可以看到竞价结果）")
    print("   - 9:30以后: 连续竞价（竞价量清零）")

print("\n" + "=" * 80)