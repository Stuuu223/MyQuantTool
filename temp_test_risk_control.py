"""
风控管理器测试脚本
"""
from logic.risk_control import RiskControlManager


def test_check_exit():
    """测试单票风控检查"""
    print("=" * 60)
    print("测试 check_exit (单票风控检查)")
    print("=" * 60)
    
    rc = RiskControlManager()
    
    # 测试用例1：价格止损（-6%）
    print("\n用例1：价格止损测试")
    print("  入场价: 10.0, 现价: 9.4, 下跌 -6%")
    should_exit, reason = rc.check_exit(
        symbol="603607",
        entry_price=10.0,
        current_price=9.4,
        entry_date="2026-02-05",
        current_date="2026-02-08"
    )
    print(f"  结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == True and reason == "PRICE_STOP", "价格止损测试失败"
    print("  ✓ 通过")
    
    # 测试用例2：时间止损（持仓4天，浮盈3%）
    print("\n用例2：时间止损测试")
    print("  入场价: 10.0, 现价: 10.3, 持仓4天, 浮盈 3%")
    should_exit, reason = rc.check_exit(
        symbol="603607",
        entry_price=10.0,
        current_price=10.3,
        entry_date="2026-02-04",
        current_date="2026-02-08"
    )
    print(f"  结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == True and reason == "TIME_STOP", "时间止损测试失败"
    print("  ✓ 通过")
    
    # 测试用例3：不触发止损（持仓2天，浮盈3%）
    print("\n用例3：不触发止损（持仓时间不足）")
    print("  入场价: 10.0, 现价: 10.3, 持仓2天, 浮盈 3%")
    should_exit, reason = rc.check_exit(
        symbol="603607",
        entry_price=10.0,
        current_price=10.3,
        entry_date="2026-02-06",
        current_date="2026-02-08"
    )
    print(f"  结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == False and reason == "NONE", "不触发止损测试失败"
    print("  ✓ 通过")
    
    # 测试用例4：不触发止损（持仓4天，浮盈6%）
    print("\n用例4：不触发止损（收益达标）")
    print("  入场价: 10.0, 现价: 10.6, 持仓4天, 浮盈 6%")
    should_exit, reason = rc.check_exit(
        symbol="603607",
        entry_price=10.0,
        current_price=10.6,
        entry_date="2026-02-04",
        current_date="2026-02-08"
    )
    print(f"  结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == False and reason == "NONE", "收益达标测试失败"
    print("  ✓ 通过")
    
    # 测试用例5：强制时间止损（持仓6天）
    print("\n用例5：强制时间止损（超过最大持仓天数）")
    print("  入场价: 10.0, 现价: 10.8, 持仓6天, 浮盈 8%")
    should_exit, reason = rc.check_exit(
        symbol="603607",
        entry_price=10.0,
        current_price=10.8,
        entry_date="2026-02-02",
        current_date="2026-02-08"
    )
    print(f"  结果: should_exit={should_exit}, reason={reason}")
    assert should_exit == True and reason == "TIME_STOP", "强制时间止损测试失败"
    print("  ✓ 通过")
    
    print("\n" + "=" * 60)
    print("✅ 所有 check_exit 测试通过！")
    print("=" * 60)


def test_check_portfolio_constraints():
    """测试组合约束检查"""
    print("\n" + "=" * 60)
    print("测试 check_portfolio_constraints (组合约束检查)")
    print("=" * 60)
    
    rc = RiskControlManager()
    total_equity = 100000.0  # 10万总资金
    
    # 测试用例1：持仓数量过多（4只票）
    print("\n用例1：持仓数量过多测试")
    print(f"  总资金: {total_equity}, 持仓数量: 4")
    positions = {
        "603607": 20000.0,
        "000001": 20000.0,
        "000002": 20000.0,
        "000003": 20000.0,
    }
    ok, reason = rc.check_portfolio_constraints(total_equity, positions)
    print(f"  结果: ok={ok}, reason={reason}")
    assert ok == False and reason == "TOO_MANY_POS", "持仓数量过多测试失败"
    print("  ✓ 通过")
    
    # 测试用例2：单票仓位过大（30%）
    print("\n用例2：单票仓位过大测试")
    print(f"  总资金: {total_equity}, 单票仓位: 30000 (30%)")
    positions = {
        "603607": 30000.0,
        "000001": 20000.0,
    }
    ok, reason = rc.check_portfolio_constraints(total_equity, positions)
    print(f"  结果: ok={ok}, reason={reason}")
    assert ok == False and reason == "POSITION_TOO_LARGE", "单票仓位过大测试失败"
    print("  ✓ 通过")
    
    # 测试用例3：所有检查通过
    print("\n用例3：所有检查通过测试")
    print(f"  总资金: {total_equity}, 2只票，每只20%")
    positions = {
        "603607": 20000.0,
        "000001": 20000.0,
    }
    ok, reason = rc.check_portfolio_constraints(total_equity, positions)
    print(f"  结果: ok={ok}, reason={reason}")
    assert ok == True and reason == "OK", "所有检查通过测试失败"
    print("  ✓ 通过")
    
    # 测试用例4：边界测试（3只票，不能加新仓）
    print("\n用例4：边界测试（3只票，不能加新仓）")
    print(f"  总资金: {total_equity}, 3只票，每只25%")
    positions = {
        "603607": 25000.0,
        "000001": 25000.0,
        "000002": 25000.0,
    }
    ok, reason = rc.check_portfolio_constraints(total_equity, positions)
    print(f"  结果: ok={ok}, reason={reason}")
    assert ok == False and reason == "TOO_MANY_POS", "边界测试失败"
    print("  ✓ 通过")
    
    print("\n" + "=" * 60)
    print("✅ 所有 check_portfolio_constraints 测试通过！")
    print("=" * 60)


def test_can_open_position():
    """测试开仓检查"""
    print("\n" + "=" * 60)
    print("测试 can_open_position (开仓检查)")
    print("=" * 60)
    
    rc = RiskControlManager()
    total_equity = 100000.0
    
    # 测试用例1：新开仓超过单票限制
    print("\n用例1：新开仓超过单票限制测试")
    print(f"  总资金: {total_equity}, 新开仓: 30000 (30%)")
    positions = {
        "603607": 20000.0,
        "000001": 20000.0,
    }
    ok, reason = rc.can_open_position(total_equity, positions, 30000.0)
    print(f"  结果: ok={ok}, reason={reason}")
    assert ok == False and reason == "POSITION_TOO_LARGE", "新开仓超过单票限制测试失败"
    print("  ✓ 通过")
    
    # 测试用例2：新开仓允许
    print("\n用例2：新开仓允许测试")
    print(f"  总资金: {total_equity}, 新开仓: 20000 (20%)")
    positions = {
        "603607": 20000.0,
        "000001": 20000.0,
    }
    ok, reason = rc.can_open_position(total_equity, positions, 20000.0)
    print(f"  结果: ok={ok}, reason={reason}")
    assert ok == True and reason == "OK", "新开仓允许测试失败"
    print("  ✓ 通过")
    
    print("\n" + "=" * 60)
    print("✅ 所有 can_open_position 测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    print("\n开始风控管理器测试...\n")
    
    test_check_exit()
    test_check_portfolio_constraints()
    test_can_open_position()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！风控模块可用！")
    print("=" * 60)
    print("\n核心规则总结：")
    print("  ✓ 价格止损：-5%")
    print("  ✓ 时间止损：3-5天且收益 <+5%")
    print("  ✓ 仓位限制：单票≤25%，总数≤3只")
    print("=" * 60 + "\n")