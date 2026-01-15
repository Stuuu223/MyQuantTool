"""
测试 ST 股过滤逻辑
验证 *ST天山 不会被误判为龙头
"""

import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logic.ai_agent import DragonAIAgent

def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_st_filter():
    """测试 ST 股过滤"""
    print("=" * 60)
    print("测试 ST 股过滤逻辑")
    print("=" * 60)

    # 加载配置
    config = load_config()
    api_key = config.get('api_key', '')

    if not api_key:
        print("❌ 错误：config.json 中没有找到 api_key")
        return

    # 创建 DragonAIAgent（专门用于龙头战法）
    agent = DragonAIAgent(api_key=api_key, provider='deepseek')

    # 模拟 *ST天山 的数据
    st_context = """
股票代码：300313
股票名称：*ST天山
当前价格：12.50
涨跌幅：+13.40%
成交量：50000万
成交额：6.25亿
涨停板：20/20
KDJ：10/20
板块：农业
"""

    print("\n【测试数据】")
    print(f"股票名称：*ST天山")
    print(f"涨跌幅：+13.40%")
    print(f"板块：农业")

    print("\n【分析中...】")
    # 使用 analyze_stock_dragon 方法
    import pandas as pd

    result = agent.analyze_stock_dragon(
        symbol="300313",
        name="*ST天山",  # 传递股票名称
        price_data={
            'close': 12.50,
            'change_percent': 13.40,
            'volume': 500000000,
            'amount': 625000000,
            'high': 12.50,
            'low': 11.00,
            'current_price': 12.50
        },
        technical_data={
            'kdj': {'k': 10, 'd': 20, 'j': 0},
            'macd': {'dif': 0.1, 'dea': 0.05, 'hist': 0.05}
        },
        auction_data={
            'open_volume': 50000000,
            'prev_day_volume': 500000000,
            'open_amount': 62500000,
            'prev_day_amount': 625000000
        },
        sector_data={
            'sector': '农业',
            'sector_stocks': pd.DataFrame(),  # 空 DataFrame
            'limit_up_count': 0
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
    reason = result.get('reason', '')

    if score <= 10:
        print("✅ 评分正确：<= 10 分")
    else:
        print(f"❌ 评分错误：{score} 分（应该 <= 10）")

    if role == '杂毛':
        print("✅ 角色正确：杂毛")
    else:
        print(f"❌ 角色错误：{role}（应该是杂毛）")

    if signal in ['SELL', 'WAIT']:
        print(f"✅ 信号正确：{signal}")
    else:
        print(f"❌ 信号错误：{signal}（应该是 SELL 或 WAIT）")

    if '退市风险' in reason or '流动性风险' in reason or 'ST' in reason:
        print("✅ 理由正确：包含退市风险/流动性风险")
    else:
        print(f"❌ 理由错误：{reason}")

    print("\n" + "=" * 60)
    if score <= 10 and role == '杂毛' and signal in ['SELL', 'WAIT']:
        print("✅ 测试通过：ST 股过滤逻辑正常工作")
    else:
        print("❌ 测试失败：ST 股过滤逻辑存在问题")
    print("=" * 60)

def test_20cm_limit():
    """测试 20cm 涨跌幅判断"""
    print("\n" + "=" * 60)
    print("测试 20cm 涨跌幅判断")
    print("=" * 60)

    # 加载配置
    config = load_config()
    api_key = config.get('api_key', '')

    if not api_key:
        print("❌ 错误：config.json 中没有找到 api_key")
        return

    # 创建 DragonAIAgent（专门用于龙头战法）
    agent = DragonAIAgent(api_key=api_key, provider='deepseek')

    # 模拟创业板 13% 涨幅（未涨停）
    context_20cm = """
股票代码：300001
股票名称：特锐德
当前价格：11.30
涨跌幅：+13.00%
成交量：30000万
成交额：3.39亿
涨停板：20/20
板块：充电桩
"""

    print("\n【测试数据】")
    print(f"股票名称：特锐德（创业板）")
    print(f"涨跌幅：+13.00%（未涨停）")
    print(f"板块：充电桩")

    print("\n【分析中...】")
    import pandas as pd

    result = agent.analyze_stock_dragon(
        symbol="300001",
        price_data={
            'close': 11.30,
            'change_percent': 13.00,
            'volume': 300000000,
            'amount': 339000000,
            'high': 11.30,
            'low': 10.00,
            'current_price': 11.30
        },
        technical_data={},
        auction_data={
            'open_volume': 30000000,
            'prev_day_volume': 300000000,
            'open_amount': 33900000,
            'prev_day_amount': 339000000
        },
        sector_data={
            'sector': '充电桩',
            'sector_stocks': pd.DataFrame(),  # 空 DataFrame
            'limit_up_count': 0
        }
    )

    print("\n【分析结果】")
    print(f"评分: {result.get('score', 0)}")
    print(f"角色: {result.get('role', 'N/A')}")
    print(f"信号: {result.get('signal', 'N/A')}")
    print(f"理由: {result.get('reason', 'N/A')}")

    # 验证结果
    print("\n【验证结果】")
    score = result.get('score', 0)
    reason = result.get('reason', '')

    # 13% 的涨幅对于 20cm 股票来说不算强势，应该给低分
    if score < 70:
        print(f"✅ 评分合理：{score} 分（13% 未涨停，不算强势）")
    else:
        print(f"⚠️ 评分偏高：{score} 分（13% 未涨停，应该给低分）")

    if '分歧' in reason or '烂板' in reason or '未封板' in reason:
        print("✅ 理由正确：识别出分歧/烂板")
    else:
        print(f"⚠️ 理由：{reason}")

    print("=" * 60)

if __name__ == "__main__":
    test_st_filter()
    test_20cm_limit()