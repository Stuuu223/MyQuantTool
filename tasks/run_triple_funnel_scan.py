#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三漏斗扫描系统 - 运行脚本

功能：
1. 盘后扫描 (Level 1-3) - 每日收盘后运行
2. 盘中监控 (Level 4) - 交易时间实时运行
3. 观察池管理 - 添加/移除股票
4. 信号查看 - 查看最近的信号
5. 自动模式 - 根据当前时间自动选择运行模式

使用方式：
    # 自动模式 (推荐) - 根据当前时间自动判断
    python tasks/run_triple_funnel_scan.py

    # 指定盘后扫描
    python tasks/run_triple_funnel_scan.py --mode post-market

    # 指定盘中监控
    python tasks/run_triple_funnel_scan.py --mode intraday

    # 查看信号
    python tasks/run_triple_funnel_scan.py --mode signals

    # 添加股票
    python tasks/run_triple_funnel_scan.py --mode add --code 000001 --name 平安银行

作者: iFlow CLI
版本: V1.1
日期: 2026-02-06
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger
from logic.triple_funnel_scanner import TripleFunnelScanner
from logic.signal_manager import get_signal_manager

logger = get_logger(__name__)


def run_post_market_scan(scanner: TripleFunnelScanner, max_stocks: int = 100):
    """
    运行盘后扫描

    Args:
        scanner: 扫描器实例
        max_stocks: 最大扫描股票数
    """
    logger.info("=" * 80)
    logger.info("🚀 开始盘后扫描 (Level 1-3)")
    logger.info("=" * 80)

    passed = scanner.run_post_market_scan(max_stocks=max_stocks)

    logger.info("=" * 80)
    logger.info(f"✅ 盘后扫描完成: {len(passed)} 只股票通过筛选")
    logger.info("=" * 80)

    # 显示通过筛选的股票
    if passed:
        logger.info("\n📋 通过筛选的股票:")
        for code in passed:
            item = scanner.watchlist_manager.watchlist.get(code)
            if item:
                logger.info(f"  {code} {item.name}")


def run_intraday_monitor(scanner: TripleFunnelScanner, interval: int = 3):
    """
    运行盘中监控

    Args:
        scanner: 扫描器实例
        interval: 监控间隔 (秒)
    """
    import time

    logger.info("=" * 80)
    logger.info("🚀 开始盘中监控 (Level 4)")
    logger.info(f"监控间隔: {interval} 秒")
    logger.info("=" * 80)

    signal_manager = get_signal_manager()

    try:
        while True:
            # 检查交易时间
            from logic.intraday_monitor import IntraDayMonitor
            monitor = IntraDayMonitor()
            phase = monitor.get_trading_phase()

            if phase in ['WEEKEND', 'AFTER_HOURS']:
                logger.info(f"⏰ 当前阶段: {phase}, 暂停监控")
                time.sleep(60)
                continue

            # 运行监控
            signals = scanner.run_intraday_monitor(interval=interval)

            # 处理信号
            for signal in signals:
                signal_manager.process_signal(signal)

            # 等待下一次
            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断，停止监控")


def show_signals():
    """显示最近的信号"""
    signal_manager = get_signal_manager()

    logger.info("=" * 80)
    logger.info("📜 最近的信号")
    logger.info("=" * 80)

    signals = signal_manager.get_recent_signals(hours=24)

    if not signals:
        logger.info("暂无信号")
        return

    for signal in signals:
        logger.info(f"\n🚀 {signal.stock_name} ({signal.stock_code})")
        logger.info(f"   信号: {signal.signal_type}")
        logger.info(f"   时间: {signal.timestamp}")
        logger.info(f"   价格: {signal.price:.2f}")
        logger.info(f"   触发价: {signal.trigger_price:.2f}")
        logger.info(f"   强度: {signal.signal_strength:.2f}")
        logger.info(f"   风险: {signal.risk_level}")

    # 显示统计
    logger.info("\n📊 信号统计:")
    stats = signal_manager.get_signal_stats()
    for stat in stats:
        logger.info(f"  {stat['stock_name']} {stat['signal_type']}: {stat['count']}次")


def add_stock(scanner: TripleFunnelScanner, code: str, name: str, reason: str = ""):
    """
    添加股票到观察池

    Args:
        scanner: 扫描器实例
        code: 股票代码
        name: 股票名称
        reason: 添加原因
    """
    if not reason:
        reason = "手动添加"

    scanner.watchlist_manager.add(code, name, reason)
    logger.info(f"✅ 已添加股票到观察池: {code} {name}")


