#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龙虎榜数据清洗测试 (V16.2.3)

测试目标：
1. 验证龙虎榜数据清洗功能
2. 验证核心字段提取
3. 验证缓存机制

Usage:
    python tests/test_lhb_cleaning.py

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
    print("龙虎榜数据清洗测试 (V16.2.3)")
    print("=" * 80)

    # 测试日期（使用历史日期确保有数据）
    test_date = "20250214"

    print(f"\n📋 测试配置:")
    print(f"  测试日期: {test_date}")

    print(f"\n🚀 开始测试龙虎榜数据清洗...")

    # 创建预热模式的管理器
    manager = AkShareDataManager(mode='warmup')

    # 测试龙虎榜数据获取（包含数据清洗）
    print(f"\n1️⃣ 测试龙虎榜数据获取（包含数据清洗）: {test_date}")
    lhb_data = manager.get_lhb_detail(test_date)

    if lhb_data:
        print(f"  ✅ 龙虎榜数据获取成功")
        print(f"  📊 上榜股票数: {len(lhb_data.get('代码', {})) if isinstance(lhb_data, dict) else len(lhb_data)}")

        # 显示核心字段
        if isinstance(lhb_data, dict):
            print(f"  📋 核心字段: {list(lhb_data.keys())}")

            # 显示前3只股票的数据
            print(f"\n  📈 前3只上榜股票:")
            for i in range(min(3, len(lhb_data.get('代码', {})))):
                code = lhb_data['代码'][i]
                name = lhb_data['名称'][i]
                net_buy = lhb_data['龙虎榜净买额'][i]
                reason = lhb_data['上榜原因'][i]
                print(f"     {i+1}. {code} {name} - 净买入: {net_buy}万 - 原因: {reason}")
    else:
        print(f"  ❌ 龙虎榜数据获取失败")

    # 检查缓存文件
    print(f"\n2️⃣ 检查缓存文件...")
    cache_dir = Path('data/ak_cache')
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        lhb_cache = [f for f in cache_files if 'lhb' in str(f).lower()]
        print(f"  龙虎榜缓存文件数: {len(lhb_cache)}")
        if lhb_cache:
            for file in lhb_cache:
                file_size = file.stat().st_size
                print(f"  - {file.name} ({file_size} bytes)")
    else:
        print(f"  ❌ 缓存目录不存在: {cache_dir}")

    # 测试缓存读取
    print(f"\n3️⃣ 测试缓存读取（应该从缓存读取）: {test_date}")
    manager2 = AkShareDataManager(mode='warmup')
    lhb_cached = manager2.get_lhb_detail(test_date)

    if lhb_cached:
        print(f"  ✅ 缓存读取成功")
    else:
        print(f"  ❌ 缓存读取失败")

    print("\n" + "=" * 80)
    print("✅ 龙虎榜数据清洗测试完成")
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