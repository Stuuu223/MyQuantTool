#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
防守斧拦截逻辑验证脚本

测试所有拦截点：
1. 风控层（risk_control.py）
2. 监控层（run_event_driven_monitor.py）
3. 订单执行层（broker_api.py）
4. 模拟交易系统（paper_trading_system.py）
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger
logger = get_logger(__name__)


def test_risk_control_layer():
    """测试风控层拦截"""
    print("\n" + "=" * 80)
    print("测试1：风控层拦截 (logic/risk_control.py)")
    print("=" * 80)

    from logic.risk_control import RiskControlManager, FORBIDDEN_SCENARIOS

    print(f"禁止场景列表: {FORBIDDEN_SCENARIOS}")

    risk_mgr = RiskControlManager()

    # 测试用例1：TAIL_RALLY场景
    print("\n测试用例1: TAIL_RALLY场景")
    can_open, reason = risk_mgr.can_open_position_by_scenario(
        stock_code="000001.SZ",
        scenario_type="TAIL_RALLY",
        stock_name="平安银行"
    )
    print(f"结果: can_open={can_open}, reason={reason}")
    assert not can_open, "❌ 风控层应该拦截TAIL_RALLY场景"
    print("✅ 风控层成功拦截TAIL_RALLY场景")

    # 测试用例2：TRAP_PUMP_DUMP场景
    print("\n测试用例2: TRAP_PUMP_DUMP场景")
    can_open, reason = risk_mgr.can_open_position_by_scenario(
        stock_code="600519.SH",
        scenario_type="TRAP_PUMP_DUMP",
        stock_name="贵州茅台"
    )
    print(f"结果: can_open={can_open}, reason={reason}")
    assert not can_open, "❌ 风控层应该拦截TRAP_PUMP_DUMP场景"
    print("✅ 风控层成功拦截TRAP_PUMP_DUMP场景")

    # 测试用例3：正常场景
    print("\n测试用例3: 正常场景（MAINLINE_RALLY）")
    can_open, reason = risk_mgr.can_open_position_by_scenario(
        stock_code="000002.SZ",
        scenario_type="MAINLINE_RALLY",
        stock_name="万科A"
    )
    print(f"结果: can_open={can_open}, reason={reason}")
    assert can_open, "❌ 风控层应该允许MAINLINE_RALLY场景"
    print("✅ 风控层正确允许MAINLINE_RALLY场景")

    # 测试用例4：通过布尔值检查
    print("\n测试用例4: 通过布尔值检查（is_tail_rally=True）")
    can_open, reason = risk_mgr.can_open_position_by_scenario(
        stock_code="603607.SH",
        is_tail_rally=True,
        stock_name="京东方A"
    )
    print(f"结果: can_open={can_open}, reason={reason}")
    assert not can_open, "❌ 风控层应该拦截is_tail_rally=True"
    print("✅ 风控层成功拦截is_tail_rally=True")

    print("\n✅ 风控层拦截逻辑测试通过")
    return True


def test_monitoring_layer():
    """测试监控层拦截"""
    print("\n" + "=" * 80)
    print("测试2：监控层拦截 (tasks/run_event_driven_monitor.py)")
    print("=" * 80)

    # 模拟监控器的检查方法
    from tasks.run_event_driven_monitor import EventDrivenMonitor

    # 创建一个模拟的监控器实例
    monitor = EventDrivenMonitor(scan_interval=300, mode="event_driven")

    # 模拟机会池数据
    opportunities = [
        {
            'code': '000001.SZ',
            'name': '平安银行',
            'risk_score': 0.1,
            'capital_type': 'INSTITUTIONAL',
            'scenario_type': 'TAIL_RALLY',
            'is_tail_rally': True,
            'is_potential_trap': False,
            'scenario_reasons': ['补涨尾声模式', '长期流出后突然流入'],
            'trap_signals': []
        },
        {
            'code': '600519.SH',
            'name': '贵州茅台',
            'risk_score': 0.2,
            'capital_type': 'INSTITUTIONAL',
            'scenario_type': 'MAINLINE_RALLY',
            'is_tail_rally': False,
            'is_potential_trap': False,
            'scenario_reasons': ['多日资金流健康', '风险评分较低'],
            'trap_signals': []
        }
    ]

    # 测试用例：过滤禁止场景
    print("\n测试用例: 过滤机会池中的禁止场景")
    safe_count = 0
    blocked_count = 0

    for item in opportunities:
        is_forbidden, reason = monitor._check_defensive_scenario(item)
        if is_forbidden:
            blocked_count += 1
            print(f"🛡️ 拦截: {item['code']} ({item['name']}) - {reason}")
        else:
            safe_count += 1
            print(f"✅ 通过: {item['code']} ({item['name']})")

    print(f"\n统计: 安全={safe_count}, 拦截={blocked_count}")
    assert blocked_count == 1, "❌ 应该拦截1只禁止场景股票"
    assert safe_count == 1, "❌ 应该通过1只安全股票"
    print("✅ 监控层拦截逻辑测试通过")

    return True


