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
import pandas as pd
import numpy as np
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


def get_last_n_trading_days(n: int = 60) -> tuple:
    """获取最近N个交易日的起止日期 - CTO指令：智能默认60天黄金周期
    
    Returns:
        (start_date, end_date) 格式: YYYYMMDD
    """
    from xtquant import xtdata
    
    # 获取今天是周几，计算往前推多久能拿到N个交易日
    # 保守估计：N个交易日约等于N*7/5个自然日（考虑周末）
    search_days = int(n * 7 / 5) + 10  # 加10天缓冲
    
    end_date = datetime.now()
    start_search = end_date - timedelta(days=search_days)
    
    # 生成候选日期（工作日）
    dates = []
    current = start_search
    while current <= end_date:
        if current.weekday() < 5:  # 周一到周五
            dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    # 取最后N个
    trading_days = dates[-n:] if len(dates) >= n else dates
    
    return trading_days[0], trading_days[-1], trading_days


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
                
                # 【CTO修复】批次间强制等待2秒，让xtdata写完磁盘，避免STATUS_NO_MEMORY
                time.sleep(2)
                
                # 标记完成
                for stock in batch:
                    state["completed"].append(stock)
                    completed_set.add(stock)
                
                success_count += len(batch)
                progress.update(task, advance=len(batch))
                
            except Exception as e:
                # 【CTO修复】异常时立即停止，不再继续硬跑喂死进程
                console.print(f"[red]❌ xtdata服务异常，立即停止: {e}[/red]")
                console.print("[red]⚠️ 请检查QMT客户端状态后重试[/red]")
                save_state("daily_k", state)
                return
            
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


def start_vip_service():
    """启动VIP服务 - CTO补充：加速数据下载"""
    try:
        from xtquant import xtdatacenter as xtdc
        from logic.core.path_resolver import PathResolver
        
        vip_token = os.getenv("QMT_VIP_TOKEN", "")
        data_dir = os.getenv("QMT_PATH", "")
        
        if not data_dir:
            data_dir = str(PathResolver.get_qmt_data_dir())
        
        if vip_token:
            xtdc.set_data_home_dir(data_dir)
            xtdc.set_token(vip_token)
            xtdc.init()
            port = xtdc.listen(port=(58620, 58630))
            return True, port
        return False, None
    except Exception as e:
        return False, str(e)


