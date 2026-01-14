"""
测试龙头战法 V3.0 增强版（规则决策）
验证竞价量比、板块地位、弱转强、分时强承接等特征
"""

import sys
import os
import json
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logic.dragon_tactics import DragonTactics

def test_dragon_glasses():
    """测试博士眼镜（AI眼镜龙头）"""
    print("=" * 80)
    print("测试博士眼镜（AI眼镜龙头）- 规则决策")
    print("=" * 80)

    # 创建 DragonTactics
    tactics = DragonTactics()

    # 模拟博士眼镜的数据
    print("\n【测试数据】")
    print(f"股票代码：300622")
    print(f"股票名称：博士眼镜")
    print(f"板块：AI眼镜")
    print(f"板块地位：龙一 (板块核心龙头)")
    print(f"竞价抢筹度：0.18 (极强)")
    print(f"弱转强：是")
    print(f"分时强承接：是")
    print(f"涨跌幅：+19.80% (20cm 封板)")

    print("\n【分析中...】")

    # 1. 代码前缀检查
    code_check = tactics.check_code_prefix("300622", "博士眼镜")
    print(f"\n【代码前缀检查】")
    print(f"  前缀类型: {code_check.get('prefix_type', 'N/A')}")
    print(f"  涨跌幅限制: {code_check.get('max_limit', 'N/A')}cm")
    print(f"  是否ST: {code_check.get('is_st', 'N/A')}")
    print(f"  是否禁止: {code_check.get('banned', 'N/A')}")

    # 2. 竞价分析
    auction_analysis = tactics.analyze_call_auction(
        current_open_volume=144000000,
        prev_day_total_volume=800000000,
        current_open_amount=368640000,
        prev_day_total_amount=2048000000
    )
    print(f"\n【竞价分析】")
    print(f"  竞价量比: {auction_analysis.get('call_auction_ratio', 'N/A'):.2%}")
    print(f"  竞价强度: {auction_analysis.get('auction_intensity', 'N/A')}")
    print(f"  竞价评分: {auction_analysis.get('auction_score', 'N/A')}")

    # 3. 板块地位分析
    sector_analysis = tactics.analyze_sector_rank(
        symbol="300622",
        sector="AI眼镜",
        current_change=19.80,
        sector_stocks_data=pd.DataFrame(),  # 模拟板块数据
        limit_up_count=3
    )
    print(f"\n【板块地位分析】")
    print(f"  角色: {sector_analysis.get('role', 'N/A')}")
    print(f"  角色评分: {sector_analysis.get('role_score', 'N/A')}")
    print(f"  板块热度: {sector_analysis.get('sector_heat', 'N/A')}")

    # 4. 弱转强分析（模拟 K 线数据）
    # 昨天大跌（炸板），今天高开，形成弱转强
    kline_data = pd.DataFrame({
        'date': pd.date_range(start='2026-01-10', periods=5),
        'close': [22.0, 21.5, 20.0, 19.0, 25.6],  # 昨天大跌 19.0 -> 20.2 (炸板)
        'open': [22.5, 22.0, 21.5, 20.0, 22.0],  # 今天高开 22.0 > 19.0
        'high': [22.8, 22.2, 21.8, 20.5, 25.6],
        'low': [21.8, 21.0, 19.5, 18.5, 22.0]
    })
    weak_to_strong_analysis = tactics.analyze_weak_to_strong(kline_data)
    print(f"\n【弱转强分析】")
    print(f"  完整结果: {weak_to_strong_analysis}")
    print(f"  是否弱转强: {weak_to_strong_analysis.get('weak_to_strong', 'N/A')}")
    print(f"  弱转强评分: {weak_to_strong_analysis.get('weak_to_strong_score', 'N/A')}")

    # 5. 分时承接分析（模拟分时数据）
    intraday_data = pd.DataFrame({
        'time': pd.date_range(start='2026-01-14 09:30', periods=60, freq='5min'),
        'price': [22.0 + i * 0.06 for i in range(60)],  # 上涨趋势
        'volume': [10000000 + i * 500000 for i in range(60)]  # 上涨放量
    })
    intraday_support_analysis = tactics.analyze_intraday_support(intraday_data)
    print(f"\n【分时承接分析】")
    print(f"  是否强承接: {intraday_support_analysis.get('has_strong_support', 'N/A')}")
    print(f"  分时承接评分: {intraday_support_analysis.get('intraday_support_score', 'N/A')}")

    # 6. 决策矩阵
    decision = tactics.make_decision_matrix(
        role_score=sector_analysis.get('role_score', 0),
        auction_score=auction_analysis.get('auction_score', 0),
        weak_to_strong_score=weak_to_strong_analysis.get('weak_to_strong_score', 0),
        intraday_support_score=intraday_support_analysis.get('intraday_support_score', 0),
        current_change=19.80,
        is_20cm=True
    )

    print(f"\n【决策矩阵】")
    print(f"  龙头地位 (40%): {sector_analysis.get('role_score', 0)} 分")
    print(f"  竞价强度 (20%): {auction_analysis.get('auction_score', 0)} 分")
    print(f"  弱转强形态 (20%): {weak_to_strong_analysis.get('weak_to_strong_score', 0)} 分")
    print(f"  分时承接 (20%): {intraday_support_analysis.get('intraday_support_score', 0)} 分")
    print(f"  总评分: {decision.get('total_score', 0)} 分")
    print(f"  角色: {decision.get('role', 'N/A')}")
    print(f"  信号: {decision.get('signal', 'N/A')}")
    print(f"  置信度: {decision.get('confidence', 'N/A')}")
    print(f"  理由: {decision.get('reason', 'N/A')}")
    print(f"  建议仓位: {decision.get('position', 'N/A')}")

    # 验证结果
    print("\n【验证结果】")
    score = decision.get('total_score', 0)
    role = decision.get('role', '')
    signal = decision.get('signal', '')

    if score >= 85:
        print(f"✅ 评分正确：{score} 分（>= 85，龙头股）")
    else:
        print(f"❌ 评分错误：{score} 分（应该 >= 85）")

    if role == '核心龙':
        print("✅ 角色正确：核心龙")
    else:
        print(f"❌ 角色错误：{role}（应该是核心龙）")

    if signal == 'BUY_AGGRESSIVE':
        print("✅ 信号正确：BUY_AGGRESSIVE (猛干)")
    else:
        print(f"❌ 信号错误：{signal}（应该是 BUY_AGGRESSIVE）")

    print("\n" + "=" * 80)
    if score >= 85 and role == '核心龙' and signal == 'BUY_AGGRESSIVE':
        print("✅ 测试通过：博士眼镜被正确识别为龙头")
    else:
        print("❌ 测试失败：博士眼镜未被正确识别为龙头")
    print("=" * 80)

