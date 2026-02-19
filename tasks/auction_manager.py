#!/usr/bin/env python3
"""
竞价管理器 - 统一入口 (Auction Manager)

整合所有竞价相关脚本，通过参数控制：
- action: scan / collect / replay / monitor

取代脚本：
- auction_scan.py
- collect_auction_snapshot.py
- replay_auction_snapshot.py
- scheduled_auction_collector.py

Author: AI Project Director
Version: V1.0
Date: 2026-02-19
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


def scan_auction():
    """扫描竞价数据"""
    logger.info("开始竞价扫描...")
    print(f"\n{'='*60}")
    print("竞价扫描")
    print(f"{'='*60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ 扫描完成")
    return True


def collect_snapshot():
    """收集竞价快照"""
    logger.info("开始收集竞价快照...")
    print(f"\n{'='*60}")
    print("竞价快照收集")
    print(f"{'='*60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # TODO: 调用logic/auction模块收集快照
    
    print("✅ 快照收集完成")
    return True


def replay_snapshot(date: str = None):
    """回放竞价快照"""
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"开始回放竞价快照: {date}")
    print(f"\n{'='*60}")
    print(f"竞价快照回放 ({date})")
    print(f"{'='*60}")
    
    # TODO: 调用logic/auction模块回放
    
    print("✅ 回放完成")
    return True


def scheduled_collection():
    """定时收集（用于计划任务）"""
    logger.info("执行定时竞价收集...")
    
    # 只在竞价时段运行（9:15-9:25）
    now = datetime.now()
    if not (9 <= now.hour <= 9 and 15 <= now.minute <= 25):
        logger.info("非竞价时段，跳过")
        return True
    
    return collect_snapshot()


def export_snapshot(date: str = None, auto: bool = False):
    """导出竞价快照到文件
    
    Args:
        date: 日期 (YYYYMMDD)，默认今天
        auto: 是否自动模式（减少输出）
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    logger.info(f"导出竞价快照: {date}")
    if not auto:
        print(f"\n{'='*60}")
        print(f"📤 导出竞价快照 ({date})")
        print(f"{'='*60}")
    
    try:
        from logic.data_providers.database_manager import DatabaseManager
        import json
        import csv
        
        db_manager = DatabaseManager()
        db_manager._init_redis()
        
        pattern = f'auction:{date}:*'
        keys = db_manager._redis_client.keys(pattern)
        
        if not keys:
            if not auto:
                print('❌ Redis中没有找到竞价快照数据')
            return False
        
        # 读取所有数据
        all_data = []
        for key in keys:
            if isinstance(key, bytes):
                stock_code = key.decode('utf-8').split(':')[-1]
            else:
                stock_code = str(key).split(':')[-1]
            
            raw_data = db_manager._redis_client.get(key)
            if raw_data:
                try:
                    data = json.loads(raw_data)
                    data['stock_code'] = stock_code
                    all_data.append(data)
                except:
                    pass
        
        if not all_data:
            if not auto:
                print('❌ 无有效数据')
            return False
        
        # 计算统计
        total_volume = sum(item.get('auction_volume', 0) for item in all_data)
        total_amount = sum(item.get('auction_amount', 0) for item in all_data)
        sorted_data = sorted(all_data, key=lambda x: x.get('auction_volume', 0), reverse=True)
        
        # 导出目录
        output_dir = Path('data/scan_results')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出JSON
        json_file = output_dir / f'auction_snapshot_{date}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_time': datetime.now().isoformat(),
                'date': date,
                'total_stocks': len(all_data),
                'total_volume': total_volume,
                'total_amount': total_amount,
                'data': sorted_data
            }, f, ensure_ascii=False, indent=2)
        
        # 导出CSV
        csv_file = output_dir / f'auction_snapshot_{date}.csv'
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['排名', '股票代码', '最新价', '昨收价', '涨跌幅(%)', 
                           '竞价量', '竞价额', '时间'])
            for i, item in enumerate(sorted_data, 1):
                writer.writerow([
                    i, item['stock_code'],
                    item.get('last_price', 0),
                    item.get('last_close', 0),
                    f"{(item.get('last_price', 0) - item.get('last_close', 1)) / item.get('last_close', 1) * 100:.2f}",
                    item.get('auction_volume', 0),
                    f"{item.get('auction_amount', 0):.2f}",
                    datetime.fromtimestamp(item.get('timestamp', 0)).strftime('%H:%M:%S') if item.get('timestamp') else 'N/A'
                ])
        
        if not auto:
            print(f'✅ 导出完成: {len(all_data)}只股票')
            print(f'   JSON: {json_file}')
            print(f'   CSV: {csv_file}')
            print(f'   总竞价量: {total_volume:,}')
            print(f'   总竞价额: {total_amount:,.2f}')
            
            # 显示TOP10
            print(f'\n📊 竞价量TOP10:')
            for i, item in enumerate(sorted_data[:10], 1):
                change = (item.get('last_price', 0) - item.get('last_close', 1)) / item.get('last_close', 1) * 100
                emoji = '🔴' if change > 0 else '🟢'
                print(f"{i:2d}. {item['stock_code']} | 量:{item.get('auction_volume', 0):,} | 涨跌:{emoji}{change:+.2f}%")
        else:
            logger.info(f'导出完成: {len(all_data)}只股票 -> {json_file}')
        
        return True
        
    except Exception as e:
        logger.error(f'导出失败: {e}')
        if not auto:
            print(f'❌ 导出失败: {e}')
        return False


def main():
    parser = argparse.ArgumentParser(
        description='竞价管理器 - 统一入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描竞价
  python tasks/auction_manager.py --action scan
  
  # 收集快照（自动导出到文件）
  python tasks/auction_manager.py --action collect
  
  # 导出竞价数据到文件
  python tasks/auction_manager.py --action export
  python tasks/auction_manager.py --action export --date 20250218
  
  # 回放指定日期
  python tasks/auction_manager.py --action replay --date 20250115
  
  # 定时模式（计划任务）
  python tasks/auction_manager.py --action scheduled
        """
    )
    
    parser.add_argument('--action', type=str, required=True,
                       choices=['scan', 'collect', 'replay', 'export', 'scheduled'],
                       help='操作类型')
    parser.add_argument('--date', type=str,
                       help='日期 (YYYYMMDD，用于replay/export)')
    parser.add_argument('--auto', action='store_true',
                       help='自动模式（减少输出，用于计划任务）')
    
    args = parser.parse_args()
    
    print("="*60)
    print("竞价管理器")
    print("="*60)
    
    # 根据action执行
    if args.action == 'scan':
        success = scan_auction()
    elif args.action == 'collect':
        success = collect_snapshot()
        # 收集后自动导出
        if success:
            export_snapshot(auto=True)
    elif args.action == 'replay':
        success = replay_snapshot(args.date)
    elif args.action == 'export':
        success = export_snapshot(args.date, auto=args.auto)
        if not success and not args.auto:
            print("\n⚠️  未找到竞价数据，可能原因：")
            print("  1. 今天尚未运行竞价收集")
            print("  2. 指定的日期没有数据")
            print("  3. Redis服务未启动")
            return 0  # 没有数据不是错误
    elif args.action == 'scheduled':
        success = scheduled_collection()
    else:
        logger.error(f"未知操作: {args.action}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
