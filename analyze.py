#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键式股票分析工具
用法: python analyze.py <股票代码> [天数]
示例: python analyze.py 300502 90
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.stock_ai_tool import analyze_stock

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze.py <股票代码> [天数]")
        print("示例: python analyze.py 300502 90")
        sys.exit(1)

    stock_code = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 90

    print(f"📊 正在分析 {stock_code}（最近{days}天）...\n")

    result, file_path = analyze_stock(stock_code, days=days, mode='enhanced', auto_save=True)

    print("=" * 60)
    print(f"📈 {stock_code} 分析结果")
    print("=" * 60)
    print(f"📁 文件保存路径: {file_path}")
    print(f"📅 分析时间: {result['analyze_time']}")
    print(f"📊 分析天数: {result['analyze_days']}")
    print()

    # 资金分类
    cap = result['capital_analysis']
    print("💰 资金分类")
    print("-" * 60)
    print(f"  类型: {cap['type']} ({cap['type_name']})")
    print(f"  置信度: {cap['confidence']}")
    print(f"  风险等级: {cap['risk_level']}")
    print(f"  预计持仓周期: {cap['holding_period_estimate']}")
    print(f"  证据: {cap['evidence']}")
    print()

    # 诱多陷阱
    trap = result['trap_detection']
    print("⚠️  诱多陷阱检测")
    print("-" * 60)
    print(f"  陷阱数量: {trap['trap_count']}")
    print(f"  最高严重程度: {trap['highest_severity']}")
    print(f"  综合风险评分: {trap['comprehensive_risk_score']}")
    print(f"  累计流出: {trap['total_outflow']} 万")
    print()

    if trap['trap_count'] > 0:
        print("  前5个诱多陷阱（按吸筹金额排序）:")
        for i, t in enumerate(trap['detected_traps'][:5], 1):
            print(f"    {i}. {t['inflow_day']}: {t['inflow_amount']:.2f}万 → {t['dump_day']}: {t['dump_amount']:.2f}万 ({t.get('severity', 'N/A')})")
        print()

    print("=" * 60)
    print("✅ 分析完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()