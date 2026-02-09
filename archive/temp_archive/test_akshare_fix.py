#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复后的AkShare连通性测试
关键：在Session实例上显式禁用代理
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("🔍 修复后的AkShare连通性测试")
print("=" * 80)
print()

# Step 1: 清空环境变量
print("Step 1: 清空环境变量")
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
print("✅ 已清空代理环境变量")

print()

# Step 2: Monkey patch requests.Session.__init__ 来禁用代理
print("Step 2: 修复requests.Session代理设置")
import requests

original_init = requests.Session.__init__

def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    # 关键：在Session实例上禁用代理
    self.trust_env = False
    self.proxies = {
        'http': None,
        'https': None,
        'no_proxy': '*'
    }

requests.Session.__init__ = patched_init
print("✅ 已patch Session类，所有新实例都会禁用代理")

print()

# Step 3: 测试AkShare
print("Step 3: 测试AkShare接口")
print()

try:
    import akshare as ak

    print("   📥 正在获取全A股基础信息...")
    stock_info = ak.stock_zh_a_spot_em()

    print(f"✅ 获取成功！共 {len(stock_info)} 只股票")
    print()
    print("   数据列名:")
    for col in stock_info.columns:
        print(f"      - {col}")

    print()
    print("   示例数据（前5只）:")
    print(stock_info.head(5)[['代码', '名称', '最新价', '总股本', '流通股']].to_string(index=False))

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
    print("💡 如果仍然失败，可能需要:")
    print("   1. 检查系统代理设置（Windows 代理设置）")
    print("   2. 检查VPN/代理软件是否开启")
    print("   3. 尝试使用代理而不是禁用代理")
    print("=" * 80)