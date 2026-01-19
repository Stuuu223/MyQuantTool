#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 V18.4 概念猎手性能
"""

import time
from logic.data_manager import DataManager
from logic.sector_analysis_streamlit import get_fast_sector_analyzer_streamlit

def test_v18_4_performance():
    """测试 V18.4 概念猎手性能"""
    print("=" * 80)
    print("🧪 V18.4 概念猎手性能测试")
    print("=" * 80)
    
    # 初始化
    db = DataManager()
    analyzer = get_fast_sector_analyzer_streamlit(db)
    
    # 测试 1: 测试概念信息为空的股票（应该跳过概念板块共振分析）
    print("\n📊 测试 1: 测试概念信息为空的股票")
    test_stock = "000001"  # 平安银行，概念可能为空
    
    # 首次调用（会触发概念板块数据获取）
    t_start = time.time()
    result = analyzer.check_stock_full_resonance(test_stock, "平安银行")
    t_cost = time.time() - t_start
    
    print(f"  耗时: {t_cost:.3f}秒")
    print(f"  共振评分: {result.get('resonance_score', 0)}")
    print(f"  共振详情: {result.get('resonance_details', [])}")
    
    # 测试 2: 测试概念信息不为空的股票
    print("\n📊 测试 2: 测试概念信息不为空的股票（如果有）")
    # 查找一个概念信息不为空的股票
    stock_with_concepts = None
    for stock_code, stock_info in analyzer._stock_sector_map.items():
        if stock_info.get('concepts') and len(stock_info.get('concepts', [])) > 0:
            stock_with_concepts = stock_code
            print(f"  找到概念信息不为空的股票: {stock_code}")
            print(f"  概念: {stock_info.get('concepts', [])}")
            break
    
    if stock_with_concepts:
        t_start = time.time()
        result = analyzer.check_stock_full_resonance(stock_with_concepts)
        t_cost = time.time() - t_start
        
        print(f"  耗时: {t_cost:.3f}秒")
        print(f"  共振评分: {result.get('resonance_score', 0)}")
        print(f"  共振详情: {result.get('resonance_details', [])}")
    else:
        print("  ⚠️  未找到概念信息不为空的股票")
    
    # 测试 3: 性能对比（多次调用，应该使用缓存）
    print("\n📊 测试 3: 性能对比（10次调用，使用缓存）")
    test_stocks = [
        ("000001", "平安银行"),
        ("000002", "万科A"),
        ("600000", "浦发银行"),
        ("600519", "贵州茅台"),
        ("300750", "宁德时代")
    ]
    
    total_time = 0
    for code, name in test_stocks:
        t_start = time.time()
        result = analyzer.check_stock_full_resonance(code, name)
        t_cost = time.time() - t_start
        total_time += t_cost
        print(f"  {code} {name}: {t_cost:.3f}秒")
    
    avg_time = total_time / len(test_stocks)
    print(f"  总耗时: {total_time:.3f}秒")
    print(f"  平均耗时: {avg_time:.3f}秒")
    
    # 测试 4: 检查是否还有 5.8秒延迟
    print("\n📊 测试 4: 检查是否还有 5.8秒延迟")
    if avg_time > 0.5:
        print(f"  ⚠️  平均耗时 {avg_time:.3f}秒 > 0.5秒，可能仍有延迟")
    else:
        print(f"  ✅ 平均耗时 {avg_time:.3f}秒 < 0.5秒，性能优秀")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_v18_4_performance()