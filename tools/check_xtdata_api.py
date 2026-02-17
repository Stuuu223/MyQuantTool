#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查 xtdata.download_history_data 的参数
"""

from xtquant import xtdata
import inspect

print("=" * 60)
print("🔍 检查 xtdata.download_history_data 函数签名")
print("=" * 60)

# 获取函数签名
try:
    sig = inspect.signature(xtdata.download_history_data)
    print(f"✅ 函数签名: {sig}")
    print(f"✅ 参数列表:")
    for name, param in sig.parameters.items():
        print(f"   - {name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'any'}")
except Exception as e:
    print(f"❌ 获取函数签名失败: {e}")

# 尝试调用 help()
print("\n📋 函数帮助文档:")
try:
    help(xtdata.download_history_data)
except Exception as e:
    print(f"❌ 获取帮助文档失败: {e}")