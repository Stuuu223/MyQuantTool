#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.3 回滚脚本
回滚到 V18.2 版本
"""

import shutil
import os
from datetime import datetime

def rollback_v18_3():
    """回滚 V18.3 到 V18.2"""
    print("=" * 80)
    print("🔄 V18.3 回滚脚本")
    print(f"📅 回滚时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 备份当前版本
    backup_file = f"logic/sector_analysis_streamlit.py.v18.3.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if os.path.exists("logic/sector_analysis_streamlit.py"):
        shutil.copy("logic/sector_analysis_streamlit.py", backup_file)
        print(f"✅ 已备份当前版本到: {backup_file}")
    
    # 恢复 V18.2 版本
    # 这里需要手动恢复或从 Git 恢复
    print("\n📝 回滚步骤:")
    print("1. 当前版本已备份")
    print("2. 请使用以下命令恢复到 V18.2:")
    print("   git checkout ee08a42 -- logic/sector_analysis_streamlit.py")
    print("   或者手动恢复 sector_analysis_streamlit.py 文件")
    print("\n⚠️  注意: V18.3 的性能优化将被移除")
    print("   - 恢复到 V18.2 的自下而上聚合方法")
    print("   - 查询耗时将从 0.0005秒 回退到 5.8秒")
    
    print("\n" + "=" * 80)
    print("✅ 回滚脚本执行完成")
    print("=" * 80)

if __name__ == "__main__":
    rollback_v18_3()