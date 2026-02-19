#!/usr/bin/env python3
"""
下载管理器 - 统一入口 (Download Manager)

整合所有下载脚本，通过参数控制行为：
- 股票池：--universe {wanzhu_top150, wanzhu_selected, custom}
- 数据源：--source {tick, 1m, daily, equity}
- 模式：--mode {full, incremental, missing}

取代脚本：
- download_150_stocks_tick.py
- download_missing_150.py
- download_single_test.py
- download_wangsu_tick.py
- download_wanzhu_tick_data.py
- download_wanzhu_top150_tick.py
- download_from_list.py
- fetch_1m_data.py
- per_day_tick_runner.py

Author: AI Project Director
Version: V1.0
Date: 2026-02-19
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_providers.tick_provider import TickProvider
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def load_stock_universe(universe: str, custom_path: Optional[str] = None) -> List[str]:
    """加载股票池
    
    Args:
        universe: 股票池类型
        custom_path: 自定义股票列表路径
    
    Returns:
        股票代码列表
    """
    if universe == 'wanzhu_top150':
        csv_path = PROJECT_ROOT / 'config' / 'wanzhu_top150_tick_download.json'
        import json
        with open(csv_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [item['qmt_code'] for item in data.get('stocks', [])]
    
    elif universe == 'wanzhu_selected':
        csv_path = PROJECT_ROOT / 'data' / 'wanzhu_data' / 'processed' / 'wanzhu_selected_150.csv'
        import pandas as pd
        df = pd.read_csv(csv_path)
        codes = []
        for _, row in df.iterrows():
            code = str(row['code']).zfill(6)
            if code.startswith('6'):
                codes.append(f"{code}.SH")
            else:
                codes.append(f"{code}.SZ")
        return codes
    
    elif universe == 'custom' and custom_path:
        with open(custom_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    
    else:
        raise ValueError(f"未知股票池: {universe}")


def download_tick_data(stock_codes: List[str], start_date: str, end_date: str, mode: str = 'full'):
    """下载Tick数据"""
    logger.info(f"开始下载Tick数据: {len(stock_codes)}只股票, {start_date} 至 {end_date}")
    
    with TickProvider() as provider:
        if mode == 'missing':
            # 只下载缺失的数据
            missing = provider.get_missing_stocks(stock_codes, start_date)
            if missing:
                logger.info(f"发现{len(missing)}只股票需要补录")
                stock_codes = missing
            else:
                logger.info("所有股票数据已完整，无需下载")
                return
        
        result = provider.download_ticks(stock_codes, start_date, end_date)
        
        logger.info(f"下载完成: 成功{result.get('success_count', 0)}, "
                   f"失败{result.get('failed_count', 0)}")


def download_minute_data(stock_codes: List[str], start_date: str, end_date: str, period: str = '1m'):
    """下载分钟数据"""
    logger.info(f"开始下载{period}数据: {len(stock_codes)}只股票")
    
    with TickProvider() as provider:
        result = provider.download_minute_data(stock_codes, start_date, end_date, period)
        
        logger.info(f"下载完成: 成功{result.get('success_count', 0)}, "
                   f"失败{result.get('failed_count', 0)}")


def check_coverage(stock_codes: List[str], start_date: str, end_date: str):
    """检查数据覆盖情况"""
    logger.info(f"检查数据覆盖: {len(stock_codes)}只股票")
    
    with TickProvider() as provider:
        coverage = provider.check_coverage(stock_codes, start_date, end_date)
        
        print("\n" + "=" * 60)
        print("数据覆盖检查报告")
        print("=" * 60)
        print(f"总股票数: {coverage['total']}")
        print(f"有数据: {coverage['has_data']} ({coverage['has_data']/coverage['total']*100:.1f}%)")
        print(f"缺失: {coverage['missing']} ({coverage['missing']/coverage['total']*100:.1f}%)")
        
        if coverage['missing_stocks']:
            print("\n缺失股票列表:")
            for code in coverage['missing_stocks'][:10]:
                print(f"  - {code}")
            if len(coverage['missing_stocks']) > 10:
                print(f"  ... 等共{len(coverage['missing_stocks'])}只")


def main():
    parser = argparse.ArgumentParser(
        description='下载管理器 - 统一数据下载入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 下载顽主Top150的Tick数据
  python scripts/download_manager.py --universe wanzhu_top150 --source tick --start-date 20250101 --end-date 20250131
  
  # 只下载缺失的数据
  python scripts/download_manager.py --universe wanzhu_selected --source tick --mode missing
  
  # 检查数据覆盖
  python scripts/download_manager.py --universe wanzhu_selected --action check --start-date 20250101 --end-date 20250131
  
  # 下载1分钟K线
  python scripts/download_manager.py --universe wanzhu_top150 --source 1m --start-date 20250101 --end-date 20250131
        """
    )
    
    parser.add_argument('--universe', type=str, default='wanzhu_selected',
                       choices=['wanzhu_top150', 'wanzhu_selected', 'custom'],
                       help='股票池选择')
    parser.add_argument('--custom-path', type=str,
                       help='自定义股票列表路径（universe=custom时使用）')
    parser.add_argument('--source', type=str, default='tick',
                       choices=['tick', '1m', '5m', 'daily'],
                       help='数据源类型')
    parser.add_argument('--mode', type=str, default='full',
                       choices=['full', 'incremental', 'missing'],
                       help='下载模式：full=全量, incremental=增量, missing=只补缺失')
    parser.add_argument('--start-date', type=str,
                       help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str,
                       help='结束日期 (YYYYMMDD)')
    parser.add_argument('--action', type=str, default='download',
                       choices=['download', 'check'],
                       help='操作类型')
    
    args = parser.parse_args()
    
    # 加载股票池
    try:
        stock_codes = load_stock_universe(args.universe, args.custom_path)
        logger.info(f"加载股票池: {len(stock_codes)}只 ({args.universe})")
    except Exception as e:
        logger.error(f"加载股票池失败: {e}")
        sys.exit(1)
    
    # 执行操作
    if args.action == 'check':
        if not args.start_date or not args.end_date:
            logger.error("检查模式需要指定--start-date和--end-date")
            sys.exit(1)
        check_coverage(stock_codes, args.start_date, args.end_date)
    
    elif args.action == 'download':
        if not args.start_date or not args.end_date:
            logger.error("下载模式需要指定--start-date和--end-date")
            sys.exit(1)
        
        if args.source == 'tick':
            download_tick_data(stock_codes, args.start_date, args.end_date, args.mode)
        elif args.source in ['1m', '5m']:
            download_minute_data(stock_codes, args.start_date, args.end_date, args.source)
        else:
            logger.error(f"暂不支持数据源: {args.source}")
            sys.exit(1)


if __name__ == '__main__':
    main()
