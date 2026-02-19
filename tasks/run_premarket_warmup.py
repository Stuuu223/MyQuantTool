#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘前预热脚本 (V16.2 - AkShare数据预热)

功能：
1. 预热昨日涨停池（用于计算晋级率）
2. 预热昨日龙虎榜（用于判断游资/机构属性）
3. 预热核心池个股资金流（用于判断主力潜伏）
4. 预热核心池个股新闻（用于舆情风控）
5. 生成预热报告

Usage:
    python tasks/run_premarket_warmup.py

Schedule:
    每天早上08:30自动运行

Author: MyQuantTool Team
Date: 2026-02-16
Version: V16.2
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.data_providers.akshare_manager import AkShareDataManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    print("=" * 80)
    print("盘前预热脚本 (V16.2 - AkShare数据预热)")
    print("=" * 80)
    
    print("\n📋 预热清单:")
    print("  1. 昨日涨停池（用于计算晋级率）")
    print("  2. 昨日龙虎榜（用于判断游资/机构属性）")
    print("  3. 核心池个股资金流（用于判断主力潜伏）")
    print("  4. 核心池个股新闻（用于舆情风控）")
    print("  5. 生成预热报告")
    
    print("\n🚀 开始预热...")
    
    # 创建预热模式的管理器
    manager = AkShareDataManager(mode='warmup')
    
    # 预热所有数据
    report = manager.warmup_all()
    
    # 打印预热报告
    print("\n📊 预热报告:")
    print(f"  涨停池: ✅{report['limit_up_pool']['success']} ❌{report['limit_up_pool']['failed']}")
    print(f"  龙虎榜: ✅{report['lhb_detail']['success']} ❌{report['lhb_detail']['failed']}")
    print(f"  资金流: ✅{report['fund_flow']['success']} ❌{report['fund_flow']['failed']}")
    print(f"  新闻: ✅{report['news']['success']} ❌{report['news']['failed']}")
    print(f"  基本面: ✅{report['financial_indicator']['success']} ❌{report['financial_indicator']['failed']}")
    
    # 计算总成功率
    total_success = sum([r['success'] for r in report.values()])
    total_failed = sum([r['failed'] for r in report.values()])
    success_rate = total_success / (total_success + total_failed) * 100 if (total_success + total_failed) > 0 else 0
    
    print(f"\n📈 总成功率: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("✅ 预热成功，盘中可以使用缓存数据")
    else:
        print("⚠️ 预热成功率较低，部分数据可能缺失")
    
    print("\n" + "=" * 80)
    print("✅ 盘前预热完成")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断预热")
    except Exception as e:
        print(f"\n❌ 预热失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
