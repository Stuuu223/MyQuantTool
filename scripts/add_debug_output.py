#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在 check_all() 返回前添加调试输出"""

import os

file_path = 'logic/qmt_health_check.py'

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 "self._print_result(result)" 这一行（应该是第119行）
for i, line in enumerate(lines):
    if "self._print_result(result)" in line:
        # 在这一行之前添加调试输出
        debug_output = """        # 🔥 [调试] 输出完整结果
        import json
        logger.info(f"DEBUG: result['status'] = {result['status']}")
        logger.info(f"DEBUG: result['recommendations'] = {result['recommendations']}")
        for check_name, check_result in result['details'].items():
            logger.info(f"DEBUG: {check_name}: status={check_result.get('status')}, message={check_result.get('message', 'N/A')}")
        logger.info("=" * 80)
"""
        lines.insert(i, debug_output)
        print(f"✅ 在第{i+1}行之前添加调试输出")
        break

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ 调试输出已添加")

# 验证语法
import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("✅ 语法检查通过")
except SyntaxError as e:
    print(f"❌ 语法错误: {e}")