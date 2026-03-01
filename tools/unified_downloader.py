#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一下载器 - All-in-One Data Downloader
支持日K、Tick、全息数据下载，断点续传，Rich进度条，后台线程UI

启动方式（参数启动，所有方式均弹出 Rich CLI 面板）：
    # 日K下载（全市场最近365天）
    python tools/unified_downloader.py --type daily_k --days 365

    # Tick下载（指定日期范围）
    python tools/unified_downloader.py --type tick --start-date 20260101 --end-date 20260228

    # 全息单日
    python tools/unified_downloader.py --type holographic --date 20260228

    # 全息范围
    python tools/unified_downloader.py --type holographic --start-date 20260101 --end-date 20260228

    # 全息默认（自动最近60交易日）
    python tools/unified_downloader.py --type holographic

    # 禁用断点续传
    python tools/unified_downloader.py --type daily_k --days 365 --no-resume

    # 无参数启动 → 交互式菜单
    python tools/unified_downloader.py

依赖：
    pip install rich click
    xtquant（QMT本地安装）

Author: CTO重构 V20.1
Date: 2026-03-01
变更:
    - [修复] _get_trade_date_offset: 改用 xtdata.get_trading_calendar('SSE') 真实交易日历
             get_trading_calendar 是纯本地读取，不触发网络请求，不会引发BSON崩溃
             原1.8倍估算多算10天 = 多拉几GB冗余Tick，直接给死锁埋雷，已驳回
    - [修复] Tick验证阈值 len > 100 → len > 0，停牌/新股首日秒板不再误判失败
    - [修复] download_daily_k 批次间加 time.sleep(2)，让C++磁盘写入完成
    - [修复] download_daily_k 异常熔断：检测到xtdata崩溃立即return，不继续喂死进程
    - [修复] generate_dates → get_trading_calendar_qmt_local 过滤真实节假日
    - [修复] generate_target_pool Magic Number 5191 → 动态 len(all_stocks)
    - [修复] calculate_download_candidates apply lambda → 全向量化 (col/col).fillna(0)
    - [新增] run_with_rich_ui: 所有启动方式均显示 Rich Panel 常驻面板，下载在后台线程
    - [新增] interactive_menu: 无参数启动弹 Rich Table 菜单
    - [新增] Windows编码修复在文件顶部统一处理
