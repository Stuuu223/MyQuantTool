"""
MyQuantTool 应用启动脚本 (Rich CLI 版本)
"""

import os
import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """检查依赖是否安装"""
    print("🔍 检查依赖...")

    required_packages = [
        'pandas',
        'rich',
        'akshare',
        'sqlalchemy'
    ]

    optional_packages = [
        'tensorflow',
        'xgboost',
        'requests'
    ]

    missing_required = []
    missing_optional = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_required.append(package)

    for package in optional_packages:
        try:
            __import__(package)
        except ImportError:
            missing_optional.append(package)

    if missing_required:
        print(f"❌ 缺少必需依赖: {', '.join(missing_required)}")
        print("请运行: pip install -r requirements.txt")
        return False

    if missing_optional:
        print(f"⚠️  缺少可选依赖: {', '.join(missing_optional)}")
        print("部分功能可能不可用")

    print("✅ 依赖检查完成")
    return True


def start_event_driven_monitor():
    """启动事件驱动监控"""
    print("\n🚀 启动事件驱动监控...")
    try:
        subprocess.run([sys.executable, "tasks/run_event_driven_monitor.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


def start_cli_monitor():
    """启动Rich CLI监控终端"""
    print("\n📺 启动Rich CLI监控终端...")
    try:
        subprocess.run([sys.executable, "tools/cli_monitor.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


def start_full_market_scan():
    """启动全市场扫描"""
    print("\n🔍 启动全市场扫描...")
    try:
        subprocess.run([sys.executable, "tasks/run_full_market_scan.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                    🚀 MyQuantTool V11.1.0                    ║
    ║              小资金量化 · Rich CLI · 零延迟                 ║
    ╠════════════════════════════════════════════════════════════════╣
    ║  三把斧体系：防守斧 · 资格斧 · 时机斧                       ║
    ║  核心策略：半路战法 · 龙头战法 · 资金流推断                 ║
    ╚════════════════════════════════════════════════════════════════╝
    """)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    print("\n请选择启动模式：")
    print("  1. 事件驱动监控 (推荐)")
    print("  2. Rich CLI监控终端")
    print("  3. 全市场扫描")
    print("  0. 退出")

    choice = input("\n请输入选项 (0-3): ").strip()

    if choice == '1':
        start_event_driven_monitor()
    elif choice == '2':
        start_cli_monitor()
    elif choice == '3':
        start_full_market_scan()
    elif choice == '0':
        print("👋 退出")
        sys.exit(0)
    else:
        print("❌ 无效选项")
        sys.exit(1)


if __name__ == "__main__":
    main()