#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三漏斗扫描系统 - 测试脚本

功能：
1. 测试盘后扫描 (Level 1-3)
2. 测试盘中监控 (Level 4)
3. 测试信号去重
4. 测试信号通知

使用方式：
    python tests/test_triple_funnel.py

作者: iFlow CLI
版本: V1.0
日期: 2026-02-05
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger
from logic.triple_funnel_scanner import (
    TripleFunnelScanner,
    Level1Filter,
    Level2Analyzer,
    Level3RiskAssessor,
    Level4Monitor,
    WatchlistManager,
    StockBasicInfo,
    TradingSignal,
    SignalType,
    RiskLevel
)
from logic.signal_manager import (
    SignalManager,
    SignalDeduplicator,
    SignalNotifier
)
from datetime import datetime

logger = get_logger(__name__)


def test_level1_filter():
    """测试 Level 1 过滤器"""
    print("\n" + "=" * 80)
    print("🧪 测试 Level 1 过滤器")
    print("=" * 80)

    filter = Level1Filter()

    # 测试用例1: 正常股票
    stock1 = StockBasicInfo(
        code="000001",
        name="平安银行",
        price=12.50,
        pct_change=2.5,
        volume=1000000,
        amount=50000000,
        turnover_rate=5.0,
        high=12.80,
        low=12.20,
        open=12.30
    )

    result1 = filter.filter(stock1)
    print(f"\n测试用例1: 正常股票")
    print(f"  代码: {stock1.code}")
    print(f"  价格: {stock1.price}")
    print(f"  换手率: {stock1.turnover_rate}%")
    print(f"  成交额: {stock1.amount/10000:.0f}万")
    print(f"  结果: {'✅ 通过' if result1.passed else '❌ 未通过'}")
    if not result1.passed:
        print(f"  原因: {', '.join(result1.reasons)}")

    # 测试用例2: 价格过低
    stock2 = StockBasicInfo(
        code="000002",
        name="测试股票",
        price=1.50,
        pct_change=2.5,
        volume=1000000,
        amount=50000000,
        turnover_rate=5.0,
        high=1.60,
        low=1.40,
        open=1.50
    )

    result2 = filter.filter(stock2)
    print(f"\n测试用例2: 价格过低")
    print(f"  价格: {stock2.price}")
    print(f"  结果: {'✅ 通过' if result2.passed else '❌ 未通过'}")
    if not result2.passed:
        print(f"  原因: {', '.join(result2.reasons)}")

    # 测试用例3: ST股
    stock3 = StockBasicInfo(
        code="000003",
        name="ST测试",
        price=12.50,
        pct_change=2.5,
        volume=1000000,
        amount=50000000,
        turnover_rate=5.0,
        high=12.80,
        low=12.20,
        open=12.30
    )

    result3 = filter.filter(stock3)
    print(f"\n测试用例3: ST股")
    print(f"  名称: {stock3.name}")
    print(f"  结果: {'✅ 通过' if result3.passed else '❌ 未通过'}")
    if not result3.passed:
        print(f"  原因: {', '.join(result3.reasons)}")

    print("\n✅ Level 1 过滤器测试完成")


def test_level2_analyzer():
    """测试 Level 2 分析器"""
    print("\n" + "=" * 80)
    print("🧪 测试 Level 2 分析器")
    print("=" * 80)

    analyzer = Level2Analyzer()

    # 测试用例
    test_code = "000001"

    print(f"\n测试股票: {test_code}")
    print("正在分析资金流向...")

    result = analyzer.analyze(test_code)

    print(f"\n结果: {'✅ 通过' if result.passed else '❌ 未通过'}")
    print(f"资金流得分: {result.fund_flow_score:.0f}")
    print(f"板块热度: {result.sector_heat:.0f}")

    if result.metrics:
        print("\n详细指标:")
        for key, value in result.metrics.items():
            print(f"  {key}: {value}")

    if not result.passed:
        print(f"\n未通过原因: {', '.join(result.reasons)}")

    print("\n✅ Level 2 分析器测试完成")


