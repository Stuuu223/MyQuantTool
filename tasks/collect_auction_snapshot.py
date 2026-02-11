#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价快照采集脚本 (Phase3 第1周) - 数据修复版

功能：
1. 每个交易日09:25采集全市场竞价快照（批量API）
2. 手动计算涨跌幅和量比（QMT API不返回这些字段）
3. 保存竞价数据到SQLite和Redis

使用方法：
    # 采集今日竞价快照
    python tasks/collect_auction_snapshot.py
    
    # 采集指定日期竞价快照（用于补数据）
    python tasks/collect_auction_snapshot.py --date 2026-02-10
    
    # 批量采集历史竞价快照
    python tasks/collect_auction_snapshot.py --start-date 2026-02-01 --end-date 2026-02-10

数据保存：
- SQLite: data/auction_snapshots.db
- Redis: auction:YYYYMMDD:CODE (24小时过期)

性能：
- 批量采集：500只/批
- 预期速度：5190只股票 < 30秒
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from logic.logger import get_logger
from logic.database_manager import DatabaseManager
from logic.auction_snapshot_manager import AuctionSnapshotManager

logger = get_logger(__name__)


class AuctionSnapshotCollector:
    """
    竞价快照采集器
    
    负责采集全市场竞价数据并保存到数据库
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化采集器
        
        Args:
            db_path: SQLite数据库路径（默认：data/auction_snapshots.db）
        """
        # 数据库路径
        if db_path is None:
            db_path = project_root / "data" / "auction_snapshots.db"
        else:
            db_path = Path(db_path)
        
        # 确保数据目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        self.db_path = str(db_path)
        
        # 初始化竞价快照管理器
        self.snapshot_manager = AuctionSnapshotManager(self.db_manager)
        
        # 初始化数据库表
        self._init_database()
        
        logger.info(f"✅ 竞价快照采集器初始化成功")
        logger.info(f"📁 数据库路径: {self.db_path}")
        logger.info(f"💾 Redis状态: {'可用' if self.snapshot_manager.is_available else '不可用'}")
    
    def _init_database(self):
        """
        初始化SQLite数据库表
        """
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建竞价快照表
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
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_date 
                ON auction_snapshots(date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_code 
                ON auction_snapshots(code)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_date_code 
                ON auction_snapshots(date, code)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ 数据库表初始化成功")
        
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
    
    def get_all_stock_codes(self) -> List[str]:
        """
        获取全市场股票代码列表
        
        Returns:
            股票代码列表
        """
        try:
            # 尝试从QMT获取股票列表
            try:
                import xtquant.xtdata as xtdata
                
                # 获取所有A股代码
                sh_stocks = xtdata.get_stock_list_in_sector("沪深A股")
                logger.info(f"✅ 从QMT获取到 {len(sh_stocks)} 只股票")
                return sh_stocks
            
            except Exception as e:
                logger.warning(f"⚠️ QMT获取失败: {e}，尝试使用AkShare")
                
                # 备用方案：使用AkShare
                import akshare as ak
                
                stock_list = ak.stock_info_a_code_name()
                codes = stock_list['code'].tolist()
                
                # 转换为QMT格式（6位数字+市场后缀）
                formatted_codes = []
                for code in codes:
                    if code.startswith('6'):
                        formatted_codes.append(f"{code}.SH")
                    elif code.startswith(('0', '3')):
                        formatted_codes.append(f"{code}.SZ")
                
                logger.info(f"✅ 从AkShare获取到 {len(formatted_codes)} 只股票")
                return formatted_codes
        
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            return []
    
    def get_historical_avg_volume(self, codes: List[str], date: str) -> Dict[str, Optional[float]]:
        """
        获取历史5日平均成交量（用于计算量比）

        Args:
            codes: 股票代码列表
            date: 当前日期

        Returns:
            {code: avg_volume_per_minute}  # None表示无效数据

        数据质量保证：
            - 返回None明确标记无效数据
            - 超过10%数据失败时告警
            - 区分模拟环境和生产环境
        """
        try:
            import xtquant.xtdata as xtdata
            import pandas as pd

            # 🔥 关键修复：使用 get_market_data_ex（项目成功案例使用的API）
            # get_market_data_ex 返回：{code: DataFrame, ...}
            # DataFrame列名是字段名，索引是时间
            hist_data = xtdata.get_market_data_ex(
                field_list=['volume'],
                stock_list=codes,
                period='1d',
                count=5,
                dividend_type='none',
                fill_data=True
            )

            result = {}
            invalid_count = 0

            for code in codes:
                try:
                    # get_market_data_ex 返回结构：{code: DataFrame, ...}
                    if code in hist_data:
                        code_data = hist_data[code]

                        # 检查数据有效性
                        if isinstance(code_data, pd.DataFrame):
                            if 'volume' in code_data.columns and len(code_data) > 0:
                                volumes = code_data['volume'].tolist()
                                valid_vols = [v for v in volumes if v is not None and v > 0]

                                if len(valid_vols) >= 1:  # 至少1天有效数据
                                    avg_volume_per_day = sum(valid_vols) / len(valid_vols)
                                    avg_volume_per_minute = avg_volume_per_day / 240.0
                                    result[code] = avg_volume_per_minute
                                else:
                                    result[code] = None
                                    invalid_count += 1
                            else:
                                result[code] = None
                                invalid_count += 1
                        else:
                            result[code] = None
                            invalid_count += 1
                    else:
                        result[code] = None
                        invalid_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ 处理{code}历史数据失败: {e}")
                    result[code] = None
                    invalid_count += 1

            # 数据质量告警
            if len(codes) > 0:
                invalid_rate = invalid_count / len(codes)
                if invalid_rate > 0.5:
                    logger.error(f"❌ 历史数据获取失败率{invalid_rate*100:.1f}% ({invalid_count}/{len(codes)})，可能为QMT模拟环境")
                elif invalid_rate > 0.1:
                    logger.warning(f"⚠️ 历史数据获取失败率{invalid_rate*100:.1f}% ({invalid_count}/{len(codes)})")
                else:
                    logger.debug(f"✅ 历史数据获取成功，失败率{invalid_rate*100:.1f}%")

            return result

        except Exception as e:
            logger.error(f"❌ 获取历史成交量异常: {e}", exc_info=True)
            return {code: None for code in codes}
    
    def save_snapshots_batch(self, snapshots: List[Dict[str, Any]]) -> int:
        """
        批量保存快照到SQLite（使用事务提升性能）

        Args:
            snapshots: 快照列表

        Returns:
            成功保存的数量
        """
        if not snapshots:
            return 0

        try:
            import sqlite3

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 确保表包含数据质量字段（兼容旧数据）
            try:
                cursor.execute("ALTER TABLE auction_snapshots ADD COLUMN volume_ratio_valid INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE auction_snapshots ADD COLUMN data_source TEXT DEFAULT 'unknown'")
                conn.commit()
            except sqlite3.OperationalError:
                # 字段已存在，忽略
                pass

            # 批量插入（使用executemany）
            cursor.executemany("""
                INSERT OR REPLACE INTO auction_snapshots (
                    date, code, name, auction_time, auction_price, auction_volume,
                    auction_amount, auction_change, volume_ratio, buy_orders,
                    sell_orders, bid_vol_1, ask_vol_1, market_type,
                    volume_ratio_valid, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (s['date'], s['code'], s['name'], s['auction_time'],
                 s['auction_price'], s['auction_volume'], s['auction_amount'],
                 s['auction_change'], s['volume_ratio'], s['buy_orders'],
                 s['sell_orders'], s['bid_vol_1'], s['ask_vol_1'], s['market_type'],
                 s.get('volume_ratio_valid', 0), s.get('data_source', 'unknown'))
                for s in snapshots
            ])

            conn.commit()
            conn.close()

            return len(snapshots)

        except sqlite3.DatabaseError as e:
            logger.error(f"❌ 数据库错误: {e}")
            return 0
        except Exception as e:
            logger.error(f"❌ 批量保存失败: {e}", exc_info=True)
            return 0
    
    def collect_all_snapshots_batch(self, date: str = None, batch_size: int = 500) -> Dict[str, int]:
        """
        批量采集全市场竞价快照（使用QMT批量API + 手动计算）
        
        Args:
            date: 日期（格式：YYYY-MM-DD，默认为今天）
            batch_size: 每批次处理的股票数量（默认500）
        
        Returns:
            采集统计信息 {"total": 总数, "success": 成功数, "failed": 失败数}
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"🚀 开始批量采集 {date} 的竞价快照")
        
        # 获取股票列表
        stock_codes = self.get_all_stock_codes()
        total = len(stock_codes)
        
        if total == 0:
            logger.error("❌ 未获取到股票列表")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        total_batches = (total + batch_size - 1) // batch_size
        logger.info(f"📊 共需采集 {total} 只股票，分 {total_batches} 批次，每批 {batch_size} 只")
        
        # 批量采集
        import xtquant.xtdata as xtdata
        
        success_count = 0
        failed_count = 0
        processed = 0
        
        start_time = time.time()
        
        # 分批处理
        for i in range(0, total, batch_size):
            batch_codes = stock_codes[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            batch_start = time.time()
            logger.info(f"🔄 处理第 {batch_num}/{total_batches} 批次（{len(batch_codes)} 只股票）")

            try:
                # 🔥 关键1：批量获取tick数据
                tick_data = xtdata.get_full_tick(batch_codes)

                if not tick_data:
                    logger.warning(f"⚠️ 第 {batch_num} 批次未获取到数据")
                    failed_count += len(batch_codes)
                    continue

                # 🔥 关键2：批量获取历史成交量（用于计算量比）
                avg_volumes = self.get_historical_avg_volume(batch_codes, date)

                # 🔥 三级验证：检查历史数据质量
                if avg_volumes:
                    valid_avg_count = sum(1 for v in avg_volumes.values() if v is not None and v > 0)
                    total_avg_count = len(avg_volumes)
                    invalid_rate = 1 - (valid_avg_count / total_avg_count) if total_avg_count > 0 else 1

                    # 告警阈值：超过50%数据无效，模拟环境
                    if invalid_rate > 0.5:
                        logger.warning(f"⚠️ 批次{batch_num}历史数据无效率{invalid_rate*100:.1f}%，量比计算可能不准确")

                    # ✅ P1修复：拦截阈值：超过90%数据无效，跳过此批次
                    if invalid_rate > 0.9:
                        logger.error(f"❌ 批次{batch_num}历史数据严重缺失（{invalid_rate*100:.1f}%），跳过此批次处理")
                        failed_count += len(batch_codes)
                        continue  # 跳过当前批次，不处理无效数据

                # 准备批量保存的数据
                batch_snapshots = []
                
                # 处理每只股票的数据
                for code in batch_codes:
                    processed += 1
                    
                    if code not in tick_data:
                        failed_count += 1
                        continue
                    
                    try:
                        data = tick_data[code]
                        
                        # 🔥 关键3：手动计算涨跌幅
                        last_price = data.get('lastPrice', 0)
                        last_close = data.get('lastClose', 0)
                        
                        if last_close > 0:
                            auction_change = (last_price - last_close) / last_close
                        else:
                            auction_change = 0.0
                        
                        # 🔥 关键4：手动计算量比（带质量标记）
                        auction_volume = data.get('volume', 0)
                        avg_volume_per_minute = avg_volumes.get(code)

                        # 判断历史数据是否有效
                        volume_ratio_valid = avg_volume_per_minute is not None and avg_volume_per_minute > 0

                        if volume_ratio_valid:
                            volume_ratio = auction_volume / avg_volume_per_minute
                            # 合理性验证：量比应在0.01-1000范围内
                            if volume_ratio < 0.01 or volume_ratio > 1000:
                                logger.warning(f"⚠️ {code}量比异常({volume_ratio:.2f})，请人工审核")
                        else:
                            volume_ratio = None  # 标记为无效
                            volume_ratio_valid = False

                        # 环境标记
                        is_simulated = (avg_volume_per_minute is None)

                        # 提取竞价数据（含质量标记）
                        auction_data = {
                            'date': date,
                            'code': code,
                            'name': data.get('stockName', ''),
                            'auction_time': f"{date} 09:25:00",
                            'auction_price': last_price,
                            'auction_volume': auction_volume,
                            'auction_amount': data.get('amount', 0),
                            'auction_change': auction_change,           # ✅ 手动计算
                            'volume_ratio': volume_ratio or 0.0,       # ✅ 手动计算（无效为0）
                            'buy_orders': 0,                            # ⚠️ QMT不提供
                            'sell_orders': 0,                           # ⚠️ QMT不提供
                            'bid_vol_1': data.get('bidVol', [0])[0] if data.get('bidVol') else 0,
                            'ask_vol_1': data.get('askVol', [0])[0] if data.get('askVol') else 0,
                            'market_type': 'SH' if code.endswith('.SH') else 'SZ',
                            # 新增：数据质量字段
                            'volume_ratio_valid': int(volume_ratio_valid),  # 1=有效, 0=无效
                            'data_source': 'simulated' if is_simulated else 'production',  # 数据来源
                        }
                        
                        batch_snapshots.append(auction_data)
                        
                        # 同时保存到Redis（用于快速查询）
                        if self.snapshot_manager.is_available:
                            self.snapshot_manager.save_auction_snapshot(
                                code.split('.')[0],
                                auction_data
                            )
                    
                    except Exception as e:
                        logger.warning(f"⚠️ 处理 {code} 失败: {e}")
                        failed_count += 1
                
                # 批量保存到SQLite
                saved_count = self.save_snapshots_batch(batch_snapshots)
                success_count += saved_count
                failed_count += len(batch_codes) - saved_count
                
                # 批次统计
                batch_time = time.time() - batch_start
                elapsed = time.time() - start_time
                avg_time_per_stock = elapsed / processed if processed > 0 else 0
                eta_seconds = avg_time_per_stock * (total - processed)
                
                logger.info(
                    f"📈 进度: {processed}/{total} ({processed/total*100:.1f}%) | "
                    f"成功: {success_count} | 失败: {failed_count} | "
                    f"批次耗时: {batch_time:.1f}s | 预计剩余: {eta_seconds:.0f}s"
                )
                
                # 批次间短暂延迟（避免请求过快）
                time.sleep(0.05)
            
            except Exception as e:
                logger.error(f"❌ 第 {batch_num} 批次失败: {e}")
                failed_count += len(batch_codes)
        
        total_time = time.time() - start_time
        logger.info(
            f"✅ 批量采集完成 - 总数: {total}, 成功: {success_count}, 失败: {failed_count}, "
            f"总耗时: {total_time:.1f}s, 平均: {total_time/total*1000:.1f}ms/股"
        )
        
        return {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'time_seconds': total_time
        }
    
    def get_snapshot_stats(self, date: str = None) -> Dict[str, Any]:
        """
        获取竞价快照统计信息
        
        Args:
            date: 日期（格式：YYYY-MM-DD，默认为今天）
        
        Returns:
            统计信息字典
        """
        try:
            import sqlite3
            
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询统计信息
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN auction_change > 0.03 THEN 1 END) as high_open_count,
                    COUNT(CASE WHEN auction_change < -0.03 THEN 1 END) as low_open_count,
                    COUNT(CASE WHEN volume_ratio > 2.0 THEN 1 END) as high_volume_count,
                    AVG(auction_change) as avg_change,
                    AVG(volume_ratio) as avg_volume_ratio
                FROM auction_snapshots
                WHERE date = ?
            """, (date,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'date': date,
                    'total': row[0],
                    'high_open_count': row[1],
                    'low_open_count': row[2],
                    'high_volume_count': row[3],
                    'avg_change': row[4],
                    'avg_volume_ratio': row[5]
                }
            else:
                return {'date': date, 'total': 0}
        
        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {'date': date, 'error': str(e)}


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='竞价快照采集脚本（数据修复版）')
    parser.add_argument('--date', type=str, help='采集日期（格式：YYYY-MM-DD）')
    parser.add_argument('--start-date', type=str, help='开始日期（用于批量采集）')
    parser.add_argument('--end-date', type=str, help='结束日期（用于批量采集）')
    parser.add_argument('--batch-size', type=int, default=500, help='每批次股票数量（默认500）')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    # 初始化采集器
    collector = AuctionSnapshotCollector()
    
    # 显示统计信息
    if args.stats:
        stats = collector.get_snapshot_stats(args.date)
        logger.info(f"\n📊 竞价快照统计信息：")
        logger.info(f"日期: {stats.get('date')}")
        logger.info(f"总数: {stats.get('total')}")
        logger.info(f"高开股票: {stats.get('high_open_count')} (涨幅>3%)")
        logger.info(f"低开股票: {stats.get('low_open_count')} (跌幅>3%)")
        logger.info(f"放量股票: {stats.get('high_volume_count')} (量比>2.0)")
        logger.info(f"平均涨幅: {stats.get('avg_change', 0)*100:.2f}%")
        logger.info(f"平均量比: {stats.get('avg_volume_ratio', 0):.2f}")
        return
    
    # 批量采集
    if args.start_date and args.end_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
        end = datetime.strptime(args.end_date, "%Y-%m-%d")
        
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            
            # 跳过周末
            if current.weekday() < 5:  # 0-4 是周一到周五
                logger.info(f"\n{'='*60}")
                logger.info(f"采集日期: {date_str}")
                logger.info(f"{'='*60}")
                
                result = collector.collect_all_snapshots_batch(date_str, args.batch_size)
                
                logger.info(
                    f"\n结果: 总数={result['total']}, 成功={result['success']}, "
                    f"失败={result['failed']}, 耗时={result.get('time_seconds', 0):.1f}s"
                )
            else:
                logger.info(f"⏭️  跳过周末: {date_str}")
            
            current += timedelta(days=1)
            time.sleep(1)  # 避免频繁请求
    
    # 单日采集
    else:
        date = args.date or datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"采集日期: {date}")
        logger.info(f"{'='*60}\n")
        
        result = collector.collect_all_snapshots_batch(date, args.batch_size)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 采集完成")
        logger.info(f"总数: {result['total']}")
        logger.info(f"成功: {result['success']}")
        logger.info(f"失败: {result['failed']}")
        logger.info(f"总耗时: {result.get('time_seconds', 0):.1f}s")
        logger.info(f"{'='*60}\n")
        
        # 显示统计信息
        stats = collector.get_snapshot_stats(date)
        logger.info(f"📊 竞价快照统计信息：")
        logger.info(f"高开股票: {stats.get('high_open_count')} (涨幅>3%)")
        logger.info(f"低开股票: {stats.get('low_open_count')} (跌幅>3%)")
        logger.info(f"放量股票: {stats.get('high_volume_count')} (量比>2.0)")


if __name__ == "__main__":
    main()
