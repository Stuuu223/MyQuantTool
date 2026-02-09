#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模拟浏览器访问东财API
"""

import requests
import json

print("=" * 80)
print("🔍 模拟浏览器访问东财API")
print("=" * 80)
print()

# 测试不同的请求头配置
test_configs = [
    {
        'name': '简单User-Agent',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    },
    {
        'name': '完整浏览器头',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://quote.eastmoney.com/',
            'Connection': 'keep-alive'
        }
    },
    {
        'name': '移动端User-Agent',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
        }
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
    print(f"   请求头: {config['headers']}")

    try:
        session = requests.Session()
        session.headers.update(config['headers'])

        response = session.get(url, params=params, timeout=15)

        print(f"   状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'diff' in data['data']:
                print(f"   ✅ 成功！获取到 {len(data['data']['diff'])} 条数据")
                # 打印前几条
                for item in data['data']['diff'][:3]:
                    print(f"      - {item.get('f12', 'N/A')}: {item.get('f14', 'N/A')} 价格: {item.get('f2', 'N/A')}")
            else:
                print(f"   ✅ 成功但数据格式不同")
        else:
            print(f"   ⚠️  失败: {response.text[:200]}")

    except Exception as e:
        print(f"   ❌ 异常: {str(e)[:100]}")

    print()

print("=" * 80)
print("💡 如果所有配置都失败，建议:")
print("   1. 在交易时间测试（可能是时间限制）")
print("   2. 使用其他数据源")
print("   3. 使用MVP本地数据验证逻辑")
print("=" * 80)