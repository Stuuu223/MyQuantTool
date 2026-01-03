from google import genai

# 填入你的 Key
api_key = "AIzaSyC9mFvAjbWTiuqr4bgiNKikEdRDn8_nnnw"
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents="你好，测试一下网络通不通"
    )
    print("成功！API Key 和网络都没问题。")
    print("回复:", response.text)
except Exception as e:
    print("失败:", str(e))