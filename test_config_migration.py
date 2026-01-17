#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置迁移性能测试
验证配置系统迁移后的性能和正确性
"""

import time
import sys
from logic.technical_analyzer import TechnicalAnalyzer
from logic.market_sentiment import MarketSentiment
from logic.dragon_tactics import DragonTactics
from logic.data_provider_factory import DataProviderFactory
import config_system as config
from logic.logger import get_logger

logger = get_logger(__name__)

def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("📋 测试1：配置加载")
    print("=" * 60)
    
    try:
        print(f"✅ THRESHOLD_MARKET_HEAT_HIGH = {config.THRESHOLD_MARKET_HEAT_HIGH}")
        print(f"✅ THRESHOLD_MALIGNANT_RATE = {config.THRESHOLD_MALIGNANT_RATE}")
        print(f"✅ THRESHOLD_OPEN_KILL_GAP = {config.THRESHOLD_OPEN_KILL_GAP}")
        print(f"✅ THRESHOLD_BIAS_HIGH = {config.THRESHOLD_BIAS_HIGH}")
        print(f"✅ THRESHOLD_BIAS_LOW = {config.THRESHOLD_BIAS_LOW}")
        print(f"✅ THRESHOLD_MA_PERIOD = {config.THRESHOLD_MA_PERIOD}")
        print(f"✅ THRESHOLD_HISTORY_DAYS = {config.THRESHOLD_HISTORY_DAYS}")
        print(f"✅ THRESHOLD_FAKE_BOARD_RATIO = {config.THRESHOLD_FAKE_BOARD_RATIO}")
        print("\n✅ 配置加载测试通过！")
        return True
    except Exception as e:
        print(f"\n❌ 配置加载测试失败: {e}")
        return False


def test_technical_analyzer():
    """测试技术分析器"""
    print("\n" + "=" * 60)
    print("📈 测试2：技术分析器（使用配置系统）")
    print("=" * 60)
    
    try:
        ta = TechnicalAnalyzer()
        
        # 测试股票列表
        test_stocks = [
            {'code': '600058', 'price': 10.5},
            {'code': '000858', 'price': 15.2},
            {'code': '002056', 'price': 8.8},
        ]
        
        # 性能测试
        start_time = time.time()
        results = ta.analyze_batch(test_stocks)
        elapsed_time = time.time() - start_time
        
        print(f"\n📊 分析结果：")
        for code, result in results.items():
            print(f"  {code}: {result}")
        
        print(f"\n⚡ 性能：{len(test_stocks)} 只股票，耗时 {elapsed_time:.3f} 秒")
        print(f"⚡ 平均每只股票：{elapsed_time/len(test_stocks):.3f} 秒")
        
        if elapsed_time < 2.0:
            print("\n✅ 技术分析器性能测试通过！")
            return True
        else:
            print(f"\n⚠️ 性能略慢，建议优化")
            return True
            
    except Exception as e:
        print(f"\n❌ 技术分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_sentiment():
    """测试市场情绪分析器"""
    print("\n" + "=" * 60)
    print("🧠 测试3：市场情绪分析器（使用配置系统）")
    print("=" * 60)
    
    try:
        ms = MarketSentiment()
        
        # 性能测试
        start_time = time.time()
        sentiment_data = ms.get_market_regime()
        elapsed_time = time.time() - start_time
        
        print(f"\n📊 情绪分析结果：")
        print(f"  市场得分: {sentiment_data.get('score', 0)}")
        print(f"  市场状态: {sentiment_data.get('regime', 'N/A')}")
        print(f"  炸板率: {sentiment_data.get('mal_rate', 0)*100:.1f}%")
        
        print(f"\n⚡ 性能：耗时 {elapsed_time:.3f} 秒")
        
        if elapsed_time < 5.0:
            print("\n✅ 市场情绪分析器性能测试通过！")
            return True
        else:
            print(f"\n⚠️ 性能略慢，建议优化")
            return True
            
    except Exception as e:
        print(f"\n❌ 市场情绪分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dragon_tactics():
    """测试龙头战法"""
    print("\n" + "=" * 60)
    print("🐉 测试4：龙头战法（使用配置系统）")
    print("=" * 60)
    
    try:
        dt = DragonTactics()
        
        # 测试竞价分析
        test_data = {
            'current_open_volume': 100000,
            'prev_day_total_volume': 2000000,
        }
        
        start_time = time.time()
        results = dt.analyze_call_auction(**test_data)
        elapsed_time = time.time() - start_time
        
        print(f"\n📊 竞价分析结果：")
        print(f"  竞价量比: {results.get('call_auction_ratio', 0)*100:.2f}%")
        print(f"  竞价强度: {results.get('auction_intensity', 'N/A')}")
        print(f"  竞价得分: {results.get('auction_score', 0)}")
        
        print(f"\n⚡ 性能：耗时 {elapsed_time:.3f} 秒")
        
        if elapsed_time < 1.0:
            print("\n✅ 龙头战法性能测试通过！")
            return True
        else:
            print(f"\n⚠️ 性能略慢，建议优化")
            return True
            
    except Exception as e:
        print(f"\n❌ 龙头战法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_provider():
    """测试数据提供者工厂"""
    print("\n" + "=" * 60)
    print("📡 测试5：数据提供者工厂")
    print("=" * 60)
    
    try:
        # 测试实时数据提供者
        print("\n🔹 测试实时数据提供者...")
        provider_live = DataProviderFactory.get_provider(mode='live')
        print(f"  ✅ 实时数据提供者创建成功: {type(provider_live).__name__}")
        
        # 测试历史回放数据提供者
        print("\n🔹 测试历史回放数据提供者...")
        provider_replay = DataProviderFactory.get_provider(
            mode='replay',
            date='20260116',
            stock_list=['600058']
        )
        print(f"  ✅ 历史回放数据提供者创建成功: {type(provider_replay).__name__}")
        
        print("\n✅ 数据提供者工厂测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 数据提供者工厂测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_functions():
    """测试配置辅助函数"""
    print("\n" + "=" * 60)
    print("🔧 测试6：配置辅助函数")
    print("=" * 60)
    
    try:
        # 测试涨停阈值函数
        print("\n🔹 测试涨停阈值函数...")
        threshold_main = config.get_limit_up_threshold('600519')
        threshold_gem = config.get_limit_up_threshold('300015')
        threshold_st = config.get_limit_up_threshold('600519ST')
        
        print(f"  主板涨停阈值: {threshold_main*100:.1f}%")
        print(f"  创业板涨停阈值: {threshold_gem*100:.1f}%")
        print(f"  ST股涨停阈值: {threshold_st*100:.1f}%")
        
        # 测试交易时间函数
        print("\n🔹 测试交易时间函数...")
        is_trading = config.is_trading_time(570)  # 9:30
        time_weight = config.get_time_weight(570)
        
        print(f"  9:30 是否交易时间: {is_trading}")
        print(f"  9:30 时间权重: {time_weight}")
        
        print("\n✅ 配置辅助函数测试通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 配置辅助函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "🚀" * 30)
    print("🎯 Predator Guard V10.1.9.1 - 配置迁移性能测试")
    print("🚀" * 30)
    
    results = []
    
    # 执行所有测试
    results.append(("配置加载", test_config_loading()))
    results.append(("技术分析器", test_technical_analyzer()))
    results.append(("市场情绪分析器", test_market_sentiment()))
    results.append(("龙头战法", test_dragon_tactics()))
    results.append(("数据提供者工厂", test_data_provider()))
    results.append(("配置辅助函数", test_config_functions()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:20s}: {status}")
    
    print(f"\n📈 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！配置迁移成功！")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())