import google.generativeai as genai
import os

# 填入你的 Key
api_key = "AIzaSyC9mFvAjbWTiuqr4bgiNKikEdRDn8_nnnw"
genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("你好，测试一下网络通不通")
    print("✅ 成功！API Key 和网络都没问题。")
    print("回复:", response.text)
except Exception as e:
    print("❌ 失败:", e)