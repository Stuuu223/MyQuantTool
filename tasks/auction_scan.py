#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价扫描脚本（09:20执行）

自动扫描集合竞价异动股票

Author: MyQuantTool Team
Date: 2026-02-12
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from logic.full_market_scanner import FullMarketScanner
from logic.signal_tracker.signal_recorder import get_signal_recorder
from logic.logger import get_logger

logger = get_logger(__name__)


def main():
    """竞价扫描主函数"""
    logger.info("=" * 80)
    logger.info(f"🔔 竞价扫描开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    try:
        # 1. 初始化扫描器
        scanner = FullMarketScanner()
        recorder = get_signal_recorder()

        # 2. 执行竞价扫描
        results = scanner.scan_with_risk_management(mode='premarket')

        # 3. 记录候选池
        for stock in results['opportunities']:
            recorder.record_auction_candidate(
                code=stock['code'],
                name=stock.get('name', ''),
                reason=','.join(stock.get('scenario_reasons', [])),
                decision_tag=stock.get('decision_tag', 'FOCUS✅'),
                risk_score=stock.get('risk_score', 0),
                hot_score=stock.get('hot_score', 0),
                sector_name=stock.get('sector_name', '')
            )

        # 4. 输出结果
        logger.info(f"\n✅ 竞价扫描完成")
        logger.info(f"   机会池: {len(results['opportunities'])} 只")
        logger.info(f"   观察池: {len(results['watchlist'])} 只")
        logger.info(f"   黑名单: {len(results['blacklist'])} 只")

        # 5. 显示TOP5
        if results['opportunities']:
            logger.info(f"\n🎯 机会池 TOP5:")
            for idx, stock in enumerate(results['opportunities'][:5], 1):
                logger.info(f"   {idx}. {stock['code']} {stock.get('name', '')} "
                           f"风险={stock.get('risk_score', 0):.2f} "
                           f"热度={stock.get('hot_score', 0):.4f}")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 竞价扫描失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()