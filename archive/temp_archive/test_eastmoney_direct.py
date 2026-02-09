#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试东财API
"""

import requests
import json
import time

print("=" * 80)
print("🔍 直接测试东财API")
print("=" * 80)
print()

# 测试不同的东财接口
test_cases = [
    {
        'name': '东财实时行情接口',
        'url': 'http://push2.eastmoney.com/api/qt/clist/get',
        'params': {
            'pn': 1,
            'pz': 10,
            'po': 1,
            'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'
        }
    },
    {
        'name': '东财指数接口',
        'url': 'http://push2.eastmoney.com/api/qt/clist/get',
        'params': {
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
    },
    {
        'name': '东财首页',
        'url': 'https://www.eastmoney.com/',
        'params': {}
    }
]

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

for idx, test_case in enumerate(test_cases, 1):
    print(f"测试 {idx}: {test_case['name']}")
    print(f"   URL: {test_case['url']}")

    try:
        response = session.get(
            test_case['url'],
            params=test_case['params'],
            timeout=15
        )

        print(f"   ✅ 状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                if 'data' in data and 'diff' in data['data']:
                    print(f"   ✅ 获取数据成功: {len(data['data']['diff'])} 条")
                elif 'data' in data:
                    print(f"   ✅ 获取数据成功（格式不同）")
                else:
                    print(f"   ✅ 获取成功，但无数据字段")
            except:
                print(f"   ✅ 获取成功（非JSON响应，长度: {len(response.text)} 字符）")
        else:
            print(f"   ⚠️  响应: {response.text[:200]}")

    except requests.exceptions.Timeout:
        print(f"   ❌ 超时")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ 连接错误: {str(e)[:100]}")
    except Exception as e:
        print(f"   ❌ 异常: {str(e)[:100]}")

    print()

print("=" * 80)
print("💡 结论:")
print("   如果所有接口都失败，可能是:")
print("   1. 东财服务器维护或限流")
print("   2. 网络连接问题（DNS、防火墙等）")
print("   3. 需要在交易时间访问")
print("=" * 80)