from openai import OpenAI

# 测试 DeepSeek API 连接
# 请在 https://platform.deepseek.com/ 获取您的 API Key

api_key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 请替换为您的实际 API Key

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    response = client.chat.completions.create(
        model='deepseek-chat',
        messages=[
            {'role': 'user', 'content': '你好，测试一下 DeepSeek API 连接是否正常'}
        ],
        temperature=0.7,
        max_tokens=100
    )

    print("✅ DeepSeek API 连接成功！")
    print("回复:", response.choices[0].message.content)

except Exception as e:
    print("❌ 连接失败:", str(e))
    print("\n提示：")
    print("1. 请访问 https://platform.deepseek.com/ 注册并获取 API Key")
    print("2. 新用户可获得 10 元免费额度（约 125 万 tokens）")
    print("3. 将您的 API Key 替换到本文件的 api_key 变量中")