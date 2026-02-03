#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试AkShare实时行情接口"""

import os

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['NO_PROXY'] = '*'

import akshare as ak

try:
    print("🔍 测试 stock_zh_a_spot_em()...")
    df = ak.stock_zh_a_spot_em()
    
    print(f"✅ 成功！共 {len(df)} 只股票")
    print(f"\n字段列表: {df.columns.tolist()}")
    
    # 查找300997
    stock_data = df[df['代码'] == '300997']
    
    if not stock_data.empty:
        row = stock_data.iloc[0]
        print(f"\n📊 300997 实时数据:")
        print(f"  最新价: {row['最新价']}")
        print(f"  涨跌幅: {row['涨跌幅']}%")
        print(f"  成交量: {row['成交量']}")
        print(f"  今开: {row['今开']}")
        print(f"  最高: {row['最高']}")
        print(f"  最低: {row['最低']}")
        print(f"  换手率: {row.get('换手率', 'N/A')}")
        print(f"  买一价: {row.get('买一价', 'N/A')}")
        print(f"  买一量: {row.get('买一量', 'N/A')}")
        print(f"  卖一价: {row.get('卖一价', 'N/A')}")
        print(f"  卖一量: {row.get('卖一量', 'N/A')}")
        
        # 计算买卖压力
        bid_vol = sum([int(row.get(f'买{i}量', 0)) for i in range(1, 6)])
        ask_vol = sum([int(row.get(f'卖{i}量', 0)) for i in range(1, 6)])
        if ask_vol == 0:
            pressure = 1.0 if bid_vol > 0 else 0.0
        else:
            pressure = (bid_vol - ask_vol) / (bid_vol + ask_vol)
        print(f"\n💰 买卖压力: {pressure:.2f}")
    else:
        print("❌ 未找到300997")
        
except Exception as e:
    print(f"❌ 失败: {e}")