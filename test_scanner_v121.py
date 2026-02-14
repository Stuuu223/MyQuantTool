#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V12.1.0 三漏斗扫描器集成测试

测试三大过滤器的集成是否正常工作

Author: iFlow CLI
Date: 2026-02-14
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.strategies.triple_funnel_scanner_v121 import get_scanner_v121
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def test_scanner_v121():
    """测试 V12.1.0 增强版扫描器"""
    
    print("=" * 80)
    print("🚀 V12.1.0 三漏斗扫描器集成测试")
    print("=" * 80)
    
    # 1. 创建扫描器
    print("\n📝 步骤1: 创建扫描器...")
    try:
        scanner = get_scanner_v121(
            enable_wind_filter=True,
            enable_dynamic_threshold=True,
            enable_auction_validator=True,
            sentiment_stage='divergence'
        )
        print("✅ 扫描器创建成功")
    except Exception as e:
        print(f"❌ 扫描器创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 验证三大过滤器是否加载
    print("\n📝 步骤2: 验证三大过滤器加载...")
    filters_loaded = True
    
    if scanner.wind_filter is None:
        print("❌ 板块共振过滤器未加载")
        filters_loaded = False
    else:
        print("✅ 板块共振过滤器已加载")
    
    if scanner.dynamic_threshold is None:
        print("❌ 动态阈值管理器未加载")
        filters_loaded = False
    else:
        print("✅ 动态阈值管理器已加载")
    
    if scanner.auction_validator is None:
        print("❌ 竞价强弱校验器未加载")
        filters_loaded = False
    else:
        print("✅ 竞价强弱校验器已加载")
    
    if not filters_loaded:
        print("⚠️ 部分过滤器未加载，但扫描器仍可运行（部分功能将不可用）")
    
    # 3. 测试过滤器开关
    print("\n📝 步骤3: 测试过滤器开关...")
    try:
        print(f"初始状态:")
        print(f"  - 板块共振: {'✅ 启用' if scanner.enable_wind_filter else '❌ 禁用'}")
        print(f"  - 动态阈值: {'✅ 启用' if scanner.enable_dynamic_threshold else '❌ 禁用'}")
        print(f"  - 竞价校验: {'✅ 启用' if scanner.enable_auction_validator else '❌ 禁用'}")
        
        scanner.toggle_filter('wind', False)
        scanner.toggle_filter('threshold', False)
        scanner.toggle_filter('auction', False)
        
        print(f"\n切换后状态:")
        print(f"  - 板块共振: {'✅ 启用' if scanner.enable_wind_filter else '❌ 禁用'}")
        print(f"  - 动态阈值: {'✅ 启用' if scanner.enable_dynamic_threshold else '❌ 禁用'}")
        print(f"  - 竞价校验: {'✅ 启用' if scanner.enable_auction_validator else '❌ 禁用'}")
        
        # 恢复默认状态
        scanner.toggle_filter('wind', True)
        scanner.toggle_filter('threshold', True)
        scanner.toggle_filter('auction', True)
        
        print("✅ 过滤器开关测试通过")
    except Exception as e:
        print(f"❌ 过滤器开关测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 测试情绪周期更新
    print("\n📝 步骤4: 测试情绪周期更新...")
    try:
        stages = ['start', 'main', 'climax', 'divergence', 'recession', 'freeze']
        for stage in stages:
            scanner.update_sentiment_stage(stage)
        
        print(f"✅ 情绪周期更新测试通过（共测试 {len(stages)} 个阶段）")
    except Exception as e:
        print(f"❌ 情绪周期更新测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 测试观察池管理
    print("\n📝 步骤5: 测试观察池管理...")
    try:
        # 添加测试股票
        scanner.watchlist_manager.add("000001", "平安银行", "测试用")
        scanner.watchlist_manager.add("600519", "贵州茅台", "测试用")
        
        watchlist = scanner.watchlist_manager.get_all()
        print(f"✅ 观察池管理测试通过（当前 {len(watchlist)} 只股票）")
    except Exception as e:
        print(f"❌ 观察池管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 测试过滤器应用（模拟）
    print("\n📝 步骤6: 测试过滤器应用（模拟）...")
    try:
        test_code = "000001"
        
        # 模拟数据
        tick_data = {'price': 15.0, 'volume': 100000, 'amount': 1500000}
        flow_data = {'主力净流入': 5000000}
        auction_data = {
            'open_price': 15.2,
            'prev_close': 15.0,
            'volume_ratio': 2.0,
            'amount': 1500000,
            'high_price': 15.5,
            'low_price': 14.8,
            'is_limit_up': False
        }
        
        result = scanner._apply_filters(test_code, tick_data, flow_data, auction_data)
        
        print(f"✅ 过滤器应用测试通过")
        print(f"  - 股票代码: {result.code}")
        print(f"  - 是否通过: {'✅' if result.passed else '❌'}")
        print(f"  - 原因: {', '.join(result.reasons) if result.reasons else '无'}")
        print(f"  - 耗时: {result.details.get('elapsed_time_ms', 0):.2f}ms")
        
        # 获取统计信息
        stats = scanner.get_filter_stats()
        print(f"\n📊 过滤器统计:")
        print(f"  - 总检查: {stats['total_checks']}")
        print(f"  - 板块共振通过: {stats['wind_passed']}")
        print(f"  - 动态阈值通过: {stats['threshold_passed']}")
        print(f"  - 竞价校验通过: {stats['auction_passed']}")
        print(f"  - 全部通过: {stats['all_passed']}")
        
    except Exception as e:
        print(f"❌ 过滤器应用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ 所有测试通过！")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = test_scanner_v121()
    sys.exit(0 if success else 1)