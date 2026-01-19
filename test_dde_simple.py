#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试 DDE 适配器
"""

import sys

try:
    import akshare as ak
    print("✅ akshare 已安装")
except ImportError:
    print("❌ akshare 未安装，请运行: pip install akshare")
    sys.exit(1)

try:
    from logic.data_adapter_akshare import MoneyFlowAdapter
    print("✅ MoneyFlowAdapter 已导入")
except ImportError as e:
    print(f"❌ 导入 MoneyFlowAdapter 失败: {e}")
    sys.exit(1)

# 测试获取资金流排名
print("\n正在测试获取资金流排名数据...")
try:
    df = ak.stock_individual_fund_flow_rank(indicator="今日")
    if df is not None and not df.empty:
        print(f"✅ 成功获取资金流排名数据，共 {len(df)} 只股票")
        print(f"\n列名: {list(df.columns)}")
        print(f"\n前 3 行数据:")
        print(df.head(3))
    else:
        print("❌ 获取资金流排名数据失败")
except Exception as e:
    print(f"❌ 获取资金流排名数据时出错: {e}")

print("\n测试完成！")