def test_follower():
    """测试跟风股"""
    print("\n" + "=" * 80)
    print("测试跟风股（后排跟风）- 规则决策")
    print("=" * 80)

    # 创建 DragonTactics
    tactics = DragonTactics()

    # 模拟跟风股的数据
    print("\n【测试数据】")
    print(f"股票代码：300001")
    print(f"股票名称：特锐德")
    print(f"板块：充电桩")
    print(f"板块地位：跟风 (板块后排)")
    print(f"竞价抢筹度：0.03 (弱)")
    print(f"弱转强：否")
    print(f"分时强承接：否")
    print(f"涨跌幅：+5.20% (未涨停)")

    print("\n【分析中...】")

    # 1. 代码前缀检查
    code_check = tactics.check_code_prefix("300001", "特锐德")
    print(f"\n【代码前缀检查】")
    print(f"  前缀类型: {code_check.get('prefix_type', 'N/A')}")
    print(f"  涨跌幅限制: {code_check.get('max_limit', 'N/A')}cm")

    # 2. 竞价分析
    auction_analysis = tactics.analyze_call_auction(
        current_open_volume=9000000,
        prev_day_total_volume=300000000,
        current_open_amount=10170000,
        prev_day_total_amount=339000000
    )
    print(f"\n【竞价分析】")
    print(f"  竞价量比: {auction_analysis.get('call_auction_ratio', 'N/A'):.2%}")
    print(f"  竞价强度: {auction_analysis.get('auction_intensity', 'N/A')}")
    print(f"  竞价评分: {auction_analysis.get('auction_score', 'N/A')}")

    # 3. 板块地位分析
    sector_analysis = tactics.analyze_sector_rank(
        symbol="300001",
        sector="充电桩",
        current_change=5.20,
        sector_stocks_data=pd.DataFrame(),
        limit_up_count=2
    )
    print(f"\n【板块地位分析】")
    print(f"  角色: {sector_analysis.get('role', 'N/A')}")
    print(f"  角色评分: {sector_analysis.get('role_score', 'N/A')}")

    # 4. 弱转强分析
    kline_data = pd.DataFrame({
        'date': pd.date_range(start='2026-01-10', periods=5),
        'close': [10.5, 10.8, 11.0, 11.1, 11.3],
        'open': [10.3, 10.5, 10.8, 11.0, 11.1],
        'high': [10.6, 10.9, 11.1, 11.2, 11.3],
        'low': [10.2, 10.4, 10.7, 10.9, 11.0]
    })
    weak_to_strong_analysis = tactics.analyze_weak_to_strong(kline_data)
    print(f"\n【弱转强分析】")
    print(f"  是否弱转强: {weak_to_strong_analysis.get('is_weak_to_strong', 'N/A')}")
    print(f"  弱转强评分: {weak_to_strong_analysis.get('weak_to_strong_score', 'N/A')}")

    # 5. 分时承接分析
    intraday_data = pd.DataFrame({
        'time': pd.date_range(start='2026-01-14 09:30', periods=60, freq='5min'),
        'price': [11.0 - i * 0.01 for i in range(60)],  # 下跌趋势
        'volume': [10000000 - i * 50000 for i in range(60)]  # 下跌缩量
    })
    intraday_support_analysis = tactics.analyze_intraday_support(intraday_data)
    print(f"\n【分时承接分析】")
    print(f"  是否强承接: {intraday_support_analysis.get('has_strong_support', 'N/A')}")
    print(f"  分时承接评分: {intraday_support_analysis.get('intraday_support_score', 'N/A')}")

    # 6. 决策矩阵
    decision = tactics.make_decision_matrix(
        role_score=sector_analysis.get('role_score', 0),
        auction_score=auction_analysis.get('auction_score', 0),
        weak_to_strong_score=weak_to_strong_analysis.get('weak_to_strong_score', 0),
        intraday_support_score=intraday_support_analysis.get('intraday_support_score', 0),
        current_change=5.20,
        is_20cm=True
    )

    print(f"\n【决策矩阵】")
    print(f"  龙头地位 (40%): {sector_analysis.get('role_score', 0)} 分")
    print(f"  竞价强度 (20%): {auction_analysis.get('auction_score', 0)} 分")
    print(f"  弱转强形态 (20%): {weak_to_strong_analysis.get('weak_to_strong_score', 0)} 分")
    print(f"  分时承接 (20%): {intraday_support_analysis.get('intraday_support_score', 0)} 分")
    print(f"  总评分: {decision.get('total_score', 0)} 分")
    print(f"  角色: {decision.get('role', 'N/A')}")
    print(f"  信号: {decision.get('signal', 'N/A')}")

    # 验证结果
    print("\n【验证结果】")
    score = decision.get('total_score', 0)
    role = decision.get('role', '')
    signal = decision.get('signal', '')

    if score < 70:
        print(f"✅ 评分正确：{score} 分（< 70，跟风股）")
    else:
        print(f"⚠️ 评分偏高：{score} 分（跟风股应该给低分）")

    if role == '跟风':
        print("✅ 角色正确：跟风")
    else:
        print(f"⚠️ 角色：{role}")

    if signal == 'WAIT':
        print("✅ 信号正确：WAIT (只看不买)")
    else:
        print(f"⚠️ 信号：{signal}")

    print("=" * 80)

if __name__ == "__main__":
    test_dragon_glasses()
    test_follower()
