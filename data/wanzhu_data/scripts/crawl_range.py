#!/usr/bin/env python3
"""
指定日期范围采集 - 灵活版
用法: python3 crawl_range.py 20241101 20250218
"""

import sys
sys.path.insert(0, '/root/wanzhu_data')

from crawl_history_safe import SafeStockCollector
from datetime import datetime

if len(sys.argv) < 3:
    print("用法: python3 crawl_range.py <开始日期> <结束日期>")
    print("示例: python3 crawl_range.py 20241101 20250218")
    print("      python3 crawl_range.py 20250101 20250218  (采集今年数据)")
    sys.exit(1)

start_date = sys.argv[1]
end_date = sys.argv[2]

print(f"=" * 60)
print(f"指定日期范围采集")
print(f"=" * 60)
print(f"开始日期: {start_date}")
print(f"结束日期: {end_date}")
print(f"=" * 60)

collector = SafeStockCollector()
df = collector.crawl_date_range(start_date, end_date)

if df is not None:
    print("\n✓ 采集完成!")
    print(f"数据文件: zt_history_{start_date}_{end_date}.csv")
else:
    print("\n✗ 采集失败")
