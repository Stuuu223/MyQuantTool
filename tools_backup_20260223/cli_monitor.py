#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyQuantTool 命令行监控终端 (CLI Monitor)

功能：
- 实时显示三把斧状态
- 时机斧：板块雷达（Leaders + Breadth）
- 资格斧：狙击镜（最终买入信号）
- 防守斧：拦截网（被拦截的垃圾票）

运行方式：
    python tools/cli_monitor.py

依赖：
    pip install rich
"""

import time
import json
import os
from datetime import datetime
from pathlib import Path

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.console import Console
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  rich库未安装，请运行: pip install rich")
    exit(1)

# 配置路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "monitor_state.json"
LOG_DIR = PROJECT_ROOT / "logs"

console = Console()


def make_sector_table(sector_data):
    """生成时机斧-板块雷达表"""
    table = Table(box=box.SIMPLE_HEAD, expand=True)
    table.add_column("板块名称", style="cyan", width=20)
    table.add_column("Leaders", justify="center", style="magenta", width=10)
    table.add_column("Breadth", justify="center", style="green", width=12)
    table.add_column("状态", justify="center", width=12)
    
    if not sector_data:
        table.add_row("-", "-", "-", "等待数据...")
    else:
        # 按 Leaders 排序
        sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1].get('leaders', 0), reverse=True)
        
        for name, stats in sorted_sectors[:10]:  # 显示前10个
            leaders = stats.get('leaders', 0)
            breadth = stats.get('breadth', 0)
            is_hot = leaders >= 3 and breadth >= 0.35
            
            if is_hot:
                status = "🔥 共振"
                style = "bold red"
            else:
                status = "等待"
                style = "dim"
            
            table.add_row(name, str(leaders), f"{breadth:.1%}", status, style=style)
    
    return Panel(table, title="[bold red]🛡️ 时机斧 - 板块雷达[/]", border_style="red")


def make_signal_table(signals):
    """生成资格斧-狙击镜表"""
    table = Table(box=box.SIMPLE_HEAD, expand=True)
    table.add_column("时间", style="dim", width=10)
    table.add_column("代码", style="yellow", width=12)
    table.add_column("名称", width=16)
    table.add_column("现价", justify="right", width=10)
    table.add_column("资金流(万)", justify="right", width=12)
    
    if not signals:
        table.add_row("-", "-", "暂无信号", "-", "-")
    else:
        for s in signals[-10:]:  # 显示最近10个
            flow = s.get('flow', 0)
            flow_color = "red" if flow > 0 else "green"
            table.add_row(
                s.get('time', '-'),
                s.get('code', '-'),
                s.get('name', '-'),
                f"{s.get('price', 0):.2f}",
                f"[{flow_color}]{flow:.0f}[/]"
            )
    
    return Panel(table, title="[bold green]🎯 资格斧 - 狙击镜[/]", border_style="green")


def make_log_panel():
    """生成防守斧-拦截日志"""
    try:
        # 查找最新的日志文件
        log_files = sorted(LOG_DIR.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if log_files:
            log_file = log_files[0]
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 过滤拦截信息
            intercepts = []
            for line in lines:
                line_str = line.strip()
                if any(keyword in line_str for keyword in ["拦截", "TAIL_RALLY", "TRAP", "防守斧"]):
                    intercepts.append(line_str)
            
            content = "\n".join(intercepts[-15:])  # 显示最后15条
        else:
            content = "等待日志..."
    except Exception as e:
        content = f"读取日志失败: {e}"
    
    return Panel(content, title="[bold blue]🛡️ 防守斧 - 拦截网[/]", border_style="blue")


def make_summary_panel(sector_data, signals):
    """生成汇总面板"""
    total_sectors = len(sector_data)
    hot_sectors = sum(1 for s in sector_data.values() if s.get('leaders', 0) >= 3 and s.get('breadth', 0) >= 0.35)
    total_signals = len(signals)
    
    summary = f"""
    [bold yellow]系统状态[/]
    共振板块: {hot_sectors}/{total_sectors}
    买入信号: {total_signals}
    
    [dim]刷新时间: {datetime.now().strftime('%H:%M:%S')}[/]
    """
    
    return Panel(summary, title="[bold cyan]📊 系统汇总[/]", border_style="cyan")


def generate_layout():
    """生成布局"""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="upper", ratio=1),
        Layout(name="middle", size=20),
        Layout(name="footer", size=3)
    )
    
    layout["upper"].split_row(
        Layout(name="sector", ratio=1),
        Layout(name="signal", ratio=1)
    )
    
    # 读取状态文件
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
        else:
            state = {"sectors": {}, "signals": []}
    except Exception as e:
        state = {"sectors": {}, "signals": []}
    
    # 生成各个面板
    header = Text("🚀 MyQuantTool 命令行监控终端", style="bold yellow")
    layout["header"].update(Panel(header, border_style="yellow"))
    
    layout["sector"].update(make_sector_table(state.get("sectors", {})))
    layout["signal"].update(make_signal_table(state.get("signals", [])))
    layout["middle"].update(make_log_panel())
    layout["footer"].update(make_summary_panel(state.get("sectors", {}), state.get("signals", [])))
    
    return layout


def main():
    """主函数"""
    console.clear()
    
    # 启动信息
    console.print("\n")
    console.print("[bold yellow]🚀 MyQuantTool 命令行监控终端启动...[/]")
    console.print("[dim]读取状态文件: {}[/]".format(STATE_FILE))
    console.print("[dim]刷新频率: 1秒/次[/]")
    console.print("\n")
    time.sleep(1)
    
    # 启动实时监控
    with Live(generate_layout(), refresh_per_second=1, screen=True) as live:
        while True:
            try:
                live.update(generate_layout())
                time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️  监控已停止[/]")
                break
            except Exception as e:
                console.print(f"\n[red]❌ 错误: {e}[/]")
                time.sleep(1)


if __name__ == "__main__":
    main()