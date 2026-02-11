#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证资金流缓存修复效果

测试缓存键不匹配Bug是否修复成功
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from logic.fund_flow_analyzer import FundFlowAnalyzer

def main():
    analyzer = FundFlowAnalyzer(enable_cache=True)
    
    # 测试股票列表
    test_stocks = ['600519', '000858', '002475']
    
    print("=" * 80)
    print("🧪 P0缓存修复验证测试")
    print(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 第一轮：应该全部缓存未命中
    print("\n[第一轮] 清空缓存后首次查询（应全部未命中）")
    for stock in test_stocks:
        result = analyzer.get_fund_flow_cached(stock)
        latest = result.get('latest', {})
        from_cache = result.get('from_cache', False)
        data_date = latest.get('date', 'N/A')
        
        print(f"  {stock}: 数据日期={data_date}, 缓存={from_cache}")
    
    # 第二轮：应该全部缓存命中
    print("\n[第二轮] 立即重复查询（应全部命中）")
    pass_count = 0
    for stock in test_stocks:
        result = analyzer.get_fund_flow_cached(stock)
        latest = result.get('latest', {})
        from_cache = result.get('from_cache', False)
        data_date = latest.get('date', 'N/A')
        cache_date = result.get('cache_date', 'N/A')
        
        status = "✅ PASS" if from_cache else "❌ FAIL"
        if from_cache:
            pass_count += 1
        print(f"  {stock}: 数据日期={data_date}, 缓存键={cache_date}, 命中={from_cache} {status}")
    
    # 测试结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    print(f"总测试数: {len(test_stocks)}")
    print(f"通过数: {pass_count}")
    print(f"通过率: {pass_count/len(test_stocks)*100:.1f}%")
    
    if pass_count == len(test_stocks):
        print("\n✅ P0修复验证通过！缓存系统正常工作")
    else:
        print(f"\n❌ P0修复验证失败！有 {len(test_stocks) - pass_count} 个测试未通过")
    
    print("=" * 80)

if __name__ == "__main__":
    main()