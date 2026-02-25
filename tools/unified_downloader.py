#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一下载器 - All-in-One Data Downloader
支持日K、Tick、全息数据下载，断点续传，Rich进度条

用法:
    python tools/unified_downloader.py --type daily_k --days 365
    python tools/unified_downloader.py --type tick --start-date 20250101 --end-date 20260225
    python tools/unified_downloader.py --type holographic --date 20260224

Author: CTO重构
Date: 2026-02-25
"""

import os
import sys
import json
import time
import click
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# 添加项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 状态文件路径
STATE_DIR = PROJECT_ROOT / "data"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_state_file(download_type: str) -> Path:
    """获取状态文件路径"""
    return STATE_DIR / f"download_state_{download_type}.json"


def load_state(download_type: str) -> Dict:
    """加载断点状态"""
    state_file = get_state_file(download_type)
    if state_file.exists():
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"completed": [], "failed": [], "last_update": None}


def save_state(download_type: str, state: Dict):
    """保存断点状态"""
    state_file = get_state_file(download_type)
    state["last_update"] = datetime.now().isoformat()
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def generate_dates(start_date: str, end_date: str) -> List[str]:
    """生成日期列表（只保留工作日）"""
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:  # 工作日
            dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


def download_daily_k(days: int = 365, resume: bool = True):
    """下载全市场日K数据"""
    from xtquant import xtdata
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.console import Console
    
    console = Console()
    
    # 计算日期范围
    today = datetime.now()
    start_date = (today - timedelta(days=days)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    console.print(f"\n[bold cyan]📊 日K数据下载器[/bold cyan]")
    console.print(f"📅 日期范围: {start_date} ~ {end_date} ({days}天)")
    
    # 加载断点状态
    state = load_state("daily_k") if resume else {"completed": [], "failed": []}
    completed_set = set(state.get("completed", []))
    
    # 获取股票列表
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    console.print(f"📈 股票数量: {len(all_stocks)} 只")
    
    # 过滤已完成的
    pending_stocks = [s for s in all_stocks if s not in completed_set]
    console.print(f"⏭️  待下载: {len(pending_stocks)} 只 (已完成: {len(completed_set)})")
    
    if not pending_stocks:
        console.print("[green]✅ 所有数据已下载完成！[/green]")
        return
    
    # 分批下载
    BATCH_SIZE = 500
    total_batches = (len(pending_stocks) + BATCH_SIZE - 1) // BATCH_SIZE
    
    success_count = len(completed_set)
    failed_count = len(state.get("failed", []))
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]下载进度", total=len(pending_stocks))
        
        for i in range(0, len(pending_stocks), BATCH_SIZE):
            batch = pending_stocks[i:i+BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            
            try:
                xtdata.download_history_data2(
                    stock_list=batch,
                    period='1d',
                    start_time=start_date,
                    end_time=end_date
                )
                
                # 标记完成
                for stock in batch:
                    state["completed"].append(stock)
                    completed_set.add(stock)
                
                success_count += len(batch)
                progress.update(task, advance=len(batch))
                
            except Exception as e:
                state["failed"].extend(batch)
                failed_count += len(batch)
                console.print(f"[red]❌ 批次 {batch_num} 失败: {e}[/red]")
            
            # 定期保存状态
            if batch_num % 5 == 0:
                save_state("daily_k", state)
    
    # 最终保存状态
    save_state("daily_k", state)
    
    console.print(f"\n[green]✅ 下载完成！[/green]")
    console.print(f"   成功: {success_count} 只")
    console.print(f"   失败: {failed_count} 只")


def download_tick_data(start_date: str, end_date: str, stock_list: List[str] = None, resume: bool = True):
    """下载Tick数据"""
    from xtquant import xtdata
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.console import Console
    
    console = Console()
    
    console.print(f"\n[bold cyan]📊 Tick数据下载器[/bold cyan]")
    console.print(f"📅 日期范围: {start_date} ~ {end_date}")
    
    # 加载断点状态
    state_key = f"tick_{start_date}_{end_date}"
    state = load_state(state_key) if resume else {"completed": [], "failed": []}
    completed_set = set(state.get("completed", []))
    
    # 获取股票列表
    if not stock_list:
        stock_list = xtdata.get_stock_list_in_sector('沪深A股')
    
    console.print(f"📈 股票数量: {len(stock_list)} 只")
    
    # 过滤已完成的
    pending_stocks = [s for s in stock_list if s not in completed_set]
    console.print(f"⏭️  待下载: {len(pending_stocks)} 只 (已完成: {len(completed_set)})")
    
    if not pending_stocks:
        console.print("[green]✅ 所有数据已下载完成！[/green]")
        return
    
    success_count = len(completed_set)
    failed_count = len(state.get("failed", []))
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]下载进度", total=len(pending_stocks))
        
        for i, stock in enumerate(pending_stocks):
            try:
                # 标准化代码
                if "." not in stock:
                    if stock.startswith("6"):
                        stock = f"{stock}.SH"
                    else:
                        stock = f"{stock}.SZ"
                
                # 下载
                xtdata.download_history_data(
                    stock_code=stock,
                    period="tick",
                    start_time=start_date,
                    end_time=end_date
                )
                
                # 验证
                data = xtdata.get_local_data(
                    field_list=["time"],
                    stock_list=[stock],
                    period="tick",
                    start_time=start_date,
                    end_time=end_date
                )
                
                if data and stock in data and len(data[stock]) > 100:
                    state["completed"].append(stock)
                    success_count += 1
                else:
                    state["failed"].append(stock)
                    failed_count += 1
                
            except Exception as e:
                state["failed"].append(stock)
                failed_count += 1
            
            progress.update(task, advance=1)
            
            # 定期保存状态
            if (i + 1) % 50 == 0:
                save_state(state_key, state)
            
            # 避免限流
            time.sleep(0.1)
    
    # 最终保存状态
    save_state(state_key, state)
    
    console.print(f"\n[green]✅ 下载完成！[/green]")
    console.print(f"   成功: {success_count} 只")
    console.print(f"   失败: {failed_count} 只")


def download_holographic(date: str, resume: bool = True):
    """下载全息数据（V18双Ratio筛选后的股票Tick）
    
    筛选条件（对齐实盘live_sniper参数）：
    - 量比分位数: 0.95
    - 换手率范围: 3% - 70%
    - 剔除: 科创板、北交所
    """
    from xtquant import xtdata
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.console import Console
    from logic.core.config_manager import get_config_manager
    
    console = Console()
    config_manager = get_config_manager()
    
    # 获取实盘参数
    live_sniper_config = config_manager._config.get('live_sniper', {})
    volume_percentile = live_sniper_config.get('volume_ratio_percentile', 0.95)
    min_turnover = live_sniper_config.get('min_active_turnover_rate', 3.0)
    max_turnover = live_sniper_config.get('death_turnover_rate', 70.0)
    
    console.print(f"\n[bold cyan]📊 全息数据下载器 (V18双Ratio筛选)[/bold cyan]")
    console.print(f"📅 目标日期: {date}")
    console.print(f"📐 筛选参数:")
    console.print(f"   量比分位数: {volume_percentile}")
    console.print(f"   换手率范围: {min_turnover}% - {max_turnover}%")
    
    # 加载断点状态
    state_key = f"holographic_{date}"
    state = load_state(state_key) if resume else {"completed": [], "failed": []}
    completed_set = set(state.get("completed", []))
    
    # 获取粗筛股票池 - CTO强制：禁止回退到全市场
    console.print("\n🔍 执行V18双Ratio粗筛...")
    try:
        from logic.data_providers.universe_builder import UniverseBuilder
        builder = UniverseBuilder()
        stock_list = builder.get_daily_universe(date)
        
        if not stock_list:
            console.print(f"[red]❌ 粗筛返回空股票池，可能是非交易日或数据问题[/red]")
            console.print(f"[yellow]💡 提示: 请检查日期是否为交易日，或Tushare Token是否配置[/yellow]")
            return
            
    except Exception as e:
        console.print(f"[red]❌ 粗筛失败: {e}[/red]")
        console.print(f"[yellow]💡 提示: 请确保TUSHARE_TOKEN环境变量已设置[/yellow]")
        return
    
    console.print(f"\n✅ 粗筛完成: {len(stock_list)} 只股票")
    
    # 过滤已完成的
    pending_stocks = [s for s in stock_list if s not in completed_set]
    console.print(f"⏭️  待下载: {len(pending_stocks)} 只 (已完成: {len(completed_set)})")
    
    if not pending_stocks:
        console.print("[green]✅ 所有数据已下载完成！[/green]")
        return
    
    success_count = len(completed_set)
    failed_count = len(state.get("failed", []))
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]下载进度", total=len(pending_stocks))
        
        for i, stock in enumerate(pending_stocks):
            try:
                # 标准化代码
                if "." not in stock:
                    if stock.startswith("6"):
                        stock = f"{stock}.SH"
                    else:
                        stock = f"{stock}.SZ"
                
                # 下载
                xtdata.download_history_data(
                    stock_code=stock,
                    period="tick",
                    start_time=date,
                    end_time=date
                )
                
                # 验证
                data = xtdata.get_local_data(
                    field_list=["time"],
                    stock_list=[stock],
                    period="tick",
                    start_time=date,
                    end_time=date
                )
                
                if data and stock in data and len(data[stock]) > 100:
                    state["completed"].append(stock)
                    success_count += 1
                else:
                    state["failed"].append(stock)
                    failed_count += 1
                
            except Exception as e:
                state["failed"].append(stock)
                failed_count += 1
            
            progress.update(task, advance=1)
            
            # 定期保存状态
            if (i + 1) % 20 == 0:
                save_state(state_key, state)
            
            # 避免限流
            time.sleep(0.1)
    
    # 最终保存状态
    save_state(state_key, state)
    
    console.print(f"\n[green]✅ 下载完成！[/green]")
    console.print(f"   成功: {success_count} 只")
    console.print(f"   失败: {failed_count} 只")


@click.command()
@click.option('--type', 'download_type', 
              type=click.Choice(['daily_k', 'tick', 'holographic']),
              default='daily_k',
              help='下载类型: daily_k=日K, tick=Tick数据, holographic=全息数据')
@click.option('--start-date', default=None, help='开始日期 (YYYYMMDD)')
@click.option('--end-date', default=None, help='结束日期 (YYYYMMDD)')
@click.option('--date', default=None, help='单日日期 (YYYYMMDD)，用于全息下载')
@click.option('--days', default=365, type=int, help='下载天数 (用于日K，默认365天)')
@click.option('--no-resume', is_flag=True, help='禁用断点续传，从头开始')
def main(download_type, start_date, end_date, date, days, no_resume):
    """
    统一下载器 - All-in-One Data Downloader
    
    用法示例:
        python tools/unified_downloader.py --type daily_k --days 365
        python tools/unified_downloader.py --type tick --start-date 20250101 --end-date 20260225
        python tools/unified_downloader.py --type holographic --date 20260224
    """
    resume = not no_resume
    
    click.echo("=" * 60)
    click.echo("📊 统一下载器 - All-in-One Data Downloader")
    click.echo("=" * 60)
    
    if download_type == 'daily_k':
        download_daily_k(days=days, resume=resume)
    
    elif download_type == 'tick':
        if not start_date or not end_date:
            click.echo("❌ Tick下载需要指定 --start-date 和 --end-date")
            return
        download_tick_data(start_date, end_date, resume=resume)
    
    elif download_type == 'holographic':
        if not date:
            date = datetime.now().strftime("%Y%m%d")
            click.echo(f"💡 未指定日期，使用今天: {date}")
        download_holographic(date, resume=resume)


if __name__ == "__main__":
    main()
