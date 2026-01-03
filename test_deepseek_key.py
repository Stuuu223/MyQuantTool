from openai import OpenAI

api_key = "sk-cb81f10fb7cc412aacb561a4e562fbdf"

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

    response = client.chat.completions.create(
        model='deepseek-chat',
        messages=[
            {'role': 'user', 'content': '你好'}
        ],
        temperature=0.7,
        max_tokens=50
    )

    print("✅ API Key 有效，连接成功！")
    print("回复:", response.choices[0].message.content)

except Exception as e:
    error_str = str(e)
    print("❌ 错误:", error_str)

    # 解析错误信息
    if "401" in error_str:
        print("\n错误原因：API Key 无效")
        print("解决方案：请检查您的 API Key 是否正确复制")
    elif "429" in error_str or "quota" in error_str.lower():
        print("\n错误原因：配额不足")
        print("解决方案：")
        print("1. 访问 https://platform.deepseek.com/ 查看您的配额")
        print("2. 可能需要充值才能继续使用")
    elif "403" in error_str:
        print("\n错误原因：权限不足")
        print("解决方案：请检查您的账号状态")
    else:
        print("\n其他错误，请检查网络连接")