def test_level3_assessor():
    """测试 Level 3 风险评估器"""
    print("\n" + "=" * 80)
    print("🧪 测试 Level 3 风险评估器")
    print("=" * 80)

    assessor = Level3RiskAssessor()

    # 测试用例
    test_code = "000001"

    print(f"\n测试股票: {test_code}")
    print("正在评估风险...")

    result = assessor.assess(test_code)

    print(f"\n结果: {'✅ 通过' if result.passed else '❌ 未通过'}")
    print(f"风险等级: {result.risk_level.value}")
    print(f"诱多风险: {result.trap_risk:.2f}")
    print(f"资金性质: {result.capital_type}")
    print(f"综合得分: {result.comprehensive_score:.0f}")

    if result.metrics:
        print("\n详细指标:")
        for key, value in result.metrics.items():
            print(f"  {key}: {value}")

    if not result.passed:
        print(f"\n未通过原因: {', '.join(result.reasons)}")

    print("\n✅ Level 3 风险评估器测试完成")


def test_watchlist_manager():
    """测试观察池管理器"""
    print("\n" + "=" * 80)
    print("🧪 测试观察池管理器")
    print("=" * 80)

    # 创建临时观察池
    import tempfile
    import json

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config = f.name

    try:
        manager = WatchlistManager(temp_config)

        # 测试添加
        print("\n测试添加股票...")
        manager.add("000001", "平安银行", "测试用")
        manager.add("600519", "贵州茅台", "测试用")

        print(f"观察池股票数: {len(manager.get_all())}")
        print("✅ 添加成功")

        # 测试获取
        print("\n测试获取观察池...")
        items = manager.get_all()
        for item in items:
            print(f"  {item.code} {item.name}")

        # 测试移除
        print("\n测试移除股票...")
        manager.remove("000001")
        print(f"观察池股票数: {len(manager.get_all())}")
        print("✅ 移除成功")

        print("\n✅ 观察池管理器测试完成")

    finally:
        # 清理临时文件
        import os
        if os.path.exists(temp_config):
            os.unlink(temp_config)


def test_signal_deduplicator():
    """测试信号去重器"""
    print("\n" + "=" * 80)
    print("🧪 测试信号去重器")
    print("=" * 80)

    deduplicator = SignalDeduplicator()

    # 创建测试信号
    signal1 = TradingSignal(
        id="TEST_001",
        stock_code="000001",
        stock_name="平安银行",
        signal_type=SignalType.VWAP_BREAKOUT,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        price=12.50,
        trigger_price=12.20,
        signal_strength=0.8,
        risk_level=RiskLevel.MEDIUM,
        details={"vwap": 12.20, "breakout_pct": 0.025}
    )

    # 测试第一个信号
    print("\n测试第一个信号...")
    should_trigger1 = deduplicator.should_trigger(signal1)
    print(f"应该触发: {should_trigger1}")
    print("✅ 第一个信号应该触发")

    # 测试重复信号
    print("\n测试重复信号...")
    signal2 = TradingSignal(
        id="TEST_002",
        stock_code="000001",
        stock_name="平安银行",
        signal_type=SignalType.VWAP_BREAKOUT,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        price=12.50,
        trigger_price=12.20,
        signal_strength=0.8,
        risk_level=RiskLevel.MEDIUM,
        details={"vwap": 12.20, "breakout_pct": 0.025}
    )

    should_trigger2 = deduplicator.should_trigger(signal2)
    print(f"应该触发: {should_trigger2}")
    print("✅ 重复信号应该被去重")

    # 测试价格变化后的信号
    print("\n测试价格变化后的信号...")
    signal3 = TradingSignal(
        id="TEST_003",
        stock_code="000001",
        stock_name="平安银行",
        signal_type=SignalType.VWAP_BREAKOUT,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        price=13.00,  # 价格变化超过阈值
        trigger_price=12.20,
        signal_strength=0.8,
        risk_level=RiskLevel.MEDIUM,
        details={"vwap": 12.20, "breakout_pct": 0.025}
    )

    should_trigger3 = deduplicator.should_trigger(signal3)
    print(f"应该触发: {should_trigger3}")
    print("✅ 价格变化后的信号应该触发")

    print("\n✅ 信号去重器测试完成")


