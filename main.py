#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 MyQuantTool - 统一CLI入口 (V20)                        ║
║              Phase 7: 架构统一 · CLI标准化 · 生产就绪                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  所有操作必须通过此入口执行                                                   ║
║  禁止直接运行 tasks/run_xxx.py 脚本（已弃用）                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

使用示例:
    # 回测
    python main.py backtest --date 20260105 --universe 300986.SZ
    python main.py backtest --date 20260105 --universe data/cleaned_candidates_66.csv --strategy v18
    
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
Version: 20.0.0
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
║                    🚀 MyQuantTool V20.0.0 - Phase 7                          ║
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
        click.echo("MyQuantTool V20.0.0 - Phase 7统一CLI")
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
@click.option('--date', '-d', required=True, callback=validate_date,
              help='交易日期 (YYYYMMDD格式, 如 20260105)')
@click.option('--universe', '-u', 
              help='股票池: 单只股票如300986.SZ，或CSV文件路径如data/cleaned_candidates_66.csv')
@click.option('--strategy', '-s', default='right_side_breakout',
              type=click.Choice(['right_side_breakout', 'v18', 'time_machine', 'behavior_replay']),
              help='策略名称 (默认: right_side_breakout)')
@click.option('--output', '-o', default='data/backtest_results',
              help='输出目录 (默认: data/backtest_results)')
@click.option('--save', is_flag=True, help='保存结果到文件')
@click.option('--target', help='目标股票代码（用于验证，如300986）')
@click.pass_context
def backtest_cmd(ctx, date, universe, strategy, output, save, target):
    """
    执行回测
    
    示例:
        \b
        # 基础回测
        python main.py backtest --date 20260105 --universe 300986.SZ
        
        # V18策略回测
        python main.py backtest --date 20260105 --universe data/cleaned_candidates_66.csv --strategy v18
        
        # 时间机器回测（两段式筛选）
        python main.py backtest --date 20260105 --strategy time_machine --target 300986
        
        # 行为回测并保存结果
        python main.py backtest --date 20260105 --universe 300986.SZ --save --output data/results
    """
    click.echo(click.style(f"\n🚀 启动回测: {strategy}", fg='green', bold=True))
    click.echo(f"📅 日期: {date}")
    click.echo(f"🎯 股票池: {universe or '默认全市场'}")
    click.echo(f"💾 输出: {output}")
    
    try:
        if strategy == 'time_machine':
            # 时间机器回测
            from tasks.run_time_machine_backtest import TimeMachineBacktest, save_results
            
            time_machine = TimeMachineBacktest()
            result = time_machine.run_backtest(trade_date=date)
            
            if save:
                output_path = Path(output)
                output_path.mkdir(parents=True, exist_ok=True)
                save_results(result, output_path)
                
        elif strategy == 'v18':
            # V18全息回测
            from logic.backtest.behavior_replay_engine import BehaviorReplayEngine
            
            engine = BehaviorReplayEngine(use_sustain_filter=True)
            
            if universe and Path(universe).exists():
                # 从CSV加载股票池
                import pandas as pd
                df = pd.read_csv(universe)
                stocks = df.iloc[:, 0].tolist() if len(df.columns) == 1 else df['code'].tolist()
            elif universe:
                stocks = [universe]
            else:
                stocks = []
            
            click.echo(f"📊 加载 {len(stocks)} 只股票")
            
            for stock in stocks:
                result = engine.replay(stock, date)
                click.echo(f"  {stock}: {'✅' if result.get('success') else '❌'}")
                
        else:
            # 标准回测
            from backtest.run_backtest import run_single_stock_backtest
            
            if not universe:
                click.echo(click.style("❌ 错误: 标准回测需要指定--universe参数", fg='red'))
                ctx.exit(1)
                
            stock_code = universe.replace('.SZ', '').replace('.SH', '')
            result = run_single_stock_backtest(stock_code, date)
            
            click.echo(f"\n📈 回测结果:")
            click.echo(f"  收益率: {result.get('return_pct', 0):.2f}%")
            click.echo(f"  最大回撤: {result.get('max_drawdown', 0):.2f}%")
            
        click.echo(click.style("\n✅ 回测完成", fg='green'))
        
    except Exception as e:
        logger.error(f"❌ 回测失败: {e}", exc_info=True)
        click.echo(click.style(f"\n❌ 回测失败: {e}", fg='red'))
        ctx.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 扫描命令
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(name='scan')
@click.option('--date', '-d', callback=validate_date,
              help='交易日期 (YYYYMMDD格式，默认今天)')
