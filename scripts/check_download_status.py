#!/usr/bin/env python3
"""
检查tick下载状态
"""
import time
from pathlib import Path
import json

def check_status():
    """检查下载状态"""
    PROJECT_ROOT = Path('C:/Users/pc/Desktop/Astock/MyQuantTool')
    log_file = PROJECT_ROOT / 'logs' / 'tick_download_150.log'
    fail_list_file = PROJECT_ROOT / 'logs' / 'tick_download_failures_150.txt'

    print("=" * 80)
    print("📊 Tick下载状态检查")
    print("=" * 80)

    # 检查日志文件
    if log_file.exists():
        print(f"\n✅ 日志文件存在: {log_file}")
        print(f"   文件大小: {log_file.stat().st_size / 1024:.2f} KB")
        print(f"   最后修改: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log_file.stat().st_mtime))}")

        # 读取最后几行
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"   总行数: {len(lines)}")

            if lines:
                print(f"\n📝 最后5条日志:")
                for line in lines[-5:]:
                    print(f"   {line.strip()}")

                # 尝试提取进度信息
                success_count = 0
                fail_count = 0
                for line in lines:
                    if '下载成功' in line:
                        success_count += 1
                    elif '下载失败' in line:
                        fail_count += 1

                print(f"\n📈 当前进度:")
                print(f"   成功: {success_count} 只")
                print(f"   失败: {fail_count} 只")
    else:
        print(f"\n❌ 日志文件不存在: {log_file}")
        print("   下载任务可能尚未启动或遇到错误")

    # 检查失败列表
    if fail_list_file.exists():
        print(f"\n⚠️  失败股票列表存在: {fail_list_file}")
        with open(fail_list_file, 'r', encoding='utf-8') as f:
            failed_stocks = f.readlines()
        print(f"   失败数量: {len(failed_stocks)} 只")
    else:
        print(f"\n✅ 暂无失败股票")

    # 检查数据目录
    data_dir = PROJECT_ROOT / 'data' / 'qmt_data' / 'datadir'
    if data_dir.exists():
        subdirs = [d for d in data_dir.iterdir() if d.is_dir()]
        print(f"\n📂 数据目录: {data_dir}")
        print(f"   已下载股票目录数: {len(subdirs)}")
        if subdirs:
            print(f"   示例目录: {', '.join([d.name for d in subdirs[:5]])}")
    else:
        print(f"\n❌ 数据目录不存在: {data_dir}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    check_status()