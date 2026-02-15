#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动竞价快照采集器 - 简化版

功能：
1. 自动在9:25采集竞价快照
2. 保存到SQLite和Redis
3. 无需历史数据依赖
4. 支持Windows任务计划程序

使用方法：
    # 直接运行（自动检测时间）
    python tools/auto_auction_collector.py

    # 指定日期（用于测试）
    python tools/auto_auction_collector.py --date 2026-02-13

配置Windows任务计划程序：
    1. 打开任务计划程序
    2. 创建基本任务
    3. 触发器：每天 9:25
    4. 操作：启动程序
    5. 程序：python
    6. 参数：E:\MyQuantTool\tools\auto_auction_collector.py
    7. 起始于：E:\MyQuantTool
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.utils.logger import get_logger
from logic.database_manager import DatabaseManager
from logic.auction_snapshot_manager import AuctionSnapshotManager
from logic.data.qmt_manager import QMTManager

logger = get_logger(__name__)


class SimpleAuctionCollector:
    """简化版竞价快照采集器"""

    def __init__(self):
        """初始化采集器"""
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        # 强制初始化Redis连接
        try:
            self.db_manager._init_redis()
            self.db_manager._redis_initialized = True
            logger.info("✅ Redis连接已强制初始化")
        except Exception as e:
            logger.warning(f"⚠️ Redis初始化失败: {e}")

        # 初始化竞价快照管理器
        self.snapshot_manager = AuctionSnapshotManager(self.db_manager)

        # 初始化QMT管理器
        self.qmt_manager = QMTManager()

        # 数据库路径
        self.db_path = project_root / "data" / "auction_snapshots.db"

        logger.info(f"✅ 自动竞价采集器初始化完成")
        logger.info(f"💾 Redis状态: {'可用' if self.snapshot_manager.is_available else '不可用'}")
        logger.info(f"📊 QMT连接: {'已连接' if self.qmt_manager.data_connected else '未连接'}")

    def get_all_stocks(self):
        """获取全市场股票列表"""
        try:
            if self.qmt_manager.data_connected and self.qmt_manager.xtdata:
                stocks = self.qmt_manager.xtdata.get_stock_list_in_sector('沪深A股')
                logger.info(f"✅ 从QMT获取到 {len(stocks)} 只股票")
                return stocks
            else:
                logger.error("❌ QMT未连接")
                return []
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            return []

    def collect_auction_snapshot(self, date=None):
        """
        采集竞价快照

        Args:
            date: 日期字符串（格式：YYYY-MM-DD），默认为今天
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        logger.info("=" * 80)
        logger.info(f"🚀 开始采集 {date} 竞价快照")
        logger.info("=" * 80)

        # 获取股票列表
        stocks = self.get_all_stocks()
        if not stocks:
            logger.error("❌ 无法获取股票列表，采集失败")
            return {'total': 0, 'success': 0, 'failed': 0}

        total = len(stocks)
        batch_size = 500
        total_batches = (total + batch_size - 1) // batch_size

        logger.info(f"📊 共需采集 {total} 只股票，分 {total_batches} 批次")

        # 批量采集
        success_count = 0
        failed_count = 0

        for i in range(0, total, batch_size):
            batch_codes = stocks[i:i + batch_size]
            batch_num = i // batch_size + 1

            logger.info(f"🔄 处理第 {batch_num}/{total_batches} 批次（{len(batch_codes)} 只股票）")

            try:
                # 获取tick数据
                if self.qmt_manager.xtdata:
                    tick_data = self.qmt_manager.xtdata.get_full_tick(batch_codes)
                else:
                    logger.error("❌ QMT xtdata不可用")
                    tick_data = None

                if not tick_data:
                    logger.warning(f"⚠️ 第 {batch_num} 批次未获取到数据")
                    failed_count += len(batch_codes)
                    continue

                # 处理每只股票
                batch_snapshots = []

                for code in batch_codes:
                    if code not in tick_data:
                        failed_count += 1
                        continue

                    try:
                        data = tick_data[code]

                        # 计算涨跌幅
                        last_price = data.get('lastPrice', 0)
                        last_close = data.get('lastClose', 0)

                        if last_close > 0:
                            auction_change = (last_price - last_close) / last_close
                        else:
                            auction_change = 0.0

                        # 提取数据
                        auction_volume = data.get('volume', 0)
                        auction_amount = data.get('amount', 0)

                        # 创建竞价快照
                        snapshot = {
                            'date': date,
                            'code': code,
                            'name': data.get('stockName', ''),
                            'auction_time': f"{date} 09:25:00",
                            'auction_price': last_price,
                            'auction_volume': auction_volume,
                            'auction_amount': auction_amount,
                            'auction_change': auction_change,
                            'volume_ratio': 0.0,  # 🔥 不计算量比
                            'buy_orders': 0,
                            'sell_orders': 0,
                            'bid_vol_1': data.get('bidVol', [0])[0] if data.get('bidVol') else 0,
                            'ask_vol_1': data.get('askVol', [0])[0] if data.get('askVol') else 0,
                            'market_type': 'SH' if code.endswith('.SH') else 'SZ',
                            'volume_ratio_valid': 0,
                            'data_source': 'production'
                        }

                        batch_snapshots.append(snapshot)

                        # 保存到Redis
                        if self.snapshot_manager.is_available:
                            self.snapshot_manager.save_auction_snapshot(code, snapshot)

                    except Exception as e:
                        logger.warning(f"⚠️ 处理 {code} 失败: {e}")
                        failed_count += 1

                # 批量保存到SQLite
                saved_count = self.save_batch(batch_snapshots)
                success_count += saved_count

                logger.info(f"✅ 批次 {batch_num} 完成: 保存 {saved_count}/{len(batch_codes)} 只")

            except Exception as e:
                logger.error(f"❌ 第 {batch_num} 批次失败: {e}")
                failed_count += len(batch_codes)

        logger.info("=" * 80)
        logger.info(f"✅ 采集完成 - 总数: {total}, 成功: {success_count}, 失败: {failed_count}")
        logger.info("=" * 80)

        return {'total': total, 'success': success_count, 'failed': failed_count}

    def save_batch(self, snapshots):
        """批量保存到SQLite"""
        if not snapshots:
            return 0

        try:
            import sqlite3

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # 确保表存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auction_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT,
                    auction_time TEXT,
                    auction_price REAL,
                    auction_volume INTEGER,
                    auction_amount REAL,
                    auction_change REAL,
                    volume_ratio REAL,
                    buy_orders INTEGER,
                    sell_orders INTEGER,
                    bid_vol_1 INTEGER,
                    ask_vol_1 INTEGER,
                    market_type TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, code)
                )
            """)

            # 批量插入
            cursor.executemany("""
                INSERT OR REPLACE INTO auction_snapshots (
                    date, code, name, auction_time, auction_price, auction_volume,
                    auction_amount, auction_change, volume_ratio, buy_orders,
                    sell_orders, bid_vol_1, ask_vol_1, market_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (s['date'], s['code'], s['name'], s['auction_time'],
                 s['auction_price'], s['auction_volume'], s['auction_amount'],
                 s['auction_change'], s['volume_ratio'], s['buy_orders'],
                 s['sell_orders'], s['bid_vol_1'], s['ask_vol_1'], s['market_type'])
                for s in snapshots
            ])

            conn.commit()
            conn.close()

            return len(snapshots)

        except Exception as e:
            logger.error(f"❌ 批量保存失败: {e}")
            return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动竞价快照采集器')
    parser.add_argument('--date', type=str, help='采集日期（格式：YYYY-MM-DD）')
    args = parser.parse_args()

    # 初始化采集器
    collector = SimpleAuctionCollector()

    # 采集竞价快照
    result = collector.collect_auction_snapshot(date=args.date)

    # 显示结果
    print(f"\n✅ 采集完成: 成功 {result['success']}/{result['total']}")


if __name__ == "__main__":
    main()