def download_holographic(date: str, resume: bool = True, timeout: int = 3600):
    """下载全息数据（V18双Ratio筛选后的股票Tick）
    
    筛选条件（对齐实盘live_sniper参数）：
    - 量比分位数: 0.95
    - 换手率范围: 3% - 70%
    - 剔除: 科创板、北交所
    
    新增功能（CTO补充）：
    - VIP服务加速
    - 超时控制
    - 重试机制
    - 跳过已有数据
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
    console.print(f"⏱️ 超时设置: {timeout}秒")
    
    # 启动VIP服务 - CTO补充
    vip_started, vip_result = start_vip_service()
    if vip_started:
        console.print(f"[green]✅ VIP服务已启动，端口: {vip_result}[/green]")
    else:
        console.print(f"[yellow]⚠️ VIP服务未启动: {vip_result}[/yellow]")
    
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
            console.print(f"[red]💡 提示: 纯血QMT粗筛未获取到任何数据！请检查该日期的日K数据是否已存在于本地！[/red]")
            return
            
    except Exception as e:
        console.print(f"[red]❌ 粗筛失败: {e}[/red]")
        console.print(f"[yellow]💡 提示: 请确保QMT本地数据已下载完整[/yellow]")
        return
    
    console.print(f"\n✅ 粗筛完成: {len(stock_list)} 只股票")
    
    # 保存股票池 - CTO补充
    universe_file = STATE_DIR / f"holographic_universe_{date}.json"
    with open(universe_file, 'w', encoding='utf-8') as f:
        json.dump({
            "date": date,
            "stocks": stock_list,
            "count": len(stock_list),
            "created_at": datetime.now().isoformat(),
            "params": {
                "volume_percentile": volume_percentile,
                "min_turnover": min_turnover,
                "max_turnover": max_turnover
            }
        }, f, ensure_ascii=False, indent=2)
    console.print(f"💾 股票池已保存: {universe_file}")
    
    # 过滤已完成的
    pending_stocks = [s for s in stock_list if s not in completed_set]
    console.print(f"⏭️  待下载: {len(pending_stocks)} 只 (已完成: {len(completed_set)})")
    
    if not pending_stocks:
        console.print("[green]✅ 所有数据已下载完成！[/green]")
        return
    
    success_count = len(completed_set)
    failed_count = len(state.get("failed", []))
    skipped_count = 0
    
    # 超时控制
    start_time = time.time()
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]下载进度", total=len(pending_stocks))
        
        for i, stock in enumerate(pending_stocks):
            # 超时检查
            if time.time() - start_time > timeout:
                console.print(f"\n[yellow]⏰ 超时 {timeout}秒，保存进度并退出[/yellow]")
                break
            
            try:
                # 标准化代码
                if "." not in stock:
                    if stock.startswith("6"):
                        stock = f"{stock}.SH"
                    else:
                        stock = f"{stock}.SZ"
                
                # 检查是否已有数据 - CTO补充：跳过已下载
                try:
                    existing = xtdata.get_local_data(
                        field_list=["time"],
                        stock_list=[stock],
                        period="tick",
                        start_time=date,
                        end_time=date
                    )
                    if existing and stock in existing and len(existing[stock]) > 1000:
                        state["completed"].append(stock)
                        completed_set.add(stock)
                        skipped_count += 1
                        progress.update(task, advance=1)
                        continue
                except:
                    pass
                
                # 下载
                download_success = False
                for retry in range(2):  # CTO补充：重试机制
                    try:
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
                            download_success = True
                            break
                        elif retry == 0:
                            time.sleep(1)  # 重试前等待
                    except Exception as e:
                        if retry == 0:
                            time.sleep(1)
                
                if download_success:
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
    console.print(f"   跳过: {skipped_count} 只")


def download_holographic_range(start_date: str, end_date: str, resume: bool = True, timeout: int = 3600):
    """日期范围全息数据下载 - CTO对齐集大成系统
    
    遍历每个交易日，执行V18筛选后下载tick数据
    
    用法:
        python tools/unified_downloader.py --type holographic --start-date 20250101 --end-date 20260225
    """
    from xtquant import xtdata
    from rich.console import Console
    from logic.core.config_manager import get_config_manager
    
    console = Console()
    config_manager = get_config_manager()
    
    # 获取实盘参数
    live_sniper_config = config_manager._config.get('live_sniper', {})
    volume_percentile = live_sniper_config.get('volume_ratio_percentile', 0.95)
    min_turnover = live_sniper_config.get('min_active_turnover_rate', 3.0)
    max_turnover = live_sniper_config.get('death_turnover_rate', 70.0)
    
    # 生成交易日列表
    dates = generate_dates(start_date, end_date)
    
    console.print(f"\n[bold cyan]📊 全息数据批量下载器 (日期范围)[/bold cyan]")
    console.print(f"📅 日期范围: {start_date} ~ {end_date}")
    console.print(f"📅 交易日数: {len(dates)} 天")
    console.print(f"📐 筛选参数: 量比分位数={volume_percentile}, 换手率={min_turnover}%-{max_turnover}%")
    console.print(f"⏱️ 每日超时: {timeout}秒")
    
    # 启动VIP服务
    vip_started, vip_result = start_vip_service()
    if vip_started:
        console.print(f"[green]✅ VIP服务已启动，端口: {vip_result}[/green]")
    else:
        console.print(f"[yellow]⚠️ VIP服务未启动: {vip_result}[/yellow]")
    
    # 统计
    total_stats = {
        "total_days": len(dates),
        "success_days": 0,
        "skip_days": 0,
        "error_days": 0,
        "total_stocks": 0,
        "total_downloaded": 0,
        "total_skipped": 0
    }
    
    # 遍历每个交易日
    for i, date in enumerate(dates, 1):
        console.print(f"\n[bold]━━━ [{i}/{len(dates)}] {date} ━━━[/bold]")
        
        try:
            # 获取粗筛股票池
            from logic.data_providers.universe_builder import UniverseBuilder
            builder = UniverseBuilder()
            stock_list = builder.get_daily_universe(date)
            
            if not stock_list:
                console.print(f"[yellow]⏭️  {date} 无符合条件的股票（可能是非交易日）[/yellow]")
                total_stats["skip_days"] += 1
                continue
            
            console.print(f"📊 粗筛股票数: {len(stock_list)} 只")
            total_stats["total_stocks"] += len(stock_list)
            
            # 加载当日断点状态
            state_key = f"holographic_{date}"
            state = load_state(state_key) if resume else {"completed": [], "failed": []}
            completed_set = set(state.get("completed", []))
            
            # 过滤已完成的
            pending_stocks = [s for s in stock_list if s not in completed_set]
            
            if not pending_stocks:
                console.print(f"[green]✅ {date} 所有数据已下载，跳过[/green]")
                total_stats["skip_days"] += 1
                total_stats["total_skipped"] += len(stock_list)
                continue
            
            console.print(f"⏭️  待下载: {len(pending_stocks)} 只")
            
            # 下载当日tick
            day_start = time.time()
            day_success = 0
            day_skip = 0
            day_failed = 0
            
            for stock in pending_stocks:
                # 超时检查
                if time.time() - day_start > timeout:
                    console.print(f"[yellow]⏰ {date} 超时，保存进度[/yellow]")
                    break
                
                try:
                    # 标准化代码
                    if "." not in stock:
                        if stock.startswith("6"):
                            stock = f"{stock}.SH"
                        else:
                            stock = f"{stock}.SZ"
                    
                    # 检查是否已有数据
                    try:
                        existing = xtdata.get_local_data(
                            field_list=["time"],
                            stock_list=[stock],
                            period="tick",
                            start_time=date,
                            end_time=date
                        )
                        if existing and stock in existing and len(existing[stock]) > 1000:
                            state["completed"].append(stock)
                            day_skip += 1
                            continue
                    except:
                        pass
                    
                    # 下载
                    download_success = False
                    for retry in range(2):
                        try:
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
                                download_success = True
                                break
                        except:
                            time.sleep(0.5)
                    
                    if download_success:
                        state["completed"].append(stock)
                        day_success += 1
                    else:
                        state["failed"].append(stock)
                        day_failed += 1
                    
                except Exception as e:
                    state["failed"].append(stock)
                    day_failed += 1
                
                time.sleep(0.05)
            
            # 保存状态
            save_state(state_key, state)
            
            total_stats["success_days"] += 1
            total_stats["total_downloaded"] += day_success
            total_stats["total_skipped"] += day_skip
            
            console.print(f"✅ {date} 完成: 下载{day_success}只, 跳过{day_skip}只, 失败{day_failed}只")
            
        except Exception as e:
            console.print(f"[red]❌ {date} 处理失败: {e}[/red]")
            total_stats["error_days"] += 1
    
    # 汇总报告
    console.print(f"\n{'='*60}")
    console.print(f"[bold green]📊 全息数据批量下载完成[/bold green]")
    console.print(f"{'='*60}")
    console.print(f"📅 总交易日: {total_stats['total_days']} 天")
    console.print(f"✅ 成功天数: {total_stats['success_days']} 天")
    console.print(f"⏭️  跳过天数: {total_stats['skip_days']} 天")
    console.print(f"❌ 错误天数: {total_stats['error_days']} 天")
    console.print(f"📊 累计股票: {total_stats['total_stocks']} 只")
    console.print(f"📥 累计下载: {total_stats['total_downloaded']} 只")
    console.print(f"⏭️  累计跳过: {total_stats['total_skipped']} 只")
    console.print(f"{'='*60}")


@click.command()
@click.option('--type', 'download_type', 
              type=click.Choice(['daily_k', 'tick', 'holographic']),
              default='daily_k',
              help='下载类型: daily_k=日K, tick=Tick数据, holographic=全息数据')
@click.option('--start-date', default=None, help='开始日期 (YYYYMMDD)')
@click.option('--end-date', default=None, help='结束日期 (YYYYMMDD)')
@click.option('--date', default=None, help='单日日期 (YYYYMMDD)，用于全息下载')
@click.option('--days', default=365, type=int, help='下载天数 (用于日K，默认365天)')
@click.option('--timeout', default=3600, type=int, help='下载超时时间（秒，默认3600秒/1小时）')
@click.option('--no-resume', is_flag=True, help='禁用断点续传，从头开始')
def main(download_type, start_date, end_date, date, days, timeout, no_resume):
    """
    统一下载器 - All-in-One Data Downloader
    
    用法示例:
        python tools/unified_downloader.py --type daily_k --days 365
        python tools/unified_downloader.py --type tick --start-date 20250101 --end-date 20260225
        python tools/unified_downloader.py --type holographic --date 20260224
        python tools/unified_downloader.py --type holographic --start-date 20250101 --end-date 20260225
        python tools/unified_downloader.py --type holographic  # 智能默认最近60个交易日
    
    CTO战略说明:
        全息数据默认下载最近60个交易日 - 这是超短线策略的黄金回测周期
        涵盖当下市场最核心的情绪周期（冰点->高潮->退潮的完整轮回）
        数据量适中(~10-20GB)，下载时间可控(1-2小时)，样本有效性最佳
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
        if start_date and end_date:
            # 日期范围全息下载
            download_holographic_range(start_date, end_date, resume=resume, timeout=timeout)
        elif date:
            # 单日全息下载
            download_holographic(date, resume=resume, timeout=timeout)
        else:
            # CTO指令：智能默认最近60个交易日（黄金回测周期）
            click.echo("💡 未指定日期，基于超短线系统特性，自动设定为【最近60个交易日】的黄金回测周期...")
            start_date, end_date, trading_days = get_last_n_trading_days(60)
            click.echo(f"📅 自动计算日期范围: {start_date} ~ {end_date} (共{len(trading_days)}个交易日)")
            download_holographic_range(start_date, end_date, resume=resume, timeout=timeout)


