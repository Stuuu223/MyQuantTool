#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
每日数据更新脚本 (Daily Update Script) - V19.17.2

功能：
- 盘后自动下载历史数据（数据预热）
- 适合通过 Windows 任务计划程序运行
- 支持增量下载策略（只下载当天数据）

使用方式：
1. 手动运行：python scripts/daily_update.py
2. 手动运行指定日期：python scripts/daily_update.py 20260128
3. Windows 任务计划程序：设置为每天 16:00 自动运行

Author: iFlow CLI
Version: V19.17.2
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from logic.data_providers.tick_provider import TickProvider
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    print("=" * 70)
    print("🌅 QMT 数据自动预热系统 - Daily Update")
    print("=" * 70)
    print(f"📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 检查 QMT 是否可用
    try:
        with TickProvider() as provider:
            if not provider.connect():
                print("❌ QMT 接口不可用，请检查：")
                print("  1. QMT 客户端是否已启动")
                print("  2. QMT Python 接口是否已正确安装")
                print()
                sys.exit(1)
        print("✅ QMT 接口已连接")
        print()
    except Exception as e:
        print(f"❌ QMT 连接失败: {e}")
        print()
        sys.exit(1)

    # 检查命令行参数
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        if not target_date.isdigit() or len(target_date) != 8:
            print(f"❌ 日期格式错误：{target_date}")
            print("   请使用 YYYYMMDD 格式，例如：20260128")
            print()
            sys.exit(1)
        print(f"📅 目标日期：{target_date}")
    else:
        now = datetime.now()
        print(f"📅 当前日期：{now.strftime('%Y-%m-%d')}")

        # 检查时间
        if now.hour < 15 or (now.hour == 15 and now.minute < 30):
            print()
            print("⏰ 注意：当前时间早于 15:30，收盘数据可能尚未归档")
            print("   如需强制下载，请指定日期参数：python scripts/daily_update.py 20260128")
            print()

    print()

    # 检查下载状态
    print("-" * 70)
    print("📊 检查当前数据状态...")
    print("-" * 70)
    status = maintainer.get_download_status(target_date)
    print(f"  QMT 接口状态:   {'✅ 可用' if status['qmt_available'] else '❌ 不可用'}")
    print(f"  上次运行日期:   {status['last_run_date'] or '未运行'}")
    print(f"  1分钟K线数据:   {'✅ 已下载' if status['data_available']['1m'] else '❌ 未下载'}")
    print(f"  日K线数据:       {'✅ 已下载' if status['data_available']['1d'] else '❌ 未下载'}")
    print()

    # 如果数据已经存在，询问是否重新下载
    date_to_check = target_date if target_date else datetime.now().strftime('%Y%m%d')
    if maintainer.last_run_date == date_to_check:
        print("⚠️  检测到今天的数据已经下载过")
        print("   如需重新下载，请按 Ctrl+C 取消，然后运行：")
        print(f"   python scripts/daily_update.py {date_to_check} --force")
        print()
        print("⏳ 5秒后自动跳过...")
        try:
            import time
            time.sleep(5)
        except KeyboardInterrupt:
            print()
            print("⚠️  用户取消操作")
            sys.exit(0)

    # 执行下载
    print("-" * 70)
    print("🚀 开始执行数据预热...")
    print("-" * 70)
    maintainer.run_daily_job(target_date)
    print()

    # 再次检查下载状态
    print("-" * 70)
    print("📊 最终数据状态...")
    print("-" * 70)
    final_status = maintainer.get_download_status(target_date)
    print(f"  1分钟K线数据:   {'✅ 已下载' if final_status['data_available']['1m'] else '❌ 未下载'}")
    print(f"  日K线数据:       {'✅ 已下载' if final_status['data_available']['1d'] else '❌ 未下载'}")
    print()

    # 总结
    print("=" * 70)
    print("✅ 数据预热完成！")
    print()
    print("📝 使用说明：")
    print("  - 今晚可以直接使用复盘模式，无需等待数据下载")
    print("  - 复盘模式路径：UI → 历史重演测试")
    print("  - 支持精确时间点复盘（如 14:56:55）")
    print()
    print("🎯 下次自动运行时间：明天 16:00")
    print("=" * 70)

    # 退出码
    if final_status['data_available']['1m'] and final_status['data_available']['1d']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)