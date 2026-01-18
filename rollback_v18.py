"""
V18 The Navigator - 全维板块共振系统回退脚本（完整旗舰版）

如果 V18 系统出现问题，可以使用此脚本回退到 V17 版本

执行：python rollback_v18.py
"""

import os
import shutil
from datetime import datetime
from logic.logger import get_logger

logger = get_logger(__name__)


def backup_current_files():
    """备份当前修改的文件"""
    print("\n" + "="*60)
    print("📦 备份当前文件")
    print("="*60)
    
    files_to_backup = [
        'logic/sector_analysis.py',
        'logic/signal_generator.py',
        'ui/v18_navigator.py',
        'test_v18_navigator_performance.py',
        'test_v18_full_performance.py',
        'main.py'
    ]
    
    backup_dir = f"backup_v18_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                backup_path = os.path.join(backup_dir, os.path.basename(file_path))
                shutil.copy2(file_path, backup_path)
                print(f"✅ 已备份: {file_path} -> {backup_path}")
            else:
                print(f"⚠️ 文件不存在: {file_path}")
        
        print(f"\n✅ 备份完成！备份目录: {backup_dir}")
        return backup_dir
        
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return None


def rollback_to_v17():
    """回退到 V17 版本"""
    print("\n" + "="*60)
    print("🔄 回退到 V17 版本")
    print("="*60)
    
    # V18 新增的文件
    v18_files = [
        'ui/v18_navigator.py',
        'test_v18_navigator_performance.py',
        'test_v18_full_performance.py'
    ]
    
    # V18 修改的文件（需要回退修改）
    # 注意：这里只是示例，实际回退需要使用 git
    
    print("\n⚠️ 警告：回退操作将删除 V18 新增功能！")
    print("建议使用 git 回退：")
    print("  git diff HEAD logic/sector_analysis.py logic/signal_generator.py main.py")
    print("  git checkout HEAD -- logic/sector_analysis.py logic/signal_generator.py main.py")
    print("  git rm ui/v18_navigator.py test_v18_navigator_performance.py test_v18_full_performance.py")
    
    # 删除 V18 新增文件
    try:
        for file_path in v18_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ 已删除: {file_path}")
            else:
                print(f"⚠️ 文件不存在: {file_path}")
        
        print("\n✅ V18 新增文件已删除")
        print("⚠️ 请手动回退 sector_analysis.py、signal_generator.py 和 main.py 的修改")
        print("   或使用 git 命令回退")
        
    except Exception as e:
        print(f"❌ 回退失败: {e}")


def restore_from_backup(backup_dir):
    """从备份恢复文件"""
    print("\n" + "="*60)
    print("📥 从备份恢复文件")
    print("="*60)
    
    if not os.path.exists(backup_dir):
        print(f"❌ 备份目录不存在: {backup_dir}")
        return False
    
    try:
        # 恢复文件
        for file_name in os.listdir(backup_dir):
            backup_path = os.path.join(backup_dir, file_name)
            original_path = os.path.dirname(backup_path)
            
            shutil.copy2(backup_path, original_path)
            print(f"✅ 已恢复: {backup_path} -> {original_path}")
        
        print(f"\n✅ 恢复完成！")
        return True
        
    except Exception as e:
        print(f"❌ 恢复失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🔄 V18 The Navigator - 回退脚本（完整旗舰版）")
    print("="*60)
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n请选择操作:")
    print("1. 备份当前文件")
    print("2. 回退到 V17 版本")
    print("3. 从备份恢复")
    print("0. 退出")
    
    choice = input("\n请输入选项 (0-3): ").strip()
    
    if choice == '1':
        backup_dir = backup_current_files()
        if backup_dir:
            print(f"\n✅ 备份目录: {backup_dir}")
            print("如需恢复，请运行: python rollback_v18.py 并选择选项 3")
    
    elif choice == '2':
        confirm = input("\n⚠️ 确认要回退到 V17 版本吗？(yes/no): ").strip().lower()
        if confirm == 'yes':
            rollback_to_v17()
        else:
            print("❌ 已取消回退操作")
    
    elif choice == '3':
        backup_dir = input("\n请输入备份目录路径: ").strip()
        if backup_dir:
            restore_from_backup(backup_dir)
        else:
            print("❌ 未输入备份目录")
    
    elif choice == '0':
        print("👋 退出")
    
    else:
        print("❌ 无效选项")


if __name__ == '__main__':
    main()