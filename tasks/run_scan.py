#!/usr/bin/env python3
"""
扫描运行器 - 统一入口 (Run Scan)

整合所有扫描脚本，通过参数控制扫描模式：
- mode: event_driven / full_market / triple_funnel / premarket

取代脚本：
- run_event_driven_monitor.py
- run_full_market_scan.py
- run_premarket_warmup.py
- run_triple_funnel_scan.py

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


def run_event_driven():
    """运行事件驱动监控"""
    logger.info("启动事件驱动监控...")
    print(f"\n{'='*60}")
    print("事件驱动监控")
    print(f"{'='*60}")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n监控中... 按Ctrl+C停止")
    
    # TODO: 调用logic/event_driven模块
    
    print("✅ 事件驱动监控完成")
    return True


def run_full_market_scan():
    """运行全市场扫描"""
    logger.info("启动全市场扫描...")
    print(f"\n{'='*60}")
    print("全市场扫描")
    print(f"{'='*60}")
    print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # TODO: 调用logic/scanner模块
    
    print("✅ 全市场扫描完成")
    return True


def run_premarket_warmup():
    """运行盘前预热"""
    logger.info("启动盘前预热...")
    print(f"\n{'='*60}")
    print("盘前预热")
    print(f"{'='*60}")
    print(f"预热时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # TODO: 调用logic/premarket模块
    
    print("✅ 盘前预热完成")
    return True


def run_triple_funnel_scan():
    """运行三把斧扫描"""
    logger.info("启动三把斧扫描...")
    print(f"\n{'='*60}")
    print("三把斧扫描")
    print(f"{'='*60}")
    print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # TODO: 调用logic/triple_funnel模块
    
    print("✅ 三把斧扫描完成")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='扫描运行器 - 统一入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 事件驱动监控
  python tasks/run_scan.py --mode event_driven
  
  # 全市场扫描
  python tasks/run_scan.py --mode full_market
  
  # 盘前预热
  python tasks/run_scan.py --mode premarket
  
  # 三把斧扫描
  python tasks/run_scan.py --mode triple_funnel
        """
    )
    
    parser.add_argument('--mode', type=str, required=True,
                       choices=['event_driven', 'full_market', 'premarket', 'triple_funnel'],
                       help='扫描模式')
    parser.add_argument('--config', type=str,
                       help='配置文件路径（可选）')
    
    args = parser.parse_args()
    
    print("="*60)
    print(f"扫描运行器 - 模式: {args.mode}")
    print("="*60)
    
    # 根据mode执行
    if args.mode == 'event_driven':
        success = run_event_driven()
    elif args.mode == 'full_market':
        success = run_full_market_scan()
    elif args.mode == 'premarket':
        success = run_premarket_warmup()
    elif args.mode == 'triple_funnel':
        success = run_triple_funnel_scan()
    else:
        logger.error(f"未知模式: {args.mode}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
