#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试AkShare连通性
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("🔍 测试AkShare连通性")
print("=" * 80)
print()

# Step 1: 检查AkShare是否安装
print("Step 1: 检查AkShare是否安装")
try:
    import akshare as ak
    print("✅ AkShare已安装")
    print(f"   版本: {ak.__version__ if hasattr(ak, '__version__') else '未知'}")
except ImportError as e:
    print(f"❌ AkShare未安装: {e}")
    sys.exit(1)

print()

# Step 2: 检查代理设置
print("Step 2: 检查代理设置")
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'no_proxy']
for var in proxy_vars:
    value = os.environ.get(var, '未设置')
    status = "✅" if value in ['', '*', '未设置'] else "⚠️"
    print(f"   {status} {var} = {value}")

print()

# Step 3: 禁用代理（测试修复后的逻辑）
print("Step 3: 禁用代理")
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
print("✅ 已清空代理环境变量")

print()

# Step 4: 测试AkShare接口
print("Step 4: 测试AkShare接口")
print("   接口: stock_zh_a_spot_em()")
print("   说明: 获取A股实时行情（包含股本信息）")
print()

try:
    # 设置超时时间
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    # 配置重试策略
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # 尝试获取数据
    print("   ⏱️  正在请求东财数据...")
    stock_info = ak.stock_zh_a_spot_em()

    print(f"✅ 获取成功！共 {len(stock_info)} 只股票")
    print()
    print("   数据列名:")
    for col in stock_info.columns:
        print(f"      - {col}")

    print()
    print("   示例数据（前5只）:")
    print(stock_info.head(5).to_string(index=False))

    print()
    print("=" * 80)
    print("🎉 AkShare连通性测试通过！")
    print("=" * 80)

except Exception as e:
    print(f"❌ 获取失败: {e}")
    import traceback
    print()
    print("详细错误信息:")
    print(traceback.format_exc())
    print()
    print("=" * 80)
    print("💡 可能的原因:")
    print("   1. 网络连接不稳定")
    print("   2. 防火墙/安全软件阻止")
    print("   3. 东财服务器限流/拒绝连接")
    print("   4. 网络配置问题")
    print("=" * 80)