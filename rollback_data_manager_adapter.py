#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回滚 DataManager 适配器模式
"""

import shutil
import os
from datetime import datetime

def rollback_data_manager_adapter():
    """回滚 DataManager 适配器模式"""
    print("=" * 80)
    print("🔄 回滚 DataManager 适配器模式")
    print(f"📅 回滚时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 备份当前版本
    backup_file = f"logic/data_manager.py.adapter.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if os.path.exists("logic/data_manager.py"):
        shutil.copy("logic/data_manager.py", backup_file)
        print(f"✅ 已备份当前版本到: {backup_file}")
    
    # 恢复到 V18.3 之前的状态
    # 这里需要手动恢复或从 Git 恢复
    print("\n📝 回滚步骤:")
    print("1. 当前版本已备份")
    print("2. 请使用以下命令恢复到 V18.3 之前的状态:")
    print("   git checkout a6b999e -- logic/data_manager.py")
    print("   或者手动删除以下代码:")
    print("   - 在 __init__ 方法中删除 DataProviderFactory 集成代码")
    print("   - 删除 get_provider_realtime_data 方法")
    print("\n⚠️  注意: 回滚后，DataManager 将不再使用 DataProviderFactory")
    
    print("\n" + "=" * 80)
    print("✅ 回滚脚本执行完成")
    print("=" * 80)

if __name__ == "__main__":
    rollback_data_manager_adapter()