def remove_stock(scanner: TripleFunnelScanner, code: str):
    """
    从观察池移除股票

    Args:
        scanner: 扫描器实例
        code: 股票代码
    """
    scanner.watchlist_manager.remove(code)
    logger.info(f"✅ 已从观察池移除股票: {code}")


def show_watchlist(scanner: TripleFunnelScanner):
    """显示观察池"""
    logger.info("=" * 80)
    logger.info("📋 观察池")
    logger.info("=" * 80)

    items = scanner.watchlist_manager.get_all()

    if not items:
        logger.info("观察池为空")
        return

    for item in items:
        logger.info(f"\n📈 {item.code} {item.name}")
        logger.info(f"   原因: {item.reason}")
        logger.info(f"   添加时间: {item.added_at}")

        if item.level1_result:
            status = "✅" if item.level1_result.passed else "❌"
            logger.info(f"   Level1: {status}")

        if item.level2_result:
            status = "✅" if item.level2_result.passed else "❌"
            logger.info(f"   Level2: {status} (得分: {item.level2_result.fund_flow_score:.0f})")

        if item.level3_result:
            status = "✅" if item.level3_result.passed else "❌"
            logger.info(f"   Level3: {status} (得分: {item.level3_result.comprehensive_score:.0f})")


def auto_detect_mode():
    """
    自动检测运行模式

    Returns:
        str: 运行模式 (post-market, intraday, weekend, after-hours)
    """
    from logic.intraday_monitor import IntraDayMonitor

    monitor = IntraDayMonitor()
    phase = monitor.get_trading_phase()

    logger.info(f"🕐 当前交易阶段: {phase}")

    # 根据交易阶段自动判断
    # 交易时间（上午、下午、开盘竞价、收盘竞价）
    if phase in ['OPENING_AUCTION', 'MORNING', 'AFTERNOON', 'CLOSING_AUCTION']:
        logger.info("📈 检测到交易时间，自动运行盘中监控模式")
        return 'intraday'
    
    # 午休时间 - 也运行盘中监控（保持连接）
    elif phase == 'LUNCH_BREAK':
        logger.info("⏰ 检测到午休时间，运行盘中监控模式（保持连接）")
        return 'intraday'
    
    # 收盘后
    elif phase == 'AFTER_HOURS':
        logger.info("🌙 检测到收盘后时间，自动运行盘后扫描模式")
        return 'post-market'
    
    # 周末
    elif phase == 'WEEKEND':
        logger.info("🏖️ 检测到周末，运行盘后扫描模式（查看历史数据）")
        return 'post-market'
    
    # 未知阶段
    else:
        logger.warning(f"⚠️ 未知阶段 {phase}，默认运行盘后扫描模式")
        return 'post-market'


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="三漏斗扫描系统")
    parser.add_argument("--mode", choices=["post-market", "intraday", "signals", "add", "remove", "watchlist", "auto"],
                       default="auto", help="运行模式 (默认: auto 自动检测)")
    parser.add_argument("--code", help="股票代码")
    parser.add_argument("--name", help="股票名称")
    parser.add_argument("--reason", help="添加原因")
    parser.add_argument("--max-stocks", type=int, default=100, help="最大扫描股票数")
    parser.add_argument("--interval", type=int, default=3, help="监控间隔 (秒)")

    args = parser.parse_args()

    # 创建扫描器
    scanner = TripleFunnelScanner()

    # 自动检测模式
    if args.mode == "auto":
        args.mode = auto_detect_mode()

    # 根据模式执行
    if args.mode == "post-market":
        run_post_market_scan(scanner, max_stocks=args.max_stocks)

    elif args.mode == "intraday":
        run_intraday_monitor(scanner, interval=args.interval)

    elif args.mode == "signals":
        show_signals()

    elif args.mode == "add":
        if not args.code or not args.name:
            logger.error("❌ 请提供股票代码和名称")
            return

        add_stock(scanner, args.code, args.name, args.reason or "")

    elif args.mode == "remove":
        if not args.code:
            logger.error("❌ 请提供股票代码")
            return

        remove_stock(scanner, args.code)

    elif args.mode == "watchlist":
        show_watchlist(scanner)


if __name__ == "__main__":
    main()