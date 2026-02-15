#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价快照调度采集器 - CTO架构决策版

核心架构决策（2026-02-13 CTO批准）：
1. 触发方式：内置Spin-wait循环（精度要求，不接受任务计划的不确定性）
2. 采集时间：09:25:03（避开数据传输延迟，确保已撮合）
3. 失败重试：Redis快速失败 / SQLite异步无限重试
4. 预热检查：09:24:00，失败时报警（不自动降级）
5. Redis过期：25小时（安全边际）

运行方式：
    python tasks/scheduled_auction_collector.py

特性：
- 精准时间控制（自旋等待，误差<10ms）
- QMT连接预热（09:24:00）
- Redis热数据极速写入
- SQLite异步归档
- 下游策略触发通知

Author: MyQuantTool CTO Team
Date: 2026-02-13
Version: V1.0 (CTO架构决策版)
"""

import sys
import os
import time
import json
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.utils.logger import get_logger
from logic.database_manager import DatabaseManager
from logic.auction_snapshot_manager import AuctionSnapshotManager
from logic.data.qmt_manager import QMTManager

logger = get_logger(__name__)


class ScheduledAuctionCollector:
    """
    竞价快照调度采集器

    核心流程：
    1. 09:24:00 - QMT连接预热
    2. 09:25:03 - 精准触发采集
    3. 极速写入Redis（热数据）
    4. 异步归档SQLite（冷数据）
    5. 触发下游策略
    """

    def __init__(self):
        """初始化采集器"""
        logger.info("=" * 80)
        logger.info("🟢 竞价采集守护进程启动")
        logger.info("=" * 80)

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

        # SQLite异步写入队列
        self.sqlite_queue = queue.Queue()
        self.sqlite_worker_thread = None
        self.sqlite_worker_running = False

        # 数据库路径
        self.db_path = project_root / "data" / "auction_snapshots.db"

        # 全市场股票代码（缓存）
        self.all_codes = []

        # 预热状态
        self.has_warmup = False

        logger.info(f"💾 Redis状态: {'可用' if self.snapshot_manager.is_available else '不可用'}")
        logger.info(f"📊 QMT连接: {'已连接' if self.qmt_manager.data_connected else '未连接'}")

        # 启动SQLite异步写入线程
        self._start_sqlite_worker()

    def _start_sqlite_worker(self):
        """启动SQLite异步写入工作线程"""
        self.sqlite_worker_running = True
        self.sqlite_worker_thread = threading.Thread(
            target=self._sqlite_worker_loop,
            name="SQLiteWorker",
            daemon=True
        )
        self.sqlite_worker_thread.start()
        logger.info("✅ SQLite异步写入线程已启动")

    def _sqlite_worker_loop(self):
        """SQLite异步写入工作循环"""
        logger.info("🔄 SQLite异步写入工作线程已就绪")

        while self.sqlite_worker_running:
            try:
                # 从队列获取任务（阻塞等待，超时1秒）
                task = self.sqlite_queue.get(timeout=1.0)

                if task is None:  # 停止信号
                    break

                # 执行写入任务
                try:
                    self._save_to_sqlite_sync(task['data'], task['date'])
                    self.sqlite_queue.task_done()
                except Exception as e:
                    logger.error(f"❌ SQLite写入失败，重新排队: {e}")
                    # 失败重新排队（无限重试）
                    self.sqlite_queue.put(task)
                    time.sleep(1.0)  # 延迟后重试

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ SQLite工作线程异常: {e}")
                time.sleep(1.0)

        logger.info("🛑 SQLite异步写入工作线程已停止")

    def _load_all_codes(self):
        """加载全市场股票代码"""
        try:
            if self.qmt_manager.data_connected and self.qmt_manager.xtdata:
                stocks = self.qmt_manager.xtdata.get_stock_list_in_sector('沪深A股')
                self.all_codes = stocks
                logger.info(f"✅ 已加载全市场股票代码: {len(stocks)} 只")
                return stocks
            else:
                logger.error("❌ QMT未连接，无法获取股票列表")
                return []
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            return []

    def warmup_qmt_connection(self):
        """
        预热QMT连接（09:24:00触发）

        策略：
        - 测试获取600519.SH的tick数据
        - 失败时打印红色高亮报警
        - 不自动降级（宁可不交易，不用错误数据）
        """
        logger.info("=" * 80)
        logger.info("🔥 [09:24:00] 开始QMT连接预热...")
        logger.info("=" * 80)

        try:
            if not self.qmt_manager.data_connected or not self.qmt_manager.xtdata:
                raise ValueError("QMT未连接")

            # 测试获取一只活跃股
            test_data = self.qmt_manager.xtdata.get_full_tick(['600519.SH'])

            if not test_data or '600519.SH' not in test_data:
                raise ValueError("QMT返回空数据")

            logger.info("✅ QMT连接正常，预热完成")
            logger.info(f"   测试数据: {test_data['600519.SH'].get('lastPrice', 0):.2f}")

        except Exception as e:
            logger.error("=" * 80)
            logger.error("❌ 严重警告：QMT连接异常！")
            logger.error(f"   错误信息: {e}")
            logger.error("   请在1分钟内检查QMT客户端！")
            logger.error("=" * 80)

            # Windows弹窗强提醒（如果可用）
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"QMT连接异常！\n错误: {e}\n\n请立即检查QMT客户端！",
                    "竞价采集器 - 严重警告",
                    0x10 | 0x1  # MB_ICONERROR | MB_SYSTEMMODAL
                )
            except:
                pass

            # 不自动降级，等待人工介入
            raise

    def save_to_redis_pipeline(self, raw_data: Dict[str, Any], date: str):
        """
        极速写入Redis（热数据）

        策略：
        - 使用Redis Pipeline批量写入
        - 快速失败（仅重试1次）
        - 过期时间：25小时
        """
        if not self.snapshot_manager.is_available:
            logger.warning("⚠️ Redis不可用，跳过热数据写入")
            return

        logger.info("⚡️ 开始Redis热数据极速写入...")

        try:
            t0 = time.time()

            # 使用Pipeline批量写入
            if self.db_manager._redis_client:
                import redis
                pipe = self.db_manager._redis_client.pipeline()

                # 批量设置（过期25小时）
                expire_seconds = 25 * 3600

                for code, data in raw_data.items():
                    # 简单清洗
                    auction_data = {
                        'code': code,
                        'last_price': data.get('lastPrice', 0),
                        'last_close': data.get('lastClose', 0),
                        'volume': data.get('volume', 0),
                        'amount': data.get('amount', 0),
                        'timestamp': datetime.now().isoformat()
                    }

                    key = f"auction:{date}:{code}"
                    pipe.set(key, json.dumps(auction_data), ex=expire_seconds)

                # 执行批量写入
                pipe.execute()

                elapsed = time.time() - t0
                logger.info(f"✅ Redis热数据写入完成: {len(raw_data)} 只股票, 耗时 {elapsed:.3f}s")

        except Exception as e:
            logger.error(f"❌ Redis写入失败（快速失败）: {e}")
            # 不重试，快速失败

    def save_to_sqlite_async(self, raw_data: Dict[str, Any], date: str):
        """
        异步归档SQLite（冷数据）

        策略：
        - 放入队列，异步处理
        - 无限重试（晚10分钟写入也没关系）
        """
        logger.info("📦 SQLite归档任务已加入队列（异步处理）")

        task = {
            'data': raw_data,
            'date': date,
            'timestamp': datetime.now().isoformat()
        }

        self.sqlite_queue.put(task)

    def _save_to_sqlite_sync(self, raw_data: Dict[str, Any], date: str):
        """
        同步写入SQLite（由工作线程调用）
        """
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
        snapshots = []

        for code, data in raw_data.items():
            last_price = data.get('lastPrice', 0)
            last_close = data.get('lastClose', 0)

            if last_close > 0:
                auction_change = (last_price - last_close) / last_close
            else:
                auction_change = 0.0

            snapshot = {
                'date': date,
                'code': code,
                'name': data.get('stockName', ''),
                'auction_time': f"{date} 09:25:00",
                'auction_price': last_price,
                'auction_volume': data.get('volume', 0),
                'auction_amount': data.get('amount', 0),
                'auction_change': auction_change,
                'volume_ratio': 0.0,
                'buy_orders': 0,
                'sell_orders': 0,
                'bid_vol_1': data.get('bidVol', [0])[0] if data.get('bidVol') else 0,
                'ask_vol_1': data.get('askVol', [0])[0] if data.get('askVol') else 0,
                'market_type': 'SH' if code.endswith('.SH') else 'SZ'
            }

            snapshots.append(snapshot)

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

        logger.info(f"✅ SQLite归档完成: {len(snapshots)} 只股票")

    def notify_strategy_analyzers(self):
        """
        触发下游策略分析器

        策略：
        - 写入Redis通知标记
        - 策略分析器监听此标记
        - 非阻塞方式
        """
        if not self.snapshot_manager.is_available:
            return

        try:
            today = datetime.now().strftime("%Y%m%d")
            notification_key = f"auction:notification:{today}"
            self.db_manager._redis_client.set(
                notification_key,
                json.dumps({
                    'status': 'ready',
                    'timestamp': datetime.now().isoformat(),
                    'message': '竞价数据已就绪，策略分析器可以开始工作'
                }),
                ex=3600  # 1小时过期
            )
            logger.info("📢 已发送通知：竞价数据就绪")
        except Exception as e:
            logger.warning(f"⚠️ 发送策略通知失败: {e}")

    def run_daily(self):
        """
        运行每日调度采集

        核心流程：
        1. 智能预热（09:24:00）
        2. 精准捕获（09:25:03）
        3. 极速采集
        4. Redis热写入
        5. 触发策略
        6. SQLite异步归档
        """
        logger.info("🟢 竞价采集守护进程已启动，等待目标时间...")

        # 提前加载股票代码
        self._load_all_codes()

        if not self.all_codes:
            logger.error("❌ 无法获取股票列表，退出")
            return

        # 自旋等待循环
        while True:
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            date = now.strftime("%Y-%m-%d")

            # --- 阶段1: 智能预热（09:24:00）---
            if current_time >= "09:24:00" and not self.has_warmup:
                try:
                    self.warmup_qmt_connection()
                    self.has_warmup = True
                except Exception as e:
                    logger.error(f"❌ 预热失败，继续等待人工介入...")
                    # 预热失败后继续循环，等待人工修复

            # --- 阶段2: 精准捕获（09:25:03）---
            if current_time >= "09:25:03" and self.has_warmup:
                logger.info("=" * 80)
                logger.info("🚀 [09:25:03] 窗口触发！开始极速采集...")
                logger.info("=" * 80)
                break

            # 极低资源消耗的自旋（10ms）
            time.sleep(0.01)

        # --- 阶段3: 核心执行 ---
        try:
            t0 = time.time()

            # 1. 立即获取全市场快照（IO密集）
            logger.info(f"📡 正在获取全市场快照（{len(self.all_codes)} 只股票）...")

            if self.qmt_manager.xtdata:
                raw_data = self.qmt_manager.xtdata.get_full_tick(self.all_codes)
            else:
                raise ValueError("QMT xtdata不可用")

            if not raw_data:
                raise ValueError("QMT返回空数据")

            logger.info(f"✅ 获取到 {len(raw_data)} 只股票的快照数据")

            # 2. 极速清洗 + Redis写入（CPU密集）
            self.save_to_redis_pipeline(raw_data, date)

            elapsed_redis = time.time() - t0
            logger.info(f"⚡️ Redis热数据就绪，总耗时 {elapsed_redis:.3f}s")

            # 3. 触发下游策略（非阻塞）
            self.notify_strategy_analyzers()

            # 4. 慢速归档（异步）
            self.save_to_sqlite_async(raw_data, date)

            total_elapsed = time.time() - t0
            logger.info("=" * 80)
            logger.info(f"✅ 竞价采集核心流程完成，总耗时 {total_elapsed:.3f}s")
            logger.info("=" * 80)

        except Exception as e:
            logger.critical(f"❌ 竞价采集核心流程崩溃: {e}")
            logger.critical("请立即检查系统状态！")

    def stop(self):
        """停止采集器"""
        logger.info("🛑 正在停止竞价采集器...")

        # 停止SQLite工作线程
        self.sqlite_worker_running = False
        if self.sqlite_worker_thread:
            self.sqlite_queue.put(None)  # 发送停止信号
            self.sqlite_worker_thread.join(timeout=5.0)

        logger.info("✅ 竞价采集器已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='竞价快照调度采集器 - CTO架构决策版')
    parser.add_argument('--test', action='store_true', help='测试模式（立即执行，不等待时间）')
    parser.add_argument('--date', type=str, help='测试日期（格式：YYYY-MM-DD）')

    args = parser.parse_args()

    collector = ScheduledAuctionCollector()

    try:
        if args.test:
            # 测试模式：立即执行
            date = args.date or datetime.now().strftime("%Y-%m-%d")
            logger.info(f"🧪 测试模式：立即执行采集 {date}")

            # 加载股票代码
            collector._load_all_codes()

            # 模拟采集
            if collector.qmt_manager.xtdata:
                raw_data = collector.qmt_manager.xtdata.get_full_tick(collector.all_codes[:100])  # 只采集100只测试

                collector.save_to_redis_pipeline(raw_data, date)
                collector.notify_strategy_analyzers()
                collector.save_to_sqlite_async(raw_data, date)

                logger.info("✅ 测试采集完成")
        else:
            # 正常模式：等待时间
            collector.run_daily()

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断")
    finally:
        collector.stop()


if __name__ == "__main__":
    main()