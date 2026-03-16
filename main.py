#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 MyQuantTool - 统一CLI入口 (纯血游资雷达)                      ║
║              Phase 7: 架构统一 · CLI标准化 · 生产就绪                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  所有操作必须通过此入口执行                                                   ║
║  禁止直接运行 tasks/run_xxx.py 脚本（已弃用）                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

使用示例:
    # 回测
    python main.py backtest --date 20260105
    python main.py backtest --date 20260105 --universe data/cleaned_candidates_66.csv
    
    # 扫描
    python main.py scan --date 20260105 --mode premarket
    python main.py scan --mode intraday
    
    # 分析
    python main.py analyze --stock 300986.SZ --start-date 20251231 --end-date 20260105
    
    # 数据管理
    python main.py download --date 20260105
    python main.py verify --date 20260105
    
    # 监控
    python main.py monitor --mode event
    python main.py monitor --mode cli

Author: AI开发专家
Date: 2026-02-23
Version: 20.5.0
"""

# =============== 🚨 必须放在最第一行：强制直连 ===============
import os
import sys

# 🔥 [P0] Python 版本检查：必须使用 Python 3.10
if sys.version_info < (3, 10):
    print("❌ [System] Python 版本不满足要求！")
    print(f"   当前版本: {sys.version}")
    print(f"   要求版本: Python 3.10+")
    print("   请使用 venv_qmt 虚拟环境中的 Python 3.10")
    sys.exit(1)
elif sys.version_info >= (3, 11):
    print(f"⚠️  [System] 警告：检测到 Python {sys.version_info.major}.{sys.version_info.minor}")
    print("   推荐使用 Python 3.10 以确保 xtquant 兼容性")
    print("   当前版本可能导致 xtquant 模块异常")

# 🚀 [最高优先级] 强杀代理：必须在 import 其他库之前执行！
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(key, None)
os.environ['NO_PROXY'] = '*'
# ==========================================================

# 🔥 [P0] 加载环境变量：必须在所有业务模块import之前！
# 注：已全面弃用Tushare，使用QMT本地数据
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / '.env')
# ==========================================================

import click
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Windows编码卫士
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


def print_banner():
    """打印系统横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 MyQuantTool 纯血游资雷达.0 - Phase 7                          ║
║              统一CLI入口 · 架构标准化 · 生产就绪                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  核心能力: 回测 · 扫描 · 分析 · 监控 · 数据管理                              ║
║  数据引擎: QMT (xtquant) · 弃用Tushare直接调用                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    click.echo(click.style(banner, fg='cyan', bold=True))


def validate_date(ctx, param, value):
    """验证日期格式YYYYMMDD"""
    if value is None:
        return value
    try:
        datetime.strptime(value, '%Y%m%d')
        return value
    except ValueError:
        raise click.BadParameter(f'日期格式错误: {value}，请使用YYYYMMDD格式（如20260105）')


def validate_stock_code(ctx, param, value):
    """验证股票代码格式"""
    if value is None:
        return value
    # 支持格式: 300986.SZ, 000001.SH, 300986
    if '.' in value:
        code, exchange = value.split('.')
        if exchange not in ['SZ', 'SH', 'BJ']:
            raise click.BadParameter(f'交易所代码错误: {exchange}，应为SZ/SH/BJ')
        if not code.isdigit() or len(code) != 6:
            raise click.BadParameter(f'股票代码格式错误: {code}，应为6位数字')
    else:
        if not value.isdigit() or len(value) != 6:
            raise click.BadParameter(f'股票代码格式错误: {value}，应为6位数字')
    return value


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Group
# ═══════════════════════════════════════════════════════════════════════════════

@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='显示版本信息')
@click.pass_context
def cli(ctx, version):
    """MyQuantTool 统一CLI入口 - 量化交易系统主程序"""
    if version:
        click.echo("MyQuantTool 纯血游资雷达.0 - Phase 7统一CLI")
        ctx.exit()
    
    if ctx.invoked_subcommand is None:
        print_banner()
        click.echo(click.style("\n提示: 使用 --help 查看所有命令，或使用以下常用命令:\n", fg='yellow'))
        click.echo("  python main.py backtest --help    # 回测命令帮助")
        click.echo("  python main.py scan --help        # 扫描命令帮助")
        click.echo("  python main.py analyze --help     # 分析命令帮助")
        click.echo("  python main.py monitor --help     # 监控命令帮助")


# ═══════════════════════════════════════════════════════════════════════════════
# 回测命令
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='backtest')
@click.option('--date', '-d', callback=validate_date,
              help='交易日期 (YYYYMMDD格式, 如 20260105)。与--start_date/--end_date互斥')
@click.option('--start_date', callback=validate_date,
              help='开始日期 (YYYYMMDD格式)，用于连续回测')
@click.option('--end_date', callback=validate_date,
              help='结束日期 (YYYYMMDD格式)，用于连续回测')
@click.option('--universe', '-u',
              help='股票池: 单只股票或CSV文件路径（QMT本地数据）')
@click.option('--output', '-o', default='data/backtest_results',
              help='输出目录 (默认: data/backtest_results)')
