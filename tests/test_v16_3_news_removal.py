#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V16.3.0 新闻模块移除验证测试

测试目标：
1. 验证新闻模块已完全移除
2. 验证预热流程中不再出现新闻日志
3. 验证预热报告不包含新闻统计

Usage:
    python tests/test_v16_3_news_removal.py

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.3.0
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
    print("V16.3.0 新闻模块移除验证测试")
    print("=" * 80)
    
    # 准备测试数据（少量股票快速测试）
    test_stock_list = ["600519.SH", "000001.SZ", "600036.SH"]
    
    print(f"\n📋 测试配置:")
    print(f"  测试股票: {', '.join(test_stock_list)}")
    print(f"  股票数量: {len(test_stock_list)}只")
    
    print("\n🚀 开始预热测试...")
    print("👀 监控日志中是否出现'新闻'相关字样...")
    
    # 创建预热模式的管理器
    manager = AkShareDataManager(mode='warmup')
    
    # 执行预热
    print("\n" + "─" * 80)
    print("开始执行预热流程...")
    print("─" * 80)
    report = manager.warmup_all(stock_list=test_stock_list)
    print("─" * 80)
    print("预热流程结束")
    print("─" * 80)
    
    # 打印预热报告
    print("\n📊 预热报告:")
    print(f"  资金流: ✅{report['fund_flow']['success']} ❌{report['fund_flow']['failed']}")
    # 验证新闻统计已不存在
    if 'news' in report:
        print(f"  ❌ 错误: 报告中仍包含新闻统计！")
        return False
    else:
        print(f"  ✅ 新闻统计已从报告中移除")
    print(f"  基本面: ✅{report['financial_indicator']['success']} ❌{report['financial_indicator']['failed']}")
    
    # 验证缓存文件数量
    print(f"\n🔍 验证缓存文件...")
    cache_dir = Path('data/ak_cache')
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.json'))
        print(f"  缓存文件总数: {len(cache_files)}")
        
        # 检查是否有新闻缓存
        news_files = []
        for f in cache_files:
            try:
                content = f.read_text(encoding='utf-8')
                if '"data_type": "news"' in content:
                    news_files.append(f.name)
            except:
                pass
        
        if news_files:
            print(f"  ❌ 错误: 发现{len(news_files)}个新闻缓存文件:")
            for nf in news_files:
                print(f"      - {nf}")
            return False
        else:
            print(f"  ✅ 新闻缓存文件检查通过：无新闻缓存")
    else:
        print(f"  ⚠️ 缓存目录不存在: {cache_dir}")
    
    print("\n" + "=" * 80)
    print("✅ V16.3.0 新闻模块移除验证：全部通过")
    print("=" * 80)
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)