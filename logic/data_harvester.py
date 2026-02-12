#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据收割机 V19.13 - Data Harvester
实现本地数据库 + 增量更新机制
"慢慢存、不封号"的优雅方案

Author: iFlow CLI
Version: V19.13
"""

import time
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from logic.data_source_manager import DataSourceManager
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class DataHarvester:
    """
    数据收割机 - 自动收割和存储股票数据

    核心功能：
    1. 检查数据库里有没有这只票
    2. 如果有，只下载最近几天的新数据（增量更新）
    3. 如果没有，才下载过去 60 天的数据
    4. 每下载一只，歇 0.5 秒（慢慢存，绝不封号）
    """

    def __init__(self, db_path: str = "data/stock_data.db"):
        """
        初始化数据收割机

        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self.ds = DataSourceManager()
        self._init_db()
        logger.info(f"✅ [数据收割机] 初始化完成，数据库: {self.db_path}")

    def _init_db(self):
        """初始化 SQLite 数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # 创建日线数据表
        c.execute('''CREATE TABLE IF NOT EXISTS daily_kline
                     (code TEXT,
                      date TEXT,
                      open REAL,
                      close REAL,
                      high REAL,
                      low REAL,
                      volume REAL,
                      amount REAL,
                      turnover REAL,
                      PRIMARY KEY (code, date))''')

        # 创建索引，提高查询速度
        c.execute('''CREATE INDEX IF NOT EXISTS idx_code_date ON daily_kline(code, date)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_date ON daily_kline(date)''')

        conn.commit()
        conn.close()
        logger.info("✅ [数据收割机] 数据库表结构初始化完成")

    def get_latest_date(self, code: str) -> Optional[str]:
        """
        获取某只股票在数据库中的最新日期

        Args:
            code: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("SELECT MAX(date) FROM daily_kline WHERE code = ?", (code,))
        result = c.fetchone()
        conn.close()

        return result[0] if result and result[0] else None

    def harvest_stock(self, code: str, days: int = 60, force_update: bool = False) -> bool:
        """
        收割单只股票的数据

        Args:
            code: 股票代码
            days: 下载数据的天数
            force_update: 是否强制更新（不检查数据库）

        Returns:
            是否成功
        """
        try:
            # 检查数据库中是否已有数据
            latest_date = self.get_latest_date(code)

            # 计算需要下载的起始日期
            if latest_date and not force_update:
                # 增量更新：从最新日期的下一天开始
                latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
                start_date = latest_dt + timedelta(days=1)
                start_date_str = start_date.strftime("%Y-%m-%d")

                # 如果最新日期就是今天，不需要更新
                if start_date_str > datetime.now().strftime("%Y-%m-%d"):
                    logger.debug(f"♻️ {code} 数据已是最新，跳过")
                    return True

                logger.info(f"🔄 {code} 增量更新，从 {start_date_str} 开始")
            else:
                # 全量下载：下载过去 days 天的数据
                start_date = datetime.now() - timedelta(days=days)
                start_date_str = start_date.strftime("%Y-%m-%d")
                logger.info(f"📥 {code} 全量下载，从 {start_date_str} 开始")

            # 获取数据（使用修复好的 DataSourceManager）
            df = self.ds.get_history_kline(code)

            if df is None or df.empty:
                logger.warning(f"⚠️ {code} 无数据")
                return False

            # 数据清洗和格式化
            # 标准化列名
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '换手率': 'turnover'
            }

            df = df.rename(columns=column_mapping)

            # 检查必要的列是否存在
            required_columns = ['date', 'open', 'close', 'high', 'low', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                logger.error(f"❌ {code} 数据缺少必要列: {missing_columns}")
                return False

            # 如果是增量更新，只保留新数据
            if latest_date and not force_update:
                df = df[df['date'] > latest_date]

            if df.empty:
                logger.debug(f"♻️ {code} 没有新数据")
                return True

            # 添加股票代码列
            df['code'] = code

            # 存入数据库
            conn = sqlite3.connect(self.db_path)

            # 使用 INSERT OR REPLACE 处理重复数据
            df.to_sql('daily_kline', conn, if_exists='append', index=False)

            conn.close()

            logger.info(f"✅ {code} 已入库 {len(df)} 条数据")
            return True

        except sqlite3.IntegrityError as e:
            logger.debug(f"♻️ {code} 数据已存在: {e}")
            return True
        except Exception as e:
            logger.error(f"❌ {code} 收割失败: {e}")
            return False

    def harvest_active_stocks(
        self,
        limit: int = 300,
        days: int = 60,
        force_update: bool = False,
        delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        收割活跃股数据

        Args:
            limit: 收割股票数量
            days: 下载数据的天数
            force_update: 是否强制更新
            delay: 每只股票之间的延迟（秒）

        Returns:
            收割结果统计
        """
        logger.info(f"🚜 [数据收割机] 开始收割活跃股数据...")

        # 1. 获取活跃股名单（依赖修复好的 ActiveStockFilter）
        from logic.active_stock_filter import get_active_stocks

        stock_list = get_active_stocks(limit=limit, sort_by='amount', skip_top=30)

        if not stock_list:
            logger.error("❌ 无法获取活跃股名单，请先修复 ActiveStockFilter！")
            return {
                'total': 0,
                'success': 0,
                'failed': 0,
                'skipped': 0,
                'details': []
            }

        logger.info(f"📋 获取到 {len(stock_list)} 只活跃股")

        # 2. 逐只收割
        success = 0
        failed = 0
        skipped = 0
        details = []

        for i, stock in enumerate(stock_list):
            code = stock['code']
            name = stock['name']

            try:
                result = self.harvest_stock(code, days=days, force_update=force_update)

                if result:
                    success += 1
                    details.append({
                        'code': code,
                        'name': name,
                        'status': 'success',
                        'message': '收割成功'
                    })
                else:
                    failed += 1
                    details.append({
                        'code': code,
                        'name': name,
                        'status': 'failed',
                        'message': '收割失败'
                    })

            except Exception as e:
                failed += 1
                details.append({
                    'code': code,
                    'name': name,
                    'status': 'error',
                    'message': str(e)
                })

            # 3. 核心：慢一点，避免封号
            if i < len(stock_list) - 1:  # 最后一只不需要延迟
                time.sleep(delay)

        # 4. 汇总结果
        result = {
            'total': len(stock_list),
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'details': details
        }

        logger.info(f"🎉 [数据收割机] 收割完成！成功: {success}, 失败: {failed}, 跳过: {skipped}")

        return result

    def get_stock_data(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        从数据库获取股票数据

        Args:
            code: 股票代码
            days: 获取最近多少天的数据

        Returns:
            DataFrame，如果没有数据则返回 None
        """
        try:
            conn = sqlite3.connect(self.db_path)

            # 计算起始日期
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            query = """
                SELECT code, date, open, close, high, low, volume, amount, turnover
                FROM daily_kline
                WHERE code = ? AND date >= ?
                ORDER BY date ASC
            """

            df = pd.read_sql_query(query, conn, params=(code, start_date))
            conn.close()

            if df.empty:
                return None

            return df

        except Exception as e:
            logger.error(f"❌ 获取 {code} 数据失败: {e}")
            return None

    def get_database_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # 统计股票数量
            c.execute("SELECT COUNT(DISTINCT code) FROM daily_kline")
            stock_count = c.fetchone()[0]

            # 统计数据总量
            c.execute("SELECT COUNT(*) FROM daily_kline")
            total_records = c.fetchone()[0]

            # 统计最新数据日期
            c.execute("SELECT MAX(date) FROM daily_kline")
            latest_date = c.fetchone()[0]

            # 统计最早数据日期
            c.execute("SELECT MIN(date) FROM daily_kline")
            earliest_date = c.fetchone()[0]

            # 数据库文件大小
            db_size = os.path.getsize(self.db_path) / 1024 / 1024  # MB

            conn.close()

            return {
                'stock_count': stock_count,
                'total_records': total_records,
                'latest_date': latest_date,
                'earliest_date': earliest_date,
                'db_size_mb': round(db_size, 2)
            }

        except Exception as e:
            logger.error(f"❌ 获取数据库统计失败: {e}")
            return {
                'stock_count': 0,
                'total_records': 0,
                'latest_date': None,
                'earliest_date': None,
                'db_size_mb': 0
            }


# 便捷函数
_harvester_instance = None

def get_data_harvester(db_path: str = "data/stock_data.db") -> DataHarvester:
    """获取数据收割机单例"""
    global _harvester_instance
    if _harvester_instance is None or _harvester_instance.db_path != db_path:
        _harvester_instance = DataHarvester(db_path)
    return _harvester_instance