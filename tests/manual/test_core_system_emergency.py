#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V16.4.1 紧急测试：核心系统健康检查

CTO要求：验证心脏和大脑是否还活着
Date: 2026-02-16 17:00
Author: MyQuantTool Team
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logic.utils.logger import get_logger

logger = get_logger(__name__)


def test_full_market_scanner_import():
    """测试1：三漏斗扫描器能否导入"""
    print("=" * 80)
    print("🧪 测试1: full_market_scanner.py导入测试")
    print("=" * 80)

    try:
        from logic.strategies.full_market_scanner import FullMarketScanner
        print("✅ FullMarketScanner导入成功")
        return True
    except Exception as e:
        print(f"❌ FullMarketScanner导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_market_scanner_init():
    """测试2：三漏斗扫描器能否初始化"""
    print("\n" + "=" * 80)
    print("🧪 测试2: full_market_scanner.py初始化测试")
    print("=" * 80)

    try:
        from logic.strategies.full_market_scanner import FullMarketScanner

        # 尝试初始化（可能需要配置文件）
        config_file = Path('config/market_scan_config.json')
        if not config_file.exists():
            print("⚠️  警告: 配置文件不存在，使用默认配置")

        scanner = FullMarketScanner()
        print(f"✅ FullMarketScanner初始化成功")
        print(f"📊 扫描器类型: {type(scanner).__name__}")
        print(f"📊 股票池大小: {len(scanner.all_stocks)} 只")
        return True
    except Exception as e:
        print(f"❌ FullMarketScanner初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_driven_monitor_import():
    """测试3：事件驱动监控能否导入"""
    print("\n" + "=" * 80)
    print("🧪 测试3: run_event_driven_monitor.py导入测试")
    print("=" * 80)

    try:
        # 尝试导入事件驱动监控
        import tasks.run_event_driven_monitor as monitor_module
        print("✅ run_event_driven_monitor导入成功")

        # 检查是否有EventDrivenMonitor类
        if hasattr(monitor_module, 'EventDrivenMonitor'):
            print(f"✅ EventDrivenMonitor类存在")
            return True
        else:
            print(f"⚠️  警告: EventDrivenMonitor类不存在")
            return False

    except Exception as e:
        print(f"❌ run_event_driven_monitor导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qmt_connection():
    """测试4：QMT连接测试（核心数据源）"""
    print("\n" + "=" * 80)
    print("🧪 测试4: QMT连接测试（核心数据源）")
    print("=" * 80)

    try:
        from xtquant import xtdata

        # 测试获取单只股票快照
        print("📋 测试获取600519.SH实时快照...")
        snapshot = xtdata.get_full_tick(['600519.SH'])

        if snapshot and '600519.SH' in snapshot:
            tick = snapshot['600519.SH']
            print(f"✅ QMT连接正常")
            print(f"📊 600519.SH最新价: {tick.get('lastPrice', 'N/A')}")
            print(f"📊 600519.SH成交量: {tick.get('totalVolume', 'N/A')}")
            return True
        else:
            print("⚠️  QMT返回空数据(可能是非交易时间或未登录)")
            return False

    except Exception as e:
        print(f"❌ QMT连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_source_priority():
    """测试5：数据源优先级验证（QMT优先，AkShare辅助）"""
    print("\n" + "=" * 80)
    print("🧪 测试5: 数据源优先级验证")
    print("=" * 80)

    try:
        # 检查full_market_scanner.py是否依赖AkShare
        scanner_file = Path('logic/strategies/full_market_scanner.py')

        if not scanner_file.exists():
            print("❌ full_market_scanner.py不存在!")
            return False

        content = scanner_file.read_text(encoding='utf-8')

        # 检查是否有akshare导入
        if 'import akshare' in content or 'from akshare' in content:
            print("⚠️  警告: full_market_scanner.py导入了akshare")
            print("⚠️  违反架构原则: 三漏斗应该用QMT Tick推断")
            return False
        else:
            print("✅ full_market_scanner.py没有导入akshare")
            print("✅ 符合架构原则: QMT优先")
            return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_market_scanner_level2_dependency():
    """测试6：Level 2是否依赖AkShare（CTO关注点）"""
    print("\n" + "=" * 80)
    print("🧪 测试6: Level 2资金流向分析是否依赖AkShare")
    print("=" * 80)

    try:
        from logic.strategies.full_market_scanner import FullMarketScanner

        # 获取Level 2方法
        level2_method = getattr(FullMarketScanner, '_level2_capital_analysis', None)

        if level2_method is None:
            print("⚠️  警告: _level2_capital_analysis方法不存在")
            return False

        # 读取方法源码
        import inspect
        source_code = inspect.getsource(level2_method)

        # 检查是否直接调用akshare
        if 'ak.' in source_code or 'akshare.' in source_code:
            print("⚠️  警告: Level 2直接调用akshare")
            print("⚠️  违反架构原则: Level 2应该通过抽象层调用")
            return False
        else:
            print("✅ Level 2没有直接调用akshare")
            print("✅ 符合架构原则: 通过抽象层调用")

        # 检查是否通过data_provider抽象层
        if 'get_provider' in source_code or 'data_provider' in source_code:
            print("✅ Level 2通过data_provider抽象层调用")
            return True
        else:
            print("⚠️  警告: Level 2可能直接调用底层API")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        print("\n" + "=" * 80)
        print("🚨 V16.4.1 紧急测试：核心系统健康检查")
        print("CTO要求：验证心脏和大脑是否还活着")
        print("=" * 80 + "\n")

        results = {
            '测试1 (FullMarketScanner导入)': test_full_market_scanner_import(),
            '测试2 (FullMarketScanner初始化)': test_full_market_scanner_init(),
            '测试3 (EventDrivenMonitor导入)': test_event_driven_monitor_import(),
            '测试4 (QMT连接)': test_qmt_connection(),
            '测试5 (数据源优先级)': test_data_source_priority(),
            '测试6 (Level 2依赖AkShare)': test_full_market_scanner_level2_dependency(),
        }

        # 汇总结果
        print("\n" + "=" * 80)
        print("📊 测试结果汇总")
        print("=" * 80)
        for name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{name}: {status}")

        print("=" * 80)

        # 核心系统健康度评估
        core_tests = [
            results['测试1 (FullMarketScanner导入)'],
            results['测试2 (FullMarketScanner初始化)'],
            results['测试3 (EventDrivenMonitor导入)'],
            results['测试4 (QMT连接)'],
            results['测试6 (Level 2依赖AkShare)']
        ]

        if all(core_tests):
            print("\n✅ 核心系统健康度: 存活")
            print("✅ 心脏和大脑还活着，可以继续修复")
        else:
            print("\n❌ 核心系统健康度: 停跳")
            print("❌ 心脏或大脑已死，必须紧急救援!")

        # 架构一致性评估
        if results['测试5 (数据源优先级)'] and results['测试6 (Level 2依赖AkShare)']:
            print("\n✅ 架构一致性: 符合QMT优先原则")
        else:
            print("\n⚠️ 架构一致性: 违反QMT优先原则，需要重构")

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)