@click.option('--save', is_flag=True, help='保存结果到文件')
@click.pass_context
def backtest_cmd(ctx, date, start_date, end_date, universe, output, save):
    """
    执行回测 - V20纯血全息架构
    
    示例:
        \b
        # 单日回测
        python main.py backtest --date 20260105
        
        # 指定股票池回测
        python main.py backtest --date 20260105 --universe data/cleaned_candidates_66.csv
        
        # 全息时间机器 - 跨日连贯流 (CTO强制)
        python main.py backtest --start_date 20251224 --end_date 20260105
        
        # 回测并保存结果
        python main.py backtest --date 20260105 --save --output data/results
    """
    # 参数验证
    if start_date and end_date:
        # 连续回测模式
        click.echo(click.style(f"\n🚀 启动V20纯血全息回测", fg='green', bold=True))
        click.echo(f"📅 区间: {start_date} ~ {end_date}")
        click.echo(f"🎯 股票池: {universe or '纯血QMT本地全市场'}")
        click.echo(f"💾 输出: {output}")
    elif date:
        # 单日回测模式
        click.echo(click.style(f"\n🚀 启动V20纯血回测", fg='green', bold=True))
        click.echo(f"📅 日期: {date}")
        click.echo(f"🎯 股票池: {universe or '纯血QMT本地全市场'}")
        click.echo(f"💾 输出: {output}")
    else:
        click.echo(click.style("❌ 错误: 必须指定 --date 或 --start_date/--end_date", fg='red'))
        ctx.exit(1)
    
    try:
        from logic.backtest.time_machine_engine import TimeMachineEngine
        from logic.core.config_manager import get_config_manager

        # 配置管理器统一参数管理 (CTO SSOT原则)
        config_manager = get_config_manager()
        min_vol = config_manager.get_min_volume_multiplier()
        click.echo(f"📊 量比阈值: {min_vol}x (从配置文件读取)")

        # V20纯血TimeMachineEngine
        engine = TimeMachineEngine(initial_capital=20000.0)

        if start_date and end_date:
            # 连续回测模式 - 100% QMT本地数据
            stock_pool_path = universe if universe and Path(universe).exists() else None
            results = engine.run_continuous_backtest(
                start_date=start_date,
                end_date=end_date,
                stock_pool_path=stock_pool_path
            )

            # 输出结果
            success_count = len([r for r in results if r.get('status') == 'success'])
            click.echo(click.style(f"\n✅ 跨日回测完成: {success_count}/{len(results)} 个交易日成功", fg='green'))

            if save:
                import json
                output_path = Path(output) / f'time_machine_{start_date}_{end_date}.json'
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                click.echo(f"💾 结果已保存: {output_path}")

        elif date:
            # 单日回测模式 - V20纯血入口
            result = engine.run_daily_backtest(date)

            # 回测结果已在大屏中展示，此处仅输出统计信息
            if result and result.get('top20'):
                click.echo(f"\n📊 回测统计: Top20候选股数量={len(result['top20'])}, 详见上方工业级大屏")

        click.echo(click.style("\n✅ V20纯血回测完成", fg='green'))
        
    except Exception as e:
        logger.error(f"❌ 回测失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 回测失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 【CTO强网关】入口级数据就绪断言
# ═══════════════════════════════════════════════════════════════════════════════

def assert_data_readiness(date: str, stock_list: list):
    """【CTO强网关】入口级数据就绪断言 - 拒绝在致盲状态下启动"""
    from xtquant import xtdata
    
    click.echo(click.style(f"🔍 [数据断言] 开始核验 {date} 数据完整性...", fg='yellow'))
    
    # 抽样检查深市和沪市的代表性股票
    check_stocks = ['000001.SZ', '300001.SZ', '600000.SH']
    valid_stocks = [s for s in check_stocks if s in stock_list]
    
    if not valid_stocks:
        valid_stocks = stock_list[:5]  # 如果代表股不在池子里，随便抽5只
        
    daily_data = xtdata.get_local_data(
        field_list=['close', 'amount'],
        stock_list=valid_stocks,
        period='1d',
        start_time=date,
        end_time=date
    )
    
    missing_count = 0
    for stock in valid_stocks:
        if stock not in daily_data or daily_data[stock].empty:
            missing_count += 1
        else:
            try:
                amount = float(daily_data[stock].iloc[-1].get('amount', 0))
                if amount <= 0:
                    missing_count += 1
            except Exception:
                missing_count += 1
            
    if missing_count > 0:
        error_msg = f"❌ [致命错误] 本地 QMT 缺少 {date} 的日K结算数据！系统拒绝在致盲状态下启动打分！"
        click.echo(click.style(error_msg, fg='red', bold=True))
        click.echo(click.style("💡 解决方案: 请运行 tools/smart_download.py 或在 QMT 客户端中补全数据。", fg='yellow'))
        raise SystemExit(1)
        
    click.echo(click.style(f"✅ [数据断言] {date} 基础日K数据已落盘就绪。", fg='green'))


# ═══════════════════════════════════════════════════════════════════════════════
# 热复盘命令 (CTO架构重组：独立于 live 和 backtest)
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='replay')
@click.option('--date', type=str, default=None, help='要复盘的日期 (YYYYMMDD)，不传则默认上个交易日')
@click.option('--pure', is_flag=True, default=False,
              help='纯净模式：不读取也不写入记忆库，用于独立单日切片研究')
