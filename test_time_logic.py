#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试截停时间与收盘时间之间的逻辑
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from datetime import datetime, time

# 模拟时间判断逻辑
def test_time_logic():
    print("测试时间判断逻辑...")
    
    # 模拟一个在截停时间后但收盘时间前的时间
    test_time = datetime.now().replace(hour=14, minute=55, second=0, microsecond=0)  # 14:55
    cutoff_time = "14:50:00"
    market_close_time = "15:05:00"
    
    print(f"当前模拟时间: {test_time.strftime('%H:%M:%S')}")
    print(f"截停时间: {cutoff_time}")
    print(f"收盘时间: {market_close_time}")
    
    # 转换时间
    cutoff = datetime.strptime(cutoff_time, '%H:%M:%S').time()
    cutoff_dt = test_time.replace(hour=cutoff.hour, minute=cutoff.minute, second=cutoff.second)
    market_close = test_time.replace(hour=15, minute=5, second=0, microsecond=0)
    
    print(f"截停时间点: {cutoff_dt.strftime('%H:%M:%S')}")
    print(f"收盘时间点: {market_close.strftime('%H:%M:%S')}")
    
    print(f"当前时间 > 截停时间: {test_time > cutoff_dt}")
    print(f"当前时间 > 收盘时间: {test_time > market_close}")
    
    # 根据修正后的逻辑判断
    if test_time > market_close:
        print("✅ 逻辑判断: 执行收盘后历史回放")
    elif test_time > cutoff_dt:
        print("✅ 逻辑判断: 已进入尾盘垃圾时间，等待收盘")
    else:
        print("✅ 逻辑判断: 仍在交易时间内")

if __name__ == "__main__":
    test_time_logic()