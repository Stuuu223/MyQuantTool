#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞价快照采集脚本 (Phase3 第1周)

功能：
1. 每个交易日09:25采集全市场竞价快照
2. 保存竞价数据到SQLite和Redis
3. 支持批量采集和实时更新

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
    
    def collect_single_snapshot(self, code: str, date: str = None) -> Optional[Dict[str, Any]]:
        """
        采集单只股票的竞价快照
        
        Args:
            code: 股票代码（如"600058.SH"）
            date: 日期（格式：YYYY-MM-DD，默认为今天）
        
        Returns:
            竞价数据字典，失败返回None
        """
        try:
            import xtquant.xtdata as xtdata
            
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # 获取竞价数据（09:25:00的快照）
            auction_time = f"{date} 09:25:00"
            
            # 获取分时数据
            tick_data = xtdata.get_full_tick([code])
            
            if not tick_data or code not in tick_data:
                logger.warning(f"⚠️ 未获取到 {code} 的数据")
                return None
            
            data = tick_data[code]
            
            # 提取竞价数据
            auction_data = {
                'date': date,
                'code': code,
                'name': data.get('stockName', ''),
                'auction_time': auction_time,
                'auction_price': data.get('lastPrice', 0),
                'auction_volume': data.get('volume', 0),
                'auction_amount': data.get('amount', 0),
                'auction_change': data.get('pctChg', 0),
                'volume_ratio': data.get('volumeRatio', 0),
                'buy_orders': data.get('buyOrdersVolume', 0),
                'sell_orders': data.get('sellOrdersVolume', 0),
                'bid_vol_1': data.get('bidVol', [0])[0] if data.get('bidVol') else 0,
                'ask_vol_1': data.get('askVol', [0])[0] if data.get('askVol') else 0,
                'market_type': 'SH' if code.endswith('.SH') else 'SZ',
            }
            
            return auction_data
        
        except Exception as e:
            logger.error(f"❌ 采集 {code} 失败: {e}")
            return None
    
    def save_snapshot_to_db(self, snapshot: Dict[str, Any]) -> bool:
        """
        保存竞价快照到SQLite数据库
        
        Args:
            snapshot: 竞价数据字典
        
        Returns:
            是否保存成功
        """
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入或更新数据
            cursor.execute("""
                INSERT OR REPLACE INTO auction_snapshots (
                    date, code, name, auction_time, auction_price, auction_volume,
                    auction_amount, auction_change, volume_ratio, buy_orders,
                    sell_orders, bid_vol_1, ask_vol_1, market_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot['date'], snapshot['code'], snapshot['name'],
                snapshot['auction_time'], snapshot['auction_price'],
                snapshot['auction_volume'], snapshot['auction_amount'],
                snapshot['auction_change'], snapshot['volume_ratio'],
                snapshot['buy_orders'], snapshot['sell_orders'],
                snapshot['bid_vol_1'], snapshot['ask_vol_1'],
                snapshot['market_type']
            ))
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            logger.error(f"❌ 保存快照失败: {e}")
            return False
    
    def collect_all_snapshots(self, date: str = None) -> Dict[str, int]:
        """
        采集全市场竞价快照
        
        Args:
            date: 日期（格式：YYYY-MM-DD，默认为今天）
        
        Returns:
            采集统计信息 {"total": 总数, "success": 成功数, "failed": 失败数}
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"🚀 开始采集 {date} 的竞价快照")
        
        # 获取股票列表
        stock_codes = self.get_all_stock_codes()
        total = len(stock_codes)
        
        if total == 0:
            logger.error("❌ 未获取到股票列表")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        logger.info(f"📊 共需采集 {total} 只股票")
        
        # 采集数据
        success_count = 0
        failed_count = 0
        
        for i, code in enumerate(stock_codes, 1):
            # 采集单只股票快照
            snapshot = self.collect_single_snapshot(code, date)
            
            if snapshot:
                # 保存到SQLite
                if self.save_snapshot_to_db(snapshot):
                    # 保存到Redis（用于快速查询）
                    self.snapshot_manager.save_auction_snapshot(
                        code.split('.')[0],  # 去掉市场后缀
                        snapshot
                    )
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1
            
            # 进度提示
            if i % 100 == 0 or i == total:
                logger.info(f"📈 进度: {i}/{total} ({i/total*100:.1f}%) - 成功: {success_count}, 失败: {failed_count}")
            
            # 避免频繁请求
            time.sleep(0.01)
        
        logger.info(f"✅ 采集完成 - 总数: {total}, 成功: {success_count}, 失败: {failed_count}")
        
        return {
            'total': total,
            'success': success_count,
            'failed': failed_count
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
                date = datetime.now().strftime("%Y-%m-d")            
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
    parser = argparse.ArgumentParser(description='竞价快照采集脚本')
    parser.add_argument('--date', type=str, help='采集日期（格式：YYYY-MM-DD）')
    parser.add_argument('--start-date', type=str, help='开始日期（用于批量采集）')
    parser.add_argument('--end-date', type=str, help='结束日期（用于批量采集）')
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
                
                result = collector.collect_all_snapshots(date_str)
                
                logger.info(f"\n结果: 总数={result['total']}, 成功={result['success']}, 失败={result['failed']}")
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
        
        result = collector.collect_all_snapshots(date)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 采集完成")
        logger.info(f"总数: {result['total']}")
        logger.info(f"成功: {result['success']}")
        logger.info(f"失败: {result['failed']}")
        logger.info(f"{'='*60}\n")
        
        # 显示统计信息
        stats = collector.get_snapshot_stats(date)
        logger.info(f"📊 竞价快照统计信息：")
        logger.info(f"高开股票: {stats.get('high_open_count')} (涨幅>3%)")
        logger.info(f"低开股票: {stats.get('low_open_count')} (跌幅>3%)")
        logger.info(f"放量股票: {stats.get('high_volume_count')} (量比>2.0)")


if __name__ == "__main__":
    main()