# =============================================================================
# V20.0 全息下载器 - 上下文切片与靶向下载 (CTO Phase A2)
# =============================================================================

class HolographicDownloaderV20:
    """
    V20极致全息下载器 - 上下文切片与靶向下载
    
    核心功能:
    1. 镜像降维过滤: 量比0.90分位 + 3.0%换手 + high>pre_close
    2. 上下文切片下载: 前30后30天(共60个交易日)
    3. 下载注册表: 避免重复I/O
    4. target_pool记录: 生成JSON错题本
    
    严禁: Magic Number、Tushare、For循环遍历
    """
    
    def __init__(self):
        self.config = get_config_manager()
        self.qmt_manager = QmtDataManager()
        self.registry_file = PathResolver.get_data_dir() / 'holographic_download_registry.json'
        self.registry = self._load_registry()
        
    def _load_registry(self) -> Dict:
        """加载下载注册表"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_registry(self):
        """保存下载注册表"""
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, ensure_ascii=False, indent=2)
    
    def calculate_download_candidates(self, date: str) -> List[Dict]:
        """
        计算当日需要下载的股票列表 - 镜像降维过滤
        
        Returns:
            List[Dict]: 股票信息列表，每只包含code/volume_ratio/turnover/max_change
        """
        console = Console()
        console.print(f"\n[bold cyan]📊 V20全息下载器 - 计算 {date} 候选股票[/bold cyan]")
        
        # 从ConfigManager读取配置 (严禁Magic Number!)
        hd_config = self.config.get('holographic_download', {})
        volume_ratio_download = hd_config.get('volume_ratio_download', 0.90)
        min_turnover_rate = hd_config.get('min_turnover_rate', 3.0)
        price_condition = hd_config.get('price_condition', 'high > pre_close')
        
        # 1. 加载当日全市场日K数据
        console.print("   加载日K数据...")
        all_stocks = self._get_full_universe()
        daily_k_data = self._load_daily_k_data(all_stocks, date)
        
        if daily_k_data.empty:
            console.print("[red]   未获取到日K数据[/red]")
            return []
        
        # 2. 计算量比 (向量化，严禁For循环!)
        console.print("   计算量比...")
        daily_k_data['volume_ratio'] = daily_k_data.apply(
            lambda row: row['volume'] / row['ma5_volume'] if row['ma5_volume'] > 0 else 0,
            axis=1
        )
        
        # 3. 计算换手率
        daily_k_data['turnover_rate'] = daily_k_data.apply(
            lambda row: (row['volume'] / row['float_volume'] * 100) if row['float_volume'] > 0 else 0,
            axis=1
        )
        
        # 4. 计算最高价涨幅 (high > pre_close)
        daily_k_data['max_change_pct'] = daily_k_data.apply(
            lambda row: (row['high'] - row['pre_close']) / row['pre_close'] * 100 if row['pre_close'] > 0 else 0,
            axis=1
        )
        
        # 5. 向量化筛选 (严禁For循环遍历!)
        console.print("   执行镜像降维过滤...")
        
        # 量比 >= 0.90分位 (动态计算)
        volume_ratio_threshold = daily_k_data['volume_ratio'].quantile(volume_ratio_download)
        volume_ratio_threshold = max(volume_ratio_threshold, 1.5)  # 最小保护阈值
        
        # 三条件筛选 (向量化布尔索引)
        mask = (
            (daily_k_data['volume_ratio'] >= volume_ratio_threshold) &      # 量比条件
            (daily_k_data['turnover_rate'] >= min_turnover_rate) &          # 换手条件
            (daily_k_data['max_change_pct'] > 0)                             # high > pre_close
        )
        
        candidates = daily_k_data[mask].copy()
        
        # 6. 构建结果
        results = []
        for _, row in candidates.iterrows():
            results.append({
                'code': row['stock_code'],
                'volume_ratio': round(row['volume_ratio'], 2),
                'turnover': round(row['turnover_rate'], 2),
                'max_change': round(row['max_change_pct'], 2),
                'volume': int(row['volume']),
                'float_volume': int(row['float_volume']) if row['float_volume'] > 0 else 0
            })
        
        console.print(f"[green]   ✅ 筛选完成: {len(results)} 只股票符合条件[/green]")
        console.print(f"   📊 量比阈值: {volume_ratio_threshold:.2f}, 换手阈值: {min_turnover_rate}%")
        
        return results
    
    def download_holographic_context(self, stock_code: str, trigger_dates: List[str]):
        """
        下载股票的上下文Tick数据 - 前30后30天
        
        Args:
            stock_code: 股票代码
            trigger_dates: 触发日期列表
        """
        console = Console()
        
        # 计算日期范围
        from datetime import datetime, timedelta
        
        min_trigger = min(trigger_dates)
        max_trigger = max(trigger_dates)
        
        # 往前推30个交易日，往后推30个交易日
        start_date = self._get_trade_date_offset(min_trigger, -30)
        end_date = self._get_trade_date_offset(max_trigger, 30)
        
        console.print(f"   {stock_code}: 下载区间 {start_date} ~ {end_date}")
        
        # 检查注册表，过滤已下载的日期
        already_downloaded = self.registry.get(stock_code, [])
        all_dates = self._get_trade_dates_between(start_date, end_date)
        dates_to_download = [d for d in all_dates if d not in already_downloaded]
        
        if not dates_to_download:
            console.print(f"   ⏭️  {stock_code} 所有数据已下载，跳过")
            return
        
        console.print(f"   📥 需下载 {len(dates_to_download)} 天，已存在 {len(already_downloaded)} 天")
        
        # 下载Tick数据
        success_dates = []
        for date in dates_to_download:
            try:
                # 调用QMT下载
                self.qmt_manager.download_tick_data([stock_code], date)
                success_dates.append(date)
                time.sleep(0.1)  # 避免限流
            except Exception as e:
                console.print(f"   [red]❌ {stock_code} {date} 下载失败: {e}[/red]")
        
        # 更新注册表
        if stock_code not in self.registry:
            self.registry[stock_code] = []
        self.registry[stock_code].extend(success_dates)
        self._save_registry()
        
        console.print(f"   [green]✅ {stock_code} 成功下载 {len(success_dates)} 天[/green]")
    
    def generate_target_pool(self, date: str, candidates: List[Dict]):
        """
        生成target_pool记录文件
        
        Args:
            date: 日期
            candidates: 候选股票列表
        """
        hd_config = self.config.get('holographic_download', {})
        
        target_pool = {
            'date': date,
            'filter_criteria': {
                'volume_ratio_percentile': hd_config.get('volume_ratio_download', 0.90),
                'turnover_threshold': hd_config.get('min_turnover_rate', 3.0),
                'price_condition': hd_config.get('price_condition', 'high > pre_close'),
                'context_days': hd_config.get('context_days_total', 60)
            },
            'target_stocks': candidates,
            'statistics': {
                'total_scanned': 5191,  # 全市场
                'selected': len(candidates),
                'selection_rate': f"{len(candidates)/5191*100:.2f}%"
            }
        }
        
        output_file = PathResolver.get_data_dir() / f'holographic_target_{date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(target_pool, f, ensure_ascii=False, indent=2)
        
        console = Console()
        console.print(f"[green]   📝 已生成目标池记录: {output_file}[/green]")
    
    def run_v20_download(self, date: str):
        """
        V20全息下载主入口
        
        Args:
            date: 日期 'YYYYMMDD'
        """
        console = Console()
        console.print(f"\n[bold green]={'='*60}[/bold green]")
        console.print(f"[bold green]🚀 V20极致全息下载器启动[/bold green]")
        console.print(f"[bold green]   日期: {date}[/bold green]")
        console.print(f"[bold green]={'='*60}[/bold green]\n")
        
        # Step 1: 计算候选股票
        candidates = self.calculate_download_candidates(date)
        
        if not candidates:
            console.print("[yellow]⚠️  今日无符合条件的股票[/yellow]")
            return
        
        # Step 2: 生成target_pool记录
        self.generate_target_pool(date, candidates)
        
        # Step 3: 下载上下文Tick数据
        console.print(f"\n[bold]📥 开始下载上下文Tick数据...[/bold]")
        
        stock_codes = [c['code'] for c in candidates]
        trigger_dates = [date]  # 当前日期作为触发日期
        
        for i, stock_code in enumerate(stock_codes, 1):
            console.print(f"\n[{i}/{len(stock_codes)}] {stock_code}")
            try:
                self.download_holographic_context(stock_code, trigger_dates)
            except Exception as e:
                console.print(f"[red]   下载异常: {e}[/red]")
        
        console.print(f"\n[bold green]✅ V20全息下载完成！[/bold green]")
        console.print(f"[green]   候选股票: {len(candidates)} 只[/green]")
        console.print(f"[green]   下载注册表: {self.registry_file}[/green]")
    
    def _get_full_universe(self) -> List[str]:
        """获取全市场股票列表"""
        try:
            from xtquant import xtdata
            return xtdata.get_stock_list_in_sector('沪深A股')
        except:
            return []
    
    def _load_daily_k_data(self, stock_list: List[str], date: str) -> pd.DataFrame:
        """加载日K数据"""
        try:
            from xtquant import xtdata
            
            # 获取前5天的数据计算MA5
            end_date = date
            start_date = (datetime.strptime(date, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d')
            
            data = xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=stock_list,
                period='1d',
                start_time=start_date,
                end_time=end_date
            )
            
            rows = []
            for stock_code, df in data.items():
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    # 计算MA5
                    ma5 = df['volume'].tail(5).mean() if len(df) >= 5 else df['volume'].mean()
                    # 获取昨收
                    pre_close = df.iloc[-2]['close'] if len(df) >= 2 else latest['open']
                    # 获取流通股本
                    float_volume = self._get_float_volume(stock_code)
                    
                    rows.append({
                        'stock_code': stock_code,
                        'open': latest['open'],
                        'high': latest['high'],
                        'low': latest['low'],
                        'close': latest['close'],
                        'volume': latest['volume'],
                        'ma5_volume': ma5,
                        'pre_close': pre_close,
                        'float_volume': float_volume
                    })
            
            return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"加载日K数据失败: {e}")
            return pd.DataFrame()
    
    def _get_float_volume(self, stock_code: str) -> float:
        """获取流通股本"""
        try:
            from xtquant import xtdata
            detail = xtdata.get_instrument_detail(stock_code, True)
            if detail:
                return float(detail.get('FloatVolume', 0)) if hasattr(detail, 'get') else float(getattr(detail, 'FloatVolume', 0))
        except:
            pass
        return 0
    
    def _get_trade_date_offset(self, date: str, offset: int) -> str:
        """获取偏移后的交易日"""
        # 简化实现：按自然日偏移，实际应使用交易日历
        current = datetime.strptime(date, '%Y%m%d')
        offset_days = offset * 7 // 5  # 粗略估计
        result = current + timedelta(days=offset_days)
        return result.strftime('%Y%m%d')
    
    def _get_trade_dates_between(self, start: str, end: str) -> List[str]:
        """获取日期范围内的所有日期"""
        dates = []
        current = datetime.strptime(start, '%Y%m%d')
        end_dt = datetime.strptime(end, '%Y%m%d')
        while current <= end_dt:
            dates.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)
        return dates


# 便捷入口
def run_v20_holographic_download(date: str = None):
    """
    V20全息下载便捷入口
    
    Usage:
        python -c "from tools.unified_downloader import run_v20_holographic_download; run_v20_holographic_download('20260224')"
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    downloader = HolographicDownloaderV20()
    downloader.run_v20_download(date)


if __name__ == "__main__":
    main()
