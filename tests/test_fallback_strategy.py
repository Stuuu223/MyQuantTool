#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面数据降级策略测试 (V16.2.3)

测试目标：
1. 验证stock_financial_analysis_indicator失败时自动降级到stock_financial_abstract
2. 验证数据源标识和警告标记
3. 验证缓存机制在降级模式下正常工作

Usage:
    python tests/test_fallback_strategy.py

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.2.3
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.data_providers.akshare_manager import AkShareDataManager

def main():
    """主函数"""
    print("=" * 80)
    print("基本面数据降级策略测试 (V16.2.3)")
    print("=" * 80)

    # 测试股票
    test_code = "600519.SH"  # 贵州茅台

    print(f"\n📋 测试配置:")
    print(f"  测试股票: {test_code}")

    print(f"\n🚀 开始测试降级策略...")

    # 创建预热模式的管理器
    manager = AkShareDataManager(mode='warmup')

    # 测试基本面指标获取（应该触发降级策略）
    print(f"\n1️⃣ 测试基本面指标获取（包含降级策略）: {test_code}")
    financial = manager.get_financial_indicator(test_code)

    if financial:
        print(f"  ✅ 基本面指标获取成功")
        
        # 检查数据源标识
        if '_metadata' in financial:
            metadata = financial['_metadata']
            print(f"  📊 数据源: {metadata.get('data_source', '未知')}")
            print(f"  ⏰ 获取时间: {metadata.get('timestamp', '未知')}")
            
            if 'warning' in metadata:
                print(f"  ⚠️  警告: {metadata['warning']}")
        
        # 检查数据内容
        if '指标' in financial and '20250930' in financial:
            print(f"  📈 数据包含: {len(financial['指标'])}个指标")
            print(f"  📅 最新报告期: 2025Q3")
            
            # 显示核心指标
            core_indicators = ['归母净利润', '营业总收入', '营业成本', '净利润']
            print(f"  💰 核心指标:")
            for idx in range(min(len(financial['指标']), len(financial['20250930']))):
                indicator = financial['指标'][idx]
                if indicator in core_indicators:
                    value = financial['20250930'][idx]
                    print(f"     - {indicator}: {value}")
    else:
        print(f"  ❌ 基本面指标获取失败（所有数据源均失败）")

    # 检查缓存文件
    print(f"\n2️⃣ 检查缓存文件...")
    cache_dir = Path('data/ak_cache')
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        financial_cache = [f for f in cache_files if 'financial' in str(f).lower()]
        print(f"  基本面缓存文件数: {len(financial_cache)}")
        if financial_cache:
            for file in financial_cache:
                file_size = file.stat().st_size
                print(f"  - {file.name} ({file_size} bytes)")
    else:
        print(f"  ❌ 缓存目录不存在: {cache_dir}")

    # 测试缓存读取（验证降级模式缓存是否正常）
    print(f"\n3️⃣ 测试缓存读取（应该从缓存读取）: {test_code}")
    manager2 = AkShareDataManager(mode='warmup')
    financial_cached = manager2.get_financial_indicator(test_code)
    
    if financial_cached:
        print(f"  ✅ 缓存读取成功")
        if '_metadata' in financial_cached:
            print(f"  📊 数据源: {financial_cached['_metadata'].get('data_source', '未知')}")
    else:
        print(f"  ❌ 缓存读取失败")

    print("\n" + "=" * 80)
    print("✅ 降级策略测试完成")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
