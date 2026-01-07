"""
真实龙虎榜数据集成模块
属性：
- akshare 实时数据接入
- 本地 SQLite 数据库上业
- 数据流绯化处理
- 错误重试机制
"""

import akshare as ak
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import time
import json
from collections import deque

logger = logging.getLogger(__name__)


class RealTimeDataLoader:
    """
    实时龙虎榜数据加载器
    """
    
    def __init__(
        self,
        db_path: str = 'data/production.db',
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Args:
            db_path: SQLite 数据库路径
            max_retries: 最大重试次数
            retry_delay: 重试延迟 (秒)
        """
        self.db_path = db_path
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_log = deque(maxlen=100)  # 保持最角100条错误
        
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            # 龙虎榜表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lhb_realtime (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    capital_name TEXT NOT NULL,
                    direction TEXT,  -- '买' 或 '卖'
                    amount REAL,  -- 成交额 (万元)
                    price REAL,
                    rank INTEGER,  -- 龙虎榜排名
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, stock_code, capital_name, direction),
                    FOREIGN KEY (stock_code) REFERENCES stock_meta(code)
                )
            """)
            
            # 股票元数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_meta (
                    code TEXT PRIMARY KEY,
                    name TEXT,
                    industry TEXT,
                    last_update DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 絢計数据表 (用于过滤)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lhb_stats (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL UNIQUE,
                    total_records INTEGER,
                    total_stocks INTEGER,
                    total_capitals INTEGER,
                    total_amount REAL,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON lhb_realtime(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_stock ON lhb_realtime(stock_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_capital ON lhb_realtime(capital_name)")
            conn.commit()
    
    def fetch_lhb_with_retry(
        self,
        date_str: str,
        attempt: int = 1
    ) -> Optional[pd.DataFrame]:
        """
        带重试橜制的 LHB 数据获取
        
        Args:
            date_str: 日期 'YYYY-MM-DD'
            attempt: 当前尝试次数
        
        Returns:
            DataFrame 或 None
        """
        try:
            logger.info(f"⭐ 正在获取 {date_str} 龙虎榜数据...")
            df = ak.stock_lgb_daily(date=date_str)
            
            if df is None or len(df) == 0:
                logger.warning(f"⚠️  {date_str} 无数据 (可能是节假日)")
                return None
            
            logger.info(f"✅ 成功获取 {len(df)} 条记录")
            return df
        
        except Exception as e:
            error_msg = f"{date_str} 获取失败: {str(e)}"
            self.error_log.append((datetime.now(), error_msg))
            
            if attempt < self.max_retries:
                logger.warning(f"⚠️  {error_msg}. 即将需要 {self.retry_delay}s 后第 {attempt+1} 次氫试...")
                time.sleep(self.retry_delay)
                return self.fetch_lhb_with_retry(date_str, attempt + 1)
            else:
                logger.error(f"❌ {error_msg} (超过最大重试次数)")
                return None
    
    def preprocess_lhb_data(
        self,
        df_raw: pd.DataFrame,
        date_str: str
    ) -> pd.DataFrame:
        """
        预处理龙虎榜数据
        
        处理扥筥：
        - 列重命名
        - 数据类型转换
        - 缺失值处理
        - 重复值处理
        """
        df = df_raw.copy()
        
        # 列重命名
        rename_map = {
            '代码': 'stock_code',
            '名称': 'stock_name',
            '游资名称': 'capital_name',
            '操作方向': 'direction',
            '成交额': 'amount',  # 单位：万元
            '最新价': 'price',
        }
        df.rename(columns=rename_map, inplace=True)
        
        # 数据类型转换
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['date'] = date_str
        
        # 缺失值处理
        df.dropna(subset=['stock_code', 'capital_name', 'amount'], inplace=True)
        
        # 重复值处理 (取第一条)
        df.drop_duplicates(subset=['stock_code', 'capital_name', 'direction'], 
                          keep='first', inplace=True)
        
        # 补充龙虎榜排名
        if '排名' not in df.columns:
            df['rank'] = df.groupby('stock_code').cumcount() + 1
        else:
            df.rename(columns={'排名': 'rank'}, inplace=True)
        
        return df
    
    def upsert_to_db(
        self,
        df_processed: pd.DataFrame
    ) -> Dict[str, int]:
        """
        插入/更新数据库
        
        Returns:
            {
                'inserted': int,
                'updated': int,
                'skipped': int,
                'errors': int
            }
        """
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df_processed.iterrows():
                try:
                    # 先更新株提取批
                    cursor = conn.execute("""
                        INSERT OR REPLACE INTO lhb_realtime
                        (date, stock_code, stock_name, capital_name, direction, amount, price, rank)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row['date'],
                        row['stock_code'],
                        row.get('stock_name', ''),
                        row['capital_name'],
                        row.get('direction', ''),
                        row['amount'],
                        row.get('price', None),
                        row.get('rank', 0)
                    ))
                    
                    if cursor.rowcount > 0:
                        stats['inserted'] += 1
                    else:
                        stats['updated'] += 1
                
                except sqlite3.IntegrityError:
                    stats['skipped'] += 1
                except Exception as e:
                    logger.error(f"插入数据失败: {str(e)}")
                    stats['errors'] += 1
            
            conn.commit()
        
        return stats
    
    def load_daily_data(
        self,
        date_str: str = None
    ) -> Tuple[Optional[pd.DataFrame], Dict]:
        """
        一体化加载日常数据的标准流程
        
        Returns:
            (DataFrame, 处理统计)
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"📄 开始加载 {date_str} 数据...")
        
        # 步骤 1: 获取原始数据
        df_raw = self.fetch_lhb_with_retry(date_str)
        if df_raw is None:
            return None, {'status': 'failed', 'reason': 'no_data'}
        
        # 步骤 2: 预处理
        df_processed = self.preprocess_lhb_data(df_raw, date_str)
        logger.info(f"✅ 预处理完成: {len(df_processed)} 条有效记录")
        
        # 步骤 3: 入库
        db_stats = self.upsert_to_db(df_processed)
        logger.info(f"💾 入库完成: 新增 {db_stats['inserted']}, 戉佐 {db_stats['skipped']}, 攙误 {db_stats['errors']}")
        
        # 步骤 4: 统计数据
        self._update_stats(date_str, df_processed)
        
        return df_processed, db_stats
    
    def _update_stats(
        self,
        date_str: str,
        df: pd.DataFrame
    ) -> None:
        """更新絢計数据"""
        stats = {
            'total_records': len(df),
            'total_stocks': df['stock_code'].nunique(),
            'total_capitals': df['capital_name'].nunique(),
            'total_amount': df['amount'].sum()
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO lhb_stats
                (date, total_records, total_stocks, total_capitals, total_amount)
                VALUES (?, ?, ?, ?, ?)
            """, (date_str, stats['total_records'], stats['total_stocks'],
                   stats['total_capitals'], stats['total_amount']))
            conn.commit()
        
        logger.info(f"📊 统计: {stats['total_stocks']}只股, {stats['total_capitals']}个游资, 统计成交额 {stats['total_amount']:.2f}万元")
    
    def batch_load(
        self,
        start_date: str,
        end_date: str,
        skip_weekends: bool = True
    ) -> Dict:
        """
        批量加载历史数据
        
        Args:
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            skip_weekends: 是否跳过周末
        
        Returns:
            {
                'total_days': int,
                'successful_days': int,
                'failed_days': int,
                'total_records': int
            }
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        total_records = 0
        successful_days = 0
        failed_days = 0
        
        current = start
        while current <= end:
            # 跳过周末
            if skip_weekends and current.weekday() >= 5:
                current += timedelta(days=1)
                continue
            
            date_str = current.strftime('%Y-%m-%d')
            df, stats = self.load_daily_data(date_str)
            
            if df is not None and len(df) > 0:
                successful_days += 1
                total_records += len(df)
            else:
                failed_days += 1
            
            current += timedelta(days=1)
            time.sleep(0.5)  # 为了不你便服务器，推迟请求
        
        return {
            'total_days': (end - start).days + 1,
            'successful_days': successful_days,
            'failed_days': failed_days,
            'total_records': total_records
        }
    
    def query_realtime(
        self,
        date_str: str = None
    ) -> pd.DataFrame:
        """
        查询指定日日的数据
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(self.db_path) as conn:
            query = f"""
                SELECT * FROM lhb_realtime 
                WHERE date = '{date_str}'
                ORDER BY amount DESC
            """
            return pd.read_sql(query, conn)
    
    def get_error_log(self) -> List[Tuple]:
        """获取错误日志"""
        return list(self.error_log)
