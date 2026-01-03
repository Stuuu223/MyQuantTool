from openai import OpenAI

# 测试硅基流动 API
# 访问 https://siliconflow.cn/ 注册获取 API Key（新用户送 2000 万免费 tokens）

api_key = "sk-cb81f10fb7cc412aacb561a4e562fbdf"  # 使用相同的 Key 格式

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1"
    )

    response = client.chat.completions.create(
        model='deepseek-ai/DeepSeek-V3',
        messages=[
            {'role': 'user', 'content': '你好，测试一下硅基流动 API 连接'}
        ],
        temperature=0.7,
        max_tokens=100
    )

    print("✅ 硅基流动 API 连接成功！")
    print("回复:", response.choices[0].message.content)

except Exception as e:
    print("❌ 连接失败:", str(e))
    print("\n提示：")
    print("1. 请访问 https://siliconflow.cn/ 注册账号")
    print("2. 新用户免费获得 2000 万 tokens")
    print("3. 在个人中心获取 API Key")
    print("4. 支持多种模型：DeepSeek-V3、DeepSeek-R1、Qwen、GLM 等")