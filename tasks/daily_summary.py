#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日统计脚本（14:55执行）

汇总当日交易信号和结果

Author: MyQuantTool Team
Date: 2026-02-12
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from logic.signal_tracker.signal_recorder import get_signal_recorder
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """每日统计主函数"""
    logger.info("=" * 80)
    logger.info(f"📊 每日统计开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    try:
        recorder = get_signal_recorder()

        # 1. 获取统计数据（最近7天）
        stats_7d = recorder.get_statistics(days=7)

        # 2. 获取统计数据（最近30天）
        stats_30d = recorder.get_statistics(days=30)

        # 3. 输出报告
        logger.info("\n📈 近7日统计:")
        logger.info(f"   总信号: {stats_7d['total_signals']}")
        logger.info(f"   总交易: {stats_7d['total_trades']}")
        logger.info(f"   胜率: {stats_7d['win_rate']:.1f}%")
        logger.info(f"   平均收益: {stats_7d['avg_return']:+.2f}%")
        logger.info(f"   最大盈利: {stats_7d['max_gain']:+.2f}%")
        logger.info(f"   最大亏损: {stats_7d['max_loss']:+.2f}%")

        logger.info("\n📈 近30日统计:")
        logger.info(f"   总信号: {stats_30d['total_signals']}")
        logger.info(f"   总交易: {stats_30d['total_trades']}")
        logger.info(f"   胜率: {stats_30d['win_rate']:.1f}%")
        logger.info(f"   平均收益: {stats_30d['avg_return']:+.2f}%")

        # 4. 导出报告
        recorder.export_report(days=30)

        # 5. 评估系统状态
        if stats_7d['total_trades'] >= 10:
            if stats_7d['win_rate'] >= 60:
                logger.info("\n✅ 系统状态: 良好（胜率≥60%）")
            elif stats_7d['win_rate'] >= 50:
                logger.info("\n⚠️  系统状态: 可接受（胜率50-60%）")
            else:
                logger.info("\n❌ 系统状态: 需优化（胜率<50%）")
        else:
            logger.info("\n⏳ 样本不足，继续积累数据...")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 每日统计失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()