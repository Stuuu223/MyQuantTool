# -*- coding: utf-8 -*-
"""
每日日志和结果自动归档脚本

功能：
- 归档旧的扫描结果 JSON 文件
- 归档旧的日志文件
- 按月归档，保持目录整洁

建议：每天盘后运行一次

Author: iFlow CLI
Version: V1.0
Date: 2026-02-09 10:00 AM
"""

import os
import shutil
from datetime import datetime
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置
TODAY = datetime.now().strftime('%Y%m%d')
CURRENT_MONTH = TODAY[:6]  # YYYYMM

# 目录路径
SCAN_RESULTS_DIR = 'data/scan_results'
LOGS_DIR = 'logs'
ARCHIVE_ROOT = 'data/archive'

def archive_files():
    """执行归档操作"""
    print("=" * 80)
    print(f"📦 [归档工具] 开始归档今日之前的文件")
    print(f"📅 当前日期: {TODAY}")
    print("=" * 80)

    # 创建归档目录
    archive_dir = os.path.join(ARCHIVE_ROOT, CURRENT_MONTH)
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        print(f"📁 创建归档目录: {archive_dir}")

    total_archived = 0

    # 1. 归档扫描结果 JSON
    if os.path.exists(SCAN_RESULTS_DIR):
        archived_count = archive_scan_results(archive_dir)
        total_archived += archived_count
    else:
        print(f"⚠️  扫描结果目录不存在: {SCAN_RESULTS_DIR}")

    # 2. 归档日志文件
    if os.path.exists(LOGS_DIR):
        archived_count = archive_logs(archive_dir)
        total_archived += archived_count
    else:
        print(f"⚠️  日志目录不存在: {LOGS_DIR}")

    print("=" * 80)
    print(f"✅ 归档完成！共归档 {total_archived} 个文件")
    print(f"📁 归档位置: {archive_dir}")
    print("=" * 80)

def archive_scan_results(archive_dir: str) -> int:
    """
    归档扫描结果文件

    Args:
        archive_dir: 归档目录

    Returns:
        归档的文件数量
    """
    print(f"\n📦 [扫描结果] 开始归档...")

    count = 0
    files = os.listdir(SCAN_RESULTS_DIR)

    for filename in files:
        if not filename.endswith('.json'):
            continue

        # 文件名格式: YYYY-MM-DD_intraday.json 或 YYYY-MM-DD_XXX.json
        # 我们只归档不是今天的文件
        if TODAY in filename:
            continue

        src_path = os.path.join(SCAN_RESULTS_DIR, filename)
        dst_path = os.path.join(archive_dir, f"scan_{filename}")

        try:
            shutil.move(src_path, dst_path)
            print(f"   ✅ 归档: {filename}")
            count += 1
        except Exception as e:
            print(f"   ❌ 归档失败: {filename} - {e}")

    print(f"📦 [扫描结果] 归档完成: {count} 个文件")
    return count

def archive_logs(archive_dir: str) -> int:
    """
    归档日志文件

    Args:
        archive_dir: 归档目录

    Returns:
        归档的文件数量
    """
    print(f"\n📦 [日志] 开始归档...")

    count = 0
    files = os.listdir(LOGS_DIR)

    # 创建日志归档子目录
    log_archive_dir = os.path.join(archive_dir, "logs")
    if not os.path.exists(log_archive_dir):
        os.makedirs(log_archive_dir)

    for filename in files:
        # 日志文件名格式: app_YYYYMMDD.log
        if not filename.startswith('app_') or not filename.endswith('.log'):
            continue

        # 从文件名提取日期
        # app_20260202.log -> 20260202
        parts = filename.split('_')
        if len(parts) < 2:
            continue

        file_date = parts[1].split('.')[0]

        # 归档不是今天的日志
        if file_date >= TODAY:
            continue

        src_path = os.path.join(LOGS_DIR, filename)
        dst_path = os.path.join(log_archive_dir, filename)

        try:
            shutil.move(src_path, dst_path)
            print(f"   ✅ 归档: {filename}")
            count += 1
        except Exception as e:
            print(f"   ❌ 归档失败: {filename} - {e}")

    print(f"📦 [日志] 归档完成: {count} 个文件")
    return count

def clean_empty_directories():
    """清理空目录"""
    print(f"\n🧹 [清理] 清理空目录...")

    dirs_to_clean = [SCAN_RESULTS_DIR]

    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            if len(files) == 0:
                print(f"   📁 目录为空: {dir_path}")
            else:
                print(f"   📁 目录有 {len(files)} 个文件: {dir_path}")

def generate_archive_report():
    """生成归档报告"""
    print(f"\n📊 [报告] 生成归档统计...")

    report = {
        'archive_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'archive_month': CURRENT_MONTH,
        'today': TODAY
    }

    # 统计各目录文件数
    report['scan_results'] = count_files(SCAN_RESULTS_DIR, '.json') if os.path.exists(SCAN_RESULTS_DIR) else 0
    report['logs'] = count_files(LOGS_DIR, '.log') if os.path.exists(LOGS_DIR) else 0

    archive_dir = os.path.join(ARCHIVE_ROOT, CURRENT_MONTH)
    report['archived_scan_results'] = count_files(os.path.join(archive_dir), '.json') if os.path.exists(archive_dir) else 0
    report['archived_logs'] = count_files(os.path.join(archive_dir, 'logs'), '.log') if os.path.exists(os.path.join(archive_dir, 'logs')) else 0

    print(f"   📊 当前扫描结果: {report['scan_results']} 个")
    print(f"   📊 当前日志: {report['logs']} 个")
    print(f"   📊 归档扫描结果: {report['archived_scan_results']} 个")
    print(f"   📊 归档日志: {report['archived_logs']} 个")

    return report

def count_files(directory: str, suffix: str) -> int:
    """
    统计目录中指定后缀的文件数量

    Args:
        directory: 目录路径
        suffix: 文件后缀

    Returns:
        文件数量
    """
    if not os.path.exists(directory):
        return 0

    count = 0
    for filename in os.listdir(directory):
        if filename.endswith(suffix):
            count += 1

    return count

if __name__ == "__main__":
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 执行归档
    archive_files()

    # 清理空目录
    clean_empty_directories()

    # 生成报告
    report = generate_archive_report()

    print()
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("✅ 归档工具执行完成！")