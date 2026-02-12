#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 603607.SH 的 ratio 计算和决策标签
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.equity_data_accessor import get_circ_mv

# 测试数据
code = "603607.SH"
trade_date = "20260206"
main_net_yuan = 77685610.0  # 7768.56 万

print("=" * 80)
print("测试 603607.SH 的 ratio 计算和决策标签")
print("=" * 80)
print()

# 步骤1: 获取流通市值
try:
    circ_mv_tushare = get_circ_mv(code, trade_date)
    print(f"✅ 步骤1: 查询流通市值成功")
    print(f"   circ_mv_tushare = {circ_mv_tushare} 元 ({circ_mv_tushare / 1e8:.2f} 亿)")
except Exception as e:
    print(f"❌ 步骤1: 查询流通市值失败: {e}")
    sys.exit(1)

print()

# 步骤2: 计算 ratio
ratio = main_net_yuan / circ_mv_tushare * 100
print(f"✅ 步骤2: 计算 ratio")
print(f"   main_net_inflow = {main_net_yuan} 元 ({main_net_yuan / 1e8:.4f} 亿)")
print(f"   circ_mv_tushare = {circ_mv_tushare} 元 ({circ_mv_tushare / 1e8:.2f} 亿)")
print(f"   ratio = {ratio:.4f}%")
print()

# 步骤3: 决策标签
risk_score = 0.1
trap_signals = []

print(f"✅ 步骤3: 决策标签")
print(f"   risk_score = {risk_score}")
print(f"   trap_signals = {trap_signals}")
print()

if ratio is not None and ratio < 0.5:
    decision_tag = "PASS❌"
    print(f"   ratio < 0.5% → {decision_tag}")
elif ratio is not None and ratio > 5:
    decision_tag = "TRAP❌"
    print(f"   ratio > 5% → {decision_tag}")
elif trap_signals and risk_score >= 0.4:
    decision_tag = "BLOCK❌"
    print(f"   诱多 + 高风险 → {decision_tag}")
elif (ratio is not None and 1 <= ratio <= 3 and risk_score <= 0.2 and not trap_signals):
    decision_tag = "FOCUS✅"
    print(f"   1% ≤ ratio ≤ 3% + 低风险 + 无诱多 → {decision_tag}")
else:
    decision_tag = "BLOCK❌"
    print(f"   其他情况 → {decision_tag}")

print()
print("=" * 80)
print(f"最终结果: {decision_tag}")
print("=" * 80)

# 验证是否符合预期
print()
print("验证:")
print(f"  预期 circ_mv ≈ 45.47 亿: {'✅' if abs(circ_mv_tushare / 1e8 - 45.47) < 0.01 else '❌'}")
print(f"  预期 ratio ≈ 1.71%: {'✅' if abs(ratio - 1.71) < 0.01 else '❌'}")
print(f"  预期标签 = FOCUS✅: {'✅' if decision_tag == 'FOCUS✅' else '❌'}")