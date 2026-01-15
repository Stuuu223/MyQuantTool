"""
测试龙头战法 V3.0 增强版
验证竞价量比、板块地位、弱转强、分时强承接等特征
"""

import sys
import os
import json
import pandas as pd
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logic.ai_agent import DragonAIAgent

def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_dragon_glasses():
    """测试博士眼镜（AI眼镜龙头）"""
    print("=" * 80)
    print("测试博士眼镜（AI眼镜龙头）")
    print("=" * 80)

    # 加载配置
    config = load_config()
    api_key = config.get('api_key', '')

    if not api_key:
        print("❌ 错误：config.json 中没有找到 api_key")
        return

    # 创建 DragonAIAgent
    agent = DragonAIAgent(api_key=api_key, provider='deepseek')

    # 模拟博士眼镜的数据（假设数据）
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

    result = agent.analyze_stock_dragon(
        symbol="300622",
        name="博士眼镜",
        price_data={
            'close': 25.60,
            'change_percent': 19.80,  # 20cm 封板
            'volume': 800000000,
            'amount': 2048000000,
            'high': 25.60,
            'low': 22.00,
            'current_price': 25.60,
            'open_volume': 144000000,  # 竞价量比 = 0.18
            'prev_day_volume': 800000000,
            'sector': 'AI眼镜',
            'sector_rank': 1,  # 龙一
            'sector_total': 15,
            'weak_to_strong': True,  # 弱转强
            'intraday_support': True  # 分时强承接
        },
        technical_data={
            'kdj': {'k': 95, 'd': 90, 'j': 105},  # KDJ 钝化，不看
            'macd': {'dif': 1.2, 'dea': 0.8, 'hist': 0.4},
            'rsi': {'RSI': 85},
            'ma': {'MA5': 22.5, 'MA10': 21.0, 'MA20': 19.5}
        },
        auction_data={
            'open_volume': 144000000,
            'prev_day_volume': 800000000,
            'open_amount': 368640000,
            'prev_day_amount': 2048000000
        },
        sector_data={
            'sector': 'AI眼镜',
            'sector_stocks': pd.DataFrame(),  # 模拟板块数据
            'limit_up_count': 3  # 板块内有 3 只涨停助攻
        }
    )

    print("\n【分析结果】")
    print(f"评分: {result.get('score', 0)}")
    print(f"角色: {result.get('role', 'N/A')}")
    print(f"信号: {result.get('signal', 'N/A')}")
    print(f"置信度: {result.get('confidence', 'N/A')}")
    print(f"理由: {result.get('reason', 'N/A')}")
    print(f"止损价: {result.get('stop_loss_price', 0)}")

    # 验证结果
    print("\n【验证结果】")
    score = result.get('score', 0)
    role = result.get('role', '')
    signal = result.get('signal', '')
    reason = result.get('reason', '')

    if score >= 85:
        print(f"✅ 评分正确：{score} 分（>= 85，龙头股）")
    else:
        print(f"❌ 评分错误：{score} 分（应该 >= 85）")

    if role == '龙头':
        print("✅ 角色正确：龙头")
    else:
        print(f"❌ 角色错误：{role}（应该是龙头）")

    if signal == 'BUY_AGGRESSIVE':
        print("✅ 信号正确：BUY_AGGRESSIVE (猛干)")
    else:
        print(f"❌ 信号错误：{signal}（应该是 BUY_AGGRESSIVE）")

    if '龙头' in reason or '核心' in reason:
        print("✅ 理由正确：识别出龙头地位")
    else:
        print(f"⚠️ 理由：{reason}")

    print("\n" + "=" * 80)
    if score >= 85 and role == '龙头' and signal == 'BUY_AGGRESSIVE':
        print("✅ 测试通过：博士眼镜被正确识别为龙头")
    else:
        print("❌ 测试失败：博士眼镜未被正确识别为龙头")
    print("=" * 80)

def test_follower():
    """测试跟风股"""
    print("\n" + "=" * 80)
    print("测试跟风股（后排跟风）")
    print("=" * 80)

    # 加载配置
    config = load_config()
    api_key = config.get('api_key', '')

    if not api_key:
        print("❌ 错误：config.json 中没有找到 api_key")
        return

    # 创建 DragonAIAgent
    agent = DragonAIAgent(api_key=api_key, provider='deepseek')

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

    result = agent.analyze_stock_dragon(
        symbol="300001",
        name="特锐德",
        price_data={
            'close': 11.30,
            'change_percent': 5.20,
            'volume': 300000000,
            'amount': 339000000,
            'high': 11.30,
            'low': 11.00,
            'current_price': 11.30,
            'open_volume': 9000000,  # 竞价量比 = 0.03
            'prev_day_volume': 300000000,
            'sector': '充电桩',
            'sector_rank': 8,  # 跟风
            'sector_total': 15,
            'weak_to_strong': False,
            'intraday_support': False
        },
        technical_data={
            'kdj': {'k': 50, 'd': 45, 'j': 60},
            'macd': {'dif': 0.1, 'dea': 0.05, 'hist': 0.05},
            'rsi': {'RSI': 55},
            'ma': {'MA5': 11.0, 'MA10': 10.8, 'MA20': 10.5}
        },
        auction_data={
            'open_volume': 9000000,
            'prev_day_volume': 300000000,
            'open_amount': 10170000,
            'prev_day_amount': 339000000
        },
        sector_data={
            'sector': '充电桩',
            'sector_stocks': pd.DataFrame(),
            'limit_up_count': 2
        }
    )

    print("\n【分析结果】")
    print(f"评分: {result.get('score', 0)}")
    print(f"角色: {result.get('role', 'N/A')}")
    print(f"信号: {result.get('signal', 'N/A')}")
    print(f"置信度: {result.get('confidence', 'N/A')}")
    print(f"理由: {result.get('reason', 'N/A')}")

    # 验证结果
    print("\n【验证结果】")
    score = result.get('score', 0)
    role = result.get('role', '')
    signal = result.get('signal', '')

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