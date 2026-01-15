测试 UI 中的龙头战法逻辑

import pandas as pd
from logic.dragon_tactics import DragonTactics


def test_ui_logic():
    """测试 UI 中的龙头战法逻辑"""
    print("=" * 80)
    print("测试 UI 中的龙头战法逻辑")
    print("=" * 80)

    # 创建 DragonTactics 实例
    tactics = DragonTactics()

    # 创建测试数据（模拟数据库返回的股票数据）
    dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
    data = {
        'open': [10.0, 10.2, 10.4, 10.6, 10.8, 11.0, 11.2, 11.4, 11.6, 12.0],
        'close': [10.0, 10.2, 10.4, 10.6, 10.8, 11.0, 11.2, 11.4, 11.6, 12.1],
        'high': [10.2, 10.4, 10.6, 10.8, 11.0, 11.2, 11.4, 11.6, 11.8, 12.3],
        'low': [9.8, 10.0, 10.2, 10.4, 10.6, 10.8, 11.0, 11.2, 11.4, 11.9],
        'volume': [1000000, 1200000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000, 4500000, 5000000],
        'amount': [10000000, 12240000, 15600000, 21200000, 27000000, 33000000, 39200000, 45600000, 52200000, 60500000],
        'pct_chg': [0.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 4.3]
    }
    stock_data = pd.DataFrame(data, index=dates)

    # 获取最新数据
    latest = stock_data.iloc[-1]
    prev_day = stock_data.iloc[-2]

    print("\n【测试数据】")
    print(f"股票代码：300622")
    print(f"最新价：{latest.get('close', 0):.2f}")
    print(f"涨跌幅：{latest.get('pct_chg', 0):.2f}%")
    print(f"成交量：{latest.get('volume', 0):,.0f}")

    print("\n【分析中...】")

    # 1. 代码前缀检查
    code_check = tactics.check_code_prefix('300622', '博士眼镜')
    print(f"\n【代码前缀检查】")
    print(f"  前缀类型: {code_check.get('prefix_type', '未知')}")
    print(f"  涨跌幅限制: {code_check.get('max_limit', 10)}cm")
    print(f"  是否ST: {code_check.get('is_st', False)}")
    print(f"  是否禁止: {code_check.get('banned', False)}")

    # 2. 竞价分析（使用涨跌幅作为代理）
    change_percent = latest.get('pct_chg', 0)
    if change_percent > 5:
        auction_ratio = 0.03
    elif change_percent > 3:
        auction_ratio = 0.02
    elif change_percent > 0:
        auction_ratio = 0.01
    else:
        auction_ratio = 0.005

    auction_analysis = tactics.analyze_call_auction(
        current_open_volume=prev_day.get('volume', 1) * auction_ratio,
        prev_day_total_volume=prev_day.get('volume', 1),
        current_open_amount=prev_day.get('amount', 1) * auction_ratio,
        prev_day_total_amount=prev_day.get('amount', 1)
    )

    print(f"\n【竞价分析】")
    print(f"  竞价量比: {auction_analysis.get('call_auction_ratio', 0):.1%}")
    print(f"  竞价强度: {auction_analysis.get('auction_intensity', '未知')}")
    print(f"  竞价评分: {auction_analysis.get('auction_score', 0)}")

    # 3. 板块地位分析（使用涨跌幅作为代理）
    if change_percent > 7:
        sector_role_score = 80
        sector_role = '龙一（推断）'
    elif change_percent > 5:
        sector_role_score = 60
        sector_role = '前三（推断）'
    elif change_percent > 3:
        sector_role_score = 40
        sector_role = '中军（推断）'
    elif change_percent > 0:
        sector_role_score = 20
        sector_role = '跟风（推断）'
    else:
        sector_role_score = 0
        sector_role = '杂毛'

    print(f"\n【板块地位分析】")
    print(f"  涨跌幅: {change_percent:.2f}%")
    print(f"  板块角色: {sector_role}")
    print(f"  板块角色评分: {sector_role_score}")

    # 4. 弱转强分析
    weak_to_strong_analysis = tactics.analyze_weak_to_strong(df=stock_data)

    print(f"\n【弱转强分析】")
    print(f"  是否弱转强: {weak_to_strong_analysis.get('weak_to_strong', False)}")
    print(f"  弱转强评分: {weak_to_strong_analysis.get('weak_to_strong_score', 0)}")
    print(f"  弱转强描述: {weak_to_strong_analysis.get('weak_to_strong_desc', '')}")

    # 5. 分时承接分析（使用 K 线数据作为代理）
    if latest.get('close', 0) > latest.get('open', 0):
        intraday_support_score = 80
        intraday_support = True
    elif latest.get('close', 0) > latest.get('low', 0):
        intraday_support_score = 60
        intraday_support = True
    else:
        intraday_support_score = 20
        intraday_support = False

    print(f"\n【分时承接分析】")
    print(f"  是否强承接: {intraday_support}")
    print(f"  分时承接评分: {intraday_support_score}")

    # 6. 决策矩阵
    is_20cm = code_check.get('max_limit', 10) == 20
    decision = tactics.make_decision_matrix(
        role_score=sector_role_score,
        auction_score=auction_analysis.get('auction_score', 0),
        weak_to_strong_score=weak_to_strong_analysis.get('weak_to_strong_score', 0),
        intraday_support_score=intraday_support_score,
        current_change=change_percent,
        is_20cm=is_20cm
    )

    print(f"\n【决策矩阵】")
    print(f"  龙头地位 (40%): {sector_role_score} 分")
    print(f"  竞价强度 (20%): {auction_analysis.get('auction_score', 0)} 分")
    print(f"  弱转强形态 (20%): {weak_to_strong_analysis.get('weak_to_strong_score', 0)} 分")
    print(f"  分时承接 (20%): {intraday_support_score} 分")
    print(f"  总评分: {decision.get('total_score', 0):.1f} 分")
    print(f"  角色: {decision.get('role', '未知')}")
    print(f"  信号: {decision.get('signal', 'WAIT')}")
    print(f"  置信度: {decision.get('confidence', 'MEDIUM')}")
    print(f"  理由: {decision.get('reason', '')}")
    print(f"  建议仓位: {decision.get('position', '观望')}")

    # 验证结果
    print("\n【验证结果】")
    if decision.get('total_score', 0) >= 60:
        print(f"✅ 评分正确：{decision.get('total_score', 0):.1f} 分（>= 60，符合最低门槛）")
    else:
        print(f"❌ 评分错误：{decision.get('total_score', 0):.1f} 分（应该 >= 60）")

    print("\n" + "=" * 80)
    if decision.get('total_score', 0) >= 60:
        print("✅ 测试通过：能够识别到符合条件的股票")
    else:
        print("❌ 测试失败：无法识别到符合条件的股票")
    print("=" * 80)


if __name__ == "__main__":
    test_ui_logic()