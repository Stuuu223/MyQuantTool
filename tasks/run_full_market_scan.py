#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全市场三漏斗扫描启动脚本（V11.0.1 架构重构版）

功能：
- 简化的调度入口，只负责调用 FullMarketScanner
- 输出逻辑已下沉到 core 层

Usage:
    python tasks/run_full_market_scan.py --mode premarket
    python tasks/run_full_market_scan.py --mode intraday
    python tasks/run_full_market_scan.py --mode postmarket
"""

import sys
import os
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.strategies.full_market_scanner import FullMarketScanner
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='全市场三漏斗扫描系统（V11.0.1 架构重构版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  盘前扫描（9:00前）:
    python tasks/run_full_market_scan.py --mode premarket
  
  盘中扫描（交易时间）:
    python tasks/run_full_market_scan.py --mode intraday
  
  盘后复盘（15:00后）:
    python tasks/run_full_market_scan.py --mode postmarket

输出文件：
  data/scan_results/YYYY-MM-DD_{mode}.json
        """
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='premarket',
        choices=['premarket', 'intraday', 'postmarket'],
        help='扫描模式（默认: premarket）'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/market_scan_config.json',
        help='配置文件路径'
    )
    
    args = parser.parse_args()
    
    # 🎯 [V11.0.1] 简化脚本层：只负责调度，不负责输出逻辑
    try:
        # 初始化扫描器
        scanner = FullMarketScanner(config_path=args.config)
        
        # 执行扫描（带风险管理）
        # 输出逻辑已下沉到 FullMarketScanner.scan_with_risk_management()
        results = scanner.scan_with_risk_management(mode=args.mode)
        
        # 返回结果状态码
        if results.get('opportunities'):
            sys.exit(0)  # 有机会池
        elif results.get('watchlist'):
            sys.exit(1)  # 只有观察池
        else:
            sys.exit(2)  # 无结果
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断扫描")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ 扫描失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
