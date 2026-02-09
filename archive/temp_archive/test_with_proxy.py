#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试使用代理连接
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("🔍 测试使用代理连接")
print("=" * 80)
print()

# Step 1: 检查代理是否可用
print("Step 1: 测试代理连接")
proxy_url = "http://127.0.0.1:7897"

import requests

try:
    # 通过代理访问百度
    response = requests.get(
        'https://www.baidu.com',
        proxies={'http': proxy_url, 'https': proxy_url},
        timeout=10
    )
    print(f"✅ 代理可用！状态码: {response.status_code}")
except Exception as e:
    print(f"❌ 代理不可用: {e}")
    sys.exit(1)

print()

# Step 2: 通过代理访问AkShare
print("Step 2: 通过代理访问AkShare")

try:
    import akshare as ak

    # 临时修改AkShare的请求函数使用代理
    import akshare.utils.request as ak_request
    original_request = ak_request.request_with_retry

    def request_with_proxy(url, params=None, method="get", timeout=10, max_retries=3):
        return original_request(
            url, params=params, method=method, timeout=timeout,
            max_retries=max_retries,
            proxies={'http': proxy_url, 'https': proxy_url}
        )

    ak_request.request_with_retry = request_with_proxy

    print("   📥 正在通过代理获取全A股基础信息...")
    stock_info = ak.stock_zh_a_spot_em()

    print(f"✅ 获取成功！共 {len(stock_info)} 只股票")
    print()
    print("   示例数据（前5只）:")
    print(stock_info.head(5)[['代码', '名称', '最新价', '总股本', '流通股']].to_string(index=False))

    print()
    print("=" * 80)
    print("🎉 通过代理连接成功！")
    print("=" * 80)

except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    print()
    print("详细错误信息:")
    print(traceback.format_exc())
    print()
    print("=" * 80)
    print("💡 结论:")
    print("   如果代理也失败，说明问题可能是:")
    print("   1. 东财服务器对当前时段/地区限制访问")
    print("   2. 需要更换代理或等待其他时段")
    print("   3. 考虑使用其他数据源（如Tushare）")
    print("=" * 80)