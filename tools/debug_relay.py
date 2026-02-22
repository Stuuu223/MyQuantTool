#!/usr/bin/env python3
"""调试跨日接力引擎"""

import sys
sys.path.insert(0, 'E:\\MyQuantTool')

from datetime import datetime

# 测试日期解析
mem_date_str = '20251231'
current_date_str = '20260105'

mem_date = datetime.strptime(mem_date_str, '%Y%m%d')
current = datetime.strptime(current_date_str, '%Y%m%d')

days_diff = (current - mem_date).days

print(f"记忆日期: {mem_date_str} -> {mem_date}")
print(f"当前日期: {current_date_str} -> {current}")
print(f"天数差: {days_diff}")
print(f"是否<=3天: {days_diff <= 3}")
print(f"是否>0天: {days_diff > 0}")
