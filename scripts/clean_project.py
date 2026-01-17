#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V10 系统大扫除 - 项目瘦身脚本
清理旧测试文件、缓存、备份文件
"""

import os
import shutil
import glob
from datetime import datetime

def clean_project():
    print("=" * 60)
    print("🧹 V10 系统大扫除开始")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    deleted_count = 0
    failed_count = 0
    
    # 1. 删除旧的测试脚本 (保留最新的 integrity_check)
    print("📂 第1步：清理旧测试脚本...")
    test_files = glob.glob("test_v10*.py")
    keep_file = "test_v10_1_9_1_integrity_check.py"
    
    for f in test_files:
        if f != keep_file:
            try:
                os.remove(f)
                print(f"  ✅ 已删除: {f}")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ 删除失败: {f} ({e})")
                failed_count += 1
    
    # 保留的测试文件
    if os.path.exists(keep_file):
        print(f"  ✅ 保留: {keep_file}")
    else:
        print(f"  ⚠️  警告: {keep_file} 不存在")
    
    print()
    
    # 2. 删除 Python 缓存 (__pycache__)
    print("📂 第2步：清理 Python 缓存...")
    cache_dirs = []
    for root, dirs, files in os.walk("."):
        if "__pycache__" in dirs:
            cache_dir = os.path.join(root, "__pycache__")
            cache_dirs.append(cache_dir)
    
    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir)
            print(f"  ✅ 已清理: {cache_dir}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ 清理失败: {cache_dir} ({e})")
            failed_count += 1
    
    if not cache_dirs:
        print("  ℹ️  没有发现缓存文件夹")
    
    print()
    
    # 3. 删除备份文件
    print("📂 第3步：清理备份文件...")
    backup_patterns = [
        "data/*.backup",
        "data/*.orig",
        "*.backup",
        "*.orig"
    ]
    
    backup_files = []
    for pattern in backup_patterns:
        backup_files.extend(glob.glob(pattern))
    
    for f in backup_files:
        try:
            os.remove(f)
            print(f"  ✅ 已删除: {f}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ 删除失败: {f} ({e})")
            failed_count += 1
    
    if not backup_files:
        print("  ℹ️  没有发现备份文件")
    
    print()
    
    # 4. 清理 .pyc 文件
    print("📂 第4步：清理 .pyc 文件...")
    pyc_files = glob.glob("**/*.pyc", recursive=True)
    
    for f in pyc_files:
        try:
            os.remove(f)
            print(f"  ✅ 已删除: {f}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ 删除失败: {f} ({e})")
            failed_count += 1
    
    if not pyc_files:
        print("  ℹ️  没有发现 .pyc 文件")
    
    print()
    
    # 5. 清理临时文件
    print("📂 第5步：清理临时文件...")
    temp_patterns = [
        "*.tmp",
        "*.temp",
        "*.swp",
        "*~"
    ]
    
    temp_files = []
    for pattern in temp_patterns:
        temp_files.extend(glob.glob(pattern))
    
    for f in temp_files:
        try:
            os.remove(f)
            print(f"  ✅ 已删除: {f}")
            deleted_count += 1
        except Exception as e:
            print(f"  ❌ 删除失败: {f} ({e})")
            failed_count += 1
    
    if not temp_files:
        print("  ℹ️  没有发现临时文件")
    
    print()
    print("=" * 60)
    print("✨ 清理完成！")
    print("=" * 60)
    print(f"删除文件数: {deleted_count}")
    print(f"失败文件数: {failed_count}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("👉 下一步建议：")
    print("   1. 创建 logic/utils.py 提取通用工具")
    print("   2. 创建 config.py 集中管理配置")
    print("   3. 运行测试验证系统正常")
    print()

if __name__ == "__main__":
    clean_project()