"""

import os
import sys
import json
import time
import threading
import traceback
import click
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ── Windows 编码修复（必须最早执行）──
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 状态文件路径
STATE_DIR = PROJECT_ROOT / "data"
STATE_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# 工具函数
# =============================================================================

def get_state_file(download_type: str) -> Path:
    return STATE_DIR / f"download_state_{download_type}.json"


def load_state(download_type: str) -> Dict:
    state_file = get_state_file(download_type)
    if state_file.exists():
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"completed": [], "failed": [], "last_update": None}


def save_state(download_type: str, state: Dict):
    state_file = get_state_file(download_type)
    state["last_update"] = datetime.now().isoformat()
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_trading_calendar_qmt_local(start_date: str, end_date: str) -> List[str]:
    """
    用 QMT 原生 get_trading_calendar 获取真实交易日历。
    【安全保证】纯本地读取，不触发任何网络请求，不下载数据，
    不引发 BSON 崩溃，可在任何阶段安全调用。
    只有 get_local_data 和 download_history_data 才是危险操作。

    Returns:
        List[str]: 交易日列表，格式 'YYYYMMDD'
    """
    try:
        from xtquant import xtdata
        calendar: list = xtdata.get_trading_calendar('SSE', start_date, end_date)
        if calendar:
            return [str(d) for d in calendar]
    except Exception:
        pass

    # 兜底：只过滤周末（无法过滤节假日，但不引入外部依赖）
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    dates = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            dates.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return dates


def generate_dates(start_date: str, end_date: str) -> List[str]:
    """生成交易日列表（使用QMT本地交易日历，精确覆盖节假日）"""
    return get_trading_calendar_qmt_local(start_date, end_date)


def get_trade_date_offset(date: str, offset: int) -> str:
    """
    用 QMT 原生交易日历精确推算偏移日期，覆盖春节/国庆长假。
    get_trading_calendar 是纯本地读取，安全。

    Args:
        date: 基准日期 'YYYYMMDD'（可为非交易日，自动向后找最近交易日）
        offset: 偏移交易日数（正=向后，负=向前）
    Returns:
        str: 偏移后的交易日 'YYYYMMDD'
    """
    try:
        from xtquant import xtdata
        calendar: list = xtdata.get_trading_calendar('SSE', '20230101', '20270101')
        calendar = [str(d) for d in calendar]

        # date 可能是非交易日，找第一个 >= date 的交易日
        base_idx = None
        for i, d in enumerate(calendar):
            if d >= date:
                base_idx = i
                break
        if base_idx is None:
            base_idx = len(calendar) - 1

        target_idx = max(0, min(len(calendar) - 1, base_idx + offset))
        return calendar[target_idx]

    except Exception:
        # 兜底：自然日粗算，多加15天安全缓冲
        d = datetime.strptime(date, '%Y%m%d')
        safe_days = int(abs(offset) * 7 / 5) + 15
        delta = timedelta(days=safe_days if offset >= 0 else -safe_days)
        return (d + delta).strftime('%Y%m%d')


def get_last_n_trading_days(n: int = 60) -> Tuple[str, str, List[str]]:
    """
    获取最近N个真实交易日（QMT本地日历，纯本地，安全）。

    Returns:
        (start_date, end_date, trading_days_list)
    """
    end_date = datetime.now().strftime("%Y%m%d")
    start_search = (datetime.now() - timedelta(days=n * 2)).strftime("%Y%m%d")
    trading_days = get_trading_calendar_qmt_local(start_search, end_date)
    trading_days = trading_days[-n:] if len(trading_days) >= n else trading_days
    if not trading_days:
        return start_search, end_date, []
    return trading_days[0], trading_days[-1], trading_days


# =============================================================================
# Rich UI 壳：无论从 click 还是交互菜单启动，均显示 Rich Panel 常驻面板
# =============================================================================

def run_with_rich_ui(task_name: str, task_fn):
    """
    统一 Rich UI 壳：下载任务在后台线程执行，前台保持 Rich Panel 常驻。
    不管通过参数还是菜单启动，所有下载均走此壳。
    内部下载函数已有 rich.progress.Progress 输出，
    此壳负责：① 保证 Rich Panel 弹出 ② 后台线程下载 ③ 异常汇总展示
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text

    console = Console()
    result: Dict = {"ok": False, "err": None, "tb": ""}
    done_event = threading.Event()

    def worker():
        try:
            task_fn()
            result["ok"] = True
        except Exception as e:
            result["err"] = e
            result["tb"] = traceback.format_exc()
        finally:
            done_event.set()

    t = threading.Thread(target=worker, name=f"dl-{task_name}", daemon=True)
    t.start()

    spinner = Spinner("dots", text=Text(f" 后台执行中：{task_name}", style="cyan"))

    with Live(
        Panel(spinner, title="[bold cyan]MyQuantTool Downloader[/bold cyan]", border_style="cyan"),
        refresh_per_second=8,
        console=console,
    ):
        while not done_event.is_set():
            time.sleep(0.1)

    if result["ok"]:
        console.print(Panel(f"[green]✅ 任务完成：{task_name}[/green]", border_style="green"))
        return

    console.print(Panel(
        f"[red]❌ 任务失败：{task_name}[/red]\n{result['err']}\n\n{result['tb']}",
        border_style="red"
    ))


# =============================================================================
# 日K下载
# =============================================================================

