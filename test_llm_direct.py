"""
直接测试 LLM 调用
"""

import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logic.llm_interface import DeepSeekProvider

def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_llm():
    """测试 LLM 调用"""
    print("=" * 60)
    print("测试 LLM 调用")
    print("=" * 60)

    # 加载配置
    config = load_config()
    api_key = config.get('api_key', '')

    if not api_key:
        print("❌ 错误：config.json 中没有找到 api_key")
        return

    # 创建 LLM 提供商
    provider = DeepSeekProvider(api_key=api_key)

    # 构建测试 Prompt
    prompt = """【角色定义】
你是A股顶级游资操盘手。

【核心禁令】
1. 禁止建议"等待回调"
2. 禁止使用 KDJ、MACD 金叉作为买入依据
3. 禁止看市盈率 (PE/PB)

【当前数据】
股票代码：300313
股票名称：*ST天山
当前价格：12.50
涨跌幅：+13.40%

【输出格式】
请务必只返回标准的 JSON 格式：
{
    "score": 0-100,
    "role": "龙头" | "中军" | "跟风" | "杂毛",
    "signal": "BUY_AGGRESSIVE" | "BUY_DIP" | "WAIT" | "SELL",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "reason": "简短理由",
    "stop_loss_price": 0
}"""

    print("\n【发送 Prompt】")
    print(prompt[:200] + "...")

    print("\n【调用 LLM...】")
    try:
        from logic.llm_interface import LLMMessage
        messages = [LLMMessage(role="user", content=prompt)]
        response = provider.chat(messages, model="deepseek-chat")

        print(f"\n【响应类型】")
        print(f"  type: {type(response)}")
        print(f"  hasattr content: {hasattr(response, 'content')}")

        if hasattr(response, 'content'):
            print(f"\n【响应内容】")
            print(response.content)
        else:
            print(f"\n【响应内容】")
            print(response)

    except Exception as e:
        print(f"\n❌ 错误：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm()