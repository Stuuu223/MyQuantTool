"""
测试"强更强"逻辑（昨天涨停 + 今天高开）
"""

import pandas as pd
from logic.dragon_tactics import DragonTactics


def test_strong_to_strong():
    """测试强更强逻辑"""
    print("=" * 80)
    print("测试强更强逻辑（昨天涨停 + 今天高开）")
    print("=" * 80)

    # 创建 DragonTactics 实例
    tactics = DragonTactics()

    # 创建测试数据（昨天涨停 + 今天高开）
    dates = pd.date_range(start='2024-01-01', periods=5, freq='D')
    data = {
        'open': [10.0, 10.5, 11.0, 11.0, 12.4],  # 昨天开盘 11.0，今天高开 12.4（+2.5%）
        'close': [10.0, 10.5, 11.0, 12.1, 12.1],  # 昨天收盘 12.1（涨停板）
        'high': [10.2, 10.7, 11.2, 12.3, 13.2],
        'low': [9.8, 10.3, 10.8, 10.9, 12.0],
        'volume': [1000000, 1200000, 1500000, 2000000, 1800000],
        'amount': [10000000, 12600000, 16500000, 24200000, 23400000]
    }
    df = pd.DataFrame(data, index=dates)

    print("\n【测试数据】")
    print("股票代码：300622")
    print("股票名称：博士眼镜")
    print("昨天：涨停板（+10%）")
    print("今天：高开（+2%）")
    print("预期：强更强形态，评分 90 分")

    print("\n【分析中...】")

    # 弱转强分析
    weak_to_strong_analysis = tactics.analyze_weak_to_strong(df)

    print("\n【弱转强分析】")
    print(f"  完整结果: {weak_to_strong_analysis}")
    print(f"  是否弱转强: {weak_to_strong_analysis.get('weak_to_strong', False)}")
    print(f"  弱转强评分: {weak_to_strong_analysis.get('weak_to_strong_score', 0)}")
    print(f"  弱转强描述: {weak_to_strong_analysis.get('weak_to_strong_desc', '')}")

    # 验证结果
    print("\n【验证结果】")
    if weak_to_strong_analysis.get('weak_to_strong', False):
        print("✅ 弱转强/强更强识别成功")
    else:
        print("❌ 弱转强/强更强识别失败")

    if weak_to_strong_analysis.get('weak_to_strong_score', 0) >= 90:
        print("✅ 评分正确：>= 90 分")
    else:
        print(f"❌ 评分错误：{weak_to_strong_analysis.get('weak_to_strong_score', 0)} 分（应该 >= 90）")

    if '强更强' in weak_to_strong_analysis.get('weak_to_strong_desc', ''):
        print("✅ 描述正确：包含'强更强'")
    else:
        print("❌ 描述错误：不包含'强更强'")

    if weak_to_strong_analysis.get('is_strong_to_strong', False):
        print("✅ 强更强标志正确")
    else:
        print("❌ 强更强标志错误")

    print("\n" + "=" * 80)
    if (weak_to_strong_analysis.get('weak_to_strong', False) and 
        weak_to_strong_analysis.get('weak_to_strong_score', 0) >= 90 and
        '强更强' in weak_to_strong_analysis.get('weak_to_strong_desc', '')):
        print("✅ 测试通过：强更强逻辑正常工作")
    else:
        print("❌ 测试失败：强更强逻辑存在问题")
    print("=" * 80)


if __name__ == "__main__":
    test_strong_to_strong()