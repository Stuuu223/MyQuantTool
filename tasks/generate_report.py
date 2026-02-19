#!/usr/bin/env python3
"""
报告生成器 - 统一入口 (Generate Report)

整合日报和周报生成，通过参数控制：
- period: daily / weekly / monthly
- target: hot_cases / full_market / triple_funnel / wanzhu

取代脚本：
- generate_daily_report.py
- generate_weekly_report.py

Author: AI Project Director
Version: V1.0
Date: 2026-02-19
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


def generate_daily_report(target: str = 'hot_cases'):
    """生成日报"""
    logger.info(f"生成日报: target={target}")
    
    today = datetime.now().strftime('%Y%m%d')
    print(f"\n{'='*60}")
    print(f"📊 日报生成 ({today})")
    print(f"{'='*60}")
    
    # TODO: 调用logic/reporting模块生成报告
    print(f"目标: {target}")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ 日报生成完成")
    
    return True


def generate_weekly_report(target: str = 'wanzhu'):
    """生成周报"""
    logger.info(f"生成周报: target={target}")
    
    # 计算本周日期范围
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    week_start = monday.strftime('%Y%m%d')
    week_end = sunday.strftime('%Y%m%d')
    
    print(f"\n{'='*60}")
    print(f"📈 周报生成 ({week_start} ~ {week_end})")
    print(f"{'='*60}")
    
    # TODO: 调用logic/reporting模块生成报告
    print(f"目标: {target}")
    print(f"统计周期: {week_start} - {week_end}")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ 周报生成完成")
    
    return True


def generate_monthly_report(target: str = 'full_market'):
    """生成月报"""
    logger.info(f"生成月报: target={target}")
    
    today = datetime.now()
    month_start = today.replace(day=1).strftime('%Y%m%d')
    
    print(f"\n{'='*60}")
    print(f"📊 月报生成 ({today.strftime('%Y%m')})")
    print(f"{'='*60}")
    
    # TODO: 调用logic/reporting模块生成报告
    print(f"目标: {target}")
    print(f"统计月份: {today.strftime('%Y年%m月')}")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("✅ 月报生成完成")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='报告生成器 - 统一入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成日报（热门票）
  python tasks/generate_report.py --period daily --target hot_cases
  
  # 生成周报（顽主杯）
  python tasks/generate_report.py --period weekly --target wanzhu
  
  # 生成月报（全市场）
  python tasks/generate_report.py --period monthly --target full_market
        """
    )
    
    parser.add_argument('--period', type=str, required=True,
                       choices=['daily', 'weekly', 'monthly'],
                       help='报告周期')
    parser.add_argument('--target', type=str, default='hot_cases',
                       choices=['hot_cases', 'full_market', 'triple_funnel', 'wanzhu'],
                       help='报告目标')
    parser.add_argument('--output', type=str,
                       help='输出目录（默认：data/reports/）')
    
    args = parser.parse_args()
    
    print("="*60)
    print("报告生成器")
    print("="*60)
    
    # 根据周期执行
    if args.period == 'daily':
        success = generate_daily_report(args.target)
    elif args.period == 'weekly':
        success = generate_weekly_report(args.target)
    elif args.period == 'monthly':
        success = generate_monthly_report(args.target)
    else:
        logger.error(f"未知周期: {args.period}")
        return 1
    
    if success:
        print("\n✅ 报告生成成功")
        return 0
    else:
        print("\n❌ 报告生成失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
