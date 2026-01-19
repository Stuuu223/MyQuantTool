#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18.4 回滚脚本
回滚到 V18.3 版本
"""

import shutil
import os
from datetime import datetime

def rollback_v18_4():
    """回滚 V18.4 到 V18.3"""
    print("=" * 80)
    print("🔄 V18.4 回滚脚本")
    print(f"📅 回滚时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 备份当前版本
    backup_file = f"logic/sector_analysis_streamlit.py.v18.4.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if os.path.exists("logic/sector_analysis_streamlit.py"):
        shutil.copy("logic/sector_analysis_streamlit.py", backup_file)
        print(f"✅ 已备份当前版本到: {backup_file}")
    
    # 恢复到 V18.3 之前的状态
    # 这里需要手动恢复或从 Git 恢复
    print("\n📝 回滚步骤:")
    print("1. 当前版本已备份")
    print("2. 请使用以下命令恢复到 V18.3 之前的状态:")
    print("   git checkout 4a89ee6 -- logic/sector_analysis_streamlit.py")
    print("   或者手动恢复以下代码:")
    print("   - 在 check_stock_full_resonance 方法中，恢复调用 get_akshare_concept_ranking()")
    print("   - 恢复概念板块共振分析的 else 分支")
    print("\n⚠️  注意: 回滚后，概念信息为空的股票可能会触发 5.8秒延迟")
    
    print("\n" + "=" * 80)
    print("✅ 回滚脚本执行完成")
    print("=" * 80)

if __name__ == "__main__":
    rollback_v18_4()