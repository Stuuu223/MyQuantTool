#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主目录文件清理脚本
清理主目录下的临时文件和冗余启动脚本
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

def print_section(title):
    """打印分节标题"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def analyze_root_files():
    """分析主目录文件"""
    print_section("📊 主目录文件分析")

    root_dir = Path('E:/MyQuantTool')

    # 文件分类
    core_files = {
        '✅ 核心文件（必须保留）': [
            'analyze.py',                    # 个股分析工具
            'main.py',                       # 主程序入口
            'start_app.py',                  # 应用启动脚本
            'start.bat',                     # 主启动脚本
            'requirements.txt',              # Python依赖列表
            'pytest.ini',                    # 测试配置
            'my_quant_cache.sqlite',         # 缓存数据库
        ],
        '✅ 启动脚本（常用）': [
            'analyze_supplement.bat',        # 分析工具启动
            'quick_analyze.bat',             # 快速分析
            'run_daily_ths_collector.bat',   # 每日数据收集
            'run_qmt_downloader.bat',        # QMT下载器
            'start_continuous_monitor.bat',  # 持续监控
            'start_event_driven_monitor.bat',# 事件驱动监控
            'start_triple_funnel.bat',       # 三漏斗监控
        ],
        '✅ 文档文件（重要）': [
            'CORE_ARCHITECTURE.md',          # 核心架构文档
            'HALFWAY_MOMO_STRATEGY.md',      # 半路推背策略
            'PROJECT_ARCHITECTURE.md',       # 项目架构
            'PROJECT_STRUCTURE.md',          # 项目结构
            'TASK_PLAN.md',                  # 任务计划
            'TASK_PROGRESS.md',              # 任务进度
            'TODO.md',                       # 待办事项
        ],
        '📦 临时数据（可归档）': [
            'pending_equity_codes_20260206.txt',      # 待处理股票代码（2026-02-06）
            'pending_equity_codes_multi_date.txt',    # 多日期待处理股票代码
            'pending_equity_codes_summary.txt',       # 待处理股票代码汇总
        ],
        '🗑️  冗余文件（可删除）': [
            'check_data_structure.py',       # 检查数据结构（一次性脚本）
            'check_scan_result.py',          # 检查扫描结果（一次性脚本）
            'export_event_records.py',       # 导出事件记录（一次性脚本）
            'export_records.bat',            # 导出记录（冗余）
            'install_dependencies.bat',      # 安装依赖（用一次后可删除）
            'pip.bat',                       # pip快捷方式（冗余）
            'quick_start.bat',               # 快速启动（有start.bat了）
            'weekly_check.bat',              # 周检查（用tasks里的任务）
            'intraday_monitor_v2.py',        # 盘中监控v2（旧版本）
            'quick_analyze.py',              # 快速分析（已有analyze.py）
        ],
    }

    total_count = 0
    keep_count = 0
    archive_count = 0
    delete_count = 0

    for category, files in core_files.items():
        print(f"\n{category}")
        print("-"*80)

        for filename in files:
            filepath = root_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                total_count += 1

                if category.startswith('📦'):
                    archive_count += 1
                    print(f"  📦 {filename:40s} {size:>8}B  {mtime.strftime('%Y-%m-%d')}")
                elif category.startswith('🗑️'):
                    delete_count += 1
                    print(f"  🗑️  {filename:40s} {size:>8}B  {mtime.strftime('%Y-%m-%d')}")
                else:
                    keep_count += 1
                    print(f"  ✅ {filename:40s} {size:>8}B  {mtime.strftime('%Y-%m-%d')}")
            else:
                print(f"  ⚠️  {filename:40s} (不存在)")

    print(f"\n📊 统计:")
    print(f"  总文件数: {total_count}")
    print(f"  保留文件: {keep_count}")
    print(f"  归档文件: {archive_count}")
    print(f"  删除文件: {delete_count}")

    return {
        'total': total_count,
        'keep': keep_count,
        'archive': archive_count,
        'delete': delete_count
    }

def archive_temp_files():
    """归档临时数据文件"""
    print_section("📦 归档临时数据文件")

    root_dir = Path('E:/MyQuantTool')
    archive_dir = Path('E:/MyQuantTool/archive/root_temp')

    archive_dir.mkdir(parents=True, exist_ok=True)

    temp_files = [
        'pending_equity_codes_20260206.txt',
        'pending_equity_codes_multi_date.txt',
        'pending_equity_codes_summary.txt',
    ]

    archived_count = 0

    for filename in temp_files:
        src = root_dir / filename
        if src.exists():
            dest = archive_dir / filename
            shutil.move(str(src), str(dest))
            archived_count += 1
            print(f"  📦 归档: {filename}")
        else:
            print(f"  ⚠️  {filename} (不存在)")

    print(f"\n📊 归档统计: {archived_count}个文件")
    print(f"   归档位置: {archive_dir}")

    return archived_count

def delete_redundant_files():
    """删除冗余文件"""
    print_section("🗑️  删除冗余文件")

    root_dir = Path('E:/MyQuantTool')

    redundant_files = [
        'check_data_structure.py',
        'check_scan_result.py',
        'export_event_records.py',
        'export_records.bat',
        'install_dependencies.bat',
        'pip.bat',
        'quick_start.bat',
        'weekly_check.bat',
        'intraday_monitor_v2.py',
        'quick_analyze.py',
    ]

    deleted_count = 0

    for filename in redundant_files:
        filepath = root_dir / filename
        if filepath.exists():
            filepath.unlink()
            deleted_count += 1
            print(f"  🗑️  删除: {filename}")
        else:
            print(f"  ⚠️  {filename} (不存在)")

    print(f"\n📊 删除统计: {deleted_count}个文件")

    return deleted_count

def generate_final_report():
    """生成最终报告"""
    print_section("📋 清理后主目录状态")

    root_dir = Path('E:/MyQuantTool')

    # 统计剩余文件
    remaining_files = []
    for f in root_dir.glob('*'):
        if f.is_file() and not f.name.startswith('.'):
            remaining_files.append(f)

    print(f"\n📊 剩余文件数: {len(remaining_files)}")
    print(f"\n✅ 核心文件:")
    for f in sorted(remaining_files):
        if f.suffix in ['.py', '.bat', '.md', '.txt'] and f.name not in ['TODO.md', 'TASK_PLAN.md', 'TASK_PROGRESS.md']:
            print(f"  - {f.name}")

    print(f"\n✅ 文档文件:")
    for f in sorted(remaining_files):
        if f.name in ['TODO.md', 'TASK_PLAN.md', 'TASK_PROGRESS.md']:
            print(f"  - {f.name}")

def main():
    """主函数"""
    print("\n" + "="*80)
    print("  🚀 MyQuantTool 主目录文件清理")
    print(f"  清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # 1. 分析文件
    stats = analyze_root_files()

    # 2. 归档临时文件
    archived = archive_temp_files()

    # 3. 删除冗余文件
    deleted = delete_redundant_files()

    # 4. 生成最终报告
    generate_final_report()

    print("\n" + "="*80)
    print("  ✅ 清理完成!")
    print("="*80)
    print(f"\n📊 清理统计:")
    print(f"  归档文件: {archived}个")
    print(f"  删除文件: {deleted}个")
    print(f"  保留文件: {stats['keep']}个")
    print(f"\n💡 建议:")
    print(f"  1. 定期执行清理脚本（每月一次）")
    print(f"  2. 临时数据文件归档到 archive/root_temp/")
    print(f"  3. 保持主目录简洁，只保留核心文件")

if __name__ == '__main__':
    main()
