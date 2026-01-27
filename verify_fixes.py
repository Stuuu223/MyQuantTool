#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.13 修复验证脚本
验证所有修复是否正确应用

Author: iFlow CLI
Version: V19.13
"""

import sys
from logic.logger import get_logger

logger = get_logger(__name__)


def verify_active_stock_filter():
    """验证活跃股筛选器"""
    print("=" * 60)
    print("🔍 验证1: 活跃股筛选器 (active_stock_filter.py)")
    print("=" * 60)

    try:
        from logic.active_stock_filter import ActiveStockFilter, get_active_stocks

        # 检查类是否存在
        print("✅ ActiveStockFilter 类已导入")

        # 检查方法是否存在
        asf = ActiveStockFilter()
        print("✅ ActiveStockFilter 实例化成功")

        # 检查方法签名
        import inspect
        sig = inspect.signature(asf.get_active_stocks)
        params = list(sig.parameters.keys())
        print(f"✅ get_active_stocks 方法存在，参数: {params}")

        # 检查关键参数
        required_params = ['limit', 'sort_by', 'only_20cm']
        for param in required_params:
            if param in params:
                print(f"   ✅ 参数 '{param}' 存在")
            else:
                print(f"   ❌ 参数 '{param}' 缺失")
                return False

        return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_connection_pool():
    """验证连接池扩容"""
    print("\n" + "=" * 60)
    print("🔍 验证2: 连接池扩容 (realtime_data_provider.py)")
    print("=" * 60)

    try:
        from logic.realtime_data_provider import RealtimeDataProvider

        # 检查类是否存在
        print("✅ RealtimeDataProvider 类已导入")

        # 检查初始化逻辑
        import inspect
        source = inspect.getsource(RealtimeDataProvider.__init__)

        # 检查连接池配置
        if "pool_connections=200" in source:
            print("✅ 连接池配置正确 (pool_connections=200)")
        else:
            print("❌ 连接池配置缺失 (pool_connections=200)")
            return False

        if "pool_maxsize=200" in source:
            print("✅ 连接池配置正确 (pool_maxsize=200)")
        else:
            print("❌ 连接池配置缺失 (pool_maxsize=200)")
            return False

        # 检查代理清除
        if "trust_env = False" in source:
            print("✅ 代理禁用配置正确 (trust_env=False)")
        else:
            print("❌ 代理禁用配置缺失 (trust_env=False)")
            return False

        return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_midway_strategy():
    """验证半路战法集成"""
    print("\n" + "=" * 60)
    print("🔍 验证3: 半路战法集成 (midway_strategy.py)")
    print("=" * 60)

    try:
        from logic.midway_strategy import MidwayStrategy

        # 检查类是否存在
        print("✅ MidwayStrategy 类已导入")

        # 检查方法签名
        import inspect
        sig = inspect.signature(MidwayStrategy.scan_market)
        params = list(sig.parameters.keys())
        print(f"✅ scan_market 方法存在，参数: {params}")

        # 检查关键参数
        if "use_active_filter" in params:
            print("✅ 参数 'use_active_filter' 存在")
        else:
            print("❌ 参数 'use_active_filter' 缺失")
            return False

        # 检查方法实现
        source = inspect.getsource(MidwayStrategy.scan_market)
        if "from logic.active_stock_filter import get_active_stocks" in source:
            print("✅ 活跃股筛选器导入正确")
        else:
            print("❌ 活跃股筛选器导入缺失")
            return False

        if "use_active_filter:" in source:
            print("✅ use_active_filter 逻辑存在")
        else:
            print("❌ use_active_filter 逻辑缺失")
            return False

        return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_ui_integration():
    """验证UI集成"""
    print("\n" + "=" * 60)
    print("🔍 验证4: UI集成 (dragon_strategy.py)")
    print("=" * 60)

    try:
        with open('ui/dragon_strategy.py', 'r', encoding='utf-8') as f:
            source = f.read()

        # 检查保守半路调用
        if 'use_active_filter=True' in source:
            print("✅ 保守半路调用 use_active_filter=True")
        else:
            print("❌ 保守半路未调用 use_active_filter=True")
            return False

        return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主验证函数"""
    print("\n🚀 V19.13 修复验证开始\n")

    results = []

    # 验证1: 活跃股筛选器
    results.append(("活跃股筛选器", verify_active_stock_filter()))

    # 验证2: 连接池扩容
    results.append(("连接池扩容", verify_connection_pool()))

    # 验证3: 半路战法集成
    results.append(("半路战法集成", verify_midway_strategy()))

    # 验证4: UI集成
    results.append(("UI集成", verify_ui_integration()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有验证通过！修复已正确应用。")
    else:
        print("❌ 部分验证失败，请检查上述错误。")
    print("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
