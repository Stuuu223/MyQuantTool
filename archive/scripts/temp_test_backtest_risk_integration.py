"""
测试回测框架的风控集成
"""
import sys
sys.path.append('.')

from logic.backtest_framework import BacktestEngine, BacktestPosition
from datetime import datetime


def test_date_conversion():
    """测试日期格式转换"""
    print("=" * 60)
    print("测试日期格式转换")
    print("=" * 60)

    engine = BacktestEngine()

    # 测试用例1：YYYYMMDD -> YYYY-MM-DD
    date1 = "20260208"
    result1 = engine._convert_date_format(date1)
    print(f"  {date1} -> {result1}")
    assert result1 == "2026-02-08", "日期转换测试失败"
    print("  ✓ 通过")

    # 测试用例2：已经是YYYY-MM-DD格式
    date2 = "2026-02-08"
    result2 = engine._convert_date_format(date2)
    print(f"  {date2} -> {result2}")
    assert result2 == "2026-02-08", "日期格式保持测试失败"
    print("  ✓ 通过")

    print("\n✅ 日期格式转换测试通过！")


def test_risk_control_initialization():
    """测试风控管理器初始化"""
    print("\n" + "=" * 60)
    print("测试风控管理器初始化")
    print("=" * 60)

    engine = BacktestEngine()

    # 检查初始状态
    assert engine.risk_mgr is None, "风控管理器初始应该为None"
    print("  ✓ 风控管理器初始状态正确（None）")

    # 创建一个虚拟持仓
    position = BacktestPosition(code="603607", entry_price=10.0, entry_date="20260205")

    # 创建虚拟股票数据
    stock_data = {
        'code': '603607',
        'trade_date': '20260208',
        'price_data': {
            'close': 9.4  # -6%触发价格止损
        },
        'flow_data': {},
        'decision_tag': None,
        'risk_score': 0.5,
        'trap_signals': []
    }

    # 调用风控检查（会触发懒加载）
    should_exit, reason = engine._check_risk_control(position, stock_data, "20260208")

    # 检查风控管理器是否被初始化
    assert engine.risk_mgr is not None, "风控管理器应该被初始化"
    print("  ✓ 风控管理器懒加载成功")

    # 检查风控检查结果
    print(f"  风控检查结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == True and reason == "PRICE_STOP", "价格止损测试失败"
    print("  ✓ 价格止损触发正确")

    print("\n✅ 风控管理器初始化测试通过！")


def test_risk_control_time_stop():
    """测试时间止损"""
    print("\n" + "=" * 60)
    print("测试时间止损")
    print("=" * 60)

    engine = BacktestEngine()

    # 创建一个虚拟持仓（持仓4天，浮盈3%）
    position = BacktestPosition(code="603607", entry_price=10.0, entry_date="20260204")

    # 创建虚拟股票数据
    stock_data = {
        'code': '603607',
        'trade_date': '20260208',
        'price_data': {
            'close': 10.3  # 浮盈3%，持仓4天，应该触发时间止损
        },
        'flow_data': {},
        'decision_tag': None,
        'risk_score': 0.5,
        'trap_signals': []
    }

    # 调用风控检查
    should_exit, reason = engine._check_risk_control(position, stock_data, "20260208")

    print(f"  风控检查结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == True and reason == "TIME_STOP", "时间止损测试失败"
    print("  ✓ 时间止损触发正确")

    print("\n✅ 时间止损测试通过！")


def test_risk_control_no_exit():
    """测试不触发风控"""
    print("\n" + "=" * 60)
    print("测试不触发风控")
    print("=" * 60)

    engine = BacktestEngine()

    # 创建一个虚拟持仓（持仓2天，浮盈3%）
    position = BacktestPosition(code="603607", entry_price=10.0, entry_date="20260206")

    # 创建虚拟股票数据
    stock_data = {
        'code': '603607',
        'trade_date': '20260208',
        'price_data': {
            'close': 10.3  # 浮盈3%，持仓2天，不触发风控
        },
        'flow_data': {},
        'decision_tag': None,
        'risk_score': 0.5,
        'trap_signals': []
    }

    # 调用风控检查
    should_exit, reason = engine._check_risk_control(position, stock_data, "20260208")

    print(f"  风控检查结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == False and reason == "NONE", "不触发风控测试失败"
    print("  ✓ 不触发风控判断正确")

    print("\n✅ 不触发风控测试通过！")


if __name__ == "__main__":
    print("\n开始回测框架风控集成测试...\n")

    test_date_conversion()
    test_risk_control_initialization()
    test_risk_control_time_stop()
    test_risk_control_no_exit()

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！风控集成成功！")
    print("=" * 60)
    print("\n核心功能验证：")
    print("  ✓ 日期格式转换（YYYYMMDD -> YYYY-MM-DD）")
    print("  ✓ 风控管理器懒加载")
    print("  ✓ 价格止损（-5%）")
    print("  ✓ 时间止损（3-5天且收益<+5%）")
    print("=" * 60 + "\n")