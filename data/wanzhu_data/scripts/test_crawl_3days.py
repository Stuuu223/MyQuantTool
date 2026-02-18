#!/usr/bin/env python3
"""
测试采集 - 最近3天
"""

import sys
sys.path.insert(0, '/root/wanzhu_data')

from crawl_history_safe import SafeStockCollector
from datetime import datetime, timedelta

# 采集最近3天
end_date = datetime.now()
start_date = end_date - timedelta(days=3)

start_str = start_date.strftime("%Y%m%d")
end_str = end_date.strftime("%Y%m%d")

print(f"测试采集: {start_str} 至 {end_str}")
print("=" * 60)

collector = SafeStockCollector()
df = collector.crawl_date_range(start_str, end_str)

if df is not None:
    print("\n✓ 测试成功!")
    print(f"共采集 {len(df)} 条数据")
    print("\n数据预览:")
    print(df[['date', 'code', 'name', 'sector', 'limit_up_days']].head(10))
