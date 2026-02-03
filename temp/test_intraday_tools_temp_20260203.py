#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
盘中决策工具测试脚本

测试 intraday_monitor.py 和 intraday_decision.py 的功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

def test_intraday_monitor():
    """测试 intraday_monitor.py"""
    print("=" * 60)
    print("测试 intraday_monitor.py")
    print("=" * 60)
    
    from logic.intraday_monitor import IntraDayMonitor
    
    monitor = IntraDayMonitor()
    
    # 测试1: 检查是否交易时间
    print(f"\n1. 检查交易时间:")
    is_trading = monitor.is_trading_time()
    print(f"   当前是否交易时间: {is_trading}")
    
    # 测试2: 获取交易时间信息
    print(f"\n2. 交易时间信息:")
    time_info = monitor.get_trading_time_info()
    print(f"   当前时间: {time_info['current_time']}")
    print(f"   是否交易: {time_info['is_trading']}")
    print(f"   交易时段: {time_info['trading_period']}")
    print(f"   距收盘: {time_info['minutes_to_close']} 分钟" if time_info['minutes_to_close'] else "")
    
    # 测试3: 获取盘中快照（非交易时间会失败）
    print(f"\n3. 获取盘中快照:")
    snapshot = monitor.get_intraday_snapshot('300033')
    if snapshot['success']:
        print(f"   ✅ 成功")
        print(f"   价格: {snapshot['price']}")
        print(f"   涨跌幅: {snapshot['pct_change']}%")
        print(f"   买卖盘压力: {snapshot['bid_ask_pressure']}")
        print(f"   信号: {snapshot['signal']}")
    else:
        print(f"   ❌ 失败: {snapshot['error']}")
    
    # 测试4: 对比昨日数据
    yesterday_file = 'data/stock_analysis/300033/300033_20260203_125013_90days_enhanced.json'
    if os.path.exists(yesterday_file):
        print(f"\n4. 对比昨日数据:")
        comparison = monitor.compare_with_yesterday('300033', yesterday_file)
        if comparison['success']:
            print(f"   ✅ 成功")
            print(f"   价格变化: {comparison['comparison']['price_change_pct']}%")
            print(f"   5日趋势: {comparison['comparison']['flow_5d_trend']}")
            print(f"   诱多风险: {comparison['comparison']['trap_risk']}")
            print(f"   对比信号: {comparison['comparison']['signal']}")
        else:
            print(f"   ❌ 失败: {comparison['error']}")
    else:
        print(f"\n4. 对比昨日数据:")
        print(f"   ❌ 昨日文件不存在: {yesterday_file}")


def test_intraday_decision():
    """测试 intraday_decision.py"""
    print("\n" + "=" * 60)
    print("测试 intraday_decision.py")
    print("=" * 60)
    
    from tools.intraday_decision import IntraDayDecisionTool
    
    tool = IntraDayDecisionTool()
    
    # 测试1: 空仓测试
    print(f"\n1. 空仓测试:")
    decision = tool.make_decision(
        stock_code='300033',
        yesterday_file='data/stock_analysis/300033/300033_20260203_125013_90days_enhanced.json',
        current_position=0.0,
        entry_price=None
    )
    print(f"   决策: {decision['decision']}")
    print(f"   理由: {decision['reason']}")
    
    # 测试2: 有持仓测试
    print(f"\n2. 有持仓测试 (被套7个点):")
    decision = tool.make_decision(
        stock_code='300033',
        yesterday_file='data/stock_analysis/300033/300033_20260203_125013_90days_enhanced.json',
        current_position=1.0,
        entry_price=26.50
    )
    print(f"   决策: {decision['decision']}")
    print(f"   置信度: {decision['confidence']:.0%}")
    print(f"   理由: {decision['reason']}")
    
    if decision['action']:
        action = decision['action']
        print(f"   操作类型: {action.get('type', 'N/A')}")
        if 'target_position' in action:
            print(f"   目标仓位: {action['target_position']:.0%}")
        if 'stop_loss_price' in action:
            print(f"   止损价: {action['stop_loss_price']:.2f}")
    
    # 测试3: 打印决策报告
    print(f"\n3. 打印决策报告:")
    tool.print_decision_report(decision)


if __name__ == '__main__':
    print("盘中决策工具测试")
    print("=" * 60)
    
    test_intraday_monitor()
    test_intraday_decision()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)