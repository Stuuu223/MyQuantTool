#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目瘦身清理脚本
将临时文件和旧日志归档到 archive/ 目录
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

def print_section(title):
    """打印分节标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def archive_temp_files():
    """归档temp目录下的临时文件"""
    print_section("📦 归档 temp/ 目录下的临时文件")

    temp_dir = Path('E:/MyQuantTool/temp')
    archive_dir = Path('E:/MyQuantTool/archive/temp_archive')

    # 创建归档子目录
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 需要归档的文件模式（2月8日之前的一次性验证脚本）
    patterns_to_archive = [
        'analyze_*.py',      # 分析脚本
        'check_*.py',        # 检查脚本（保留今天刚创建的）
        'debug_*.py',        # 调试脚本
        'test_*.py',         # 测试脚本
        'verify_*.py',       # 验证脚本
        'find_*.py',         # 查找脚本
        'create_*.py',       # 创建脚本
        'export_*.py',       # 导出脚本
        'generate_*.py',     # 生成脚本
        'run_*.py',          # 运行脚本
        'simple_*.py',       # 简单脚本
    ]

    # 需要保留的文件（今天刚创建的）
    files_to_keep = [
        'check_qmt_status.py',
        'check_momentum_source.py',
        'pre_market_check.py',
        'pre_market_data_warmup.py',
        'pre_market_full_warmup.py',
        'pre_market_opportunity_analysis.py',
        'pre_market_warmup_qmt.py',
        'DIRECTOR_DAILY_LOG.md',
        'PRE_MARKET_DIRECTOR_REPORT.md',
    ]

    archived_count = 0
    kept_count = 0

    for py_file in temp_dir.glob('*.py'):
        if py_file.name in files_to_keep:
            kept_count += 1
            print(f"  ✅ 保留: {py_file.name}")
            continue

        # 检查文件是否匹配归档模式
        should_archive = False
        for pattern in patterns_to_archive:
            if py_file.match(pattern):
                should_archive = True
                break

        if should_archive:
            # 移动到归档目录
            dest = archive_dir / py_file.name
            shutil.move(str(py_file), str(dest))
            archived_count += 1
            print(f"  📦 归档: {py_file.name}")
        else:
            kept_count += 1
            print(f"  ✅ 保留: {py_file.name}")

    # 也归档旧的md文件（保留今天刚创建的）
    for md_file in temp_dir.glob('*.md'):
        if md_file.name in files_to_keep:
            kept_count += 1
            print(f"  ✅ 保留: {md_file.name}")
        else:
            dest = archive_dir / md_file.name
            shutil.move(str(md_file), str(dest))
            archived_count += 1
            print(f"  📦 归档: {md_file.name}")

    print(f"\n📊 统计:")
    print(f"  归档文件: {archived_count}个")
    print(f"  保留文件: {kept_count}个")
    print(f"  归档位置: {archive_dir}")

def archive_old_logs():
    """归档logs目录下的旧日志"""
    print_section("📦 归档 logs/ 目录下的旧日志")

    logs_dir = Path('E:/MyQuantTool/logs')
    archive_dir = Path('E:/MyQuantTool/archive/logs_archive')

    # 创建归档子目录
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 保留最近2天的日志
    today = datetime.now()
    cutoff_date = today.replace(day=today.day - 2)

    archived_count = 0
    kept_count = 0
    deleted_count = 0

    for log_file in logs_dir.glob('*.log'):
        file_date = datetime.fromtimestamp(log_file.stat().st_mtime)

        # 删除空的performance日志
        if log_file.name.startswith('performance_') and log_file.stat().st_size == 0:
            log_file.unlink()
            deleted_count += 1
            print(f"  🗑️  删除: {log_file.name} (空文件)")
            continue

        # 归档旧日志
        if file_date < cutoff_date:
            dest = archive_dir / log_file.name
            shutil.move(str(log_file), str(dest))
            archived_count += 1
            print(f"  📦 归档: {log_file.name} ({file_date.strftime('%Y-%m-%d')})")
        else:
            kept_count += 1
            print(f"  ✅ 保留: {log_file.name} ({file_date.strftime('%Y-%m-%d')})")

    print(f"\n📊 统计:")
    print(f"  归档日志: {archived_count}个")
    print(f"  保留日志: {kept_count}个")
    print(f"  删除空日志: {deleted_count}个")
    print(f"  归档位置: {archive_dir}")

def generate_cleanup_report():
    """生成清理报告"""
    print_section("📋 清理报告")

    temp_dir = Path('E:/MyQuantTool/temp')
    logs_dir = Path('E:/MyQuantTool/logs')
    archive_dir = Path('E:/MyQuantTool/archive')

    temp_count = len(list(temp_dir.glob('*')))
    logs_count = len(list(logs_dir.glob('*')))

    archive_size = sum(f.stat().st_size for f in archive_dir.rglob('*') if f.is_file()) / 1024 / 1024

    print(f"\n📊 当前状态:")
    print(f"  temp/ 目录: {temp_count}个文件")
    print(f"  logs/ 目录: {logs_count}个文件")
    print(f"  archive/ 目录: {archive_size:.2f} MB")

    print(f"\n✅ 清理完成!")
    print(f"\n💡 建议:")
    print(f"  1. 定期执行清理脚本（每周一次）")
    print(f"  2. 保留今天刚创建的文件（pre_market_*.py, check_qmt_status.py等）")
    print(f"  3. 定期删除archive/目录下的旧归档文件（每月一次）")

def main():
    """主函数"""
    print("\n" + "="*80)
    print("  🚀 MyQuantTool 项目瘦身清理")
    print(f"  清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # 1. 归档temp文件
    archive_temp_files()

    # 2. 归档旧日志
    archive_old_logs()

    # 3. 生成报告
    generate_cleanup_report()

    print("\n" + "="*80)
    print("  ✅ 清理完成!")
    print("="*80)

if __name__ == '__main__':
    main()