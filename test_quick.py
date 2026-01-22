# -*- coding: utf-8 -*-
"""
快速测试：直接查看半路战法返回的JSON
"""
from logic.algo import QuantAlgo
import json

print("开始扫描...")
result = QuantAlgo.scan_halfway_stocks(limit=3, min_score=30)

print("\n" + "=" * 80)
print("返回的JSON:")
print("=" * 80)
print(json.dumps(result, ensure_ascii=False, indent=2))