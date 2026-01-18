"""
V16 环境熔断系统测试

测试市场情绪对个股交易的前置条件控制：
- 冰点熔断：市场情绪 < 20，禁止开仓
- 退潮减权：市场退潮期，所有 BUY 信号的 AI 分数权重 x 0.5
- 共振加强：市场情绪高昂 + 股票趋势向上，最终评分 +10分
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.signal_generator import SignalGenerator
from logic.market_sentiment import MarketSentiment
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_ice_age_circuit_breaker():
    """
    测试冰点熔断：市场情绪 < 20，禁止开仓
    """
    print("\n" + "=" * 80)
    print("测试 1：冰点熔断 - 极度恐慌禁止开仓")
    print("=" * 80)
    
    sg = SignalGenerator()
    
    # 场景 1: 市场情绪冰点 (score=15)，个股强势 (ai_score=90)
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=90,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=15,
        market_status="冰点"
    )
    
    assert result['signal'] == "WAIT", "冰点熔断应返回 WAIT"
    assert result['score'] == 0, "冰点熔断得分应为 0"
    assert "环境熔断" in result['reason'], "理由应包含环境熔断"
    
    print(f"✅ 场景 1: 市场冰点({result['market_sentiment_score']}) → 信号: {result['signal']}")
    print(f"   得分: {result['score']}")
    print(f"   理由: {result['reason']}")
    
    # 场景 2: 市场情绪冰点 (score=15)，个股涨停豁免
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=90,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=10.0,  # 涨停
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=15,
        market_status="冰点"
    )
    
    assert result['signal'] == "BUY", "涨停股可以穿越冰点"
    assert "涨停豁免" in result['reason'], "理由应包含涨停豁免"
    assert "环境熔断-豁免" in result['reason'], "理由应包含环境熔断豁免"
    
    print(f"✅ 场景 2: 冰点 + 涨停豁免 → 信号: {result['signal']}")
    print(f"   得分: {result['score']}")
    print(f"   理由: {result['reason']}")
    
    print("\n✅ 测试 1 通过：冰点熔断逻辑正确")


def test_ebb_tide_downgrade():
    """
    测试退潮减权：市场退潮期，所有 BUY 信号的 AI 分数权重 x 0.5
    """
    print("\n" + "=" * 80)
    print("测试 2：退潮减权 - 市场退潮期评分降级")
    print("=" * 80)
    
    sg = SignalGenerator()
    
    # 场景 1: 市场退潮期，个股强势 (ai_score=90)
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=90,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=40,
        market_status="退潮"
    )
    
    # AI 分数 90 * 0.5 = 45，应该返回 WAIT
    assert result['signal'] == "WAIT", "退潮期应降级为 WAIT"
    assert result['score'] < 50, "退潮期得分应降低"
    assert "退潮期" in result['reason'], "理由应包含退潮期"
    
    print(f"✅ 场景 1: 市场退潮期 → 信号: {result['signal']}")
    print(f"   得分: {result['score']} (AI: 90 → 45)")
    print(f"   理由: {result['reason']}")
    
    # 场景 2: 市场退潮期，个股超强 (ai_score=100)
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=100,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=40,
        market_status="退潮"
    )
    
    # AI 分数 100 * 0.5 = 50，应该返回 WAIT
    assert result['signal'] == "WAIT", "退潮期超强股仍应降级"
    assert result['score'] < 60, "退潮期得分应降低"
    
    print(f"✅ 场景 2: 退潮期 + 超强股 → 信号: {result['signal']}")
    print(f"   得分: {result['score']} (AI: 100 → 50)")
    print(f"   理由: {result['reason']}")
    
    print("\n✅ 测试 2 通过：退潮减权逻辑正确")


def test_resonance_boost():
    """
    测试共振加强：市场情绪高昂 + 股票趋势向上，最终评分 +10分
    """
    print("\n" + "=" * 80)
    print("测试 3：共振加强 - 市场情绪高昂 + 趋势向上")
    print("=" * 80)
    
    sg = SignalGenerator()
    
    # 场景 1: 市场情绪高昂 (score=70)，个股趋势向上 (trend=UP)
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=75,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=70,
        market_status="主升"
    )
    
    # AI 分数 75 + 10 = 85，应该返回 BUY
    assert result['signal'] == "BUY", "共振加强应返回 BUY"
    assert result['score'] >= 85, "共振加强得分应增加"
    assert "共振加强" in result['reason'], "理由应包含共振加强"
    
    print(f"✅ 场景 1: 市场主升期 + 趋势向上 → 信号: {result['signal']}")
    print(f"   得分: {result['score']} (AI: 75 + 10 = 85)")
    print(f"   理由: {result['reason']}")
    
    # 场景 2: 市场情绪高昂 (score=70)，个股趋势向下 (trend=DOWN)
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=75,
        capital_flow=10000000,
        trend='DOWN',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=70,
        market_status="主升"
    )
    
    # 趋势向下，应被熔断
    assert result['signal'] == "WAIT", "趋势向下应返回 WAIT"
    assert "趋势熔断" in result['reason'], "理由应包含趋势熔断"
    
    print(f"✅ 场景 2: 市场主升期 + 趋势向下 → 信号: {result['signal']}")
    print(f"   得分: {result['score']}")
    print(f"   理由: {result['reason']}")
    
    print("\n✅ 测试 3 通过：共振加强逻辑正确")


def test_market_sentiment_score():
    """
    测试市场情绪分数获取
    """
    print("\n" + "=" * 80)
    print("测试 4：市场情绪分数获取")
    print("=" * 80)
    
    ms = MarketSentiment()
    
    # 获取市场情绪分数
    sentiment = ms.get_market_sentiment_score()
    
    print(f"✅ 市场情绪分数: {sentiment['score']}")
    print(f"   市场状态: {sentiment['status']}")
    print(f"   状态描述: {sentiment['description']}")
    print(f"   涨停家数: {sentiment['limit_up_count']}")
    print(f"   跌停家数: {sentiment['limit_down_count']}")
    print(f"   昨日溢价: {sentiment['prev_profit']}%")
    print(f"   恶性炸板率: {sentiment['malignant_zhaban_rate']}")
    
    # 验证分数范围
    assert 0 <= sentiment['score'] <= 100, "市场情绪分数应在 0-100 之间"
    
    # 验证状态
    valid_statuses = ['主升', '退潮', '震荡', '冰点']
    assert sentiment['status'] in valid_statuses, f"市场状态应为 {valid_statuses} 之一"
    
    print("\n✅ 测试 4 通过：市场情绪分数获取正确")


def test_real_world_scenario():
    """
    测试真实场景：德恩精工在不同市场环境下的表现
    """
    print("\n" + "=" * 80)
    print("测试 5：真实场景 - 德恩精工在不同市场环境下的表现")
    print("=" * 80)
    
    sg = SignalGenerator()
    
    # 场景 1: 市场冰点，德恩精工强势
    print("\n📅 场景 1: 市场冰点 (score=15)，德恩精工强势 (ai_score=90)")
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=90,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=15,
        market_status="冰点"
    )
    
    print(f"   信号: {result['signal']}")
    print(f"   得分: {result['score']}")
    print(f"   理由: {result['reason']}")
    print(f"   💡 分析: 市场冰点，禁止开仓，德恩精工再好也不能买")
    
    # 场景 2: 市场退潮，德恩精工强势
    print("\n📅 场景 2: 市场退潮 (score=40)，德恩精工强势 (ai_score=90)")
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=90,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=40,
        market_status="退潮"
    )
    
    print(f"   信号: {result['signal']}")
    print(f"   得分: {result['score']}")
    print(f"   理由: {result['reason']}")
    print(f"   💡 分析: 市场退潮，评分降级，德恩精工被埋风险高")
    
    # 场景 3: 市场主升，德恩精工强势
    print("\n📅 场景 3: 市场主升 (score=70)，德恩精工强势 (ai_score=90)")
    result = sg.calculate_final_signal(
        stock_code="603056",
        ai_score=90,
        capital_flow=10000000,
        trend='UP',
        current_pct_change=5.0,
        yesterday_lhb_net_buy=0,
        open_pct_change=0.5,
        market_sentiment_score=70,
        market_status="主升"
    )
    
    print(f"   信号: {result['signal']}")
    print(f"   得分: {result['score']}")
    print(f"   理由: {result['reason']}")
    print(f"   💡 分析: 市场主升 + 趋势向上，共振加强，德恩精工买入")
    
    print("\n✅ 测试 5 完成：真实场景分析")


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("V16 环境熔断系统测试")
    print("=" * 80)
    
    try:
        test_ice_age_circuit_breaker()
        test_ebb_tide_downgrade()
        test_resonance_boost()
        test_market_sentiment_score()
        test_real_world_scenario()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())