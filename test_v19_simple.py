#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19 简化性能测试
"""

import time
from logic.market_cycle import MarketCycleManager
from logic.logger import get_logger

logger = get_logger(__name__)

print("\n" + "=" * 80)
print("🚀 V19 简化性能测试")
print("=" * 80)

# 测试1：初始化
print("\n📊 测试 1: 初始化 MarketCycleManager")
start_time = time.time()
mc = MarketCycleManager()
init_time = time.time() - start_time
print(f"✅ 初始化完成，耗时: {init_time:.3f}秒")

# 测试2：启动后台线程
print("\n📊 测试 2: 启动后台更新线程")
mc.start_background_update()
print("✅ 后台线程已启动")

# 测试3：读取缓存性能
print("\n📊 测试 3: 读取缓存性能")
test_times = []
for i in range(10):
    start_time = time.time()
    indicators = mc.get_market_emotion()
    elapsed = time.time() - start_time
    test_times.append(elapsed)

avg_time = sum(test_times) / len(test_times)
max_time = max(test_times)
min_time = min(test_times)

print(f"✅ 平均响应时间: {avg_time*1000:.2f}毫秒")
print(f"✅ 最大响应时间: {max_time*1000:.2f}毫秒")
print(f"✅ 最小响应时间: {min_time*1000:.2f}毫秒")

# 检查数据
print(f"\n📊 市场情绪数据:")
print(f"  - 涨停家数: {indicators.get('limit_up_count', 0)}")
print(f"  - 跌停家数: {indicators.get('limit_down_count', 0)}")
print(f"  - 最高板数: {indicators.get('highest_board', 0)}")
print(f"  - 平均溢价: {indicators.get('avg_profit', 0):.2f}%")

# 关闭
print("\n🛑 关闭 MarketCycleManager...")
mc.close()
print("✅ 已关闭")

# 性能评估
print("\n" + "=" * 80)
print("📊 性能评估")
print("=" * 80)
if avg_time < 0.1:
    print(f"🎉 性能优秀！平均响应时间 {avg_time*1000:.2f}毫秒 < 100毫秒")
    print("\n✅ V19 优化成功！")
else:
    print(f"⚠️ 性能需要优化，平均响应时间 {avg_time*1000:.2f}毫秒 >= 100毫秒")
    print("\n⚠️ 需要进一步优化")
print("=" * 80)