#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场扫描 CLI 脚本

用法:
    python tasks/scan_market.py --scan-time 09:35 --top 30

Author: MyQuantTool Team
Date: 2026-02-11
Version: Phase 2
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️ 未安装 rich 库，将使用简单文本输出")
    print("安装方式: pip install rich")

from logic.market_scanner import MarketScanner
from logic.logger import get_logger

try:
    from xtquant import xtdata
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False

logger = get_logger(__name__)
console = Console() if RICH_AVAILABLE else None


def get_all_stocks() -> list:
    """
    获取全A股股票列表
    
    Returns:
        股票代码列表
    """
    if not QMT_AVAILABLE:
        raise RuntimeError("⚠️ xtquant 未安装，无法获取股票列表")
    
    try:
        # 获取所有A股股票
        sh_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        return sh_stocks
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return []


def display_results_rich(trap_list: list, top_n: int = 50):
    """
    使用rich库显示扫描结果（彩色表格）
    
    Args:
        trap_list: 诱多榜单
        top_n: 显示前N个结果
    """
    if not trap_list:
        console.print("\n[yellow]⚠️ 未发现符合条件的股票[/yellow]")
        return
    
    # 创建表格
    table = Table(
        title=f"🚨 诱多预警榜单 TOP {min(top_n, len(trap_list))}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    # 添加列
    table.add_column("排名", justify="center", style="cyan", width=6)
    table.add_column("股票代码", justify="center", style="green", width=12)
    table.add_column("预警类型", justify="left", width=40)
    table.add_column("置信度", justify="center", width=10)
    table.add_column("时间", justify="center", style="dim", width=10)
    
    # 添加数据行
    for idx, item in enumerate(trap_list[:top_n], start=1):
        code = item['code']
        reason = item['reason']
        confidence = item['confidence']
        timestamp = item.get('timestamp', '')
        
        # 置信度颜色编码
        if confidence >= 0.8:
            conf_color = "red bold"
        elif confidence >= 0.6:
            conf_color = "yellow"
        else:
            conf_color = "white"
        
        table.add_row(
            f"#{idx}",
            code,
            reason,
            f"[{conf_color}]{confidence:.0%}[/{conf_color}]",
            timestamp
        )
    
    console.print("\n")
    console.print(table)
    console.print("\n")


def display_results_plain(trap_list: list, top_n: int = 50):
    """
    简单文本显示扫描结果（无rich库）
    
    Args:
        trap_list: 诱多榜单
        top_n: 显示前N个结果
    """
    if not trap_list:
        print("\n⚠️ 未发现符合条件的股票\n")
        return
    
    print("\n" + "="*80)
    print(f" 🚨 诱多预警榜单 TOP {min(top_n, len(trap_list))}")
    print("="*80)
    print(f"{'#':<6} {'Code':<12} {'Reason':<50} {'Conf':<8} {'Time':<10}")
    print("-"*80)
    
    for idx, item in enumerate(trap_list[:top_n], start=1):
        code = item['code']
        reason = item['reason'][:48]  # 截断过长文本
        confidence = f"{item['confidence']:.0%}"
        timestamp = item.get('timestamp', '')
        
        print(f"{idx:<6} {code:<12} {reason:<50} {confidence:<8} {timestamp:<10}")
    
    print("="*80 + "\n")


def save_results(trap_list: list, output_dir: str = 'data/scan_results'):
    """
    保存扫描结果到JSON文件
    
    Args:
        trap_list: 诱多榜单
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 构建文件名（带时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"trap_scan_{timestamp}.json"
    filepath = output_path / filename
    
    # 保存JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'scan_time': datetime.now().isoformat(),
            'total_count': len(trap_list),
            'results': trap_list
        }, f, ensure_ascii=False, indent=2)
    
    return filepath


def main():
    """主程序"""
    # 命令行参数解析
    parser = argparse.ArgumentParser(
        description="全A股诱多扫描器 - Phase 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 默认扫描全A股
  python tasks/scan_market.py
  
  # 指定扫描时间点
  python tasks/scan_market.py --scan-time 09:35
  
  # 只显示Top 20
  python tasks/scan_market.py --top 20
  
  # 扫描指定股票列表
  python tasks/scan_market.py --codes 300997.SZ,603697.SH,601869.SH
  
  # 组合参数
  python tasks/scan_market.py --scan-time 10:00 --top 30 --no-save
        """
    )
    
    parser.add_argument(
        '--scan-time',
        type=str,
        default=None,
        help='扫描时间点（HH:MM格式，如 09:35）'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=50,
        help='显示前N个结果（默认 50）'
    )
    
    parser.add_argument(
        '--codes',
        type=str,
        default=None,
        help='指定股票代码列表（逗号分隔，如 300997.SZ,603697.SH）'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='不保存结果到JSON文件'
    )
    
    args = parser.parse_args()
    
    # 检查QMT是否可用
    if not QMT_AVAILABLE:
        if RICH_AVAILABLE:
            console.print(Panel(
                "[red bold]❌ xtquant 未安装[/red bold]\n\n"
                "请先安装 QMT 并配置 xtquant 环境\n"
                "详细步骤请参考： README.md",
                title="错误",
                border_style="red"
            ))
        else:
            print("\n❌ xtquant 未安装")
            print("请先安装 QMT 并配置 xtquant 环境")
            print("详细步骤请参考： README.md\n")
        sys.exit(1)
    
    # 获取股票列表
    if args.codes:
        # 使用指定股票列表
        stock_list = [code.strip() for code in args.codes.split(',')]
        if RICH_AVAILABLE:
            console.print(f"\n[cyan]🔍 扫描指定股票: {len(stock_list)} 只[/cyan]")
        else:
            print(f"\n🔍 扫描指定股票: {len(stock_list)} 只")
    else:
        # 获取全A股
        if RICH_AVAILABLE:
            with console.status("[bold green]正在获取全A股股票列表...", spinner="dots"):
                stock_list = get_all_stocks()
        else:
            print("正在获取全A股股票列表...")
            stock_list = get_all_stocks()
        
        if not stock_list:
            if RICH_AVAILABLE:
                console.print("[red]❌ 获取股票列表失败[/red]")
            else:
                print("❌ 获取股票列表失败")
            sys.exit(1)
        
        if RICH_AVAILABLE:
            console.print(f"[green]✅ 成功获取 {len(stock_list)} 只股票[/green]")
        else:
            print(f"✅ 成功获取 {len(stock_list)} 只股票")
    
    # 创建扫描器
    if RICH_AVAILABLE:
        with console.status("[bold green]初始化扫描器...", spinner="dots"):
            scanner = MarketScanner()
    else:
        print("初始化扫描器...")
        scanner = MarketScanner()
    
    # 执行扫描
    if RICH_AVAILABLE:
        console.print("\n" + "="*80)
        console.print(f"[bold cyan]🚀 开始全市场扫描[/bold cyan]")
        console.print("="*80 + "\n")
    else:
        print("\n" + "="*80)
        print("🚀 开始全市场扫描")
        print("="*80 + "\n")
    
    trap_list = scanner.scan(stock_list, scan_time=args.scan_time)
    
    # 显示结果
    if RICH_AVAILABLE:
        display_results_rich(trap_list, top_n=args.top)
    else:
        display_results_plain(trap_list, top_n=args.top)
    
    # 保存结果
    if not args.no_save and trap_list:
        filepath = save_results(trap_list)
        if RICH_AVAILABLE:
            console.print(f"[green]✅ 结果已保存到: {filepath}[/green]\n")
        else:
            print(f"✅ 结果已保存到: {filepath}\n")
    
    # 显示失败统计
    failed_codes = scanner.get_failed_codes()
    if failed_codes:
        if RICH_AVAILABLE:
            console.print(f"[yellow]⚠️ {len(failed_codes)} 只股票处理失败（详见日志）[/yellow]\n")
        else:
            print(f"⚠️ {len(failed_codes)} 只股票处理失败（详见日志）\n")


if __name__ == '__main__':
    main()
