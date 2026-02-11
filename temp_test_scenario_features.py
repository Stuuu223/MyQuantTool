#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试场景特征计算器
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.rolling_risk_features import (
    compute_multi_day_capital_flow,
    detect_pump_dump_pattern,
    detect_tail_rally_pattern,
    compute_sector_stage,
    compute_all_scenario_features
)

def test_multi_day_capital_flow():
    """测试多日资金流计算"""
    print("=" * 60)
    print("测试多日资金流计算")
    print("=" * 60)
    
    # 模拟资金流记录（单位：元）
    flow_records = [
        {"date": "20260208", "main_net_inflow": 5000000},    # 最新一天
        {"date": "20260207", "main_net_inflow": -3000000},
        {"date": "20260206", "main_net_inflow": 2000000},
        {"date": "20260205", "main_net_inflow": 4000000},
        {"date": "20260204", "main_net_inflow": -2000000},
    ]
    
    result = compute_multi_day_capital_flow(flow_records)
    
    print(f"5日净流入: {result['net_main_5d']/10000:.2f}万")
    print(f"10日净流入: {result.get('net_main_10d', 0)/10000:.2f}万")
    print("✓ 多日资金流计算测试通过\n")


def test_pump_dump_pattern():
    """测试拉高出货模式检测"""
    print("=" * 60)
    print("测试拉高出货模式检测")
    print("=" * 60)
    
    # 模拟拉高出货模式
    flow_records = [
        {
            "date": "20260208",  # T日：拉高
            "main_net_inflow": 10000000,
            "super_large_net_in": 6000000,
            "large_net_in": 3000000
        },
        {
            "date": "20260207",  # T+1日：出货
            "main_net_inflow": -5000000,
            "super_large_net_in": -3000000,
            "large_net_in": -2000000
        },
        {
            "date": "20260206",
            "main_net_inflow": 2000000,
        }
    ]
    
    result = detect_pump_dump_pattern(flow_records)
    
    print(f"检测到拉高出货: {result['one_day_pump_next_day_dump']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"原因: {result['reasons']}")
    print("✓ 拉高出货模式检测测试通过\n")


def test_tail_rally_pattern():
    """测试补涨尾声模式检测"""
    print("=" * 60)
    print("测试补涨尾声模式检测")
    print("=" * 60)
    
    # 模拟补涨尾声模式（30日流出，今日突然流入）
    flow_records = []
    
    # 前29天：持续流出
    for i in range(29):
        flow_records.append({
            "date": f"202601{31-i:02d}",
            "main_net_inflow": -5000000
        })
    
    # 第30天（最新）：突然大幅流入
    flow_records.insert(0, {
        "date": "20260208",
        "main_net_inflow": 15000000
    })
    
    result = detect_tail_rally_pattern(flow_records, capital_type="HOTMONEY")
    
    print(f"检测到补涨尾声: {result['first_pump_after_30d_outflow']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"原因: {result['reasons']}")
    print("✓ 补涨尾声模式检测测试通过\n")


def test_sector_stage():
    """测试板块阶段计算"""
    print("=" * 60)
    print("测试板块阶段计算")
    print("=" * 60)
    
    # 测试启动阶段
    result1 = compute_sector_stage(sector_20d_pct_change=3, sector_5d_trend=1)
    print(f"启动阶段: {result1['stage_name']} (stage={result1['sector_stage']})")
    
    # 测试主升阶段
    result2 = compute_sector_stage(sector_20d_pct_change=10, sector_5d_trend=3)
    print(f"主升阶段: {result2['stage_name']} (stage={result2['sector_stage']})")
    
    # 测试尾声阶段
    result3 = compute_sector_stage(sector_20d_pct_change=25, sector_5d_trend=-1)
    print(f"尾声阶段: {result3['stage_name']} (stage={result3['sector_stage']})")
    
    print("✓ 板块阶段计算测试通过\n")


def test_all_scenario_features():
    """测试所有场景特征计算"""
    print("=" * 60)
    print("测试所有场景特征计算")
    print("=" * 60)
    
    # 构造完整测试数据
    flow_records = [
        {
            "date": "20260208",
            "main_net_inflow": 15000000,
            "super_large_net_in": 8000000,
            "large_net_in": 5000000
        },
        {
            "date": "20260207",
            "main_net_inflow": -3000000,
            "super_large_net_in": -2000000,
            "large_net_in": -1000000
        }
    ]
    
    # 补充30天数据（用于测试补涨尾声）
    for i in range(28):
        flow_records.append({
            "date": f"202601{31-i:02d}",
            "main_net_inflow": -2000000
        })
    
    result = compute_all_scenario_features(
        code="000001",
        trade_date="20260208",
        flow_records=flow_records,
        capital_type="HOTMONEY",
        sector_20d_pct_change=10,
        sector_5d_trend=2
    )
    
    print("所有场景特征:")
    print(f"  5日净流入: {result['net_main_5d']/10000:.2f}万")
    print(f"  拉高出货: {result['one_day_pump_next_day_dump']} (置信度: {result['confidence']:.2f})")
    print(f"  补涨尾声: {result['first_pump_after_30d_outflow']}")
    print(f"  板块阶段: {result['stage_name']} (stage={result['sector_stage']})")
    print("✓ 所有场景特征计算测试通过\n")


if __name__ == "__main__":
    print("开始场景特征计算器测试...")
    print()
    
    test_multi_day_capital_flow()
    test_pump_dump_pattern()
    test_tail_rally_pattern()
    test_sector_stage()
    test_all_scenario_features()
    
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)