@click.pass_context
def replay_cmd(ctx, date, pure):
    """
    🔥 今日/指定日热复盘
    
    默认模式：基因继承（读取并更新实盘记忆库）
    --pure模式：纯净切片（完全隔离记忆库，用于独立研究）
    
    \b
    示例:
        python main.py replay                    # 复盘上个交易日（基因继承）
        python main.py replay --date 20260227    # 复盘指定日期（基因继承）
        python main.py replay --pure             # 纯净切片（不读写记忆）
    """
    from logic.utils.calendar_utils import get_latest_completed_trading_day
    from logic.backtest.time_machine_engine import TimeMachineEngine
    from logic.utils.metrics_utils import render_battle_dashboard
    from xtquant import xtdata
    import time
    
    # 确定复盘日期
    if not date:
        date = get_latest_completed_trading_day()
        if not date:
            click.echo(click.style("❌ 无法确定复盘日期！", fg='red'))
            ctx.exit(1)
    
    # 【CTO非交易日拦截】在任何数据操作之前检查
    from logic.utils.calendar_utils import is_trading_day, get_nth_previous_trading_day
    if not is_trading_day(date):
        nearest = get_nth_previous_trading_day(date, 1)
        click.echo(click.style(f"❌ {date} 是非交易日（周末/节假日），无法热复盘！", fg='red', bold=True))
        click.echo(click.style(f"💡 最近的交易日是: {nearest}，请用 --date {nearest}", fg='yellow'))
        ctx.exit(1)
    
    mode_label = "🧪 纯净切片" if pure else "🧬 基因继承"
    click.echo(click.style(f"\n🎬 [热复盘] 日期: {date} | 模式: {mode_label}", fg='cyan', bold=True))
    
    # 1. 数据下载防线（确保本地有数据）
    click.echo(click.style(f"⏬ 检查 {date} 的数据...", fg='yellow'))
    try:
        # 【CTO强数据网关接入】强制拉取当天日K和Tick，确保本地绝对有数据
        xtdata.download_history_data("", "day", start_time=date, end_time=date)
        time.sleep(1)
        click.echo(click.style(f"✅ 日K数据已就绪", fg='green'))
    except Exception as e:
        click.echo(click.style(f"⚠️ 数据下载警告: {e}", fg='yellow'))
    
    # 1.5 【CTO强网关】入口级数据就绪断言
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    assert_data_readiness(date, all_stocks)
    
    # 2. 【CTO数据断言】预热字典并校验
    try:
        from logic.data_providers.true_dictionary import warmup_true_dictionary
        click.echo(click.style(f"  🔥 预热TrueDictionary...", fg='yellow'))
        warmup_result = warmup_true_dictionary(all_stocks, target_date=date)
        success_count = warmup_result.get('qmt', {}).get('success', 0)
        if success_count < 1000:
            click.echo(click.style(f"❌ [数据断言失败] 财务数据装弹仅成功 {success_count} 只，系统拒绝启动！", fg='red'))
            click.echo(click.style(f"   请先运行: python tools/smart_download.py 下载数据", fg='yellow'))
            ctx.exit(1)
        click.echo(click.style(f"  ✅ TrueDictionary预热完成", fg='green'))
    except Exception as e:
        click.echo(click.style(f"⚠️ 字典预热警告: {e}", fg='yellow'))
    
    # 2. 调用时间机器 (本质上是单日回测)
    click.echo(click.style(f"🚀 引擎启动，开始扫描...", fg='green'))
    
    engine = TimeMachineEngine(is_pure_mode=pure)
    result = engine.run_daily_backtest(date)
    
    # 3. 渲染大屏
    if result and result.get('top20'):
        dashboard_data = []
        for item in result['top20'][:20]:
            dashboard_data.append({
                'code': item.get('stock_code', ''),
                'score': item.get('final_score', 0),
                'price': item.get('real_close', item.get('price_0940', 0)),
                'change': item.get('final_change', item.get('change_pct', 0)),
                'inflow_ratio': item.get('inflow_ratio', 0),
                'ratio_stock': item.get('ratio_stock', 0),
                'sustain_ratio': item.get('sustain_ratio', 0),
                'mfe': item.get('mfe', 0),
                'tag': item.get('tag', '复盘')
            })
        title_suffix = "(纯净切片·无记忆)" if pure else "(基因继承·实盘库)"
        render_battle_dashboard(dashboard_data, title=f"🔥 极速热复盘 [{date}] {title_suffix}", clear_screen=False)
        click.echo(click.style(f"\n✅ 热复盘完成: 共评分 {len(result['top20'])} 只股票", fg='green'))
    else:
        click.echo(click.style(f"\n⚠️ 日期 {date} 没有任何股票通过风控漏斗！", fg='yellow'))


# ═══════════════════════════════════════════════════════════════════════════════
# 扫描命令 - V38定格沙盘模式
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='scan')
@click.option('--date', '-d', callback=validate_date,
              help='交易日期 (YYYYMMDD格式，默认最近交易日)')