def test_broker_api_layer():
    """测试订单执行层拦截"""
    print("\n" + "=" * 80)
    print("测试3：订单执行层拦截 (logic/broker_api.py)")
    print("=" * 80)

    from logic.broker_api import MockBrokerAPI, Order

    # 创建模拟券商API
    broker = MockBrokerAPI({'initial_balance': 100000})

    # 测试用例1：TAIL_RALLY场景应该被拦截
    print("\n测试用例1: TAIL_RALLY场景应该被拦截")
    order = Order(
        order_id="TEST001",
        symbol="000001.SZ",
        side="buy",
        quantity=100,
        price=10.0,
        order_type="market",
        status="pending",
        timestamp=None,
        scenario_type="TAIL_RALLY",
        stock_name="平安银行"
    )

    try:
        order_id = broker.place_order(order)
        print(f"❌ 错误：应该被拦截，但返回了订单ID: {order_id}")
        return False
    except RuntimeError as e:
        print(f"✅ 成功拦截: {e}")
        assert "防守斧拦截" in str(e), "❌ 错误信息应该包含'防守斧拦截'"
        print("✅ 订单执行层成功拦截TAIL_RALLY场景")

    # 测试用例2：正常场景应该通过
    print("\n测试用例2: 正常场景应该通过")
    order = Order(
        order_id="TEST002",
        symbol="000002.SZ",
        side="buy",
        quantity=100,
        price=10.0,
        order_type="market",
        status="pending",
        timestamp=None,
        scenario_type="MAINLINE_RALLY",
        stock_name="万科A"
    )

    try:
        order_id = broker.place_order(order)
        print(f"✅ 成功下单: {order_id}")
        print("✅ 订单执行层正确允许MAINLINE_RALLY场景")
    except RuntimeError as e:
        print(f"❌ 错误：不应该拦截，但被拦截了: {e}")
        return False

    print("\n✅ 订单执行层拦截逻辑测试通过")
    return True


def test_paper_trading_system_layer():
    """测试模拟交易系统拦截"""
    print("\n" + "=" * 80)
    print("测试4：模拟交易系统拦截 (logic/paper_trading_system.py)")
    print("=" * 80)

    from logic.paper_trading_system import PaperTradingSystem, OrderType, OrderDirection

    # 创建模拟交易系统
    trading_system = PaperTradingSystem(initial_capital=100000)

    # 测试用例1：TRAP_PUMP_DUMP场景应该被拦截
    print("\n测试用例1: TRAP_PUMP_DUMP场景应该被拦截")
    try:
        order_id = trading_system.submit_order(
            symbol="600519.SH",
            order_type=OrderType.MARKET,
            direction=OrderDirection.BUY,
            quantity=10,
            price=100.0,
            scenario_type="TRAP_PUMP_DUMP",
            stock_name="贵州茅台"
        )
        print(f"❌ 错误：应该被拦截，但返回了订单ID: {order_id}")
        return False
    except RuntimeError as e:
        print(f"✅ 成功拦截: {e}")
        assert "防守斧拦截" in str(e), "❌ 错误信息应该包含'防守斧拦截'"
        print("✅ 模拟交易系统成功拦截TRAP_PUMP_DUMP场景")

    # 测试用例2：正常场景应该通过
    print("\n测试用例2: 正常场景应该通过")
    try:
        order_id = trading_system.submit_order(
            symbol="000002.SZ",
            order_type=OrderType.MARKET,
            direction=OrderDirection.BUY,
            quantity=10,
            price=10.0,
            scenario_type="MAINLINE_RALLY",
            stock_name="万科A"
        )
        print(f"✅ 成功下单: {order_id}")
        print("✅ 模拟交易系统正确允许MAINLINE_RALLY场景")
    except RuntimeError as e:
        print(f"❌ 错误：不应该拦截，但被拦截了: {e}")
        return False

    print("\n✅ 模拟交易系统拦截逻辑测试通过")
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("🛡️ 防守斧拦截逻辑验证脚本")
    print("=" * 80)
    print("测试目标：验证所有拦截点是否正确禁止 TAIL_RALLY/TRAP 场景")
    print("=" * 80)

    all_passed = True

    # 测试1：风控层
    try:
        if not test_risk_control_layer():
            all_passed = False
    except Exception as e:
        print(f"❌ 风控层测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # 测试2：监控层
    try:
        if not test_monitoring_layer():
            all_passed = False
    except Exception as e:
        print(f"❌ 监控层测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # 测试3：订单执行层
    try:
        if not test_broker_api_layer():
            all_passed = False
    except Exception as e:
        print(f"❌ 订单执行层测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # 测试4：模拟交易系统
    try:
        if not test_paper_trading_system_layer():
            all_passed = False
    except Exception as e:
        print(f"❌ 模拟交易系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # 最终结果
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过！防守斧拦截逻辑工作正常")
        print("=" * 80)
        print("\n拦截点总结：")
        print("1. ✅ 风控层 (logic/risk_control.py) - 执行层兜底检查")
        print("2. ✅ 监控层 (tasks/run_event_driven_monitor.py) - 监控层过滤")
        print("3. ✅ 订单执行层 (logic/broker_api.py) - 订单提交拦截")
        print("4. ✅ 模拟交易系统 (logic/paper_trading_system.py) - 模拟交易拦截")
        print("\n禁止场景：")
        print("   - TAIL_RALLY (补涨尾声)")
        print("   - TRAP_PUMP_DUMP (拉高出货)")
        print("   - FORBIDDEN_10CM_TAIL_RALLY (10cm补涨尾声)")
        print("   - FORBIDDEN_10CM_TRAP (10cm拉高出货)")
        print("\n双重保险机制：")
        print("   - 监控层过滤：在显示机会池时拦截")
        print("   - 执行层兜底：在下单时再次检查")
        print("=" * 80)
        return 0
    else:
        print("❌ 部分测试失败，请检查日志")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
