#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场QPST扫描器 - 阶段2 CLI脚本

功能：
1. 扫描全A股5000+股票
2. 三阶段渐进式筛选（5000→300→100→50）
3. 输出TOP 20-50诱多榜单
4. 彩色CLI输出 + JSON数据

使用方法：
    # 扫描全市场（默认设置）
    python tasks/scan_market_qpst.py
    
    # 自定义扫描时间点
    python tasks/scan_market_qpst.py --time 09:35
    
    # 指定输出目录
    python tasks/scan_market_qpst.py --output data/scan_results/
    
    # 禁用多进程
    python tasks/scan_market_qpst.py --no-multiprocess

作者：量化CTO
日期：2026-02-11
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich import box
except ImportError:
    print("\n⚠️  需要安装 rich 库: pip install rich")
    sys.exit(1)

from logic.market_scanner import MarketScanner
from logic.batch_qpst_analyzer import BatchQPSTAnalyzer
from logic.trap_detector_batch import TrapDetectorBatch

console = Console()


def print_banner():
    """打印启动横幅"""
    banner = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 全市场QPST扫描器 - 阶段2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
扫描范围: 全A股 5000+ 股票
筛选机制: 三阶段渐进式 (5000→300→100→50)
输出结果: TOP 20-50 诱多榜单
    """
    console.print(Panel(banner, style="bold cyan", box=box.DOUBLE))


def load_stock_list() -> List[str]:
    """加载全A股股票列表"""
    with console.status("[加载中] 获取全A股股票列表...", spinner="dots"):
        try:
            import xtdata
            # 获取所有A股股票
            stock_list = xtdata.get_stock_list_in_sector('沸腾板块.A股列表')
            console.print(f"\n✅ 成功加载 {len(stock_list)} 只股票\n", style="bold green")
            return stock_list
        except Exception as e:
            console.print(f"\n❌ 加载股票列表失败: {e}\n", style="bold red")
            console.print("⚠️  请确认QMT客户端已登录\n", style="yellow")
            sys.exit(1)


def run_scan(scan_time: str, stock_list: List[str], use_multiprocess: bool = True, batch_size: int = 500) -> List[Dict]:
    """执行全市场扫描"""
    
    console.print(f"\n🔍 扫描时间点: [bold cyan]{scan_time}[/bold cyan]")
    console.print(f"📊 扫描股票数: [bold cyan]{len(stock_list)}[/bold cyan]")
    console.print(f"⚙️  多进程: [bold cyan]{'启用' if use_multiprocess else '关闭'}[/bold cyan]")
    console.print(f"📦 分批大小: [bold cyan]{batch_size}只/批[/bold cyan]\n")
    
    # 初始化扫描器
    scanner = MarketScanner(
        use_multiprocess=use_multiprocess,
        batch_size=batch_size  # 🔥 [P1 FIX] 传递分批大小参数
    )
    
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("[扫描中] 执行QPST四维分析...", total=None)
        
        try:
            trap_list = scanner.scan(stock_list=stock_list, scan_time=scan_time)
            progress.update(task, completed=True)
        except Exception as e:
            console.print(f"\n\n❌ 扫描失败: {e}\n", style="bold red")
            import traceback
            traceback.print_exc()
            return []
    
    elapsed = time.time() - start_time
    console.print(f"\n✅ 扫描完成! 耗时: [bold green]{elapsed:.1f}秒[/bold green]\n")
    
    return trap_list


def display_results(trap_list: List[Dict]):
    """展示扫描结果（彩色表格）"""
    
    if not trap_list:
        console.print("🎉 未发现诱多信号，市场较为健康\n", style="bold green")
        return
    
    console.print(f"\n⚠️  发现 [bold red]{len(trap_list)}[/bold red] 只疑似诱多股票\n")
    
    # 创建表格
    table = Table(
        title=f"🚨 诱多预警榜单 TOP {len(trap_list)}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("排名", style="dim", width=6, justify="center")
    table.add_column("股票代码", style="cyan", width=12)
    table.add_column("预警类型", style="yellow", width=20)
    table.add_column("置信度", style="green", width=10, justify="center")
    table.add_column("原因", style="white", width=40)
    table.add_column("时间", style="blue", width=10)
    
    for idx, item in enumerate(trap_list[:50], 1):
        # 颜色编码
        rank_style = "bold red" if idx <= 10 else "yellow" if idx <= 20 else "white"
        confidence_color = "red" if item['confidence'] >= 90 else "yellow" if item['confidence'] >= 70 else "green"
        
        table.add_row(
            f"#{idx}",
            item['code'],
            ", ".join(item.get('trap_signals', [])),
            f"[{confidence_color}]{item['confidence']:.0f}%[/{confidence_color}]",
            item['reason'][:38] + ".." if len(item['reason']) > 40 else item['reason'],
            item['timestamp'],
            style=rank_style if idx <= 3 else None
        )
    
    console.print(table)


def save_results(trap_list: List[Dict], output_dir: str):
    """保存扫描结果"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = output_path / f"scan_qpst_{timestamp}.json"
    
    # 保存JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'scan_time': datetime.now().isoformat(),
            'total_stocks': len(trap_list),
            'results': trap_list
        }, f, ensure_ascii=False, indent=2)
    
    console.print(f"\n💾 扫描结果已保存: [cyan]{json_file}[/cyan]\n")


def main():
    parser = argparse.ArgumentParser(
        description="全市场QPST扫描器 - 阶段2",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--time',
        type=str,
        default='10:00',
        help="扫描时间点 (默认: 10:00)"
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='data/scan_results/',
        help="输出目录 (默认: data/scan_results/)"
    )
    
    parser.add_argument(
        '--no-multiprocess',
        action='store_true',
        help="禁用多进程加速"
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help="预筛选分批大小 (默认: 500只/批，防止内存溢出)"
    )
    
    args = parser.parse_args()
    
    # 打印启动横幅
    print_banner()
    
    # 加载股票列表
    stock_list = load_stock_list()
    
    # 执行扫描
    trap_list = run_scan(
        scan_time=args.time,
        stock_list=stock_list,
        use_multiprocess=not args.no_multiprocess,
        batch_size=args.batch_size  # 🔥 [P1 FIX] 传递分批大小参数
    )
    
    # 展示结果
    display_results(trap_list)
    
    # 保存结果
    if trap_list:
        save_results(trap_list, args.output)
    
    console.print("\n✨ 扫描任务完成!\n", style="bold green")


if __name__ == '__main__':
    main()
