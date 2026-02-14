"""
信号历史存储模块

用于存储和查询历史交易信号，支持AutoReviewer的案例收集功能
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class SignalHistoryManager:
    """
    信号历史管理器
    """
    
    def __init__(self, db_path: str = "data/signal_history.db"):
        """
        初始化
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建信号记录表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            date TEXT NOT NULL,
            ai_score REAL,
            capital_flow REAL,
            trend_status TEXT,
            market_cap REAL,
            final_signal TEXT,
            final_score REAL,
            reason TEXT,
            fact_veto BOOLEAN,
            risk_level TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_code, date)
        )
        """)
        
        # 创建索引
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_date 
        ON signal_records(stock_code, date)
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_date 
        ON signal_records(date)
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signal 
        ON signal_records(final_signal)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"信号历史数据库初始化完成: {self.db_path}")
    
    def save_signal(self, stock_code: str, signal_data: Dict, date: str = None):
        """
        保存信号记录
        
        Args:
            stock_code: 股票代码
            signal_data: 信号数据字典
            date: 日期字符串，格式YYYY-MM-DD，默认为今天
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO signal_records 
            (stock_code, date, ai_score, capital_flow, trend_status, market_cap, 
             final_signal, final_score, reason, fact_veto, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stock_code,
                date,
                signal_data.get('ai_score'),
                signal_data.get('capital_flow'),
                signal_data.get('trend_status'),
                signal_data.get('market_cap'),
                signal_data.get('final_signal'),
                signal_data.get('final_score'),
                signal_data.get('reason'),
                signal_data.get('fact_veto', False),
                signal_data.get('risk_level')
            ))
            
            conn.commit()
            logger.debug(f"信号记录已保存: {stock_code} {date}")
            
        except Exception as e:
            logger.error(f"保存信号记录失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_signals_by_date(self, date: str) -> List[Dict]:
        """
        获取指定日期的所有信号
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD
        
        Returns:
            信号列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT * FROM signal_records 
            WHERE date = ?
            ORDER BY final_score DESC
            """, (date,))
            
            rows = cursor.fetchall()
            signals = [dict(row) for row in rows]
            
            return signals
            
        except Exception as e:
            logger.error(f"查询信号记录失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_buy_signals_by_date(self, date: str) -> List[Dict]:
        """
        获取指定日期的BUY信号
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD
        
        Returns:
            BUY信号列表
        """
        signals = self.get_signals_by_date(date)
        buy_signals = [s for s in signals if s['final_signal'] == 'BUY']
        return buy_signals
    
    def get_fact_vetoed_signals(self, date: str) -> List[Dict]:
        """
        获取指定日期被事实熔断的信号
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD
        
        Returns:
            被熔断的信号列表
        """
        signals = self.get_signals_by_date(date)
        vetoed_signals = [s for s in signals if s['fact_veto'] == 1]
        return vetoed_signals
    
    def get_signal_by_stock_and_date(self, stock_code: str, date: str) -> Optional[Dict]:
        """
        获取指定股票在指定日期的信号
        
        Args:
            stock_code: 股票代码
            date: 日期字符串，格式YYYY-MM-DD
        
        Returns:
            信号数据，如果不存在则返回None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT * FROM signal_records 
            WHERE stock_code = ? AND date = ?
            """, (stock_code, date))
            
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            else:
                return None
            
        except Exception as e:
            logger.error(f"查询信号记录失败: {e}")
            return None
        finally:
            conn.close()
    
    def get_recent_signals(self, days: int = 7) -> List[Dict]:
        """
        获取最近N天的所有信号
        
        Args:
            days: 天数
        
        Returns:
            信号列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            SELECT * FROM signal_records 
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC, final_score DESC
            """, (days,))
            
            rows = cursor.fetchall()
            signals = [dict(row) for row in rows]
            
            return signals
            
        except Exception as e:
            logger.error(f"查询信号记录失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_statistics(self, date: str = None) -> Dict:
        """
        获取信号统计信息
        
        Args:
            date: 日期字符串，格式YYYY-MM-DD，如果为None则统计所有数据
        
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if date:
                cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN final_signal = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                    SUM(CASE WHEN final_signal = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                    SUM(CASE WHEN final_signal = 'WAIT' THEN 1 ELSE 0 END) as wait_count,
                    SUM(CASE WHEN fact_veto = 1 THEN 1 ELSE 0 END) as veto_count,
                    AVG(final_score) as avg_score
                FROM signal_records
                WHERE date = ?
                """, (date,))
            else:
                cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN final_signal = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                    SUM(CASE WHEN final_signal = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                    SUM(CASE WHEN final_signal = 'WAIT' THEN 1 ELSE 0 END) as wait_count,
                    SUM(CASE WHEN fact_veto = 1 THEN 1 ELSE 0 END) as veto_count,
                    AVG(final_score) as avg_score
                FROM signal_records
                """)
            
            row = cursor.fetchone()
            
            stats = {
                'total': row[0],
                'buy_count': row[1],
                'sell_count': row[2],
                'wait_count': row[3],
                'veto_count': row[4],
                'avg_score': row[5] if row[5] else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"查询统计信息失败: {e}")
            return {}
        finally:
            conn.close()
    
    def cleanup_old_records(self, days: int = 90):
        """
        清理旧记录
        
        Args:
            days: 保留最近N天的记录
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            DELETE FROM signal_records
            WHERE date < date('now', '-' || ? || ' days')
            """, (days,))
            
            deleted = cursor.rowcount
            conn.commit()
            
            logger.info(f"清理了 {deleted} 条旧记录")
            
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            conn.rollback()
        finally:
            conn.close()


# 全局实例
_signal_history_manager = None


def get_signal_history_manager() -> SignalHistoryManager:
    """获取信号历史管理器实例（单例）"""
    global _signal_history_manager
    if _signal_history_manager is None:
        _signal_history_manager = SignalHistoryManager()
    return _signal_history_manager