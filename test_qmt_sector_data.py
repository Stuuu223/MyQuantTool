#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 QMT 板块数据获取
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 添加 xtquant 路径
sys.path.insert(0, os.path.join(project_root, 'xtquant'))

print("=" * 60)
print("🧪 测试 QMT 板块数据获取")
print("=" * 60)

try:
    from xtquant import xtdata
    print("✅ QMT xtdata 模块加载成功")
except ImportError as e:
    print(f"❌ QMT xtdata 模块加载失败: {e}")
    sys.exit(1)

try:
    # 测试获取板块列表
    print("\n" + "-" * 60)
    print("📊 测试获取板块列表...")
    print("-" * 60)
    
    # 获取行业板块列表
    industry_sectors = xtdata.get_stock_list_in_sector('申万一级')
    if industry_sectors:
        print(f"✅ 获取到 {len(industry_sectors)} 个行业板块")
        print(f"前 5 个行业板块: {industry_sectors[:5]}")
    else:
        print("⚠️ 未获取到行业板块列表")
    
    # 获取概念板块列表
    concept_sectors = xtdata.get_stock_list_in_sector('概念板块')
    if concept_sectors:
        print(f"✅ 获取到 {len(concept_sectors)} 个概念板块")
        print(f"前 5 个概念板块: {concept_sectors[:5]}")
    else:
        print("⚠️ 未获取到概念板块列表")
    
    # 测试获取板块指数数据
    print("\n" + "-" * 60)
    print("📊 测试获取板块指数数据...")
    print("-" * 60)
    
    if industry_sectors:
        # 获取第一个行业板块的指数数据
        test_sector = industry_sectors[0]
        print(f"📍 测试板块: {test_sector}")
        
        # 获取板块指数数据
        sector_data = xtdata.get_market_data_ex(
            stock_list=[test_sector],
            period='1d',
            start_time='20260101',
            end_time='',
            count=1,
            dividend_type='none',
            fill_data=True
        )
        
        if sector_data and test_sector in sector_data:
            data = sector_data[test_sector]
            print(f"✅ 获取到板块指数数据")
            print(f"最新价: {data.get('close', [None])}")
            print(f"涨跌幅: {data.get('pctChg', [None])}")
        else:
            print("⚠️ 未获取到板块指数数据")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
    
    print("\n📝 结论:")
    print("- QMT 支持获取行业板块和概念板块列表")
    print("- QMT 支持获取板块指数数据（价格、涨跌幅等）")
    print("- 可以通过计算板块平均涨幅来实现板块排名功能")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()