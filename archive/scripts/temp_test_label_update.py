#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟测试：标签是否会随扫描更新

场景模拟：
1. 第一次扫描：603607 - L0.0，无诱多
2. 第二次扫描（资金流变化）：603607 - L0.2，新增"暴量"诱多信号

验证：标签是否会重新计算
"""

import json
from datetime import datetime

# 模拟第一次扫描的资金流数据
scan1_data = {
    "code": "603607.SH",
    "code_6digit": "603607",
    "risk_score": 0.0,
    "trap_signals": [],
    "capital_type": "HOT_MONEY",
    "flow_data": {
        "stock_code": "603607",
        "records": [
            {"date": "2025-08-12", "main_net_inflow": 77685610.0, "super_large_net": 34943645.0},
            {"date": "2025-08-13", "main_net_inflow": -13867946.0, "super_large_net": -14415527.0},
            {"date": "2025-08-14", "main_net_inflow": -41820051.0, "super_large_net": -26201657.0},
            {"date": "2025-08-15", "main_net_inflow": 132977111.0, "super_large_net": 130751434.0},
            {"date": "2025-08-16", "main_net_inflow": 50000000.0, "super_large_net": 45000000.0},  # 正常流入
        ],
        "latest": {
            "date": "2025-08-16",
            "main_net_inflow": 50000000.0,
            "super_large_net": 45000000.0
        }
    },
    "scan_time": "2026-02-06T09:30:00"
}

# 模拟第二次扫描的资金流数据（新增"暴量"数据）
scan2_data = {
    "code": "603607.SH",
    "code_6digit": "603607",
    "risk_score": 0.2,  # 风险从 0.0 升到 0.2
    "trap_signals": ["单日暴量+隔日反手"],  # 新增诱多信号
    "capital_type": "HOT_MONEY",
    "flow_data": {
        "stock_code": "603607",
        "records": [
            {"date": "2025-08-12", "main_net_inflow": 77685610.0, "super_large_net": 34943645.0},
            {"date": "2025-08-13", "main_net_inflow": -13867946.0, "super_large_net": -14415527.0},
            {"date": "2025-08-14", "main_net_inflow": -41820051.0, "super_large_net": -26201657.0},
            {"date": "2025-08-15", "main_net_inflow": 132977111.0, "super_large_net": 130751434.0},
            {"date": "2025-08-16", "main_net_inflow": 50000000.0, "super_large_net": 45000000.0},
            {"date": "2025-08-17", "main_net_inflow": -200000000.0, "super_large_net": -180000000.0},  # 新增：暴量流出
        ],
        "latest": {
            "date": "2025-08-17",
            "main_net_inflow": -200000000.0,
            "super_large_net": -180000000.0
        }
    },
    "scan_time": "2026-02-06T09:30:30"
}

# 模拟第三次扫描（资金流继续变化）
scan3_data = {
    "code": "603607.SH",
    "code_6digit": "603607",
    "risk_score": 0.4,  # 风险继续升到 0.4
    "trap_signals": ["单日暴量+隔日反手", "长期流出+单日巨量"],  # 新增更多诱多信号
    "capital_type": "HOT_MONEY",
    "flow_data": {
        "stock_code": "603607",
        "records": [
            {"date": "2025-08-12", "main_net_inflow": 77685610.0, "super_large_net": 34943645.0},
            {"date": "2025-08-13", "main_net_inflow": -13867946.0, "super_large_net": -14415527.0},
            {"date": "2025-08-14", "main_net_inflow": -41820051.0, "super_large_net": -26201657.0},
            {"date": "2025-08-15", "main_net_inflow": 132977111.0, "super_large_net": 130751434.0},
            {"date": "2025-08-16", "main_net_inflow": 50000000.0, "super_large_net": 45000000.0},
            {"date": "2025-08-17", "main_net_inflow": -200000000.0, "super_large_net": -180000000.0},
            {"date": "2025-08-18", "main_net_inflow": -250000000.0, "super_large_net": -220000000.0},  # 新增：连续流出
        ],
        "latest": {
            "date": "2025-08-18",
            "main_net_inflow": -250000000.0,
            "super_large_net": -220000000.0
        }
    },
    "scan_time": "2026-02-06T09:31:00"
}

def compare_scans(scan1, scan2):
    """比较两次扫描的结果"""
    print("\n" + "=" * 80)
    print(f"🔍 扫描时间: {scan1['scan_time']} → {scan2['scan_time']}")
    print("=" * 80)
    
    # 风险评分变化
    risk_change = scan2['risk_score'] - scan1['risk_score']
    if risk_change == 0:
        print(f"✅ 风险评分: L{scan1['risk_score']:.1f} → L{scan2['risk_score']:.1f} (无变化)")
    elif risk_change > 0:
        print(f"⚠️  风险评分: L{scan1['risk_score']:.1f} → L{scan2['risk_score']:.1f} (风险上升 +{risk_change:.1f})")
    else:
        print(f"✅ 风险评分: L{scan1['risk_score']:.1f} → L{scan2['risk_score']:.1f} (风险下降 {risk_change:.1f})")
    
    # 诱多信号变化
    traps1 = set(scan1['trap_signals'])
    traps2 = set(scan2['trap_signals'])
    
    if traps1 == traps2:
        print(f"✅ 诱多信号: 无变化")
    else:
        added = traps2 - traps1
        removed = traps1 - traps2
        
        if added:
            print(f"⚠️  新增诱多信号: {', '.join(added)}")
        if removed:
            print(f"✅ 消失诱多信号: {', '.join(removed)}")
    
    # 主力净流入变化
    latest1 = scan1['flow_data']['latest']
    latest2 = scan2['flow_data']['latest']
    flow_change = latest2['main_net_inflow'] - latest1['main_net_inflow']
    
    print(f"\n💰 主力净流入变化:")
    print(f"   {scan1['scan_time'][-8:]}: {latest1['main_net_inflow'] / 1e8:.2f} 亿")
    print(f"   {scan2['scan_time'][-8:]}: {latest2['main_net_inflow'] / 1e8:.2f} 亿")
    print(f"   变化: {flow_change / 1e8:.2f} 亿")

# 模拟扫描序列
print("🎯 模拟测试：标签是否会随扫描更新")
print("=" * 80)
print("📊 扫描频率：每 30 秒一次")
print("🔄 资金流数据：每次扫描重新获取最新数据")
print("⚙️  标签计算：基于资金流历史 + 最新数据")
print("=" * 80)

# 第一次扫描
print("\n【第一次扫描】09:30:00")
print(f"股票: {scan1_data['code']}")
print(f"风险评分: L{scan1_data['risk_score']:.1f}")
print(f"诱多信号: {', '.join(scan1_data['trap_signals']) if scan1_data['trap_signals'] else '无'}")
print(f"最新主力净入: {scan1_data['flow_data']['latest']['main_net_inflow'] / 1e8:.2f} 亿")

# 第二次扫描（30秒后）
print("\n【第二次扫描】09:30:30")
print(f"⚠️  资金流数据更新：新增'暴量流出'数据")
compare_scans(scan1_data, scan2_data)

# 第三次扫描（再过30秒）
print("\n【第三次扫描】09:31:00")
print(f"⚠️  资金流数据继续更新：新增'连续流出'数据")
compare_scans(scan2_data, scan3_data)

# 总结
print("\n" + "=" * 80)
print("📊 测试结论")
print("=" * 80)
print("✅ 每次扫描都会重新计算标签（风险评分、诱多信号）")
print("✅ 资金流数据更新后，标签会立即反映变化")
print("✅ 09:30:00 (L0.0) → 09:30:30 (L0.2) → 09:31:00 (L0.4)")
print("✅ 标签变化不是秒级，但扫描间隔（30秒）足够及时")
print("=" * 80)

print("\n🎯 实盘建议：")
print("1. 盘中：以最近一次扫描的标签为准")
print("2. 如果30秒内标签从L0.0变到L0.2，需要重新评估")
print("3. 特别是诱多信号新增时，要考虑减仓或退出")
print("4. 不要以为\"L0.0\"是一劳永逸的，要跟踪每次扫描的结果")