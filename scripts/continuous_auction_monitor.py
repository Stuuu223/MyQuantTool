#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续竞价监控脚本 - 自动检测时间并触发竞价快照保存

功能：
1. 持续运行，自动检测当前时间
2. 在竞价时间（9:15-9:25）自动触发竞价快照保存
3. 在竞价结束时（9:25-9:30）执行最终保存
4. 9:30后自动退出

使用方法：
    python scripts/continuous_auction_monitor.py

Author: MyQuantTool Team
Date: 2026-02-11
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, time as dt_time
from logic.utils.logger import get_logger

logger = get_logger(__name__)


def run_auction_snapshot():
    """执行竞价快照保存"""
    try:
        from scripts.auction_snapshot_daemon import AuctionSnapshotDaemon

        # 创建守护进程实例（内部会自动初始化DatabaseManager和AuctionSnapshotManager）
        daemon = AuctionSnapshotDaemon()

        # 保存竞价快照
        result = daemon.save_market_auction_snapshot()

        logger.info(f"✅ 竞价快照保存完成: {result['saved']}/{result['total']} ({result['saved']/result['total']*100:.1f}%)")

        return result

    except Exception as e:
        logger.error(f"❌ 竞价快照保存失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def continuous_monitor():
    """持续监控竞价时间"""
    logger.info("=" * 80)
    logger.info("🚀 持续竞价监控启动")
    logger.info("=" * 80)

    # 标记是否已完成最终保存
    final_snapshot_saved = False

    while True:
        try:
            now = datetime.now()
            current_time = now.time()

            # 🔥 关键窗口：9:25-9:30（竞价结束，数据仍可用）
            if dt_time(9, 25, 0) <= current_time < dt_time(9, 30, 0):
                if not final_snapshot_saved:
                    logger.info(f"\n⏰ {now.strftime('%H:%M:%S')} 竞价已结束，开始最终保存")
                    logger.info("=" * 80)

                    result = run_auction_snapshot()

                    if result:
                        final_snapshot_saved = True
                        logger.info("=" * 80)
                        logger.info("✅ 最终竞价快照保存完成，等待连续竞价开始...")

                        # 等待到 9:30
                        wait_seconds = (
                            datetime.combine(now.date(), dt_time(9, 30, 0)) - now
                        ).total_seconds()
                        logger.info(f"⏳ 距离连续竞价开始还有 {wait_seconds:.0f} 秒")

                        import time
                        time.sleep(wait_seconds + 5)

                        logger.info("✅ 今日竞价监控任务已完成，程序退出")
                        break
                    else:
                        logger.error("❌ 最终保存失败，重试...")
                        import time
                        time.sleep(10)
                else:
                    # 已保存，等待退出
                    import time
                    time.sleep(30)

            # 9:15-9:24: 竞价进行中，每分钟保存一次
            elif dt_time(9, 15, 0) <= current_time < dt_time(9, 25, 0):
                logger.info(f"\n⏰ {now.strftime('%H:%M:%S')} 竞价进行中，保存快照...")
                result = run_auction_snapshot()

                # 等待 60 秒
                logger.info("⏳ 等待 60 秒...")
                import time
                time.sleep(60)

            # 9:30 后：退出
            elif current_time >= dt_time(9, 30, 0):
                logger.info(f"⏰ {now.strftime('%H:%M:%S')} 连续竞价已开始")
                logger.info("✅ 今日竞价监控任务已完成，程序退出")
                break

            # 9:15 前：等待
            else:
                wait_seconds = (
                    datetime.combine(now.date(), dt_time(9, 15, 0)) - now
                ).total_seconds()

                if wait_seconds > 3600:  # 超过1小时，显示小时数
                    logger.info(f"⏰ 当前时间: {now.strftime('%H:%M:%S')} (等待竞价开始，还有 {wait_seconds/3600:.1f} 小时)")
                else:
                    logger.info(f"⏰ 当前时间: {now.strftime('%H:%M:%S')} (等待竞价开始，还有 {wait_seconds/60:.1f} 分钟)")

                import time
                time.sleep(60)  # 每分钟检查一次

        except KeyboardInterrupt:
            logger.info("\n⚠️ 用户中断，程序退出")
            break
        except Exception as e:
            logger.error(f"❌ 监控异常: {e}")
            import traceback
            traceback.print_exc()

            import time
            time.sleep(30)  # 异常后等待30秒再继续


def main():
    """主函数"""
    continuous_monitor()


if __name__ == "__main__":
    main()