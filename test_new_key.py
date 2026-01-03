from openai import OpenAI

api_key = "sk-bxjtojiiuhmtrnrnwykrompexglngkzmcjydvgesxkqgzzet"

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

    print("Success! API Key is valid.")
    print("Response:", response.choices[0].message.content)

except Exception as e:
    error_str = str(e)
    print("Error:", error_str)

    if "401" in error_str:
        print("\nReason: Invalid API Key")
    elif "429" in error_str or "quota" in error_str.lower():
        print("\nReason: Quota exceeded")
    elif "402" in error_str:
        print("\nReason: Insufficient balance")
    else:
        print("\nOther error")