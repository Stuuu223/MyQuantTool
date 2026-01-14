"""
测试 LLM 响应内容
"""

import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from logic.llm_interface import DeepSeekProvider
from logic.llm_interface import LLMMessage

def load_config():
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_llm():
    """测试 LLM 调用"""
    print("=" * 80)
    print("测试 LLM 响应")
    print("=" * 80)

    # 加载配置
    config = load_config()
    api_key = config.get('api_key', '')

    if not api_key:
        print("❌ 错误：config.json 中没有找到 api_key")
        return

    # 创建 LLM 提供商
    provider = DeepSeekProvider(api_key=api_key)

    # 构建测试 Prompt
    prompt = """股票代码：300622
股票名称：博士眼镜
当前价格：25.60
今日涨跌幅：+19.80%
竞价抢筹度: 18.00% (极强)
板块: AI眼镜
板块地位: 排名 1/15 (👑 龙一 (板块核心龙头))
弱转强: ✅ 是 (昨天炸板/大阴，今天高开逾越压力位)
分时强承接: ✅ 是 (股价在均线上方，下跌缩量上涨放量)

请返回 JSON 格式：
{
    "score": 0-100,
    "role": "龙头" | "中军" | "跟风" | "杂毛",
    "signal": "BUY_AGGRESSIVE" | "BUY_DIP" | "WAIT" | "SELL",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "reason": "简短理由",
    "stop_loss_price": 0
}"""

    print("\n【发送 Prompt】")
    print(prompt)

    print("\n【调用 LLM...】")
    try:
        messages = [LLMMessage(role="user", content=prompt)]
        response = provider.chat(messages, model="deepseek-chat")

        print(f"\n【响应类型】")
        print(f"  type: {type(response)}")
        print(f"  hasattr content: {hasattr(response, 'content')}")

        if hasattr(response, 'content'):
            print(f"\n【响应内容】")
            print(response.content)
            print(f"\n【响应长度】")
            print(f"  {len(response.content)} 字符")
        else:
            print(f"\n【响应内容】")
            print(response)

    except Exception as e:
        print(f"\n❌ 错误：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm()