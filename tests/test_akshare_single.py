#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单股票测试 - 验证AkShare API修复

测试目标：
1. 验证JSON序列化错误是否修复
2. 验证NoneType错误是否修复
3. 验证缓存文件是否成功生成

Usage:
    python tests/test_akshare_single.py

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.2.2
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.data_providers.akshare_manager import AkShareDataManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    print("=" * 80)
    print("单股票测试 (V16.2.2 - 验证API修复)")
    print("=" * 80)

    # 测试一只真实的股票
    test_code = "600519.SH"  # 贵州茅台

    print(f"\n📋 测试配置:")
    print(f"  测试股票: {test_code}")

    print(f"\n🚀 开始测试...")

    # 创建预热模式的管理器
    manager = AkShareDataManager(mode='warmup')

    # 测试1: 获取资金流
    print(f"\n1️⃣ 测试获取资金流: {test_code}")
    fund_flow = manager.get_fund_flow(test_code)
    if fund_flow:
        print(f"  ✅ 资金流获取成功")
        print(f"  数据条数: {len(fund_flow.get('日期', {})) if isinstance(fund_flow, dict) else 'N/A'}")
    else:
        print(f"  ❌ 资金流获取失败")

    # 测试2: 获取新闻
    print(f"\n2️⃣ 测试获取新闻: {test_code}")
    # 🚫 V16.3.0: 新闻模块已移除（资金为王，拒绝噪音）
    # news = manager.get_news(test_code)
    # if news:
    #     print(f"  ✅ 新闻获取成功")
    #     print(f"  新闻条数: {len(news) if isinstance(news, list) else 'N/A'}")
    # else:
    #     print(f"  ❌ 新闻获取失败")
    print(f"  ⚠️  新闻模块已移除（V16.3.0 - 资金为王，拒绝噪音）")

    # 测试3: 获取基本面指标
    print(f"\n3️⃣ 测试获取基本面指标: {test_code}")
    financial = manager.get_financial_indicator(test_code)
    if financial:
        print(f"  ✅ 基本面指标获取成功")
    else:
        print(f"  ❌ 基本面指标获取失败")

    # 检查缓存文件
    print(f"\n🔍 检查缓存文件...")
    cache_dir = Path('data/ak_cache')
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        print(f"  缓存文件数: {len(cache_files)}")
        for file in cache_files:
            file_size = file.stat().st_size
            print(f"  - {file.name} ({file_size} bytes)")
    else:
        print(f"  ❌ 缓存目录不存在: {cache_dir}")

    print("\n" + "=" * 80)
    print("✅ 测试完成")
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
