"""
V18.1 Turbo Boost 回退脚本

如果 V18.1 导致系统不稳定或性能问题，请运行此脚本回退到 V18 版本
"""

import os
import shutil
from datetime import datetime

def rollback_v18_1():
    """回退 V18.1 到 V18"""
    print("=" * 60)
    print("V18.1 Turbo Boost 回退脚本")
    print("=" * 60)
    print(f"回退时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 备份当前文件
    print("📦 正在备份当前文件...")
    backup_dir = f"backup_v18_1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'logic/sector_analysis.py',
        'ui/v18_navigator.py',
        'test_v18_1_turbo_boost_performance.py'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            shutil.copy(file_path, os.path.join(backup_dir, file_path))
            print(f"✅ 已备份: {file_path}")
    
    print(f"\n✅ 备份完成，备份目录: {backup_dir}")
    
    # 回退操作说明
    print("\n" + "=" * 60)
    print("📝 回退操作说明")
    print("=" * 60)
    print("\n请使用 Git 回退到 V18 版本:")
    print("\n1. 查看 Git 历史:")
    print("   git log --oneline -10")
    print("\n2. 回退到 V18 提交:")
    print("   git checkout <V18_COMMIT_ID> logic/sector_analysis.py ui/v18_navigator.py")
    print("\n3. 或者使用 Git reset:")
    print("   git reset --hard <V18_COMMIT_ID>")
    print("\n4. 提交回退:")
    print("   git add .")
    print("   git commit -m 'Rollback: V18.1 -> V18'")
    print("\n5. 推送到 GitHub:")
    print("   git push origin master --force")
    
    print("\n" + "=" * 60)
    print("⚠️ 注意事项")
    print("=" * 60)
    print("\n1. 回退前请确保已提交当前更改")
    print("2. 回退后需要重启系统")
    print("3. 如果使用 --force push，请谨慎操作")
    print("4. 建议在回退前创建新的分支备份")
    
    print("\n✅ 回退脚本执行完成！")


if __name__ == '__main__':
    rollback_v18_1()