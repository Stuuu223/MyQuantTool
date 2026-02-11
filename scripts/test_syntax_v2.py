#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试语法修复（版本2）"""

# 测试1：双引号结尾
code1 = """
result = {
    'status': 'WARNING',
    'message': f'数据时间滞后 {x:.0f} 分钟',
    'data_mode': 'LOCAL_FILE'
}
"""

print("测试1：双引号结尾")
try:
    compile(code1, '<string>', 'exec')
    print("✅ 合法")
except SyntaxError as e:
    print(f"❌ 非法: {e}")

# 测试2：单引号结尾
code2 = """
result = {
    'status': 'WARNING',
    'message': f'数据时间滞后 {x:.0f} 分钟',
    'data_mode': 'LOCAL_FILE'
}
"""

print("\n测试2：单引号结尾")
try:
    compile(code2, '<string>', 'exec')
    print("✅ 合法")
except SyntaxError as e:
    print(f"❌ 非法: {e}")