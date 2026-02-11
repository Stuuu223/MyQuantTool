#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试语法修复"""

# 这是一个合法的 Python 语法
line1 = "'message': f'数据时间滞后 {time_diff/60:.0f} 分钟，可能是本地文件模式（探测标的: {valid_code}）\","
line2 = "'message': f'数据时间滞后 {time_diff/60:.0f} 分钟，可能是本地文件模式（探测标的: {valid_code}）',"

print("line1 合法吗？")
try:
    compile(line1, '<string>', 'eval')
    print("✅ line1 合法")
except SyntaxError as e:
    print(f"❌ line1 非法: {e}")

print("\nline2 合法吗？")
try:
    compile(line2, '<string>', 'eval')
    print("✅ line2 合法")
except SyntaxError as e:
    print(f"❌ line2 非法: {e}")