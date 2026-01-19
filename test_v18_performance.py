#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V18 性能测试脚本
测试所有新功能的性能表现
"""

import time
import pandas as pd
from datetime import datetime
from logic.logger import get_logger

logger = get_logger(__name__)


def test_unban_warning_performance():
    """测试解禁预警性能"""
    print("\n" + "="*60)
    print("🚨 测试解禁预警性能")
    print("="*60)
    
    try:
        from logic.unban_warning_system import get_unban_warning_system
        
        unban_system = get_unban_warning_system()
        
        # 测试单只股票
        start_time = time.time()
        warning = unban_system.check_unban_warning("000001")
        elapsed_time = time.time() - start_time
        
        print(f"✅ 单只股票检查耗时: {elapsed_time:.3f}秒")
        print(f"   预警结果: {warning}")
        
        # 测试批量检查
        test_stocks = ["000001", "000002", "600000", "600519", "000858"]
        start_time = time.time()
        for stock in test_stocks:
            unban_system.check_unban_warning(stock)
        elapsed_time = time.time() - start_time
        
        print(f"✅ 批量检查（5只）耗时: {elapsed_time:.3f}秒")
        print(f"   平均耗时: {elapsed_time/5:.3f}秒/只")
        
        # 获取 SHADOW_LIST
        start_time = time.time()
        shadow_list = unban_system.get_shadow_list()
        elapsed_time = time.time() - start_time
        
        print(f"✅ 获取 SHADOW_LIST 耗时: {elapsed_time:.3f}秒")
        print(f"   SHADOW_LIST 数量: {len(shadow_list)}")
        
        return True
    
    except Exception as e:
        print(f"❌ 解禁预警测试失败: {e}")
        return False


def test_sector_resonance_performance():
    """测试板块共振性能"""
    print("\n" + "="*60)
    print("🔗 测试板块共振性能")
    print("="*60)
    
    try:
        from logic.sector_resonance_detector import get_sector_resonance_detector
        
        resonance_detector = get_sector_resonance_detector()
        
        # 测试单只股票
        start_time = time.time()
        result = resonance_detector.check_sector_resonance("000001", 5.0)
        elapsed_time = time.time() - start_time
        
        print(f"✅ 单只股票检查耗时: {elapsed_time:.3f}秒")
        print(f"   共振结果: {result}")
        
        # 测试批量检查
        test_stocks = [
            ("000001", 5.0),
            ("000002", 3.0),
            ("600000", 2.0),
            ("600519", 1.0),
            ("000858", 4.0)
        ]
        start_time = time.time()
        for stock, change in test_stocks:
            resonance_detector.check_sector_resonance(stock, change)
        elapsed_time = time.time() - start_time
        
        print(f"✅ 批量检查（5只）耗时: {elapsed_time:.3f}秒")
        print(f"   平均耗时: {elapsed_time/5:.3f}秒/只")
        
        return True
    
    except Exception as e:
        print(f"❌ 板块共振测试失败: {e}")
        return False


def test_national_team_performance():
    """测试国家队指纹性能"""
    print("\n" + "="*60)
    print("🏛️ 测试国家队指纹性能")
    print("="*60)
    
    try:
        from logic.national_team_detector import get_national_team_detector
        
        national_team = get_national_team_detector()
        
        # 测试检查信号
        start_time = time.time()
        signal = national_team.check_national_team_signal()
        elapsed_time = time.time() - start_time
        
        print(f"✅ 检查国家队信号耗时: {elapsed_time:.3f}秒")
        print(f"   信号结果: {signal}")
        
        # 测试获取救援模式信息
        start_time = time.time()
        rescue_info = national_team.get_rescue_mode_info()
        elapsed_time = time.time() - start_time
        
        print(f"✅ 获取救援模式信息耗时: {elapsed_time:.3f}秒")
        print(f"   救援模式状态: {rescue_info}")
        
        return True
    
    except Exception as e:
        print(f"❌ 国家队指纹测试失败: {e}")
        return False


def test_ai_cache_performance():
    """测试 AI 缓存性能"""
    print("\n" + "="*60)
    print("🧠 测试 AI 缓存性能")
    print("="*60)
    
    try:
        from logic.ai_agent import RealAIAgent
        
        # 创建 AI Agent（需要 API key）
        api_key = "test_api_key"  # 测试用
        ai_agent = RealAIAgent(api_key=api_key, provider='deepseek')
        
        # 测试获取缓存统计
        start_time = time.time()
        cache_stats = ai_agent.get_cache_stats()
        elapsed_time = time.time() - start_time
        
        print(f"✅ 获取缓存统计耗时: {elapsed_time:.3f}秒")
        print(f"   缓存统计: {cache_stats}")
        
        # 测试清理过期缓存
        start_time = time.time()
        ai_agent.clear_expired_cache()
        elapsed_time = time.time() - start_time
        
        print(f"✅ 清理过期缓存耗时: {elapsed_time:.3f}秒")
        
        return True
    
    except Exception as e:
        print(f"❌ AI 缓存测试失败: {e}")
        return False


def test_dynamic_priority_performance():
    """测试动态优先级性能"""
    print("\n" + "="*60)
    print("⚡ 测试动态优先级性能")
    print("="*60)
    
    try:
        from logic.realtime_data_provider import RealtimeDataProvider
        
        provider = RealtimeDataProvider()
        
        # 测试更新优先级
        start_time = time.time()
        provider.update_stock_priority("000001", 70)
        elapsed_time = time.time() - start_time
        
        print(f"✅ 更新优先级耗时: {elapsed_time:.3f}秒")
        
        # 测试批量更新优先级
        test_stocks = [
            ("000001", 70),
            ("000002", 60),
            ("600000", 80),
            ("600519", 50),
            ("000858", 90)
        ]
        start_time = time.time()
        for stock, priority in test_stocks:
            provider.update_stock_priority(stock, priority)
        elapsed_time = time.time() - start_time
        
        print(f"✅ 批量更新优先级（5只）耗时: {elapsed_time:.3f}秒")
        print(f"   平均耗时: {elapsed_time/5:.3f}秒/只")
        
        # 测试获取监控统计
        start_time = time.time()
        stats = provider.get_monitor_stats()
        elapsed_time = time.time() - start_time
        
        print(f"✅ 获取监控统计耗时: {elapsed_time:.3f}秒")
        print(f"   监控统计: {stats}")
        
        return True
    
    except Exception as e:
        print(f"❌ 动态优先级测试失败: {e}")
        return False


def run_all_performance_tests():
    """运行所有性能测试"""
    print("\n" + "="*60)
    print("🚀 V18 性能测试开始")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 测试解禁预警
    results['unban_warning'] = test_unban_warning_performance()
    
    # 测试板块共振
    results['sector_resonance'] = test_sector_resonance_performance()
    
    # 测试国家队指纹
    results['national_team'] = test_national_team_performance()
    
    # 测试 AI 缓存
    results['ai_cache'] = test_ai_cache_performance()
    
    # 测试动态优先级
    results['dynamic_priority'] = test_dynamic_priority_performance()
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 性能测试汇总")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查日志")
    
    return results


if __name__ == "__main__":
    results = run_all_performance_tests()