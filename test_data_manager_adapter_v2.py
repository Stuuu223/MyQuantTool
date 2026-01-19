#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 DataManager 适配器模式（无缓存版本）
"""

import time
from logic.data_manager import DataManager

def test_data_manager_adapter_no_cache():
    """测试 DataManager 适配器模式（无缓存）"""
    print("=" * 80)
    print("🧪 测试 DataManager 适配器模式（无缓存）")
    print("=" * 80)
    
    # 初始化
    print("\n📊 初始化 DataManager...")
    t_start = time.time()
    dm = DataManager()
    t_cost = time.time() - t_start
    print(f"  耗时: {t_cost:.3f}秒")
    
    # 检查 provider 是否集成
    print(f"\n📊 Provider 集成状态:")
    print(f"  Provider: {dm.provider}")
    print(f"  Provider 类型: {type(dm.provider) if dm.provider else 'None'}")
    
    # 清空缓存
    dm.realtime_cache.clear()
    
    # 测试 1: 使用传统方法获取数据（无缓存）
    print("\n📊 测试 1: 使用传统方法获取数据（无缓存）")
    test_stocks = ['000001', '000002', '600000']
    
    t_start = time.time()
    traditional_data = dm.get_fast_price(test_stocks)
    t_cost = time.time() - t_start
    print(f"  耗时: {t_cost:.3f}秒")
    print(f"  获取数据: {len(traditional_data)} 只股票")
    
    # 清空缓存
    dm.realtime_cache.clear()
    
    # 测试 2: 使用 Provider 获取数据（无缓存）
    print("\n📊 测试 2: 使用 Provider 获取数据（无缓存）")
    t_start = time.time()
    provider_data = dm.get_provider_realtime_data(test_stocks)
    t_cost = time.time() - t_start
    print(f"  耗时: {t_cost:.3f}秒")
    print(f"  获取数据: {len(provider_data)} 只股票")
    
    # 测试 3: 性能对比（无缓存）
    print("\n📊 测试 3: 性能对比（无缓存，5次）")
    traditional_times = []
    provider_times = []
    
    for i in range(5):
        # 清空缓存
        dm.realtime_cache.clear()
        
        # 传统方法
        t_start = time.time()
        dm.get_fast_price(test_stocks)
        traditional_times.append(time.time() - t_start)
        
        # 清空缓存
        dm.realtime_cache.clear()
        
        # Provider 方法
        t_start = time.time()
        dm.get_provider_realtime_data(test_stocks)
        provider_times.append(time.time() - t_start)
    
    avg_traditional = sum(traditional_times) / len(traditional_times)
    avg_provider = sum(provider_times) / len(provider_times)
    
    print(f"  传统方法平均耗时: {avg_traditional:.3f}秒")
    print(f"  Provider 方法平均耗时: {avg_provider:.3f}秒")
    
    if avg_provider < avg_traditional:
        improvement = (avg_traditional - avg_provider) / avg_traditional * 100
        print(f"  ✅ Provider 方法快 {improvement:.1f}%")
    elif avg_provider > avg_traditional:
        degradation = (avg_provider - avg_traditional) / avg_traditional * 100
        print(f"  ⚠️  Provider 方法慢 {degradation:.1f}%")
    else:
        print(f"  ➡️  性能相当")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_data_manager_adapter_no_cache()