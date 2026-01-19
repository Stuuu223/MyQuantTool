#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调查 2 秒延迟的根源
"""

import time
from logic.data_manager import DataManager
from logic.sector_analysis_streamlit import get_fast_sector_analyzer_streamlit

def investigate_2_second_delay():
    """调查 2 秒延迟的根源"""
    print("=" * 80)
    print("🔍 调查 2 秒延迟的根源")
    print("=" * 80)
    
    # 初始化
    db = DataManager()
    analyzer = get_fast_sector_analyzer_streamlit(db)
    
    # 测试 1: 检查静态映射表中的概念信息
    print("\n📊 测试 1: 检查静态映射表中的概念信息")
    stock_code = "000001"
    sector_info = analyzer.get_stock_sector_info(stock_code)
    print(f"  股票: {stock_code}")
    print(f"  行业: {sector_info.get('industry', '未知')}")
    print(f"  概念: {sector_info.get('concepts', [])}")
    print(f"  概念数量: {len(sector_info.get('concepts', []))}")
    
    # 测试 2: 测试概念板块排名获取（首次）
    print("\n📊 测试 2: 测试概念板块排名获取（首次）")
    t_start = time.time()
    concept_ranking = analyzer.get_akshare_concept_ranking()
    t_cost = time.time() - t_start
    print(f"  耗时: {t_cost:.3f}秒")
    print(f"  板块数量: {len(concept_ranking)}")
    
    # 测试 3: 测试概念板块排名获取（缓存）
    print("\n📊 测试 3: 测试概念板块排名获取（缓存）")
    t_start = time.time()
    concept_ranking = analyzer.get_akshare_concept_ranking()
    t_cost = time.time() - t_start
    print(f"  耗时: {t_cost:.3f}秒")
    
    # 测试 4: 测试全维共振分析（首次）
    print("\n📊 测试 4: 测试全维共振分析（首次）")
    t_start = time.time()
    result = analyzer.check_stock_full_resonance(stock_code, "平安银行")
    t_cost = time.time() - t_start
    print(f"  耗时: {t_cost:.3f}秒")
    print(f"  共振评分: {result.get('resonance_score', 0)}")
    print(f"  共振详情: {result.get('resonance_details', [])}")
    
    # 测试 5: 测试全维共振分析（缓存）
    print("\n📊 测试 5: 测试全维共振分析（缓存）")
    t_start = time.time()
    result = analyzer.check_stock_full_resonance(stock_code, "平安银行")
    t_cost = time.time() - t_start
    print(f"  耗时: {t_cost:.3f}秒")
    print(f"  共振评分: {result.get('resonance_score', 0)}")
    
    # 测试 6: 测试多只股票
    print("\n📊 测试 6: 测试多只股票（缓存）")
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
    
    print(f"  总耗时: {total_time:.3f}秒")
    print(f"  平均耗时: {total_time/len(test_stocks):.3f}秒")
    
    # 测试 7: 检查概念板块数据的列名
    print("\n📊 测试 7: 检查概念板块数据的列名")
    if not concept_ranking.empty:
        print(f"  列名: {list(concept_ranking.columns)}")
        print(f"  前3行数据:")
        print(concept_ranking.head(3))
    
    print("\n" + "=" * 80)
    print("✅ 调查完成")
    print("=" * 80)

if __name__ == "__main__":
    investigate_2_second_delay()