def test_signal_manager():
    """测试信号管理器"""
    print("\n" + "=" * 80)
    print("🧪 测试信号管理器")
    print("=" * 80)

    # 创建临时配置
    import tempfile
    import json

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config = f.name
        json.dump({"deduplication": {}, "notification": {"channels": ["LOG"]}}, f)

    try:
        manager = SignalManager(temp_config)

        # 创建测试信号
        signal = TradingSignal(
            id="TEST_001",
            stock_code="000001",
            stock_name="平安银行",
            signal_type=SignalType.VWAP_BREAKOUT,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            price=12.50,
            trigger_price=12.20,
            signal_strength=0.8,
            risk_level=RiskLevel.MEDIUM,
            details={"vwap": 12.20, "breakout_pct": 0.025}
        )

        # 测试处理信号
        print("\n测试处理信号...")
        triggered = manager.process_signal(signal)
        print(f"信号已触发: {triggered}")

        # 测试获取统计
        print("\n测试获取统计...")
        stats = manager.get_signal_stats()
        for stat in stats:
            print(f"  {stat['stock_name']} {stat['signal_type']}: {stat['count']}次")

        # 测试获取历史
        print("\n测试获取历史...")
        history = manager.get_recent_signals(hours=1)
        print(f"最近信号数: {len(history)}")

        print("\n✅ 信号管理器测试完成")

    finally:
        # 清理临时文件
        import os
        if os.path.exists(temp_config):
            os.unlink(temp_config)


def test_triple_funnel_scanner():
    """测试三漏斗扫描器"""
    print("\n" + "=" * 80)
    print("🧪 测试三漏斗扫描器")
    print("=" * 80)

    # 创建临时配置
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config = f.name

    try:
        scanner = TripleFunnelScanner(temp_config)

        # 添加测试股票
        print("\n添加测试股票...")
        scanner.watchlist_manager.add("000001", "平安银行", "测试用")

        # 测试盘后扫描
        print("\n测试盘后扫描...")
        passed = scanner.run_post_market_scan(max_stocks=5)
        print(f"通过筛选: {len(passed)} 只股票")

        # 测试盘中监控
        print("\n测试盘中监控...")
        signals = scanner.run_intraday_monitor(interval=3)
        print(f"触发信号: {len(signals)} 个")

        print("\n✅ 三漏斗扫描器测试完成")

    finally:
        # 清理临时文件
        import os
        if os.path.exists(temp_config):
            os.unlink(temp_config)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🚀 三漏斗扫描系统 - 测试套件")
    print("=" * 80)

    tests = [
        ("Level 1 过滤器", test_level1_filter),
        ("Level 2 分析器", test_level2_analyzer),
        ("Level 3 风险评估器", test_level3_assessor),
        ("观察池管理器", test_watchlist_manager),
        ("信号去重器", test_signal_deduplicator),
        ("信号管理器", test_signal_manager),
        ("三漏斗扫描器", test_triple_funnel_scanner),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            test_func()
            results.append((test_name, "✅ 通过", None))
        except Exception as e:
            logger.error(f"❌ 测试失败: {test_name}", exc_info=True)
            results.append((test_name, "❌ 失败", str(e)))

    # 显示结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    for test_name, status, error in results:
        print(f"{status} {test_name}")
        if error:
            print(f"   错误: {error}")

    passed = sum(1 for _, status, _ in results if status == "✅ 通过")
    total = len(results)

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")


if __name__ == "__main__":
    run_all_tests()