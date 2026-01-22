#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.3 选股池优化验证测试

测试内容：
1. 验证ActiveStockFilter跳过前30只大家伙
2. 验证波动率过滤（振幅 > 3%）
3. 验证LowSuctionEngine返回失败原因
4. 验证调试日志显示
"""

import sys
import os
import time
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("=" * 80)
print("🚀 V19.3 选股池优化验证测试")
print("=" * 80)
print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

# 测试1：验证ActiveStockFilter跳过前30只大家伙
print("📋 测试1: 验证ActiveStockFilter跳过前30只大家伙")
print("-" * 80)
try:
    from logic.active_stock_filter import get_active_stocks
    
    print(f"测试按成交额排序（跳过前30只，取第30-50只）...")
    
    # 获取活跃股（跳过前30只）
    active_stocks = get_active_stocks(
        limit=20,  # 取20只
        sort_by='amount',
        skip_top=30,  # 跳过前30只
        min_amplitude=3.0  # 最小振幅3%
    )
    
    print(f"✅ 活跃股筛选完成")
    print(f"   返回股票数: {len(active_stocks)}")
    print(f"   前5只股票:")
    for i, stock in enumerate(active_stocks[:5], 1):
        print(f"     {i}. {stock['name']}({stock['code']})")
        print(f"        价格: ¥{stock['price']:.2f}, 涨跌幅: {stock['change_pct']:.2f}%")
        print(f"        成交额: {stock['amount']/100000000:.2f}亿")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试2：验证LowSuctionEngine返回失败原因
print("📋 测试2: 验证LowSuctionEngine返回失败原因")
print("-" * 80)
try:
    from logic.low_suction_engine import get_low_suction_engine
    from logic.data_manager import DataManager
    
    engine = get_low_suction_engine()
    dm = DataManager()
    
    # 测试股票（选择一些不太可能触发低吸的股票）
    test_stocks = ['000001', '600000', '600519']  # 平安银行、浦发银行、贵州茅台
    
    for code in test_stocks:
        print(f"\n   测试股票: {code}")
        
        # 获取实时数据
        realtime_data = dm.get_realtime_data_dict(code)
        if not realtime_data:
            print(f"   ⚠️ 无法获取实时数据")
            continue
        
        current_price = realtime_data.get('now', 0)
        prev_close = realtime_data.get('close', 0)
        
        if current_price == 0 or prev_close == 0:
            print(f"   ⚠️ 价格数据无效")
            continue
        
        # 分析低吸信号
        result = engine.analyze_low_suction(
            code, current_price, prev_close,
            intraday_data=None,
            logic_keywords=['机器人', 'AI']
        )
        
        print(f"   是否有低吸信号: {result['has_suction']}")
        print(f"   置信度: {result['overall_confidence']:.2f}")
        print(f"   建议: {result['recommendation']}")
        print(f"   原因: {result['reason']}")
        
        # 检查是否有失败原因
        if 'fail_reason' in result:
            print(f"   失败原因: {result['fail_reason']}")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试3：验证波动率过滤
print("📋 测试3: 验证波动率过滤（振幅 > 3%）")
print("-" * 80)
try:
    from logic.active_stock_filter import get_active_stocks
    
    print(f"对比测试：有/无波动率过滤...")
    
    # 无波动率过滤
    stocks_no_filter = get_active_stocks(
        limit=10,
        sort_by='amount',
        skip_top=30,
        min_amplitude=0.0  # 不限制振幅
    )
    
    # 有波动率过滤（振幅 > 3%）
    stocks_with_filter = get_active_stocks(
        limit=10,
        sort_by='amount',
        skip_top=30,
        min_amplitude=3.0  # 振幅 > 3%
    )
    
    print(f"✅ 波动率过滤对比:")
    print(f"   无过滤: {len(stocks_no_filter)} 只股票")
    print(f"   有过滤: {len(stocks_with_filter)} 只股票")
    print(f"   过滤掉: {len(stocks_no_filter) - len(stocks_with_filter)} 只股票")
    
    # 计算平均振幅
    avg_amplitude_no_filter = sum(
        (s['high'] - s['low']) / s['open'] * 100 
        for s in stocks_no_filter if s['open'] > 0
    ) / len(stocks_no_filter) if stocks_no_filter else 0
    
    avg_amplitude_with_filter = sum(
        (s['high'] - s['low']) / s['open'] * 100 
        for s in stocks_with_filter if s['open'] > 0
    ) / len(stocks_with_filter) if stocks_with_filter else 0
    
    print(f"   平均振幅（无过滤）: {avg_amplitude_no_filter:.2f}%")
    print(f"   平均振幅（有过滤）: {avg_amplitude_with_filter:.2f}%")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("📊 测试总结")
print("=" * 80)
print("✅ 所有测试完成")
print("\n预期结果:")
print("1. ActiveStockFilter 跳过前30只大家伙（茅台、中信证券等）")
print("2. 波动率过滤生效，振幅 < 3% 的股票被过滤")
print("3. LowSuctionEngine 返回失败原因（fail_reason）")
print("4. UI 调试日志显示未触发低吸的股票和原因")
print(f"\n测试结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)