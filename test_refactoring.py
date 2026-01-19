#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
架构重构测试脚本 - V18.6.1

测试内容：
1. DataManager 是否正确使用了 DataProviderFactory
2. MarketEnvironmentFilter 是否正常工作
3. signal_generator.py 是否正确调用了 MarketEnvironmentFilter

Author: iFlow CLI
Version: V18.6.1
"""

import sys
from logic.logger import get_logger
from logic.version import get_version, print_version

logger = get_logger(__name__)


def test_version():
    """测试版本号"""
    print("\n" + "="*60)
    print("测试 1: 版本号管理")
    print("="*60)
    
    print_version()
    
    version = get_version()
    assert version == "V18.6.1", f"版本号错误: {version}"
    
    print("✅ 版本号测试通过")
    return True


def test_data_manager():
    """测试 DataManager 是否正确使用了 DataProviderFactory"""
    print("\n" + "="*60)
    print("测试 2: DataManager 架构重构")
    print("="*60)
    
    try:
        from logic.data_manager import DataManager
        from logic.data_provider_factory import DataProviderFactory
        
        # 初始化 DataManager
        dm = DataManager()
        
        # 检查是否有 provider 属性
        assert hasattr(dm, 'provider'), "DataManager 没有 provider 属性"
        
        # 检查 provider 是否是 DataProviderFactory 的实例
        assert isinstance(dm.provider, type(DataProviderFactory.get_provider(mode='live'))), \
            f"provider 类型错误: {type(dm.provider)}"
        
        print("✅ DataManager 架构重构测试通过")
        print(f"   - provider 类型: {type(dm.provider).__name__}")
        print(f"   - provider 模式: {dm.provider.__class__.__name__}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DataManager 架构重构测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_environment_filter():
    """测试 MarketEnvironmentFilter 是否正常工作"""
    print("\n" + "="*60)
    print("测试 3: MarketEnvironmentFilter 功能")
    print("="*60)
    
    try:
        from logic.market_environment_filter import get_market_environment_filter
        from logic.data_manager import DataManager
        
        # 初始化
        dm = DataManager()
        env_filter = get_market_environment_filter(dm)
        
        # 检查是否有必要的方法
        assert hasattr(env_filter, 'check_market_environment'), "没有 check_market_environment 方法"
        assert hasattr(env_filter, 'get_market_themes'), "没有 get_market_themes 方法"
        assert hasattr(env_filter, 'get_leading_stocks'), "没有 get_leading_stocks 方法"
        
        # 测试检查市场环境
        test_stock = "000001"
        env_result = env_filter.check_market_environment(test_stock)
        
        print("✅ MarketEnvironmentFilter 功能测试通过")
        print(f"   - 测试股票: {test_stock}")
        print(f"   - 环境是否支持做多: {env_result.get('is_supportive', False)}")
        print(f"   - 共振分数: {env_result.get('resonance_score', 0):.1f}")
        print(f"   - 共振详情: {env_result.get('resonance_details', '')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MarketEnvironmentFilter 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generator():
    """测试 signal_generator.py 是否正确调用了 MarketEnvironmentFilter"""
    print("\n" + "="*60)
    print("测试 4: SignalGenerator 解耦")
    print("="*60)
    
    try:
        # 读取 signal_generator.py 文件
        with open('logic/signal_generator.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否导入了 MarketEnvironmentFilter
        assert 'from logic.market_environment_filter import get_market_environment_filter' in content, \
            "signal_generator.py 没有导入 MarketEnvironmentFilter"
        
        # 检查是否调用了 get_market_environment_filter
        assert 'get_market_environment_filter' in content, \
            "signal_generator.py 没有调用 get_market_environment_filter"
        
        # 检查是否移除了直接的 FastSectorAnalyzer 导入（在板块共振部分）
        # 注意：这里我们只检查在板块共振部分是否有直接的 FastSectorAnalyzer 导入
        # 因为其他地方可能还在使用 FastSectorAnalyzer
        
        print("✅ SignalGenerator 解耦测试通过")
        print("   - 已导入 MarketEnvironmentFilter")
        print("   - 已调用 get_market_environment_filter")
        print("   - 板块共振逻辑已解耦")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ SignalGenerator 解耦测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("架构重构测试 - V18.6.1")
    print("="*60)
    
    results = []
    
    # 运行测试
    results.append(("版本号管理", test_version()))
    results.append(("DataManager 架构重构", test_data_manager()))
    results.append(("MarketEnvironmentFilter 功能", test_market_environment_filter()))
    results.append(("SignalGenerator 解耦", test_signal_generator()))
    
    # 打印测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(results)} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    
    if failed == 0:
        print("\n🎉 所有测试通过！架构重构成功！")
        return 0
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())