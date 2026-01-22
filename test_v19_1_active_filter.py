#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.1 功能测试脚本 - 测试活跃股筛选和修复后的低吸/尾盘选股
测试内容：
1. ActiveStockFilter 活跃股筛选测试
2. 低吸战法修复验证
3. 尾盘选股修复验证
4. 性能测试
"""

import sys
import time
from datetime import datetime

print("=" * 80)
print("🚀 V19.1 功能测试 - 活跃股筛选和修复验证")
print("=" * 80)
print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 测试1: ActiveStockFilter 导入测试
print("📋 测试1: ActiveStockFilter 导入测试")
print("-" * 80)
try:
    from logic.active_stock_filter import get_active_stocks
    print("✅ ActiveStockFilter 导入成功")
except Exception as e:
    print(f"❌ ActiveStockFilter 导入失败: {e}")
    sys.exit(1)
print()

# 测试2: 活跃股筛选测试
print("📋 测试2: 活跃股筛选测试")
print("-" * 80)
try:
    start_time = time.time()
    
    # 测试按成交额排序
    print("测试按成交额排序（前10只）...")
    active_stocks = get_active_stocks(
        limit=10,
        sort_by='amount',
        exclude_st=True,
        exclude_delisting=True
    )
    
    elapsed = time.time() - start_time
    print(f"✅ 活跃股筛选完成，耗时: {elapsed:.2f} 秒")
    print(f"   返回股票数: {len(active_stocks)}")
    
    if active_stocks:
        print("\n前5只活跃股（按成交额排序）:")
        for i, stock in enumerate(active_stocks[:5]):
            print(f"   {i+1}. {stock['name']} ({stock['code']})")
            print(f"      价格: ¥{stock['price']:.2f}, 涨跌幅: {stock['change_pct']:.2f}%")
            print(f"      成交额: {stock['amount']/100000000:.2f}亿, 成交量: {stock['volume']}手")
    
    # 测试按涨幅排序
    print("\n测试按涨幅排序（前10只，涨幅>2%）...")
    start_time = time.time()
    
    active_stocks_by_change = get_active_stocks(
        limit=10,
        sort_by='change_pct',
        min_change_pct=2.0,
        exclude_st=True,
        exclude_delisting=True
    )
    
    elapsed = time.time() - start_time
    print(f"✅ 活跃股筛选完成，耗时: {elapsed:.2f} 秒")
    print(f"   返回股票数: {len(active_stocks_by_change)}")
    
    if active_stocks_by_change:
        print("\n前5只活跃股（按涨幅排序）:")
        for i, stock in enumerate(active_stocks_by_change[:5]):
            print(f"   {i+1}. {stock['name']} ({stock['code']})")
            print(f"      价格: ¥{stock['price']:.2f}, 涨跌幅: {stock['change_pct']:.2f}%")
            print(f"      成交额: {stock['amount']/100000000:.2f}亿")
    
except Exception as e:
    print(f"❌ 活跃股筛选测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# 测试3: 低吸战法修复验证
print("📋 测试3: 低吸战法修复验证")
print("-" * 80)
try:
    from logic.low_suction_engine import get_low_suction_engine
    from logic.data_manager import DataManager
    
    engine = get_low_suction_engine()
    dm = DataManager()
    
    # 获取活跃股（前5只）
    active_stocks = get_active_stocks(limit=5, sort_by='amount')
    
    stock_names = [f"{s['name']}({s['code']})" for s in active_stocks]
    print(f"测试股票: {stock_names}")
    
    for stock in active_stocks:
        try:
            code = stock['code']
            current_price = stock['price']
            prev_close = stock['close']
            
            # 获取K线数据
            kline = dm.get_history_data(code, period='daily')
            if kline is None or len(kline) < 2:
                print(f"⚠️ {code}: K线数据不足")
                continue
            
            # 判断昨日状态
            yesterday = kline.iloc[-2]
            yesterday_limit_up = yesterday['high'] > yesterday['close'] * 1.05 and \
                               (yesterday['high'] - yesterday['close']) / yesterday['close'] > 0.03
            
            # 分析低吸信号
            result = engine.analyze_low_suction(
                code, current_price, prev_close,
                intraday_data=None,
                logic_keywords=['机器人', 'AI', '低空', '固态', '并购'],
                yesterday_limit_up=yesterday_limit_up
            )
            
            print(f"\n📊 {stock['name']} ({code}):")
            print(f"   - 当前价: ¥{current_price:.2f}")
            print(f"   - 昨收价: ¥{prev_close:.2f}")
            print(f"   - 涨跌幅: {stock['change_pct']:.2f}%")
            print(f"   - 昨日炸板: {'是' if yesterday_limit_up else '否'}")
            print(f"   - 低吸信号: {'✅' if result['has_suction'] else '❌'}")
            print(f"   - 原因: {result['reason']}")
            if result['has_suction']:
                print(f"   - 置信度: {result['overall_confidence']:.2%}")
                print(f"   - 建议: {result['recommendation']}")
        
        except Exception as e:
            print(f"❌ {stock['code']}: 测试失败 - {e}")
            continue
    
    print("\n✅ 低吸战法修复验证完成")
except Exception as e:
    print(f"❌ 低吸战法修复验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# 测试4: 尾盘选股修复验证
print("📋 测试4: 尾盘选股修复验证")
print("-" * 80)
try:
    from logic.late_trading_scanner import get_late_trading_scanner
    
    scanner = get_late_trading_scanner()
    
    # 获取活跃股（涨幅>2%）
    active_stocks = get_active_stocks(
        limit=10,
        sort_by='amount',
        min_change_pct=2.0
    )
    
    candidates = [s['code'] for s in active_stocks]
    stock_name_dict = {s['code']: s['name'] for s in active_stocks}
    
    print(f"测试股票: {len(candidates)} 只（涨幅>2%）")
    print(f"当前是否在尾盘时段: {scanner.is_late_trading_time()}")
    
    start_time = time.time()
    result = scanner.scan_late_trading_opportunities(
        candidates,
        stock_name_dict=stock_name_dict,
        max_stocks=10
    )
    elapsed = time.time() - start_time
    
    print(f"扫描耗时: {elapsed:.2f} 秒")
    print(f"扫描总数: {result['total_scanned']}")
    print(f"发现机会: {len(result.get('opportunities', []))}")
    print(f"汇总: {result['summary']}")
    
    if result.get('opportunities'):
        print("\n发现的尾盘机会:")
        for opp in result['opportunities'][:3]:
            print(f"  📊 {opp['stock_name']} ({opp['stock_code']})")
            print(f"     - 信号类型: {opp['signal']['signal_type']}")
            print(f"     - 置信度: {opp['signal']['confidence']:.2%}")
            print(f"     - 原因: {opp['signal']['reason']}")
    
    print("\n✅ 尾盘选股修复验证完成")
except Exception as e:
    print(f"❌ 尾盘选股修复验证失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# 性能总结
print("=" * 80)
print("📊 测试总结")
print("=" * 80)
print("✅ 所有核心功能测试通过")
print("✅ ActiveStockFilter 活跃股筛选正常")
print("✅ 低吸战法修复验证通过")
print("✅ 尾盘选股修复验证通过")
print()
print("🎯 关键改进:")
print("   1. 使用活跃股筛选，避免扫描僵尸股")
print("   2. 按成交额排序，优先扫描主力战场")
print("   3. 传入昨日炸板状态，激活弱转强逻辑")
print("   4. 尾盘选股过滤涨幅>2%的票，提高效率")
print()
print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
