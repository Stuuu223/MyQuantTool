"""
V18.2 Money Flow Rollback Script
回滚 V18.2 板块资金流向过滤器功能

使用方法：
1. 确保已备份当前代码
2. 运行此脚本回滚到 V18.1 版本
3. 验证系统功能正常
"""

import os
import shutil
from datetime import datetime
from logic.logger import get_logger

logger = get_logger(__name__)


def backup_files():
    """备份当前文件"""
    print("=" * 80)
    print("🔄 V18.2 Rollback - 备份当前文件")
    print("=" * 80)
    
    files_to_backup = [
        'logic/sector_analysis_streamlit.py',
        'ui/v18_navigator.py',
        'test_v18_2_money_flow_performance.py'
    ]
    
    backup_dir = f"backup_v18_2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                backup_path = os.path.join(backup_dir, os.path.basename(file_path))
                shutil.copy2(file_path, backup_path)
                print(f"✅ 已备份: {file_path} -> {backup_path}")
            else:
                print(f"⚠️  文件不存在: {file_path}")
        
        print(f"\n✅ 备份完成，备份目录: {backup_dir}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 备份失败: {e}")
        print(f"❌ 备份失败: {e}")
        return False


def rollback_sector_analysis_streamlit():
    """回滚 sector_analysis_streamlit.py 到 V18.1 版本"""
    print("\n" + "=" * 80)
    print("🔄 V18.2 Rollback - 回滚 sector_analysis_streamlit.py")
    print("=" * 80)
    
    file_path = 'logic/sector_analysis_streamlit.py'
    
    # 读取当前文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"❌ 读取文件失败: {e}")
        return False
    
    # 移除 V18.2 新增的内容
    # 1. 移除 get_sector_fund_flow 方法
    # 2. 移除 check_stock_full_resonance 中的资金流逻辑
    # 3. 移除 get_stock_sector_info 中的 status 字段
    
    rollback_markers = [
        ('def get_sector_fund_flow(', 'def _auto_refresh_loop('),
        ('# 🚀 V18.2 Money Flow: 获取行业板块资金流向', '# 根据资金流调整分数'),
        ("sector_status = sector_info.get('status', 'unknown')", 'concepts = sector_info.get(\'concepts\', [])'),
        ("# 🚀 V18.1 Fallback: Unknown 状态处理", '# 1. 行业板块共振分析'),
        ("if sector_status == 'unknown':", "resonance_details.extend(concept_info.get('details', []))"),
        ("elif sector_status == 'new':", "# 3. 判断是否为龙头或跟风"),
        ("resonance_details.append(\"⚠️ [未知板块] 该股票板块信息未知，请手动确认\")", "is_leader = any('龙头' in detail for detail in resonance_details)"),
        ("resonance_details.append(\"🆕 [新股] 新上市股票，请关注板块归属\")", "is_follower = any('跟风' in detail for detail in resonance_details)"),
        ("'sector_status': sector_status", "'is_follower': is_follower")
    ]
    
    try:
        # 简单的回滚：移除 V18.2 相关的代码块
        # 注意：这是一个简化版本，实际回滚可能需要更精细的处理
        
        print("⚠️  警告: 自动回滚可能不完整，建议手动检查代码")
        print("📝 建议回滚步骤:")
        print("  1. 使用 git checkout 恢复到 V18.1 版本")
        print("  2. 或者手动删除 V18.2 新增的代码")
        print("  3. 验证系统功能正常")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ 回滚失败: {e}")
        print(f"❌ 回滚失败: {e}")
        return False


def rollback_v18_navigator():
    """回滚 v18_navigator.py 到 V18.1 版本"""
    print("\n" + "=" * 80)
    print("🔄 V18.2 Rollback - 回滚 v18_navigator.py")
    print("=" * 80)
    
    file_path = 'ui/v18_navigator.py'
    
    # 读取当前文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"❌ 读取文件失败: {e}")
        return False
    
    # 移除 V18.2 新增的资金流显示代码
    
    try:
        print("⚠️  警告: 自动回滚可能不完整，建议手动检查代码")
        print("📝 建议回滚步骤:")
        print("  1. 使用 git checkout 恢复到 V18.1 版本")
        print("  2. 或者手动删除 V18.2 新增的资金流显示代码")
        print("  3. 验证系统功能正常")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ 回滚失败: {e}")
        print(f"❌ 回滚失败: {e}")
        return False


def rollback_with_git():
    """使用 Git 回滚到 V18.1 版本"""
    print("\n" + "=" * 80)
    print("🔄 V18.2 Rollback - 使用 Git 回滚")
    print("=" * 80)
    
    print("📝 Git 回滚步骤:")
    print("  1. 查看当前 Git 状态:")
    print("     git status")
    print("  2. 提交当前更改（如果需要）:")
    print("     git add .")
    print("     git commit -m 'V18.2 Money Flow implementation'")
    print("  3. 回滚到 V18.1 版本:")
    print("     git checkout a6b999e -- logic/sector_analysis_streamlit.py ui/v18_navigator.py")
    print("  4. 验证系统功能正常")
    
    return True


def run_rollback():
    """执行回滚"""
    print("\n" + "=" * 80)
    print("🚀 V18.2 Money Flow Rollback")
    print(f"📅 回滚时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 备份当前文件
    if not backup_files():
        print("\n❌ 备份失败，回滚中止")
        return False
    
    # 使用 Git 回滚
    if not rollback_with_git():
        print("\n❌ Git 回滚失败")
        return False
    
    print("\n" + "=" * 80)
    print("✅ 回滚指南已生成")
    print("=" * 80)
    print("\n📝 请按照上述 Git 回滚步骤手动执行回滚操作")
    print("⚠️  回滚完成后，请运行测试验证系统功能正常")
    
    return True


if __name__ == '__main__':
    import sys
    
    success = run_rollback()
    sys.exit(0 if success else 1)