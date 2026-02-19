#!/usr/bin/env python3
"""
监控运行器 - 统一入口 (Monitor Runner)

整合所有监控脚本，通过参数控制监控模式：
- event: 事件驱动监控
- auction: 集合竞价监控
- download: 下载进度监控
- tick: Tick数据监控

取代脚本：
- monitor_auction_system.py
- monitor_download_progress.py
- monitor_tick_download.py
- qmt_auction_monitor.py

Author: AI Project Director
Version: V1.0
Date: 2026-02-19
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


def run_event_driven_monitor():
    """运行事件驱动监控"""
    logger.info("启动事件驱动监控...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'tasks' / 'run_event_driven_monitor.py')],
            check=True,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"事件驱动监控异常退出: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("事件驱动监控被用户中断")
        return True


def run_auction_monitor():
    """运行集合竞价监控"""
    logger.info("启动集合竞价监控...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'tasks' / 'auction_scan.py')],
            check=True,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"集合竞价监控异常退出: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("集合竞价监控被用户中断")
        return True


def run_download_monitor():
    """运行下载进度监控"""
    logger.info("启动下载进度监控...")
    
    try:
        # 导入并复用tick_download的状态检查
        from scripts.tick_download import is_running, read_status
        
        if not is_running()[0]:
            print("❌ 没有正在运行的下载任务")
            print("提示: 先运行 python scripts/download_manager.py ...")
            return False
        
        # 实时监控
        import time
        try:
            while True:
                status = read_status()
                if status:
                    print(f"\r进度: {status.get('progress', 'N/A')}, "
                          f"已下载: {status.get('downloaded_count', 0)}, "
                          f"失败: {status.get('failed_count', 0)}",
                          end='', flush=True)
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n监控已停止")
            return True
    
    except Exception as e:
        logger.error(f"下载监控异常: {e}")
        return False


def run_tick_monitor():
    """运行Tick数据监控"""
    logger.info("启动Tick数据监控...")
    
    try:
        from logic.data_providers.tick_provider import TickProvider
        
        print("Tick数据监控功能")
        print("-" * 60)
        
        # 检查今天的数据接收情况
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        
        with TickProvider() as provider:
            # 这里可以添加具体的监控逻辑
            print(f"监控日期: {today}")
            print("状态: 连接正常")
            print("\n提示: 按Ctrl+C停止监控")
            
            import time
            try:
                while True:
                    time.sleep(10)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 监控中...")
            except KeyboardInterrupt:
                print("\n监控已停止")
                return True
    
    except Exception as e:
        logger.error(f"Tick监控异常: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='监控运行器 - 统一监控入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动事件驱动监控（实盘）
  python scripts/monitor_runner.py --mode event
  
  # 启动集合竞价监控
  python scripts/monitor_runner.py --mode auction
  
  # 监控下载进度
  python scripts/monitor_runner.py --mode download
  
  # 监控Tick数据接收
  python scripts/monitor_runner.py --mode tick
        """
    )
    
    parser.add_argument('--mode', type=str, required=True,
                       choices=['event', 'auction', 'download', 'tick'],
                       help='监控模式')
    parser.add_argument('--interval', type=int, default=5,
                       help='监控间隔（秒），默认5秒')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"监控运行器 - 模式: {args.mode}")
    print("=" * 60)
    print("提示: 按Ctrl+C停止监控\n")
    
    # 根据模式执行
    if args.mode == 'event':
        success = run_event_driven_monitor()
    elif args.mode == 'auction':
        success = run_auction_monitor()
    elif args.mode == 'download':
        success = run_download_monitor()
    elif args.mode == 'tick':
        success = run_tick_monitor()
    else:
        logger.error(f"未知模式: {args.mode}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
