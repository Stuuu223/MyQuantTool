#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试类型错误定位脚本
"""
import sys
sys.path.insert(0, r'C:\Users\pc\Desktop\Astock\MyQuantTool')

from logic.backtest.time_machine_engine import TimeMachineEngine

# 测试单个股票
engine = TimeMachineEngine()
test_stock = '000021.SZ'
test_date = '20251231'

print(f"测试股票: {test_stock}, 日期: {test_date}")

try:
    result = engine._calculate_morning_score(test_stock, test_date)
    print(f"结果: {result}")
except Exception as e:
    import traceback
    print(f"错误类型: {type(e).__name__}")
    print(f"错误消息: {str(e)}")
    print(f"\n完整堆栈:")
    traceback.print_exc()