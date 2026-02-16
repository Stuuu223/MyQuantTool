#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkShare预热测试脚本 (V16.3.0 - 验证新闻模块移除)

测试目标：
1. 验证[:50]切片限制是否已删除
2. 验证所有股票都能被预热
3. 验证缓存文件生成数量是否正确
4. 验证新闻模块已完全移除

Usage:
    python tests/test_akshare_warmup.py

Expected Output:
    如果预热100只股票，应该生成200个缓存文件（每只股票2个：资金流、基本面）
    如果预热200只股票，应该生成400个缓存文件

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.3.0
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.data_providers.akshare_manager import AkShareDataManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    print("=" * 80)
    print("AkShare预热测试 (V16.3.0 - 验证新闻模块移除)")
    print("=" * 80)
    
    # 准备测试数据（模拟100只股票）
    test_stock_list = []
    for i in range(100):
        test_stock_list.append(f"{600000 + i:06d}.SH")
    
    print(f"\n📋 测试配置:")
    print(f"  测试股票数量: {len(test_stock_list)}只")
    print(f"  预期缓存文件: {len(test_stock_list) * 2}个（每只股票2个数据：资金流、基本面）")
    print(f"  🚫 新闻模块已移除（V16.3.0 - 资金为王，拒绝噪音）")
    
    print("\n🚀 开始预热测试...")
    
    # 创建预热模式的管理器
    manager = AkShareDataManager(mode='warmup')
    
    # 执行预热
    report = manager.warmup_all(stock_list=test_stock_list)
    
    # 打印预热报告
    print("\n📊 预热报告:")
    print(f"  资金流: ✅{report['fund_flow']['success']} ❌{report['fund_flow']['failed']}")
    # 🚫 V16.3.0: 新闻模块已移除（资金为王，拒绝噪音）
    # print(f"  新闻: ✅{report['news']['success']} ❌{report['news']['failed']}")
    print(f"  基本面: ✅{report['financial_indicator']['success']} ❌{report['financial_indicator']['failed']}")
    
    # 验证缓存文件数量
    print(f"\n🔍 验证缓存文件...")
    cache_dir = Path('data/ak_cache')
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        print(f"  缓存文件总数: {len(cache_files)}")
        print(f"  预期缓存文件: {len(test_stock_list) * 2}个（每只股票2个：资金流、基本面）")
        
        # 检查是否只有50个股票的缓存（Bug未修复）
        fund_flow_files = [f for f in cache_files if 'fund_flow' in f.read_text(encoding='utf-8')]
        print(f"  资金流缓存文件: {len(fund_flow_files)}")
        
        # 检查是否有新闻缓存（V16.3.0不应存在）
        news_files = [f for f in cache_files if 'news' in f.read_text(encoding='utf-8')]
        if news_files:
            print(f"  ⚠️ 警告: 发现{len(news_files)}个新闻缓存文件，V16.3.0应该已移除新闻模块！")
        else:
            print(f"  ✅ 新闻模块已完全移除：无新闻缓存文件")
        
        if len(fund_flow_files) < len(test_stock_list):
            print(f"  ⚠️ 警告: 只预热了{len(fund_flow_files)}只股票，少于测试股票数{len(test_stock_list)}")
            print(f"  ⚠️ 警告: 可能还存在[:50]切片限制！")
        else:
            print(f"  ✅ Bug修复成功：所有股票都已预热")
    else:
        print(f"  ❌ 缓存目录不存在: {cache_dir}")
    
    print("\n" + "=" * 80)
    print("✅ 预热测试完成")
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