def download_daily_k(days: int = 365, resume: bool = True):
    """下载全市场日K数据"""
    from xtquant import xtdata
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.console import Console

    console = Console()
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = get_trade_date_offset(end_date, -days)

    console.print(f"\n[bold cyan]📊 日K数据下载器[/bold cyan]")
    console.print(f"📅 日期范围: {start_date} ~ {end_date} ({days}天)")

    state = load_state("daily_k") if resume else {"completed": [], "failed": []}
    completed_set = set(state.get("completed", []))

    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    console.print(f"📈 股票数量: {len(all_stocks)} 只")

    pending_stocks = [s for s in all_stocks if s not in completed_set]
    console.print(f"⏭️  待下载: {len(pending_stocks)} 只 (已完成: {len(completed_set)})")

    if not pending_stocks:
        console.print("[green]✅ 所有数据已下载完成！[/green]")
        return

    BATCH_SIZE = 50
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
            batch = pending_stocks[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1

            try:
                console.print(f"👉 正在下发批次 {batch_num}/{total_batches}...")
                xtdata.download_history_data2(
                    stock_list=batch,
                    period='1d',
                    start_time=start_date,
                    end_time=end_date,
                    incrementally=True
                )

                # 【防爆锁】批次间强制等待，让C++后台完成磁盘写入
                time.sleep(2)

                for stock in batch:
                    state["completed"].append(stock)
                    completed_set.add(stock)

                success_count += len(batch)
                progress.update(task, advance=len(batch))

            except Exception as e:
                # 【熔断】C++引擎异常立即停机，不继续喂死进程
                console.print(f"[red]❌ xtdata 服务异常，立即停止: {e}[/red]")
                console.print("[red]⚠️  请检查 QMT 客户端状态后重试[/red]")
                save_state("daily_k", state)
                return

            if batch_num % 5 == 0:
                save_state("daily_k", state)

    save_state("daily_k", state)
    console.print(f"\n[green]✅ 下载完成！成功: {success_count} 只 | 失败: {failed_count} 只[/green]")


# =============================================================================
# Tick 下载
# =============================================================================

def download_tick_data(start_date: str, end_date: str,
                       stock_list: list | None = None, resume: bool = True):
    """下载Tick数据"""
    from xtquant import xtdata
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.console import Console

    console = Console()
    console.print(f"\n[bold cyan]📊 Tick数据下载器[/bold cyan]")
    console.print(f"📅 日期范围: {start_date} ~ {end_date}")

    state_key = f"tick_{start_date}_{end_date}"
    state = load_state(state_key) if resume else {"completed": [], "failed": []}
    completed_set = set(state.get("completed", []))

    if not stock_list:
        stock_list = xtdata.get_stock_list_in_sector('沪深A股')

    console.print(f"📈 股票数量: {len(stock_list)} 只")
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
                if "." not in stock:
                    stock = f"{stock}.SH" if stock.startswith("6") else f"{stock}.SZ"

                xtdata.download_history_data(
                    stock_code=stock, period="tick",
                    start_time=start_date, end_time=end_date
                )

                data = xtdata.get_local_data(
                    field_list=["time"], stock_list=[stock],
                    period="tick", start_time=start_date, end_time=end_date
                )

                # 【修复】阈值 > 0，停牌/新股首日秒板不再误判为失败
                if data and stock in data and len(data[stock]) > 0:
                    state["completed"].append(stock)
                    success_count += 1
                else:
                    state["failed"].append(stock)
                    failed_count += 1

            except Exception:
                state["failed"].append(stock)
                failed_count += 1

            progress.update(task, advance=1)

            if (i + 1) % 50 == 0:
                save_state(state_key, state)

            time.sleep(0.1)

    save_state(state_key, state)
    console.print(f"\n[green]✅ 下载完成！成功: {success_count} 只 | 失败: {failed_count} 只[/green]")


# =============================================================================
# 全息数据下载
# =============================================================================

def start_vip_service():
    """启动VIP服务加速"""
    try:
        from xtquant import xtdatacenter as xtdc
        from logic.core.path_resolver import PathResolver

        vip_token = os.getenv("QMT_VIP_TOKEN", "")
        data_dir = os.getenv("QMT_PATH", "") or str(PathResolver.get_qmt_data_dir())

        if vip_token:
            xtdc.set_data_home_dir(data_dir)
            xtdc.set_token(vip_token)
            xtdc.init()
            port = xtdc.listen(port=(58620, 58630))
            return True, port
        return False, "未配置 QMT_VIP_TOKEN"
    except Exception as e:
        return False, str(e)


def download_holographic(date: str, resume: bool = True, timeout: int = 3600):
    """下载单日全息数据（V18双Ratio筛选后的股票Tick）"""
    from xtquant import xtdata
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.console import Console
    from logic.core.config_manager import get_config_manager

    console = Console()
    config_manager = get_config_manager()
    live_sniper_config = config_manager._config.get('live_sniper', {})
    volume_percentile = live_sniper_config.get('volume_ratio_percentile', 0.95)
    min_turnover = live_sniper_config.get('min_active_turnover_rate', 3.0)
    max_turnover = live_sniper_config.get('death_turnover_rate', 70.0)

    console.print(f"\n[bold cyan]📊 全息数据下载器 (V18双Ratio筛选)[/bold cyan]")
    console.print(f"📅 目标日期: {date}")
    console.print(f"📐 量比分位: {volume_percentile} | 换手率: {min_turnover}%-{max_turnover}%")
    console.print(f"⏱️  超时: {timeout}秒")

    vip_started, vip_result = start_vip_service()
    if vip_started:
        console.print(f"[green]✅ VIP服务已启动，端口: {vip_result}[/green]")
    else:
        console.print(f"[yellow]⚠️  VIP服务未启动: {vip_result}[/yellow]")

    state_key = f"holographic_{date}"
    state = load_state(state_key) if resume else {"completed": [], "failed": []}
    completed_set = set(state.get("completed", []))

    console.print("\n🔍 执行V18双Ratio粗筛...")
    try:
        from logic.data_providers.universe_builder import UniverseBuilder
        stock_list = UniverseBuilder(date).build()
        if not stock_list:
            console.print(f"[red]❌ 粗筛返回空股票池，可能是非交易日或本地日K数据缺失[/red]")
            return
    except Exception as e:
        console.print(f"[red]❌ 粗筛失败: {e}[/red]")
        return

    console.print(f"✅ 粗筛完成: {len(stock_list)} 只股票")

    universe_file = STATE_DIR / f"holographic_universe_{date}.json"
    with open(universe_file, 'w', encoding='utf-8') as f:
        json.dump({
            "date": date, "stocks": stock_list, "count": len(stock_list),
            "created_at": datetime.now().isoformat(),
            "params": {"volume_percentile": volume_percentile,
                       "min_turnover": min_turnover, "max_turnover": max_turnover}
        }, f, ensure_ascii=False, indent=2)
    console.print(f"💾 股票池已保存: {universe_file}")

    pending_stocks = [s for s in stock_list if s not in completed_set]
    console.print(f"⏭️  待下载: {len(pending_stocks)} 只 (已完成: {len(completed_set)})")

    if not pending_stocks:
        console.print("[green]✅ 所有数据已下载完成！[/green]")
        return

    success_count = len(completed_set)
    failed_count = len(state.get("failed", []))
    skipped_count = 0
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
            if time.time() - start_time > timeout:
                console.print(f"\n[yellow]⏰ 超时 {timeout}秒，保存进度并退出[/yellow]")
                break

            try:
                if "." not in stock:
                    stock = f"{stock}.SH" if stock.startswith("6") else f"{stock}.SZ"

                try:
                    existing = xtdata.get_local_data(
                        field_list=["time"], stock_list=[stock],
                        period="tick", start_time=date, end_time=date
                    )
                    if existing and stock in existing and len(existing[stock]) > 1000:
                        state["completed"].append(stock)
                        completed_set.add(stock)
                        skipped_count += 1
                        progress.update(task, advance=1)
                        continue
                except Exception:
                    pass

                download_success = False
                for retry in range(2):
                    try:
                        xtdata.download_history_data(
                            stock_code=stock, period="tick",
                            start_time=date, end_time=date
                        )
                        data = xtdata.get_local_data(
                            field_list=["time"], stock_list=[stock],
                            period="tick", start_time=date, end_time=date
                        )
                        # 【修复】阈值 > 0
                        if data and stock in data and len(data[stock]) > 0:
                            download_success = True
                            break
                        if retry == 0:
                            time.sleep(1)
                    except Exception:
                        if retry == 0:
                            time.sleep(1)

                if download_success:
                    state["completed"].append(stock)
                    success_count += 1
                else:
                    state["failed"].append(stock)
                    failed_count += 1

            except Exception:
                state["failed"].append(stock)
                failed_count += 1

            progress.update(task, advance=1)
            if (i + 1) % 20 == 0:
                save_state(state_key, state)
            time.sleep(0.1)

    save_state(state_key, state)
    console.print(f"\n[green]✅ 下载完成！成功: {success_count} | 失败: {failed_count} | 跳过: {skipped_count}[/green]")


def download_holographic_range(start_date: str, end_date: str,
                                resume: bool = True, timeout: int = 3600):
    """日期范围全息数据下载（使用QMT真实交易日历）"""
    from xtquant import xtdata
    from rich.console import Console
    from logic.core.config_manager import get_config_manager

    console = Console()
    config_manager = get_config_manager()
    live_sniper_config = config_manager._config.get('live_sniper', {})
    volume_percentile = live_sniper_config.get('volume_ratio_percentile', 0.95)
    min_turnover = live_sniper_config.get('min_active_turnover_rate', 3.0)
    max_turnover = live_sniper_config.get('death_turnover_rate', 70.0)

    # 【修复】用真实交易日历，精确过滤节假日
    dates = get_trading_calendar_qmt_local(start_date, end_date)

    console.print(f"\n[bold cyan]📊 全息数据批量下载器[/bold cyan]")
    console.print(f"📅 {start_date} ~ {end_date} | 交易日: {len(dates)} 天")
    console.print(f"📐 量比分位: {volume_percentile} | 换手率: {min_turnover}%-{max_turnover}%")
    console.print(f"⏱️  每日超时: {timeout}秒")

    vip_started, vip_result = start_vip_service()
    if vip_started:
        console.print(f"[green]✅ VIP服务已启动，端口: {vip_result}[/green]")
    else:
        console.print(f"[yellow]⚠️  VIP服务未启动: {vip_result}[/yellow]")

    total_stats = {
        "total_days": len(dates), "success_days": 0, "skip_days": 0, "error_days": 0,
        "total_stocks": 0, "total_downloaded": 0, "total_skipped": 0
    }

    for i, date in enumerate(dates, 1):
        console.print(f"\n[bold]━━━ [{i}/{len(dates)}] {date} ━━━[/bold]")

        try:
            from logic.data_providers.universe_builder import UniverseBuilder
            stock_list = UniverseBuilder(date).build()

            if not stock_list:
                console.print(f"[yellow]⏭️  {date} 无符合条件的股票（非交易日或数据缺失）[/yellow]")
                total_stats["skip_days"] += 1
                continue

            console.print(f"📊 粗筛股票数: {len(stock_list)} 只")
            total_stats["total_stocks"] += len(stock_list)

            state_key = f"holographic_{date}"
            state = load_state(state_key) if resume else {"completed": [], "failed": []}
            completed_set = set(state.get("completed", []))

            pending_stocks = [s for s in stock_list if s not in completed_set]

            if not pending_stocks:
                console.print(f"[green]✅ {date} 所有数据已下载，跳过[/green]")
                total_stats["skip_days"] += 1
                total_stats["total_skipped"] += len(stock_list)
                continue

            console.print(f"⏭️  待下载: {len(pending_stocks)} 只")

            day_start = time.time()
            day_success = day_skip = day_failed = 0

            for stock in pending_stocks:
                if time.time() - day_start > timeout:
                    console.print(f"[yellow]⏰ {date} 超时，保存进度[/yellow]")
                    break

                try:
                    if "." not in stock:
                        stock = f"{stock}.SH" if stock.startswith("6") else f"{stock}.SZ"

                    try:
                        existing = xtdata.get_local_data(
                            field_list=["time"], stock_list=[stock],
                            period="tick", start_time=date, end_time=date
                        )
                        if existing and stock in existing and len(existing[stock]) > 1000:
                            state["completed"].append(stock)
                            day_skip += 1
                            continue
                    except Exception:
                        pass

                    download_success = False
                    for retry in range(2):
                        try:
                            xtdata.download_history_data(
                                stock_code=stock, period="tick",
                                start_time=date, end_time=date
                            )
                            data = xtdata.get_local_data(
                                field_list=["time"], stock_list=[stock],
                                period="tick", start_time=date, end_time=date
                            )
                            # 【修复】阈值 > 0
                            if data and stock in data and len(data[stock]) > 0:
                                download_success = True
                                break
                        except Exception:
                            time.sleep(0.5)

                    if download_success:
                        state["completed"].append(stock)
                        day_success += 1
                    else:
                        state["failed"].append(stock)
                        day_failed += 1

                except Exception:
                    state["failed"].append(stock)
                    day_failed += 1

                time.sleep(0.05)

            save_state(state_key, state)
            total_stats["success_days"] += 1
            total_stats["total_downloaded"] += day_success
            total_stats["total_skipped"] += day_skip
            console.print(f"✅ {date} 完成: 下载{day_success} | 跳过{day_skip} | 失败{day_failed}")

        except Exception as e:
            console.print(f"[red]❌ {date} 处理失败: {e}[/red]")
            total_stats["error_days"] += 1

    console.print(f"\n{'=' * 60}")
    console.print(f"[bold green]📊 全息数据批量下载完成[/bold green]")
    console.print(f"总交易日: {total_stats['total_days']} | 成功: {total_stats['success_days']} | "
                  f"跳过: {total_stats['skip_days']} | 错误: {total_stats['error_days']}")
    console.print(f"累计下载: {total_stats['total_downloaded']} 只 | 累计跳过: {total_stats['total_skipped']} 只")
    console.print("=" * 60)


# =============================================================================
# V20 全息下载器（上下文切片靶向下载）
# =============================================================================

class HolographicDownloaderV20:
    """
    V20极致全息下载器 - 上下文切片与靶向下载

    核心功能：
    1. 镜像降维过滤：量比0.90分位 + 3.0%换手 + high>pre_close
    2. 上下文切片：前30后30交易日（共60日）
       - 使用 xtdata.get_trading_calendar 精确计算，不用1.8倍估算
       - 多算10天 = 多拉数GB冗余Tick I/O，给xtdata死锁埋雷
    3. 下载注册表：避免重复I/O
    4. target_pool 记录：生成JSON错题本
    """

    def __init__(self):
        from logic.core.config_manager import get_config_manager
        from logic.core.path_resolver import PathResolver
        self.config = get_config_manager()
        self.registry_file = PathResolver.get_data_dir() / 'holographic_download_registry.json'
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        if self.registry_file.exists():
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_registry(self):
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, ensure_ascii=False, indent=2)

    def calculate_download_candidates(self, date: str) -> List[Dict]:
        """
        计算当日候选股票 - 镜像降维过滤（全向量化，无apply）
        """
        from rich.console import Console
        console = Console()
        console.print(f"\n[bold cyan]📊 V20全息下载器 - 计算 {date} 候选股票[/bold cyan]")

        hd_config = self.config.get('holographic_download', {})
        volume_ratio_download = hd_config.get('volume_ratio_download', 0.90)
        min_turnover_rate = hd_config.get('min_turnover_rate', 3.0)

        console.print("   加载日K数据...")
        all_stocks = self._get_full_universe()
        daily_k_data = self._load_daily_k_data(all_stocks, date)

        if daily_k_data.empty:
            console.print("[red]   未获取到日K数据[/red]")
            return []

        # 【向量化】量比、换手率、最高涨幅全部向量化计算，无apply
        daily_k_data['volume_ratio'] = (
            daily_k_data['volume'] / daily_k_data['ma5_volume'].replace(0, np.nan)
        ).fillna(0)

        daily_k_data['turnover_rate'] = (
            daily_k_data['volume'] / daily_k_data['float_volume'].replace(0, np.nan) * 100
        ).fillna(0)

        daily_k_data['max_change_pct'] = (
            (daily_k_data['high'] - daily_k_data['pre_close'])
            / daily_k_data['pre_close'].replace(0, np.nan) * 100
        ).fillna(0)

        volume_ratio_threshold = max(
            daily_k_data['volume_ratio'].quantile(volume_ratio_download), 1.5
        )

        # 向量化布尔筛选
        mask = (
            (daily_k_data['volume_ratio'] >= volume_ratio_threshold) &
            (daily_k_data['turnover_rate'] >= min_turnover_rate) &
            (daily_k_data['max_change_pct'] > 0)
        )
        candidates = daily_k_data[mask].copy()

        results = [
            {
                'code': row['stock_code'],
                'volume_ratio': round(row['volume_ratio'], 2),
                'turnover': round(row['turnover_rate'], 2),
                'max_change': round(row['max_change_pct'], 2),
                'volume': int(row['volume']),
                'float_volume': int(row['float_volume']) if row['float_volume'] > 0 else 0
            }
            for _, row in candidates.iterrows()
        ]

        console.print(f"[green]   ✅ 筛选完成: {len(results)} 只 | 量比阈值: {volume_ratio_threshold:.2f}[/green]")
        return results

    def download_holographic_context(self, stock_code: str, trigger_dates: List[str]):
        """下载股票上下文Tick（前30后30交易日）"""
        from rich.console import Console
        console = Console()

        min_trigger = min(trigger_dates)
        max_trigger = max(trigger_dates)

        # 【修复】用真实交易日历精确推算，不用1.8倍估算 — 防止多拉数GB冗余Tick
        start_date = get_trade_date_offset(min_trigger, -30)
        end_date = get_trade_date_offset(max_trigger, 30)

        console.print(f"   {stock_code}: 下载区间 {start_date} ~ {end_date}")

        already_downloaded = self.registry.get(stock_code, [])
        all_dates = get_trading_calendar_qmt_local(start_date, end_date)
        dates_to_download = [d for d in all_dates if d not in already_downloaded]

        if not dates_to_download:
            console.print(f"   ⏭️  {stock_code} 所有数据已下载，跳过")
            return

        console.print(f"   📥 需下载 {len(dates_to_download)} 天，已存在 {len(already_downloaded)} 天")

        from logic.core.qmt_data_manager import QmtDataManager
        qmt_manager = QmtDataManager()
        success_dates = []
        for date in dates_to_download:
            try:
                qmt_manager.download_tick_data([stock_code], date)
                success_dates.append(date)
                time.sleep(0.1)
            except Exception as e:
                console.print(f"   [red]❌ {stock_code} {date} 下载失败: {e}[/red]")

        if stock_code not in self.registry:
            self.registry[stock_code] = []
        self.registry[stock_code].extend(success_dates)
        self._save_registry()
        console.print(f"   [green]✅ {stock_code} 成功下载 {len(success_dates)} 天[/green]")

    def generate_target_pool(self, date: str, candidates: List[Dict]):
        """生成target_pool记录（动态股票总数，消灭Magic Number）"""
        from logic.core.path_resolver import PathResolver
        from rich.console import Console
        console = Console()

        hd_config = self.config.get('holographic_download', {})

        # 【修复】动态获取全市场股票数，消灭 Magic Number 5191
        all_stocks = self._get_full_universe()
        total_scanned = len(all_stocks) if all_stocks else len(candidates) * 10

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
                'total_scanned': total_scanned,
                'selected': len(candidates),
                'selection_rate': f"{len(candidates) / total_scanned * 100:.2f}%" if total_scanned else "N/A"
            }
        }

        output_file = PathResolver.get_data_dir() / f'holographic_target_{date}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(target_pool, f, ensure_ascii=False, indent=2)
        console.print(f"[green]   📝 目标池记录: {output_file}[/green]")

    def run_v20_download(self, date: str):
        """V20全息下载主入口"""
        from rich.console import Console
        console = Console()
        console.print(f"\n[bold green]{'=' * 60}[/bold green]")
        console.print(f"[bold green]🚀 V20极致全息下载器启动 | 日期: {date}[/bold green]")
        console.print(f"[bold green]{'=' * 60}[/bold green]\n")

        candidates = self.calculate_download_candidates(date)
        if not candidates:
            console.print("[yellow]⚠️  今日无符合条件的股票[/yellow]")
            return

        self.generate_target_pool(date, candidates)

        console.print(f"\n[bold]📥 开始下载上下文Tick数据...[/bold]")
        stock_codes = [c['code'] for c in candidates]

        for i, stock_code in enumerate(stock_codes, 1):
            console.print(f"\n[{i}/{len(stock_codes)}] {stock_code}")
            try:
                self.download_holographic_context(stock_code, [date])
            except Exception as e:
                console.print(f"[red]   下载异常: {e}[/red]")

        console.print(f"\n[bold green]✅ V20全息下载完成！候选: {len(candidates)} 只[/bold green]")

    def _get_full_universe(self) -> List[str]:
        try:
            from xtquant import xtdata
            return xtdata.get_stock_list_in_sector('沪深A股')
        except Exception:
            return []

    def _load_daily_k_data(self, stock_list: List[str], date: str) -> pd.DataFrame:
        try:
            from xtquant import xtdata
            start = (datetime.strptime(date, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d')
            data = xtdata.get_local_data(
                field_list=['time', 'open', 'high', 'low', 'close', 'volume', 'amount'],
                stock_list=stock_list, period='1d',
                start_time=start, end_time=date
            )
            rows = []
            for stock_code, df in data.items():
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    ma5 = df['volume'].tail(5).mean() if len(df) >= 5 else df['volume'].mean()
                    pre_close = df.iloc[-2]['close'] if len(df) >= 2 else latest['open']
                    rows.append({
                        'stock_code': stock_code,
                        'open': latest['open'], 'high': latest['high'],
                        'low': latest['low'], 'close': latest['close'],
                        'volume': latest['volume'], 'ma5_volume': ma5,
                        'pre_close': pre_close,
                        'float_volume': self._get_float_volume(stock_code)
                    })
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    def _get_float_volume(self, stock_code: str) -> float:
        try:
            from xtquant import xtdata
            detail = xtdata.get_instrument_detail(stock_code, True)
            if detail:
                return float(detail.get('FloatVolume', 0)) if hasattr(detail, 'get') \
                    else float(getattr(detail, 'FloatVolume', 0))
        except Exception:
            pass
        return 0


def run_v20_holographic_download(date: str | None = None):
    """
    V20全息下载便捷入口
    用法：
        python -c "from tools.unified_downloader import run_v20_holographic_download; run_v20_holographic_download('20260228')"
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    HolographicDownloaderV20().run_v20_download(date)


# =============================================================================
# 交互式菜单 + Click 入口（均走 Rich UI 壳）
# =============================================================================

def interactive_menu():
    """无参数启动时的交互式菜单（Rich Table 展示）"""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()

    table = Table(title="统一下载器  All-in-One Data Downloader", show_header=True,
                  header_style="bold cyan", border_style="cyan")
    table.add_column("选项", style="bold yellow", width=6)
    table.add_column("功能", width=28)
    table.add_column("说明")
    table.add_row("[1]", "日K数据", "全市场，最近N天")
    table.add_row("[2]", "Tick数据", "指定日期范围")
    table.add_row("[3]", "全息数据 - 单日", "指定日期")
    table.add_row("[4]", "全息数据 - 范围", "指定起止日期")
    table.add_row("[5]", "全息数据 - 默认", "最近60交易日")
    table.add_row("[q]", "退出", "")
    console.print(table)

    choice = input("请选择 [1-5/q]: ").strip().lower()
    if choice == 'q':
        return

    resume = input("启用断点续传？[Y/n]: ").strip().lower() != 'n'

    if choice == '1':
        raw = input("下载天数 [默认365]: ").strip()
        days = int(raw) if raw.isdigit() else 365
        input(f"  日K下载: 最近{days}天 | 断点续传={'开' if resume else '关'}  按 Enter 开始...")
        run_with_rich_ui(f"日K下载 最近{days}天", lambda: download_daily_k(days=days, resume=resume))

    elif choice == '2':
        start = input("开始日期 (YYYYMMDD): ").strip()
        end = input("结束日期 (YYYYMMDD): ").strip()
        if not start or not end:
            console.print("[red]❌ 日期不能为空[/red]")
            return
        input(f"  Tick下载: {start}~{end}  按 Enter 开始...")
        run_with_rich_ui(f"Tick下载 {start}~{end}", lambda: download_tick_data(start, end, resume=resume))

    elif choice == '3':
        date = input("目标日期 (YYYYMMDD): ").strip()
        if not date:
            console.print("[red]❌ 日期不能为空[/red]")
            return
        raw = input("超时秒数 [默认3600]: ").strip()
        timeout = int(raw) if raw.isdigit() else 3600
        input(f"  全息单日: {date} | 超时{timeout}s  按 Enter 开始...")
        run_with_rich_ui(f"全息单日 {date}", lambda: download_holographic(date, resume=resume, timeout=timeout))

    elif choice == '4':
        start = input("开始日期 (YYYYMMDD): ").strip()
        end = input("结束日期 (YYYYMMDD): ").strip()
        if not start or not end:
            console.print("[red]❌ 日期不能为空[/red]")
            return
        raw = input("每日超时秒数 [默认3600]: ").strip()
        timeout = int(raw) if raw.isdigit() else 3600
        input(f"  全息范围: {start}~{end} | 每日超时{timeout}s  按 Enter 开始...")
        run_with_rich_ui(f"全息范围 {start}~{end}",
                         lambda: download_holographic_range(start, end, resume=resume, timeout=timeout))

    elif choice == '5':
        raw = input("每日超时秒数 [默认3600]: ").strip()
        timeout = int(raw) if raw.isdigit() else 3600
        s, e, td = get_last_n_trading_days(60)
        input(f"  全息默认: {s}~{e} ({len(td)}个交易日)  按 Enter 开始...")
        run_with_rich_ui("全息默认60日",
                         lambda: download_holographic_range(s, e, resume=resume, timeout=timeout))

    else:
        console.print("[red]❌ 无效选项[/red]")
        return

    console.print("\n[green]✅ 任务结束[/green]")
    time.sleep(3)


@click.command()
@click.option('--type', 'download_type',
              type=click.Choice(['daily_k', 'tick', 'holographic']),
              default='daily_k', help='下载类型: daily_k=日K, tick=Tick数据, holographic=全息数据')
@click.option('--start-date', default=None, help='开始日期 YYYYMMDD')
@click.option('--end-date', default=None, help='结束日期 YYYYMMDD')
@click.option('--date', default=None, help='单日日期 YYYYMMDD（全息单日）')
@click.option('--days', default=365, type=int, help='下载天数（日K，默认365）')
@click.option('--timeout', default=3600, type=int, help='超时秒数（默认3600）')
@click.option('--no-resume', is_flag=True, help='禁用断点续传')
def main(download_type, start_date, end_date, date, days, timeout, no_resume):
    """统一下载器 - 所有启动方式均显示 Rich CLI 面板"""
    resume = not no_resume

    if download_type == 'daily_k':
        run_with_rich_ui(f"日K下载 最近{days}天",
                         lambda: download_daily_k(days=days, resume=resume))

    elif download_type == 'tick':
        if not start_date or not end_date:
            click.echo("❌ Tick下载需要指定 --start-date 和 --end-date")
            return
        run_with_rich_ui(f"Tick下载 {start_date}~{end_date}",
                         lambda: download_tick_data(start_date, end_date, resume=resume))

    elif download_type == 'holographic':
        if start_date and end_date:
            run_with_rich_ui(f"全息范围 {start_date}~{end_date}",
                             lambda: download_holographic_range(start_date, end_date,
                                                                resume=resume, timeout=timeout))
        elif date:
            run_with_rich_ui(f"全息单日 {date}",
                             lambda: download_holographic(date, resume=resume, timeout=timeout))
        else:
            s, e, td = get_last_n_trading_days(60)
            click.echo(f"💡 自动设定最近60交易日: {s} ~ {e} (共{len(td)}天)")
            run_with_rich_ui("全息默认60日",
                             lambda: download_holographic_range(s, e, resume=resume, timeout=timeout))


if __name__ == "__main__":
    # len(sys.argv) == 1 → 无参数 → 交互式菜单（走 Rich UI 壳）
    # len(sys.argv) > 1 → 带参数 → click 路径（也走 Rich UI 壳）
    if len(sys.argv) == 1:
        interactive_menu()
    else:
        main()
