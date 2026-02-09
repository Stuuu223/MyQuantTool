#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试SSL/TLS连接
"""

import requests
import ssl

print("=" * 80)
print("🔍 测试SSL/TLS连接")
print("=" * 80)
print()

print(f"Python SSL版本: {ssl.OPENSSL_VERSION}")
print()

# 测试不同的SSL配置
test_configs = [
    {
        'name': '默认配置',
        'verify': True
    },
    {
        'name': '禁用SSL验证（不安全）',
        'verify': False
    }
]

url = 'http://push2.eastmoney.com/api/qt/clist/get'
params = {
    'pn': 1,
    'pz': 10,
    'po': 1,
    'np': 1,
    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
    'fltt': 2,
    'invt': 2,
    'fid': 'f3',
    'fs': 'm:1+t:2,m:1+t:23',
    'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'
}

for idx, config in enumerate(test_configs, 1):
    print(f"测试 {idx}: {config['name']}")

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        response = session.get(url, params=params, timeout=15, verify=config['verify'])

        print(f"   ✅ 状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'diff' in data['data']:
                print(f"   ✅ 成功！获取到 {len(data['data']['diff'])} 条数据")
        else:
            print(f"   ⚠️  失败: {response.text[:200]}")

    except Exception as e:
        print(f"   ❌ 异常: {str(e)[:100]}")

    print()

print("=" * 80)
print("💡 测试HTTPS:")
print("=" * 80)

# 测试HTTPS协议
https_url = url.replace('http://', 'https://')
print(f"URL: {https_url}")
print()

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    response = session.get(https_url, params=params, timeout=15, verify=False)

    print(f"✅ 状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if 'data' in data and 'diff' in data['data']:
            print(f"✅ 成功！获取到 {len(data['data']['diff'])} 条数据")
    else:
        print(f"⚠️  失败: {response.text[:200]}")

except Exception as e:
    print(f"❌ 异常: {str(e)[:100]}")

print()
print("=" * 80)
print("💡 结论:")
print("   如果HTTPS也失败，可能是:")
print("   1. 东财API需要在交易时间访问")
print("   2. 当前网络环境无法访问东财API")
print("   3. 需要使用其他数据源")
print("=" * 80)