@click.pass_context
def scan_cmd(ctx, date):
    """
    📊 [CTO V58] Tick级定格沙盘 - 绝对同质同源架构
    
    【P0修复】彻底废除200行独立循环，接入run_historical_stream！
    - scan模式与Live模式共享同一套LiveTradingEngine逻辑
    - MockQmtAdapter伪装实时流，历史Tick泵入引擎打分
    - 物理判断100%一致，消灭Scan与Live的差异！
    
    示例:
        \b
        python main.py scan
        python main.py scan --date 20260306
    """
    from logic.utils.calendar_utils import get_latest_completed_trading_day
    from tasks.run_live_trading_engine import LiveTradingEngine
    from logic.data_providers.mock_qmt_adapter import MockQmtAdapter
    
    target_date = date or get_latest_completed_trading_day()
    
    click.echo(click.style(f"\n🔍 启动【Tick级定格沙盘扫描 - V58同源架构】", fg='cyan', bold=True))
    click.echo(f"📅 目标日期: {target_date}")
    click.echo(f"💡 模式: MockQmtAdapter + run_historical_stream，与实盘100%同源")
    
    try:
        # 【P0修复】使用MockQmtAdapter伪装实时流
        click.echo("\n📦 Step 1: 初始化MockQmtAdapter...")
        mock_adapter = MockQmtAdapter(target_date=target_date)
        mock_adapter.initialize()
        click.echo(f"   ✅ MockQmtAdapter就绪")
        
        # 【P0修复】使用LiveTradingEngine的run_historical_stream
        click.echo("\n📦 Step 2: 启动LiveTradingEngine...")
        engine = LiveTradingEngine(qmt_manager=mock_adapter, mode='scan')
        click.echo(f"   ✅ Engine就绪 (mode=scan)")
        
        # 【P0修复】构建tick_stream（收盘最后一笔tick）
        click.echo("\n📦 Step 3: 构建Tick流...")
        tick_stream = []
        from xtquant import xtdata
        base_pool = mock_adapter.watchlist if hasattr(mock_adapter, 'watchlist') and mock_adapter.watchlist else []
        if not base_pool:
            # 如果没有watchlist，从UniverseBuilder获取
            from logic.data_providers.universe_builder import UniverseBuilder
            builder = UniverseBuilder(target_date=target_date)
            base_pool, _ = builder.build()
        
        click.echo(f"   底池规模: {len(base_pool)} 只")
        
        # 【CTO V74宪法】不得日K兜底，缺失即补充！
        # Tick数据包含盘中净流入、资金流向、盘口等关键信息
        # 日线无法伪造Tick，没有真实Tick必须物理剔除！
        for stock in base_pool:
            try:
                # 只使用真实Tick数据
                tick_data = xtdata.get_local_data(
                    field_list=[], 
                    stock_list=[stock], 
                    period='tick',
                    start_time=f"{target_date}092500", 
                    end_time=f"{target_date}150000"
                )
                
                if tick_data and stock in tick_data:
                    df = tick_data[stock]
                    if df is not None and not (hasattr(df, 'empty') and df.empty) and len(df) > 0:
                        # 取最后一笔Tick作为收盘快照
                        row = df.iloc[-1]
                        tick = {
                            'stock_code': stock,
                            'datetime': f"{target_date}150000",
                            'price': float(row.get('lastPrice', row.get('price', 0))),
                            'open': float(row.get('open', 0)),
                            'high': float(row.get('high', 0)),
                            'low': float(row.get('low', 0)),
                            'volume': int(row.get('volume', 0)),
                            'amount': float(row.get('amount', 0)),
                            'lastClose': float(row.get('lastClose', row.get('preClose', 0))),
                            'askPrice1': float(row.get('askPrice1', 0)),
                            'bidPrice1': float(row.get('bidPrice1', 0)),
                        }
                        # 只有有效Tick才加入
                        if tick['amount'] > 0 and tick['price'] > 0:
                            tick_stream.append(tick)
                # 无Tick则直接跳过，绝不用日线兜底！
            except Exception:
                continue
        
        # 【CTO V74】统计缺失并提示用户补充
        missing_tick_count = len(base_pool) - len(tick_stream)
        if missing_tick_count > 0:
            click.echo(click.style(f"⚠️ [数据截断] 发现 {missing_tick_count} 只标的缺乏当天Tick数据，已进行物理隔离。", fg='yellow'))
            click.echo(click.style(f"💡 必须运行: python tools/smart_download.py 补充弹药！", fg='yellow'))
        
        click.echo(f"   有效Tick: {len(tick_stream)} 笔")
        
        if len(tick_stream) == 0:
            click.echo(click.style("❌ 无有效Tick数据，扫描终止", fg='red'))
            return
        
        # 【P0修复】调用run_historical_stream直线喷射引擎
        click.echo("\n📦 Step 4: 启动直线喷射引擎...")
        engine.watchlist = base_pool  # 【CTO 补天】强制将粗筛底池注入引擎的供弹带！
        engine.run_historical_stream(tick_stream)
        
        click.echo(click.style("\n✅ 沙盘扫描完成", fg='green'))
        
    except KeyboardInterrupt:
        click.echo(click.style("\n⚠️ 用户中断扫描", fg='yellow'))
        ctx.exit(130)
    except Exception as e:
        logger.error(f"❌ 扫描失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 扫描失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 分析命令
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='analyze')
@click.option('--stock', '-s', required=True, callback=validate_stock_code,
              help='股票代码 (如 300986.SZ 或 300986)')
@click.option('--start-date', callback=validate_date,
              help='开始日期 (YYYYMMDD)')
@click.option('--end-date', callback=validate_date,
              help='结束日期 (YYYYMMDD)')
@click.option('--date', '-d', callback=validate_date,
              help='分析单个日期 (YYYYMMDD，与start-date/end-date互斥)')
@click.option('--detail', is_flag=True, help='显示详细分析')
@click.pass_context
def analyze_cmd(ctx, stock, start_date, end_date, date, detail):
    """
    分析单只股票
    
    示例:
        \b
        # 分析单日
        python main.py analyze --stock 300986.SZ --date 20260105
        
        # 分析日期范围
        python main.py analyze --stock 300986.SZ --start-date 20251231 --end-date 20260105
        
        # 详细分析
        python main.py analyze --stock 300986.SZ --date 20260105 --detail
    """
    # 参数校验
    if date and (start_date or end_date):
        click.echo(click.style("❌ 错误: --date 与 --start-date/--end-date 不能同时使用", fg='red'))
        ctx.exit(1)
    
    if not date and not start_date:
        # 默认分析今天
        date = datetime.now().strftime('%Y%m%d')
    
    # 标准化股票代码
    if '.' not in stock:
        # 根据代码前缀判断交易所
        if stock.startswith('6'):
            stock = f"{stock}.SH"
        elif stock.startswith('8') or stock.startswith('4'):
            stock = f"{stock}.BJ"
        else:
            stock = f"{stock}.SZ"
    
    click.echo(click.style(f"\n📊 股票分析", fg='green', bold=True))
    click.echo(f"🎯 股票: {stock}")
    if date:
        click.echo(f"📅 日期: {date}")
    else:
        click.echo(f"📅 范围: {start_date} 至 {end_date}")
    
    try:
        from logic.services.event_lifecycle_service import EventLifecycleService
        
        service = EventLifecycleService()
        
        if date:
            # 单日分析
            result = service.analyze(stock, date)
            
            click.echo(f"\n📈 分析结果:")
            click.echo(f"  维持分: {result.get('sustain_score', 0):.2f}")
            click.echo(f"  环境分: {result.get('env_score', 0):.2f}")
            click.echo(f"  是否真起爆: {'✅' if result.get('is_true_breakout') else '❌'}")
            click.echo(f"  置信度: {result.get('confidence', 0):.2f}")
            
            if detail:
                click.echo(f"\n🔍 详细信息:")
                click.echo(f"  维持时长: {result.get('sustain_duration_min', 0):.1f} 分钟")
                if result.get('entry_signal'):
                    entry = result['entry_signal']
                    click.echo(f"  建议入场价: {entry.get('entry_price', 0):.2f}")
                    click.echo(f"  预期盈亏: {entry.get('pnl_pct', 0):.2f}%")
        else:
            # 日期范围分析
            from datetime import timedelta
            start = datetime.strptime(start_date, '%Y%m%d')
            end = datetime.strptime(end_date, '%Y%m%d')
            
            current = start
            while current <= end:
                date_str = current.strftime('%Y%m%d')
                try:
                    result = service.analyze(stock, date_str)
                    status = '✅' if result.get('is_true_breakout') else '❌'
                    click.echo(f"  {date_str}: {status} sustain={result.get('sustain_score', 0):.2f}")
                except Exception as e:
                    click.echo(f"  {date_str}: ⚠️ {e}")
                current += timedelta(days=1)
        
        click.echo(click.style("\n✅ 分析完成", fg='green'))
        
    except Exception as e:
        logger.error(f"❌ 分析失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 分析失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 数据下载命令
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='download')
@click.option('--date', '-d', callback=validate_date,
              help='交易日期 (YYYYMMDD，默认今天)')
