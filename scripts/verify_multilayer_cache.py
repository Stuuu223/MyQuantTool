#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证多层回退逻辑的缓存命中率
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.fund_flow_analyzer import FundFlowAnalyzer
import time

def verify_cache_hit_rate():
    """验证缓存命中率"""
    
    analyzer = FundFlowAnalyzer(enable_cache=True)
    
    # 测试股票列表（热门池）
    test_stocks = [
        '002517.SZ', '600482.SH', '603138.SH', '600292.SH', '300767.SZ',
        '603968.SH', '600545.SH', '600299.SH', '300384.SZ', '601921.SH'
    ]
    
    print('=' * 80)
    print('🔍 验证多层回退逻辑的缓存命中率')
    print('=' * 80)
    
    # 第一轮：首次查询（应该全部缓存未命中）
    print('\n[第一轮] 首次查询（应该全部缓存未命中）')
    print('-' * 80)
    
    first_round_cache_hits = 0
    first_round_start = time.time()
    
    for stock in test_stocks:
        result = analyzer.get_fund_flow(stock, days=5)
        from_cache = result.get('from_cache', False)
        cache_date = result.get('cache_date', 'N/A')
        
        if from_cache:
            first_round_cache_hits += 1
        
        status = "✅" if from_cache else "❌"
        print(f"{status} {stock}: 缓存={from_cache}, 缓存日期={cache_date}")
    
    first_round_time = time.time() - first_round_start
    
    # 第二轮：立即重复查询（应该全部缓存命中）
    print('\n[第二轮] 立即重复查询（应该全部缓存命中）')
    print('-' * 80)
    
    second_round_cache_hits = 0
    second_round_start = time.time()
    
    for stock in test_stocks:
        result = analyzer.get_fund_flow(stock, days=5)
        from_cache = result.get('from_cache', False)
        cache_date = result.get('cache_date', 'N/A')
        
        if from_cache:
            second_round_cache_hits += 1
        
        status = "✅" if from_cache else "❌"
        print(f"{status} {stock}: 缓存={from_cache}, 缓存日期={cache_date}")
    
    second_round_time = time.time() - second_round_start
    
    # 测试结果汇总
    print('\n' + '=' * 80)
    print('📊 测试结果汇总')
    print('=' * 80)
    
    print(f'总测试数: {len(test_stocks)}')
    print()
    print(f'第一轮（首次查询）:')
    print(f'  缓存命中: {first_round_cache_hits}/{len(test_stocks)} ({first_round_cache_hits/len(test_stocks)*100:.1f}%)')
    print(f'  耗时: {first_round_time:.2f}秒')
    print(f'  平均耗时: {first_round_time/len(test_stocks)*1000:.1f}毫秒/只')
    print()
    print(f'第二轮（重复查询）:')
    print(f'  缓存命中: {second_round_cache_hits}/{len(test_stocks)} ({second_round_cache_hits/len(test_stocks)*100:.1f}%)')
    print(f'  耗时: {second_round_time:.2f}秒')
    print(f'  平均耗时: {second_round_time/len(test_stocks)*1000:.1f}毫秒/只')
    print()
    
    # 性能对比
    if second_round_time > 0:
        speedup = first_round_time / second_round_time
        print(f'性能提升: {speedup:.1f}倍')
    
    # 验证资金流数据
    print('=' * 80)
    print('🔍 验证资金流数据')
    print('=' * 80)
    
    sample_stock = test_stocks[0]
    data = analyzer.get_fund_flow(sample_stock, days=5)
    
    if 'error' not in data and data.get('latest'):
        latest = data['latest']
        main_net = latest.get('main_net_inflow', 'N/A')
        
        print(f'示例股票: {sample_stock}')
        print(f'  main_net_inflow: {main_net:.0f}' if main_net != 'N/A' else f'  main_net_inflow: {main_net}')
        print(f'  from_cache: {data.get("from_cache", False)}')
        print(f'  cache_date: {data.get("cache_date", "N/A")}')
        
        if main_net != 'N/A' and main_net != 0:
            print(f'  ✅ 资金流数据正常')
        else:
            print(f'  ❌ 资金流数据异常（为0）')
    else:
        print(f'❌ 数据获取失败')
    
    print('=' * 80)

if __name__ == "__main__":
    verify_cache_hit_rate()
