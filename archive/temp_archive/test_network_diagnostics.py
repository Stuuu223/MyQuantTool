#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络诊断 - 测试不同的连接方式
"""

import sys
import os
import socket

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("🔍 网络诊断")
print("=" * 80)
print()

# Step 1: DNS解析测试
print("Step 1: DNS解析测试")
test_domains = [
    ('eastmoney.com', '东财主域名'),
    ('quote.eastmoney.com', '东财行情域名'),
    ('www.baidu.com', '百度（对照）'),
]

for domain, desc in test_domains:
    try:
        ip = socket.gethostbyname(domain)
        print(f"   ✅ {desc:20} -> {ip}")
    except Exception as e:
        print(f"   ❌ {desc:20} -> DNS解析失败: {e}")

print()

# Step 2: 端口连通性测试
print("Step 2: 端口连通性测试")
test_ports = [
    ('quote.eastmoney.com', 80, 'HTTP'),
    ('quote.eastmoney.com', 443, 'HTTPS'),
]

for host, port, protocol in test_ports:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"   ✅ {host}:{port} ({protocol}) - 可连通")
        else:
            print(f"   ❌ {host}:{port} ({protocol}) - 连接失败 (code: {result})")
    except Exception as e:
        print(f"   ❌ {host}:{port} ({protocol}) - 异常: {e}")

print()

# Step 3: 测试其他AkShare接口
print("Step 3: 测试其他AkShare接口")
print()

try:
    import akshare as ak
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    # 配置重试策略
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # 测试1: 获取上证指数
    print("   测试1: 获取上证指数")
    try:
        index_data = ak.stock_zh_index_spot_em()
        sh_index = index_data[index_data['代码'] == '000001']
        if not sh_index.empty:
            print(f"      ✅ 成功！上证指数: {sh_index.iloc[0]['最新价']}")
        else:
            print(f"      ⚠️  成功但未找到上证指数")
    except Exception as e:
        print(f"      ❌ 失败: {e}")

    print()

    # 测试2: 获取部分股票（限制数量）
    print("   测试2: 获取部分股票信息（限制100只）")
    try:
        stock_info = ak.stock_zh_a_spot_em()
        print(f"      ✅ 成功！获取到 {len(stock_info)} 只股票")
        print(f"      前3只: {stock_info.head(3)[['代码', '名称', '最新价']].to_string(index=False)}")
    except Exception as e:
        print(f"      ❌ 失败: {e}")

    print()

    # 测试3: 使用curl测试（如果有）
    print("   测试3: 使用Python requests直接测试")
    try:
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
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
        response = session.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'diff' in data['data']:
                print(f"      ✅ 成功！获取到 {len(data['data']['diff'])} 只股票")
            else:
                print(f"      ✅ 成功！但数据格式不同")
        else:
            print(f"      ⚠️  状态码: {response.status_code}")
    except Exception as e:
        print(f"      ❌ 失败: {e}")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    print(traceback.format_exc())

print()
print("=" * 80)