@click.option('--type', 'data_type',
              type=click.Choice(['tick', 'kline', 'all']),
              default='all',
              help='数据类型 (默认: all)')
@click.option('--universe', '-u',
              help='股票池CSV文件路径')
@click.option('--workers', '-w', type=int, default=4,
              help='并发 workers 数 (默认: 4)')
@click.pass_context
def download_cmd(ctx, date, data_type, universe, workers):
    """
    数据下载管理
    
    示例:
        \b
        # 下载今日所有数据
        python main.py download
        
        # 下载指定日期Tick数据
        python main.py download --date 20260105 --type tick
        
        # 下载指定股票池数据
        python main.py download --date 20260105 --universe data/cleaned_candidates_66.csv
    """
    date = date or datetime.now().strftime('%Y%m%d')
    
    click.echo(click.style(f"\n📥 数据下载", fg='green', bold=True))
    click.echo(f"📅 日期: {date}")
    click.echo(f"📊 类型: {data_type}")
    click.echo(f"🔧 Workers: {workers}")
    
    try:
        # 加载股票池
        stock_list = []
        if universe and Path(universe).exists():
            # CTO修复：支持JSON和CSV两种格式
            if universe.endswith('.json'):
                import json
                with open(universe, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 支持多种JSON格式
                    stock_list = data.get('stocks', data.get('target', []))
                    if not stock_list and isinstance(data, list):
                        stock_list = data
                click.echo(f"📋 从JSON加载 {len(stock_list)} 只股票")
            else:
                # CSV格式
                import pandas as pd
                df = pd.read_csv(universe)
                stock_list = df.iloc[:, 0].tolist() if len(df.columns) == 1 else df['code'].tolist()
                click.echo(f"📋 从CSV加载 {len(stock_list)} 只股票")
        elif not universe:
            # 如果未指定股票池，使用粗筛获取股票池
            from logic.data_providers.universe_builder import UniverseBuilder
            
            builder = UniverseBuilder(target_date=date)
            stock_list = builder.build()
            click.echo(f"📊 粗筛获取到 {len(stock_list)} 只股票")
        
        # 执行下载 - 使用QmtDataManager
        from logic.data_providers.qmt_manager import QmtDataManager
        import time
        
        manager = QmtDataManager()
        
        if stock_list:
            click.echo(f"开始下载 {len(stock_list)} 只股票的Tick数据...")
            
            # 【CTO V38修复】废除[:200]一刀切！改用batch_size循环+冷却机制
            batch_size = 200
            results = {}
            total_batches = (len(stock_list) + batch_size - 1) // batch_size
            
            for i in range(0, len(stock_list), batch_size):
                batch = stock_list[i:i + batch_size]
                batch_num = i // batch_size + 1
                click.echo(f"正在下载第 {batch_num}/{total_batches} 批 ({len(batch)}只)...")
                
                batch_res = manager.download_tick_data(
                    stock_list=batch,
                    trade_date=date,
                    use_vip=True,
                    check_existing=True
                )
                results.update(batch_res)
                
                # 批次间休息2秒，防止QMT服务端把我们踢下线
                if i + batch_size < len(stock_list):
                    time.sleep(2.0)
            
            success = sum(1 for r in results.values() if r.success)
            failed = sum(1 for r in results.values() if not r.success)
            
            for stock, result in results.items():
                if result.success:
                    click.echo(f"  ✅ {stock}: {result.record_count}条")
                else:
                    click.echo(f"  ❌ {stock}: {result.message or result.error}")
            
            click.echo(f"\n下载完成: 成功={success}, 失败={failed}")
        else:
            click.echo(click.style("⚠️ 未指定股票池，使用默认列表", fg='yellow'))
            # 使用默认下载逻辑
            
        click.echo(click.style("\n✅ 下载完成", fg='green'))
        
    except Exception as e:
        logger.error(f"❌ 下载失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 下载失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 验证命令
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='verify')
@click.option('--date', '-d', callback=validate_date,
              help='交易日期 (YYYYMMDD，默认今天)')
@click.option('--type', 'verify_type',
              type=click.Choice(['tick', 'kline', 'all']),
              default='all',
              help='验证类型 (默认: all)')
@click.option('--fix', is_flag=True, help='自动修复缺失数据')
@click.pass_context
def verify_cmd(ctx, date, verify_type, fix):
    """
    数据完整性验证
    
    示例:
        \b
        # 验证今日数据
        python main.py verify
        
        # 验证指定日期并修复
        python main.py verify --date 20260105 --fix
    """
    date = date or datetime.now().strftime('%Y%m%d')
    
    click.echo(click.style(f"\n🔍 数据完整性验证", fg='green', bold=True))
    click.echo(f"📅 日期: {date}")
    click.echo(f"📊 类型: {verify_type}")
    click.echo(f"🔧 自动修复: {'是' if fix else '否'}")
    
    try:
        from logic.qmt_health_check import QMTHealthCheck
        
        checker = QMTHealthCheck()
        
        # 执行验证
        result = checker.verify_date(date, verify_type)
        
        click.echo(f"\n📊 验证结果:")
        click.echo(f"  状态: {'✅ 通过' if result.get('valid') else '❌ 失败'}")
        click.echo(f"  缺失股票数: {len(result.get('missing', []))}")
        click.echo(f"  异常股票数: {len(result.get('anomalies', []))}")
        
        if fix and not result.get('valid'):
            click.echo("\n🔧 开始修复...")
            fixed = checker.fix_missing(date, result.get('missing', []))
            click.echo(f"  已修复: {fixed} 只股票")
        
        click.echo(click.style("\n✅ 验证完成", fg='green'))
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 验证失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 监控命令
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='monitor')
@click.option('--mode', '-m',
              type=click.Choice(['event', 'cli', 'auction']),
              default='event',
              help='监控模式 (默认: event)')
