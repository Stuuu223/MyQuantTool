#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 第一阶段：板块记忆功能测试
测试板块忠诚度和持续性分析
"""

import sys
from datetime import datetime
from logic.review_manager import ReviewManager
from logic.predictive_engine import PredictiveEngine
from logic.logger import get_logger

logger = get_logger(__name__)

def test_v13_phase1():
    """V13 第一阶段完整测试"""
    print("=" * 60)
    print("🚀 V13 第一阶段：板块记忆功能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 测试 1: 复盘管理器
    print("\n" + "=" * 60)
    print("📊 测试 1: ReviewManager 数据库结构")
    print("=" * 60)
    
    rm = ReviewManager()
    print("✅ ReviewManager 初始化成功")
    
    # 测试 2: 运行复盘（获取板块数据）
    print("\n" + "=" * 60)
    print("🔄 测试 2: 运行每日复盘（获取板块数据）")
    print("=" * 60)
    
    # 尝试获取最近一个交易日的数据
    test_date = '20260116'
    print(f"📅 测试日期: {test_date}")
    
    result = rm.run_daily_review(date=test_date)
    if result:
        print(f"✅ 复盘归档成功: {test_date}")
    else:
        print(f"⚠️ 复盘归档失败或无数据: {test_date}")
    
    # 测试 3: 读取昨日数据
    print("\n" + "=" * 60)
    print("📖 测试 3: 读取昨日市场状态")
    print("=" * 60)
    
    stats = rm.get_yesterday_stats()
    if stats:
        print(f"✅ 读取成功:")
        print(f"  日期: {stats.get('date', 'N/A')}")
        print(f"  最高板: {stats.get('highest_board', 0)}")
        print(f"  涨停家数: {stats.get('limit_up_count', 0)}")
        print(f"  领涨板块: {stats.get('top_sectors', [])}")
    else:
        print("⚠️ 无历史数据")
    
    # 测试 4: 板块忠诚度分析
    print("\n" + "=" * 60)
    print("🎯 测试 4: 板块忠诚度分析")
    print("=" * 60)
    
    pe = PredictiveEngine()
    print("✅ PredictiveEngine 初始化成功")
    
    # 测试几个常见板块
    test_sectors = ['人工智能', '新能源', '医药', '芯片']
    
    for sector in test_sectors:
        loyalty = pe.get_sector_loyalty(sector)
        print(f"\n📊 板块: {loyalty['sector']}")
        print(f"  忠诚度评分: {loyalty['loyalty_score']}")
        print(f"  出现次数: {loyalty['appearance_count']}")
        print(f"  次日平均表现: {loyalty['avg_next_day_profit']}")
        print(f"  状态: {loyalty['status']}")
    
    # 测试 5: 数据库查询验证
    print("\n" + "=" * 60)
    print("💾 测试 5: 数据库查询验证")
    print("=" * 60)
    
    # 查询最近 5 天的复盘记录
    sql = "SELECT date, highest_board, top_sectors FROM market_summary ORDER BY date DESC LIMIT 5"
    results = rm.db.sqlite_query(sql)
    
    if results:
        print(f"✅ 找到 {len(results)} 条历史记录")
        for row in results:
            date, highest_board, top_sectors_json = row
            import json
            top_sectors = json.loads(top_sectors_json) if top_sectors_json else []
            print(f"  {date}: {highest_board}板, 领涨板块: {top_sectors}")
    else:
        print("⚠️ 无历史记录")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_v13_phase1()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)