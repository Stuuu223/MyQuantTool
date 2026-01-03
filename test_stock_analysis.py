from openai import OpenAI

api_key = "sk-bxjtojiiuhmtrnrnwykrompexglngkzmcjydvgesxkqgzzet"

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1"
    )

    # 模拟股票分析请求
    prompt = '''
    你是一位资深的A股交易员，风格理性客观。
    
    【市场数据】
    股票代码: 600519
    今日涨跌幅: 1.5%
    技术面信号: 当前价1800.0，阻力位[1850.0, 1900.0]，ATR=25.5
    
    请简短分析（100字以内）：
    1. 波动背后的可能情绪？
    2. 给小白用户的操作建议（持仓/减仓/观望）？
    '''

    response = client.chat.completions.create(
        model='deepseek-ai/DeepSeek-V3',
        messages=[
            {'role': 'user', 'content': prompt}
        ],
        temperature=0.7,
        max_tokens=200
    )

    print("Stock Analysis Test:")
    print("="*50)
    print(response.choices[0].message.content)
    print("="*50)
    print("Test completed successfully!")

except Exception as e:
    print(f"Error: {str(e)}")