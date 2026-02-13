import requests
import urllib3

# 禁用代理和SSL警告
import os
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 禁用SSL验证
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 创建无代理的session
session = requests.Session()
session.trust_env = False
session.proxies = {'http': None, 'https': None}
session.verify = False  # 禁用SSL验证（测试用）

print("🧪 测试网络连接...")
print("=" * 80)

# 测试1: 百度
print("\n1️⃣ 测试百度（HTTPS）")
try:
    response = session.get('https://www.baidu.com', timeout=10)
    print(f"   ✅ 百度连接成功！状态码: {response.status_code}")
except Exception as e:
    print(f"   ❌ 百度连接失败: {e}")

# 测试2: AkShare API
print("\n2️⃣ 测试AkShare API（HTTPS）")
try:
    response = session.get('https://82.push2.eastmoney.com/api/qt/clist/get?pn=1', timeout=10)
    print(f"   ✅ AkShare连接成功！状态码: {response.status_code}")
    print(f"   📄 响应长度: {len(response.content)} 字节")
except Exception as e:
    print(f"   ❌ AkShare连接失败: {type(e).__name__}: {e}")

# 测试3: Tushare（备用）
print("\n3️⃣ 测试Tushare（HTTPS）")
try:
    response = session.get('https://api.tushare.pro', timeout=10)
    print(f"   ✅ Tushare连接成功！状态码: {response.status_code}")
except Exception as e:
    print(f"   ❌ Tushare连接失败: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("测试完成")