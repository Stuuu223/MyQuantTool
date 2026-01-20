#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速启动定时任务监控器

Usage:
    python start_monitor.py
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from logic.scheduled_task_monitor import ScheduledTaskMonitor
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 MyQuantTool 定时任务监控器")
    print(f"📅 启动时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # 创建监控器
    monitor = ScheduledTaskMonitor()
    
    # 立即执行一次早盘前检查
    print("🔍 执行早盘前检查...")
    print()
    monitor.run_pre_market_check()
    print()
    
    # 启动定时任务
    print("📅 启动定时任务监控...")
    print()
    monitor.start()
    print()
    
    print("✅ 监控系统已启动，按 Ctrl+C 停止")
    print()
    print("📊 定时任务配置:")
    print(f"  - 早盘前检查: {monitor.tasks['pre_market_check']['time']}")
    print(f"  - 收盘后复盘: {monitor.tasks['post_market_review']['time']}")
    print(f"  - 每周检查: 周日 {monitor.tasks['weekly_check']['time']}")
    print()
    print("📁 告警文件: data/scheduled_alerts.json")
    print()
    
    # 保持运行
    try:
        while True:
            import time
            time.sleep(60)
    except KeyboardInterrupt:
        print()
        print("🛑 正在停止监控系统...")
        monitor.stop()
        print("✅ 监控系统已停止")
        print()
        print("👋 再见！")


if __name__ == '__main__':
    main()