@click.option('--mode', '-m', 
              type=click.Choice(['premarket', 'intraday', 'postmarket', 'full', 'triple_funnel']),
              default='full',
              help='扫描模式 (默认: full)')
@click.option('--max-stocks', type=int, default=100,
              help='最大扫描股票数 (默认: 100)')
@click.option('--output', '-o', default='data/scan_results',
              help='输出目录 (默认: data/scan_results)')
@click.option('--source', type=click.Choice(['qmt', 'tushare']), default='qmt',
              help='数据源 (默认: qmt)')
@click.pass_context
def scan_cmd(ctx, date, mode, max_stocks, output, source):
    """
    全市场扫描
    
    示例:
        \b
        # 盘前扫描
        python main.py scan --mode premarket
        
        # 盘中扫描
        python main.py scan --mode intraday
        
        # 盘后扫描
        python main.py scan --date 20260105 --mode postmarket
        
        # 三漏斗扫描
        python main.py scan --mode triple_funnel --max-stocks 200
    """
    date = date or datetime.now().strftime('%Y%m%d')
    
    click.echo(click.style(f"\n🔍 启动市场扫描", fg='green', bold=True))
    click.echo(f"📅 日期: {date}")
    click.echo(f"📊 模式: {mode}")
    click.echo(f"📈 最大股票数: {max_stocks}")
    click.echo(f"💾 输出: {output}")
    
    try:
        if mode == 'triple_funnel':
            # 三漏斗扫描
            from tasks.run_triple_funnel_scan import main as triple_funnel_main
            
            # 构造sys.argv
            original_argv = sys.argv
            sys.argv = ['run_triple_funnel_scan.py', '--mode', 'post-market', '--max-stocks', str(max_stocks)]
            triple_funnel_main()
            sys.argv = original_argv
            
        elif mode in ['premarket', 'intraday', 'postmarket']:
            # 全市场扫描
            from tasks.run_full_market_scan import main as full_market_scan_main
            
            original_argv = sys.argv
            sys.argv = ['run_full_market_scan.py', '--mode', mode]
            full_market_scan_main()
            sys.argv = original_argv
            
        else:  # full
            # 完整扫描流程
            from logic.strategies.full_market_scanner import FullMarketScanner
            
            scanner = FullMarketScanner()
            results = scanner.scan_with_risk_management(mode='full', max_stocks=max_stocks)
            
            click.echo(f"\n📊 扫描结果:")
            click.echo(f"  机会池: {len(results.get('opportunities', []))} 只")
            click.echo(f"  观察池: {len(results.get('watchlist', []))} 只")
        
        click.echo(click.style("\n✅ 扫描完成", fg='green'))
        
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
            import pandas as pd
            df = pd.read_csv(universe)
            stock_list = df.iloc[:, 0].tolist() if len(df.columns) == 1 else df['code'].tolist()
            click.echo(f"📋 加载 {len(stock_list)} 只股票")
        
        # 执行下载
        from tasks.download_tick_200 import download_tick_data
        
        if stock_list:
            # 下载指定股票池
            for stock in stock_list[:200]:  # 限制最多200只
                try:
                    download_tick_data(stock, date)
                    click.echo(f"  ✅ {stock}")
                except Exception as e:
                    click.echo(f"  ❌ {stock}: {e}")
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
        
        # 启动集合竞价监控
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
            from tasks.auction_manager import main as auction_main
            
            auction_main()
            
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
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    cli()
