#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键式股票分析工具
用法: python analyze.py <股票代码> [天数] [选项]
示例: python analyze.py 300502 90
      python analyze.py 300502 90 --supplement

注意：如果使用 --supplement 选项，请使用 analyze_supplement.bat 启动脚本
"""
import sys
import os
import json

# 🚀 [最高优先级] 禁用代理：必须在 import 其他库之前执行！
from logic.network_utils import disable_proxy
disable_proxy()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 检查是否使用虚拟环境
VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv_qmt', 'Scripts', 'python.exe')
CURRENT_PYTHON = sys.executable
if '--supplement' in sys.argv and CURRENT_PYTHON != VENV_PYTHON and 'venv_qmt' not in CURRENT_PYTHON:
    print("=" * 80)
    print("⚠️  警告: QMT 补充数据需要 Python 3.10 虚拟环境")
    print("=" * 80)
    print(f"当前 Python: {CURRENT_PYTHON}")
    print(f"虚拟环境: {VENV_PYTHON}")
    print()
    print("请使用启动脚本运行:")
    print("  analyze_supplement.bat <股票代码> <天数>")
    print()
    print("或激活虚拟环境后运行:")
    print("  .\\venv_qmt\\Scripts\\activate")
    print("  python analyze.py <股票代码> <天数> --supplement")
    print("=" * 80)
    print()

from tools.stock_ai_tool import analyze_stock, get_qmt_supplement

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze.py <股票代码> [天数] [选项]")
        print("示例: python analyze.py 300502 90")
        print("      python analyze.py 300502 90 --supplement")
        sys.exit(1)

    stock_code = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 90

    # 检查是否有 --supplement 选项
    use_supplement = '--supplement' in sys.argv

    if use_supplement:
        # 获取 QMT 补充数据
        print(f"📊 正在获取 {stock_code} 的 QMT 补充数据...\n")
        result, file_path = get_qmt_supplement(stock_code, days=days, auto_save=True)

        print("=" * 60)
        print(f"📈 QMT 补充数据 - {stock_code}")
        print("=" * 60)
        print(f"📁 文件保存路径: {file_path}")
        print(f"📅 获取时间: {result.get('fetch_time', 'N/A')}")
        print()

        # 换手率
        if result.get('turnover_rate'):
            print("🔄 换手率:")
            for t in result['turnover_rate']:
                level_icon = "🔥" if t['level'] == "极度活跃" else "📈" if t['level'] == "活跃" else "😐" if t['level'] == "正常" else "💤"
                print(f"  {t['date']}: {t['turnover_rate']:>6.2f}% {level_icon} {t['level']}")
            print()

        # Tick验证
        validation = result.get('tick_validation', {})
        if validation and 'error' not in validation:
            status_icon = "✅" if validation.get('is_valid') else "⚠️"
            print(f"🔍 Tick成交验证:")
            print(f"  {status_icon} 是否有效: {validation.get('is_valid')}")
            print(f"  📏 成交量单位: {validation.get('volume_unit')}")
            print(f"  💰 成交额单位: {validation.get('amount_unit')}")
            if '异常说明' in validation:
                print(f"  ℹ️  说明: {validation['异常说明']}")
            print()

        # 分时形态
        intraday_1m = result.get('intraday_ma_1m', {})
        if intraday_1m and 'error' not in intraday_1m:
            pattern_icon = "⚠️" if "回落" in intraday_1m.get('pattern', '') else "🚀" if "反转" in intraday_1m.get('pattern', '') else "📊"
            print(f"📊 分时形态 (1分钟):")
            print(f"  {pattern_icon} 形态: {intraday_1m.get('pattern')}")
            print()

        # 盘口压力
        order_book = result.get('order_book', {})
        if order_book and 'error' not in order_book:
            pressure_icon = "🟢" if order_book.get('pressure') == "买盘强势" else "🔴" if order_book.get('pressure') == "卖盘压力大" else "⚪"
            print(f"⚖️  盘口压力:")
            print(f"  {pressure_icon} 买卖压力: {order_book.get('pressure')}")
            print()

        print("=" * 60)
        print("✅ 补充数据获取完成！")
        print("=" * 60)
        return  # 补充模式完成后直接返回
    else:
        # 默认增强分析
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