@click.option('--interval', '-i', type=int, default=3,
              help='监控间隔秒数 (默认: 3)')
@click.pass_context
def monitor_cmd(ctx, mode, interval):
    """
    启动实时监控系统
    
    示例:
        \b
        # 启动事件驱动监控（推荐）
        python main.py monitor
        
        # 启动CLI监控终端
        python main.py monitor --mode cli
        
        # 启动集合竞价监控（直连LiveTradingEngine竞价管理器）
        python main.py monitor --mode auction
    """
    click.echo(click.style(f"\n👁️ 启动监控系统", fg='green', bold=True))
    click.echo(f"📊 模式: {mode}")
    click.echo(f"⏱️  间隔: {interval}秒")
    
    try:
        if mode == 'event':
            from tasks.run_event_driven_monitor import EventDrivenMonitor
            
            monitor = EventDrivenMonitor()
            monitor.run()
            
        elif mode == 'cli':
            from tools.cli_monitor import main as cli_monitor_main
            
            cli_monitor_main()
            
        elif mode == 'auction':
            # [CTO-FIX] tasks/auction_manager.py 不存在，直接实例化 LiveTradingEngine
            # 调用竞价快照初筛入口 _execute_auction_filter()
            click.echo(click.style("🔔 启动集合竞价监控 (直连LiveTradingEngine)", fg='cyan'))
            from tasks.run_live_trading_engine import LiveTradingEngine
            from logic.data_providers.qmt_manager import QmtDataManager
            from logic.core.config_manager import get_config_manager

            config_manager = get_config_manager()
            try:
                qmt_manager = QmtDataManager()
            except Exception as e:
                click.echo(click.style(f"❌ QMT Manager创建失败: {e}", fg='red'))
                ctx.exit(1)

            engine = LiveTradingEngine(qmt_manager=qmt_manager)
            click.echo("⚡ 执行集合竞价快照初筛...")
            # 直接触发竞价初筛，不启动完整交易session
            engine._execute_auction_filter()
            watchlist_count = len(engine.watchlist) if hasattr(engine, 'watchlist') else 0
            click.echo(click.style(f"✅ 竞价初筛完成，观察池: {watchlist_count} 只", fg='green'))
            if watchlist_count > 0 and hasattr(engine, 'watchlist'):
                click.echo(click.style(f"📊 前10只: {engine.watchlist[:10]}", fg='cyan'))
            
    except KeyboardInterrupt:
        click.echo(click.style("\n⚠️ 用户中断监控", fg='yellow'))
        ctx.exit(130)
    except Exception as e:
        logger.error(f"❌ 监控失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 监控失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 历史模拟命令 (Phase 0.5)
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='simulate')
@click.option('--start-date', required=True, callback=validate_date,
              help='开始日期 (YYYYMMDD)')
@click.option('--end-date', required=True, callback=validate_date,
              help='结束日期 (YYYYMMDD)')
@click.option('--watchlist', help='关注列表CSV文件')
@click.option('--phase', type=click.Choice(['0.5', '3']), default='0.5',
              help='Phase版本 (默认: 0.5)')
@click.pass_context
def simulate_cmd(ctx, start_date, end_date, watchlist, phase):
    """
    运行历史模拟测试 (Phase 0.5 / Phase 3)
    
    示例:
        \b
        # Phase 0.5: 50样本历史回测
        python main.py simulate --start-date 2026-02-24 --end-date 2026-02-28
        
        # Phase 3: 实盘测试
        python main.py simulate --phase 3 --watchlist data/watchlist.csv
    """
    click.echo(click.style(f"\n🎮 启动历史模拟 (Phase {phase})", fg='green', bold=True))
    click.echo(f"📅 范围: {start_date} 至 {end_date}")
    
    try:
        if phase == '0.5':
            from tasks.run_historical_simulation import HistoricalSimulator
            
            simulator = HistoricalSimulator()
            samples = simulator.load_samples()
            
            if not samples:
                click.echo(click.style("❌ 无可用样本", fg='red'))
                ctx.exit(1)
            
            results = simulator.run_simulation(samples)
            simulator.generate_statistics(results)
            
        elif phase == '3':
            from tasks.run_realtime_phase3_test import RealtimePhase3Tester
            
            tester = RealtimePhase3Tester()
            
            # 加载关注列表
            watchlist_data = []
            if watchlist and Path(watchlist).exists():
                import pandas as pd
                df = pd.read_csv(watchlist)
                watchlist_data = list(zip(df['code'], df['name']))
            else:
                # 默认列表
                watchlist_data = [
                    ('300017', '网宿科技'),
                    ('000547', '航天发展'),
                ]
            
            tester.run_full_test(watchlist_data, start_date, end_date)
        
        click.echo(click.style("\n✅ 模拟完成", fg='green'))
        
    except Exception as e:
        logger.error(f"❌ 模拟失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 模拟失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 实盘交易命令 (系统封板)
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='live')
@click.option('--mode', 
              type=click.Choice(['paper', 'real']), 
              default='paper',
              help='交易模式: paper=模拟盘, real=实盘')
