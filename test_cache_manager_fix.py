#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 cache_manager.py 的修复
"""

import time
from logic.cache_manager import CacheManager

def test_custom_ttl():
    """测试自定义 TTL 功能"""
    print("=" * 80)
    print("🧪 测试自定义 TTL 功能")
    print("=" * 80)
    
    # 设置缓存，自定义 TTL 为 2 秒
    CacheManager.set("test_key", "test_value", ttl=2)
    
    # 立即获取，应该成功
    value = CacheManager.get("test_key")
    print(f"✅ 立即获取: {value}")
    assert value == "test_value", "立即获取失败"
    
    # 等待 1 秒，应该还能获取
    time.sleep(1)
    value = CacheManager.get("test_key")
    print(f"✅ 1秒后获取: {value}")
    assert value == "test_value", "1秒后获取失败"
    
    # 等待 2 秒，应该过期
    time.sleep(1)
    value = CacheManager.get("test_key")
    print(f"✅ 2秒后获取: {value}")
    assert value is None, "2秒后应该过期"
    
    print("\n✅ 自定义 TTL 测试通过！")

def test_default_ttl():
    """测试默认 TTL 功能"""
    print("\n" + "=" * 80)
    print("🧪 测试默认 TTL 功能")
    print("=" * 80)
    
    # 设置缓存，使用默认 TTL（5分钟）
    CacheManager.set("default_key", "default_value")
    
    # 立即获取，应该成功
    value = CacheManager.get("default_key")
    print(f"✅ 立即获取: {value}")
    assert value == "default_value", "立即获取失败"
    
    # 手动设置为过期时间
    CacheManager._cache_timestamps["default_key"] = time.time() - 310
    
    # 应该过期
    value = CacheManager.get("default_key")
    print(f"✅ 过期后获取: {value}")
    assert value is None, "过期后应该返回 None"
    
    print("\n✅ 默认 TTL 测试通过！")

def test_memory_leak_fix():
    """测试内存泄漏修复"""
    print("\n" + "=" * 80)
    print("🧪 测试内存泄漏修复")
    print("=" * 80)
    
    # 清空缓存
    CacheManager.clear()
    
    # 设置多个缓存，包含自定义 TTL
    CacheManager.set("key1", "value1", ttl=1)
    CacheManager.set("key2", "value2", ttl=2)
    CacheManager.set("key3", "value3")  # 默认 TTL
    
    # 检查 TTL 记录是否存在
    print(f"📊 TTL 记录数: {len([k for k in CacheManager._cache_timestamps.keys() if k.endswith('_ttl')])}")
    assert len([k for k in CacheManager._cache_timestamps.keys() if k.endswith('_ttl')]) == 2, "TTL 记录数不正确"
    
    # 等待 key1 过期
    time.sleep(1.1)
    
    # 清除过期缓存
    CacheManager.clear_expired()
    
    # 检查 TTL 记录是否被删除
    ttl_keys = [k for k in CacheManager._cache_timestamps.keys() if k.endswith('_ttl')]
    print(f"📊 清除过期后 TTL 记录数: {len(ttl_keys)}")
    print(f"📊 剩余 TTL 记录: {ttl_keys}")
    
    # key1 的 TTL 记录应该被删除
    assert "key1_ttl" not in CacheManager._cache_timestamps, "key1_ttl 应该被删除"
    # key2 和 key3 的 TTL 记录应该存在
    assert "key2_ttl" in CacheManager._cache_timestamps, "key2_ttl 应该存在"
    
    # 清除单个缓存
    CacheManager.clear("key2")
    
    # 检查 TTL 记录是否被删除
    ttl_keys = [k for k in CacheManager._cache_timestamps.keys() if k.endswith('_ttl')]
    print(f"📊 清除 key2 后 TTL 记录数: {len(ttl_keys)}")
    print(f"📊 剩余 TTL 记录: {ttl_keys}")
    
    # key2 的 TTL 记录应该被删除
    assert "key2_ttl" not in CacheManager._cache_timestamps, "key2_ttl 应该被删除"
    
    print("\n✅ 内存泄漏修复测试通过！")

def test_cache_info():
    """测试缓存信息"""
    print("\n" + "=" * 80)
    print("🧪 测试缓存信息")
    print("=" * 80)
    
    # 清空缓存
    CacheManager.clear()
    
    # 设置缓存
    CacheManager.set("info_key", "info_value")
    
    # 获取缓存信息
    info = CacheManager.get_cache_info()
    print(f"📊 缓存信息: {info}")
    
    assert info['缓存数量'] == 1, "缓存数量不正确"
    assert 'info_key' in info['缓存键列表'], "缓存键列表不正确"
    
    print("\n✅ 缓存信息测试通过！")

if __name__ == "__main__":
    print("\n🚀 开始测试 cache_manager.py 修复\n")
    
    try:
        test_custom_ttl()
        test_default_ttl()
        test_memory_leak_fix()
        test_cache_info()
        
        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()