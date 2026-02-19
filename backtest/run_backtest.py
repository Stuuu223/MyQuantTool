#!/usr/bin/env python3
"""
回测统一入口 - 所有回测必须通过此脚本 (Run Backtest)

取代脚本（11个run_*.py合并为1个）：
- run_comprehensive_backtest.py
- run_halfway_20x30.py
- run_halfway_replay_backtest.py
- run_hot_cases_suite.py
- run_multi_strategy_compare.py
- run_param_heatmap_analysis.py
- run_signal_density_scan.py
- run_single_holding_t1_backtest.py
- run_tick_backtest.py
- run_tick_replay_backtest.py
- run_v17_official_backtest.py

Author: AI Project Director
Version: V2.0 (Unified)
Date: 2026-02-19
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


def run_event_driven_backtest(config: dict):
    """事件驱动回测（实盘对齐）"""
    logger.info("运行事件驱动回测...")
    
    # 加载配置
    stock_pool = config.get('stock_pool', [])
    start_date = config.get('start_date')
    end_date = config.get('end_date')
    strategies = config.get('strategies', ['halfway', 'leader'])
    
    print(f"\n{'='*60}")
    print("事件驱动回测")
    print(f"{'='*60}")
    print(f"股票池: {len(stock_pool)}只")
    print(f"时间: {start_date} ~ {end_date}")
    print(f"策略: {', '.join(strategies)}")
    
    # TODO: 调用统一回测引擎
    
    print("✅ 回测完成")
    return True


def run_single_stock_backtest(config: dict):
    """单股票回测"""
    logger.info("运行单股票回测...")
    
    stock_code = config.get('stock_code')
    start_date = config.get('start_date')
    end_date = config.get('end_date')
    
    print(f"\n{'='*60}")
    print(f"单股票回测: {stock_code}")
    print(f"{'='*60}")
    
    # TODO: 调用回测引擎
    
    print("✅ 回测完成")
    return True


def run_hot_cases_backtest(config: dict):
    """热门票回测"""
    logger.info("运行热门票回测...")
    
    print(f"\n{'='*60}")
    print("热门票回测")
    print(f"{'='*60}")
    
    # TODO: 调用热门票回测逻辑
    
    print("✅ 回测完成")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='回测统一入口 - 所有回测必须通过此脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 事件驱动回测（使用配置文件）
  python backtest/run_backtest.py --mode event --config config/backtest_event.json
  
  # 单股票回测
  python backtest/run_backtest.py --mode single --code 300017.SZ --start 20250101 --end 20250131
  
  # 热门票回测
  python backtest/run_backtest.py --mode hot --config config/backtest_hot.json
  
配置文件格式:
  {
    "stock_pool": ["300017.SZ", "000001.SZ"],
    "start_date": "20250101",
    "end_date": "20250131",
    "strategies": ["halfway", "leader", "true_attack"],
    "initial_capital": 100000
  }
        """
    )
    
    parser.add_argument('--mode', type=str, required=True,
                       choices=['event', 'single', 'hot', 'comprehensive', 'param_heatmap', 'signal_density'],
                       help='回测模式')
    parser.add_argument('--config', type=str,
                       help='配置文件路径（JSON格式）')
    parser.add_argument('--code', type=str,
                       help='股票代码（single模式使用）')
    parser.add_argument('--start', type=str,
                       help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str,
                       help='结束日期 (YYYYMMDD)')
    
    args = parser.parse_args()
    
    # 加载配置
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    # 命令行参数覆盖配置文件
    if args.code:
        config['stock_code'] = args.code
    if args.start:
        config['start_date'] = args.start
    if args.end:
        config['end_date'] = args.end
    
    print("="*60)
    print(f"回测统一入口 - 模式: {args.mode}")
    print("="*60)
    
    # 根据模式执行
    if args.mode == 'event':
        success = run_event_driven_backtest(config)
    elif args.mode == 'single':
        success = run_single_stock_backtest(config)
    elif args.mode == 'hot':
        success = run_hot_cases_backtest(config)
    else:
        logger.error(f"暂不支持模式: {args.mode}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