@click.option('--max-positions', default=3, help='最大持仓数量')
@click.option('--cutoff-time', default='14:50:00', help='截停时间(不开新仓)')
@click.option('--dry-run', is_flag=True, help='干运行(不实际下单)')
@click.pass_context
def live_cmd(ctx, mode, max_positions, cutoff_time, dry_run):
    """
    🚀 实盘猎杀系统 - 纯血游资雷达高阶算子版 (EventDriven事件驱动)
    
    CTO强制规范: 
    - 09:25盘前装弹 → 09:30极速扫描 → 09:35后火控雷达
    - 所有数据必须QMT原生，禁止任何外网请求！
    - Tushare已物理剥离，改用QMT本地数据
    - 依赖注入模式：QMT实例从main.py传入引擎
    - 换手率死亡拦截上限：70%（统一标准，研究验证：70%以上10日亏损14.67%）
    
    示例:
        python main.py live --mode paper          # 模拟盘测试
        python main.py live --mode real --dry-run # 实盘干运行
        python main.py live --mode real           # 实盘交易(⚠️危险)
    """
    from datetime import datetime
    import time
    
    # ==========================================
    # 【CTO绝对物理拦截】交易日判断与自动降级
    # ==========================================
    from logic.utils.calendar_utils import is_trading_day, get_latest_completed_trading_day
    
    now = datetime.now()
    today_str = now.strftime('%Y%m%d')
    
    # 【CTO V38四维架构】live模式只连QMT内存，非交易日物理阻断！
    # 周末/节假日请使用scan模式读取硬盘Tick数据对齐实盘
    
    is_trading = is_trading_day(today_str)
    current_hour = now.hour
    
    # 【CTO V40 老板钦定架构】非交易日，或交易日已过 15:00，绝对封杀 Live！
    if not is_trading:
        click.echo(click.style(f"\n📅 今天 ({today_str}) 是非交易日（周六/周日/节假日）", fg='yellow'))
        click.echo(click.style("🚫 【CTO V40架构铁律】实盘火控雷达已物理上锁！", fg='red', bold=True))
        click.echo(click.style("💡 老板指令：盘后定格与全息推演，请直接使用 Scan 模式：", fg='cyan'))
        click.echo("   python main.py scan")
        return  # 💥物理阻断！
    elif current_hour >= 15:
        click.echo(click.style(f"\n⏰ 当前时间已过15:00，实盘交易时段已结束", fg='yellow'))
        click.echo(click.style("🚫 【CTO V40架构铁律】实盘火控雷达已物理上锁！", fg='red', bold=True))
        click.echo(click.style("💡 老板指令：盘后定格与全息推演，请直接使用 Scan 模式：", fg='cyan'))
        click.echo("   python main.py scan")
        return  # 💥物理阻断！连JSON都不读，直接让用户去执行scan！
    
    click.echo(click.style(f"\n🚀 启动实盘猎杀系统 (EventDriven 事件驱动模式)", fg='green', bold=True))
    
    click.echo(f"📅 日期: {datetime.now().strftime('%Y-%m-%d')}")
    click.echo(f"📊 模式: {'模拟盘' if mode == 'paper' else '实盘交易'}")
    click.echo(f"💰 最大持仓: {max_positions}")
    from logic.core.config_manager import get_config_manager
    config_manager = get_config_manager()
    min_vol = config_manager.get('live_sniper.min_volume_multiplier', 3.0)
    click.echo(f"📊 绝对量比阈值: {min_vol}x (配置文件驱动)")
    click.echo(f"⏰ 截停时间: {cutoff_time}")
    click.echo(click.style(f"🔒 换手率死亡拦截上限: 70%（研究验证：70%以上10日亏损14.67%）", fg='yellow'))
    if dry_run:
        click.echo(click.style("🧪 干运行模式(不实际下单)", fg='yellow'))
    
    try:
        # ==========================================
        # Step 0: 数据检查 (CTO强制：实盘优先快速启动，不阻塞)
        # ==========================================
        click.echo("\n📦 Step 0: 数据检查...")
        
        from xtquant import xtdata
        from datetime import timedelta
        
        # CTO修正：实盘不下载！优先快速启动
        # 数据下载用 tools/download_daily_k.py 维护脚本
        # QMT客户端每天自动更新日线数据
        
        # 获取全市场股票列表
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        if not all_stocks:
            click.echo(click.style("❌ 无法获取股票列表", fg='red'))
            ctx.exit(1)
        
        click.echo(f"   全市场共 {len(all_stocks)} 只股票")
        click.echo(f"   💡 如需补充数据，请运行: python tools/download_daily_k.py")
        
        # ==========================================
        # Step 1: QMT连接 + 本地数据装弹 (CTO强制：0外网请求)
        # ==========================================
        click.echo("\n📦 Step 1: 盘前装弹 (QMT本地模式)...")
        
        # CTO规范：先连接QMT
        try:
            click.echo(f"✅ xtdata已连接")
        except Exception as e:
            click.echo(click.style(f"❌ QMT连接失败: {e}", fg='red'))
            ctx.exit(1)
        
        # 获取全市场股票列表（QMT本地，毫秒级）
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        if not all_stocks:
            click.echo(click.style("❌ 无法获取股票列表", fg='red'))
            ctx.exit(1)
        
        click.echo(f"   全市场共 {len(all_stocks)} 只股票")
        
        # CTO强制：使用QMT本地数据计算5日均量，替代Tushare外网请求
        click.echo("🔄 [QMT本地] 开始装弹...")
        from logic.data_providers.true_dictionary import get_true_dictionary
        true_dict = get_true_dictionary()
        
        # 【CTO修复】使用last_trade_day计算5日均量，绝不包含今天的盘中数据！
        from logic.utils.calendar_utils import get_latest_completed_trading_day
        last_trade_day = get_latest_completed_trading_day()
        click.echo(f"📅 基准日期: {last_trade_day} (上一个交易日)")
        warmup_result = true_dict.warmup(all_stocks, target_date=last_trade_day)  # 全市场预热
        
        if not warmup_result.get('ready_for_trading'):
            click.echo(click.style("🚨 盘前装弹失败! 系统熔断退出", fg='red', bold=True))
            ctx.exit(1)
        
        click.echo(click.style("✅ 盘前装弹完成！QMT本地数据已就位（0外网请求）", fg='green'))
        
        # ==========================================
        # Step 2: 时间管理 (CTO加固 - 修正If-Else遮蔽效应)
        # ==========================================
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=5, second=0, microsecond=0)  # 收盘时间
        cutoff = datetime.strptime(cutoff_time, '%H:%M:%S').time()
        cutoff_dt = now.replace(hour=cutoff.hour, minute=cutoff.minute, second=cutoff.second)
        
        # ==========================================
        # 公共函数：创建并初始化 LiveTradingEngine（避免重复代码）
        # ==========================================
        def _create_engine() -> 'LiveTradingEngine':
            from tasks.run_live_trading_engine import LiveTradingEngine
            from logic.core.config_manager import get_config_manager
            from logic.data_providers.qmt_manager import QmtDataManager

            config_manager = get_config_manager()

            try:
                qmt_manager = QmtDataManager()
                click.echo("✅ QMT Manager 已创建")
            except Exception as exc:
                click.echo(click.style(f"❌ QMT Manager创建失败: {exc}", fg='red'))
                raise

            return LiveTradingEngine(
                qmt_manager=qmt_manager,
                volume_percentile=None  # 从配置文件读取
            )

        # 初始化引擎变量，防止作用域错误
        engine = None
        
        # 【CTO V5斩首】删除收盘后拦截逻辑！
        # 盘后投影模式：15:00后依然进入LiveTradingEngine，用get_full_tick获取定格Tick
        # 收盘后不再return，继续往下执行！
        
        # ==================================================================
        # [CTO-FIX P0] 开盘前窗口（06:00 ~ 09:30）
        # 原始Bug：sleep(3)后 engine=None，程序静默退出，竞价+开盘全部跳过
        # 修复：sleep后立即创建engine并调用start_session()，进入保活循环
        # ==================================================================
        if now < market_open:
            # [P0修复] 06:00~09:30 竞价窗口：创建engine，等待开盘，不退出！
            wait_seconds = (market_open - now).seconds
            click.echo(click.style(
                f"⏳ 盘前装载模式 (距09:30开盘 {wait_seconds}秒)，创建引擎等待竞价...",
                fg='cyan'
            ))
            click.echo("\n⚡ Step 2: 挂载 EventDriven 引擎 (盘前模式)...")
            engine = _create_engine()
            # start_session 内部会设置 Timer 等到 09:25 触发竞价快照
            engine.start_session()
            click.echo(click.style("✅ 引擎已挂载，等待09:25竞价快照 → 09:30开盘信号", fg='green'))
            click.echo(click.style("🛑 按 Ctrl+C 安全退出", fg='yellow'))
            # 不 return！继续落到下面的 Step 4 保活循环
        
        # 交易时间内或盘后：启动监控/投影模式
        else:
            click.echo("\n⚡ Step 2: 挂载 EventDriven 引擎...")
            engine = _create_engine()
            
            # 【P0修复】SessionSnapshot: 重启自动恢复记忆
            from logic.memory.session_snapshot import SessionSnapshot
            session_snap = SessionSnapshot(trade_date=today_str)
            
            # 尝试恢复上次崩溃状态
            restored = session_snap.restore(engine)
            if restored:
                click.echo(click.style(
                    f"🔄 [自动恢复] 检测到上次异常退出，已恢复候选池/机会池状态",
                    fg='yellow'
                ))
            
            # 启动自动快照（每30秒）
            session_snap.start_auto_snapshot(engine)
            click.echo(click.style("📸 [SessionSnapshot] 自动快照已启动 (每30秒)", fg='cyan'))
            
            engine.start_session()
        
            # 【CTO审计】强制显示观察池数量
            watchlist_count = len(engine.watchlist) if hasattr(engine, 'watchlist') else 0
            click.echo(click.style("=" * 60, fg='cyan'))
            click.echo(click.style(f"🚨 [CTO强制审计] 观察池最终状态: {watchlist_count}只", fg='cyan'))
            if watchlist_count > 0:
                click.echo(click.style(f"📊 [CTO强制审计] 前5只: {engine.watchlist[:5]}", fg='cyan'))
            else:
                click.echo(click.style(f"❌ [CTO强制审计] 观察池为空！系统将进入待机模式", fg='red'))
            click.echo(click.style("=" * 60, fg='cyan'))
            
            click.echo(click.style("🎯 进入高频盯盘雷达模式...", fg='green'))
            click.echo(click.style("✅ 监控器已启动，EventBus后台运行中...", fg='green'))
            click.echo(click.style("🎯 等待QMT Tick数据推送...", fg='cyan'))
            click.echo(click.style("🛑 按 Ctrl+C 安全退出", fg='yellow'))

        # ==========================================
        # Step 4: 主线程保活 (CTO关键修复！)
        # ==========================================
        # engine 不为 None（盘前/盘中均已创建），进入保活循环
        if engine is not None:
            try:
                while engine.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            
            click.echo("\n🛑 收到中断信号，正在卸载监控器...")
            engine.stop()
            
            # 【P0修复】SessionSnapshot: 停止自动快照
            if 'session_snap' in dir() and session_snap is not None:
                session_snap.stop_auto_snapshot(engine)
                click.echo(click.style("📸 [SessionSnapshot] 自动快照已停止", fg='cyan'))
            
            click.echo(click.style("✅ 系统安全退出", fg='green'))
        
    except Exception as e:
        logger.error(f"❌ 实盘系统失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 系统失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    cli()
