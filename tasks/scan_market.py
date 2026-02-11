#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI全市场扫描器

功能：
  - 全市场批量扫描（5000+股票）
  - 彩色表格输出（rich库）
  - 支持三个时间节点（09:35, 10:00, 14:00）
  - 自动保存JSON结果

使用方式：
  python tasks/scan_market.py --time 09:35
  python tasks/scan_market.py --time 10:00
  python tasks/scan_market.py --time 14:00

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.market_scanner import MarketScanner
from logic.logger import get_logger

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

logger = get_logger(__name__)
console = Console() if RICH_AVAILABLE else None


def load_equity_info(equity_file: str = 'data/equity_info.json') -> dict:
    """
    加载股本信息
    
    Args:
        equity_file: 股本信息文件路径
    
    Returns:
        股本信息字典 {code: {float_shares, total_shares}}
    """
    equity_path = project_root / equity_file
    
    if not equity_path.exists():
        logger.error(f"❌ 股本信息文件不存在: {equity_path}")
        logger.info("💡 提示: 请先使用AkShare下载股本信息")
        return {}
    
    with open(equity_path, 'r', encoding='utf-8') as f:
        equity_info = json.load(f)
    
    logger.info(f"✅ 已加载股本信息: {len(equity_info)} 只股票")
    return equity_info


def get_all_stocks() -> list:
    """
    获取全A股股票列表
    
    Returns:
        股票代码列表 ['000001.SZ', '000002.SZ', ...]
    """
    if not QMT_AVAILABLE:
        logger.error("❌ xtquant未安装，无法获取股票列表")
        return []
    
    try:
        # 获取沪深A股
        sh_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        logger.info(f"✅ 已获取全A股列表: {len(sh_stocks)} 只股票")
        return sh_stocks
    except Exception as e:
        logger.error(f"❌ 获取股票列表失败: {e}")
        return []


def display_results_rich(results: list):
    """
    使用rich库显示彩色表格
    
    Args:
        results: 扫描结果列表
    """
    if not RICH_AVAILABLE or not console:
        display_results_plain(results)
        return
    
    # 创建表格
    table = Table(title="🚨 诱多预警榜单 TOP 50", show_header=True, header_style="bold magenta")
    
    table.add_column("排名", style="cyan", justify="right", width=6)
    table.add_column("股票代码", style="yellow", width=12)
    table.add_column("置信度", style="green", justify="right", width=8)
    table.add_column("信号", style="red", width=15)
    table.add_column("预警原因", style="white", width=50)
    table.add_column("时间", style="blue", width=10)
    
    # 添加数据行
    for idx, result in enumerate(results, 1):
        confidence = f"{result['confidence']:.1%}"
        signal = result['final_signal']
        reason = result['reason'][:50] if len(result['reason']) > 50 else result['reason']
        timestamp = result['timestamp']
        code = result.get('code', 'N/A')
        
        # 置信度颜色
        if result['confidence'] > 0.8:
            confidence_style = "bold red"
        elif result['confidence'] > 0.6:
            confidence_style = "yellow"
        else:
            confidence_style = "white"
        
        table.add_row(
            str(idx),
            code,
            Text(confidence, style=confidence_style),
            signal,
            reason,
            timestamp
        )
    
    # 显示表格
    console.print(table)
    
    # 显示统计信息
    stats_panel = Panel(
        f"[bold green]✅ 扫描完成[/bold green]\n"
        f"共发现 [bold yellow]{len(results)}[/bold yellow] 只疑似诱多股票\n"
        f"高置信度(>80%): [bold red]{sum(1 for r in results if r['confidence'] > 0.8)}[/bold red] 只\n"
        f"中置信度(60-80%): [bold yellow]{sum(1 for r in results if 0.6 < r['confidence'] <= 0.8)}[/bold yellow] 只",
        title="📊 统计信息",
        border_style="green"
    )
    console.print(stats_panel)


def display_results_plain(results: list):
    """
    纯文本表格显示（不使用rich库）
    
    Args:
        results: 扫描结果列表
    """
    print("\n" + "="*100)
    print("🚨 诱多预警榜单 TOP 50")
    print("="*100)
    print(f"{'排名':<6} {'股票代码':<12} {'置信度':<8} {'信号':<15} {'预警原因':<50} {'时间':<10}")
    print("-"*100)
    
    for idx, result in enumerate(results, 1):
        confidence = f"{result['confidence']:.1%}"
        signal = result['final_signal']
        reason = result['reason'][:50] if len(result['reason']) > 50 else result['reason']
        timestamp = result['timestamp']
        code = result.get('code', 'N/A')
        
        print(f"{idx:<6} {code:<12} {confidence:<8} {signal:<15} {reason:<50} {timestamp:<10}")
    
    print("="*100)
    print(f"✅ 扫描完成: 共发现 {len(results)} 只疑似诱多股票")
    print(f"   高置信度(>80%): {sum(1 for r in results if r['confidence'] > 0.8)} 只")
    print(f"   中置信度(60-80%): {sum(1 for r in results if 0.6 < r['confidence'] <= 0.8)} 只")
    print("="*100 + "\n")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='全市场诱多扫描器')
    parser.add_argument('--time', type=str, default=None, 
                       help='扫描时间节点（09:35 | 10:00 | 14:00），默认当前时间')
    parser.add_argument('--output', type=str, default='data/scan_results',
                       help='输出目录，默认 data/scan_results')
    
    args = parser.parse_args()
    
    # 检查依赖
    if not QMT_AVAILABLE:
        logger.error("❌ xtquant未安装，无法运行扫描器")
        sys.exit(1)
    
    # 加载股本信息
    equity_info = load_equity_info()
    if not equity_info:
        logger.error("❌ 股本信息加载失败，无法运行扫描器")
        sys.exit(1)
    
    # 获取股票列表
    stock_list = get_all_stocks()
    if not stock_list:
        logger.error("❌ 股票列表获取失败，无法运行扫描器")
        sys.exit(1)
    
    # 创建扫描器
    scanner = MarketScanner(
        equity_info=equity_info,
        cache_dir='data/kline_cache',
        enable_cache=True,
        parallel_threshold=100
    )
    
    # 执行扫描
    try:
        results = scanner.scan(stock_list, scan_time=args.time)
        
        if not results:
            logger.warning("⚠️ 未发现疑似诱多股票")
            return
        
        # 显示结果
        if RICH_AVAILABLE:
            display_results_rich(results)
        else:
            display_results_plain(results)
        
        # 保存结果
        json_file = scanner.save_results(results, output_dir=args.output)
        logger.info(f"💾 结果已保存: {json_file}")
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️ 用户中断扫描")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 扫描失败: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
