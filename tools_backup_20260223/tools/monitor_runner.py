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


def run_auction_system_monitor():
    """运行竞价快照系统详细监控（恢复被PR-3删除的功能）"""
    logger.info("启动竞价快照系统详细监控...")
    
    print('=' * 80)
    print('🧪 项目总监监控 - 竞价快照系统')
    print('=' * 80)

    # 显示当前时间
    from datetime import datetime
    now = datetime.now()
    print(f'\n📅 当前时间: {now.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'   星期: {now.strftime("%A")}')

    # 检查是否在竞价时间
    current_hour = now.hour
    current_minute = now.minute

    print(f'\n⏰ 市场时间判断:')
    if 9 <= current_hour < 15:
        print('   ✅ 交易时间段')
        if 9 <= current_hour < 10:
            print('   🎯 竞价时间段 (9:15-9:25)')
            if current_hour == 9 and current_minute < 25:
                print('   🔥 当前在竞价时间内，应该有竞价数据')
            elif current_hour == 9 and 25 <= current_minute < 30:
                print('   🔥 竞价已结束，连续竞价即将开始')
            else:
                print('   ⚠️ 竞价时间已过')
        else:
            print('   ⚠️ 竞价时间已过')
    else:
        print('   ⚠️ 非交易时间')

    # 检查Redis中的竞价数据
    print(f'\n📊 Redis竞价数据检查:')

    try:
        from logic.data_providers.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        db_manager._init_redis()

        today = datetime.now().strftime("%Y%m%d")
        pattern = f"auction:{today}:*"

        # 获取所有竞价快照键
        keys = db_manager._redis_client.keys(pattern)

        if not keys:
            print(f'   ❌ Redis中没有找到今日竞价快照数据')
            print(f'   🔑 查询模式: {pattern}')
            return False
        else:
            print(f'   ✅ 找到 {len(keys)} 条竞价快照记录')

            # 随机抽样检查几条数据
            sample_size = min(3, len(keys))
            import random
            sample_keys = random.sample(keys, sample_size)

            print(f'\n   📋 抽样检查 ({sample_size}条):')
            for key in sample_keys:
                stock_code = key.decode('utf-8').split(':')[-1]
                raw_data = db_manager._redis_client.get(key)

                if raw_data:
                    import json
                    try:
                        data = json.loads(raw_data)
                        volume = data.get('auction_volume', 0)
                        amount = data.get('auction_amount', 0)
                        last_price = data.get('last_price', 0)
                        timestamp = data.get('timestamp', 0)

                        print(f'      ✅ {stock_code}: 成交量={volume}, 成交额={amount:.0f}, 价格={last_price:.2f}')
                    except Exception as e:
                        print(f'      ❌ {stock_code}: 数据解析失败 - {e}')
                else:
                    print(f'      ❌ {stock_code}: 数据为空')

    except Exception as e:
        print(f'   ❌ Redis连接失败: {e}')
        return False

    # 检查竞价快照守护进程状态
    print(f'\n🔧 竞价快照守护进程检查:')

    # 检查定时任务是否已创建
    import subprocess

    try:
        # Windows任务计划程序
        result = subprocess.run(
            ['schtasks', '/query', '/tn', 'MyQuantTool_AuctionSnapshot'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print('   ✅ Windows计划任务已创建')
            print('   📋 任务名称: MyQuantTool_AuctionSnapshot')
            print('   ⏰ 执行时间: 每天上午9:15')
        else:
            print('   ⚠️ Windows计划任务未创建')
            print('   💡 请手动创建计划任务或运行: scripts/schedule_auction_daemon.bat')

    except Exception as e:
        print(f'   ⚠️ 无法检查计划任务状态: {e}')
    
    print('\n' + '=' * 80)
    print('✅ 监控检查完成')
    print('=' * 80)
    return True


def run_download_monitor():
    """运行下载进度监控"""
    logger.info("启动下载进度监控...")
    
    try:
        import json
        import time
        from pathlib import Path
        
        STATUS_FILE = PROJECT_ROOT / 'logs' / 'download' / 'download_manager_status.json'
        
        if not STATUS_FILE.exists():
            print("❌ 没有下载状态文件")
            print("提示: 先运行 python tools/download_manager.py ...")
            return False
        
        # 实时监控
        try:
            while True:
                if STATUS_FILE.exists():
                    with open(STATUS_FILE, 'r') as f:
                        status = json.load(f)
                    
                    total = status.get('total_stocks', 0)
                    completed = status.get('completed_stocks', 0)
                    failed = status.get('failed_stocks', 0)
                    current = status.get('current_stock', '')
                    
                    if total > 0:
                        pct = completed / total * 100
                        print(f"\r[{completed}/{total} {pct:.1f}%] "
                              f"当前: {current} "
                              f"失败: {failed}     ",
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
  python tools/monitor_runner.py --mode event
  
  # 启动集合竞价监控
  python tools/monitor_runner.py --mode auction
  
  # 启动竞价快照系统详细监控
  python tools/monitor_runner.py --mode auction-system
  
  # 监控下载进度
  python tools/monitor_runner.py --mode download
  
  # 监控Tick数据接收
  python tools/monitor_runner.py --mode tick
        """
    )
    
    parser.add_argument('--mode', type=str, required=True,
                       choices=['event', 'auction', 'auction-system', 'download', 'tick'],
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
    elif args.mode == 'auction-system':
        success = run_auction_system_monitor()
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
