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

print(f"✅ [System] Python 版本检查通过: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print()

# 🚀 [最高优先级] 强杀代理：必须在 import 其他库之前执行！
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(key, None)
os.environ['NO_PROXY'] = '*'
print("🛡️ [System] 代理已强制清除，启动直连模式...")
print()
# ==========================================================

import argparse
from pathlib import Path
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def print_banner():
    """打印横幅"""
    banner = """
    ╔════════════════════════════════════════════════════════════════╗
    ║                    🚀 MyQuantTool V11.1.0                    ║
    ║              小资金量化 · Rich CLI · 零延迟                 ║
    ╠════════════════════════════════════════════════════════════════╣
    ║  三把斧体系：防守斧 · 资格斧 · 时机斧                       ║
    ║  核心策略：半路战法 · 龙头战法 · 资金流推断                 ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_usage():
    """打印使用说明"""
    usage = """
    使用方法：
        python main.py <命令> [参数]

    可用命令：
        monitor         启动事件驱动监控（推荐）
        cli-monitor     启动Rich CLI监控终端
        scan            执行全市场扫描
        auction         执行集合竞价扫描
        help            显示帮助信息

    示例：
        python main.py monitor               # 启动事件驱动监控
        python main.py cli-monitor           # 启动CLI监控终端
        python main.py scan                  # 执行全市场扫描
        python main.py auction               # 执行集合竞价扫描

    启动脚本：
        scripts/start_quant_system.bat       # 统一启动器（推荐）

    更多命令：
        使用 start_app.py 启动应用层功能
    """
    print(usage)


def run_event_driven_monitor():
    """运行事件驱动监控"""
    try:
        from tasks.run_event_driven_monitor import EventDrivenMonitor
        monitor = EventDrivenMonitor()
        monitor.run()
    except Exception as e:
        logger.error(f"❌ 启动事件驱动监控失败: {e}")
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


def run_cli_monitor():
    """运行Rich CLI监控终端"""
    try:
        from tools.cli_monitor import main as cli_monitor_main
        cli_monitor_main()
    except Exception as e:
        logger.error(f"❌ 启动CLI监控终端失败: {e}")
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


def run_full_market_scan():
    """运行全市场扫描"""
    try:
        from tasks.run_full_market_scan import main as scan_main
        scan_main()
    except Exception as e:
        logger.error(f"❌ 执行全市场扫描失败: {e}")
        print(f"❌ 扫描失败: {e}")
        sys.exit(1)


def run_auction_scan():
    """运行集合竞价扫描"""
    try:
        from tasks.auction_scan import main as auction_main
        auction_main()
    except Exception as e:
        logger.error(f"❌ 执行集合竞价扫描失败: {e}")
        print(f"❌ 扫描失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="MyQuantTool - 小资金量化交易系统",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'command',
        nargs='?',
        choices=['monitor', 'cli-monitor', 'scan', 'auction', 'help'],
        help='要执行的命令'
    )

    args = parser.parse_args()

    # 打印横幅
    print_banner()

    # 如果没有提供命令，显示帮助
    if not args.command:
        print_usage()
        print("\n提示：运行 'python main.py help' 查看详细帮助")
        return

    # 根据命令执行相应操作
    if args.command == 'monitor':
        print("\n🚀 启动事件驱动监控...\n")
        run_event_driven_monitor()
    elif args.command == 'cli-monitor':
        print("\n📺 启动Rich CLI监控终端...\n")
        run_cli_monitor()
    elif args.command == 'scan':
        print("\n🔍 执行全市场扫描...\n")
        run_full_market_scan()
    elif args.command == 'auction':
        print("\n⚡ 执行集合竞价扫描...\n")
        run_auction_scan()
    elif args.command == 'help':
        print_usage()


if __name__ == "__main__":
    main()