#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资金流数据缓存层 (Fund Flow Cache)

功能:
1. 缓存资金流向数据到 SQLite（持久层）
2. 避免重复调用东方财富 API
3. 支持缓存过期清理

架构:
- SQLite 作为持久缓存层
- 未来可扩展 Redis 作为热缓存层

作者: MyQuantTool Team
版本: v1.0
创建日期: 2026-02-05
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class FundFlowCache:
    """资金流数据缓存器
    
    缓存资金流向数据到 SQLite，避免重复调用东方财富 API。
    使用复合主键 (stock_code, date) 确保每只股票每天只有一条记录。
    
    Attributes:
        db_path: SQLite 数据库路径
        conn: SQLite 连接对象
        
    Example:
        >>> cache = FundFlowCache()
        >>> data = cache.get('600519', '2026-02-05')
        >>> if data is None:
        >>>     data = fetch_from_eastmoney('600519')
        >>>     cache.save('600519', '2026-02-05', data)
    """
    
    def __init__(self, db_path: str = 'data/fund_flow_cache.db'):
        """
        初始化资金流缓存器
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self._init_database()
        logger.debug(f"✅ FundFlowCache 初始化成功，数据库: {db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建资金流缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fund_flow_daily (
                    stock_code TEXT NOT NULL,
                    date TEXT NOT NULL,
                    
                    -- 🔥 [P0 FIX v2] 主力净流入（超大单+大单）
                    main_net_inflow REAL,
                    
                    -- 东方财富原始字段（单位：元）
                    super_large_net REAL,
                    large_net REAL,
                    medium_net REAL,
                    small_net REAL,
                    
                    -- 计算字段（为 Level 2 服务）
                    institution_net REAL,
                    retail_net REAL,
                    super_ratio REAL,
                    
                    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                    
                    PRIMARY KEY (stock_code, date)
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_flow_stock_code 
                ON fund_flow_daily(stock_code)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fund_flow_date 
                ON fund_flow_daily(date)
            ''')
            
            conn.commit()
            logger.debug("✅ fund_flow_daily 表初始化完成")
    
    def get(self, stock_code: str, date: str) -> Optional[Dict[str, Any]]:
        """
        获取资金流缓存数据
        
        Args:
            stock_code: 股票代码（6位数字）
            date: 日期（YYYY-MM-DD）
            
        Returns:
            资金流数据字典，未找到返回 None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT stock_code, date, main_net_inflow, super_large_net, large_net, medium_net, small_net,
                           institution_net, retail_net, super_ratio, updated_at
                    FROM fund_flow_daily
                    WHERE stock_code = ? AND date = ?
                ''', (stock_code, date))
                
                row = cursor.fetchone()
                
                if row:
                    data = dict(row)
                    logger.debug(f"✅ 缓存命中: {stock_code} {date}")
                    return data
                else:
                    logger.debug(f"⚠️  缓存未命中: {stock_code} {date}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ 缓存查询失败 {stock_code} {date}: {e}")
            return None
    
    def save(self, stock_code: str, date: str, data: Dict[str, Any]) -> bool:
        """
        保存资金流数据到缓存
        
        Args:
            stock_code: 股票代码（6位数字）
            date: 日期（YYYY-MM-DD）
            data: 资金流数据字典
            
        Returns:
            是否保存成功
        """
        try:
            # 提取数据
            latest = data.get('latest', {})
            
            # 计算机构净流入和散户净流入
            super_large_net = latest.get('super_large_net', 0)
            large_net = latest.get('large_net', 0)
            medium_net = latest.get('medium_net', 0)
            small_net = latest.get('small_net', 0)
            
            institution_net = super_large_net + large_net
            retail_net = medium_net + small_net
            
            # 计算超大单占比（避免除零）
            if institution_net != 0:
                super_ratio = abs(super_large_net) / abs(institution_net)
            else:
                super_ratio = 0.0
            
            # 🔥 [P0 FIX v2] 添加main_net_inflow字段
            main_net_inflow = latest.get('main_net_inflow', 0)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 使用 INSERT OR REPLACE 确保同一天只有一条记录
                cursor.execute('''
                    INSERT OR REPLACE INTO fund_flow_daily (
                        stock_code, date,
                        main_net_inflow,
                        super_large_net, large_net, medium_net, small_net,
                        institution_net, retail_net, super_ratio,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                ''', (
                    stock_code, date,
                    main_net_inflow,
                    super_large_net, large_net, medium_net, small_net,
                    institution_net, retail_net, super_ratio
                ))
                
                conn.commit()
                logger.debug(f"✅ 缓存保存成功: {stock_code} {date}")
                return True
                
        except Exception as e:
            logger.error(f"❌ 缓存保存失败 {stock_code} {date}: {e}")
            return False
    
    def get_latest(self, stock_code: str, days: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近 N 天的资金流数据
        
        Args:
            stock_code: 股票代码（6位数字）
            days: 天数
            
        Returns:
            资金流数据列表（按日期倒序）
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                
                cursor.execute('''
                    SELECT stock_code, date, super_large_net, large_net, medium_net, small_net,
                           institution_net, retail_net, super_ratio, updated_at
                    FROM fund_flow_daily
                    WHERE stock_code = ? AND date >= ?
                    ORDER BY date DESC
                ''', (stock_code, cutoff_date))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ 查询历史数据失败 {stock_code}: {e}")
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总记录数
                cursor.execute('SELECT COUNT(*) FROM fund_flow_daily')
                total_records = cursor.fetchone()[0]
                
                # 股票数量
                cursor.execute('SELECT COUNT(DISTINCT stock_code) FROM fund_flow_daily')
                total_stocks = cursor.fetchone()[0]
                
                # 最新数据日期
                cursor.execute('SELECT MAX(date) FROM fund_flow_daily')
                latest_date = cursor.fetchone()[0]
                
                # 最早数据日期
                cursor.execute('SELECT MIN(date) FROM fund_flow_daily')
                earliest_date = cursor.fetchone()[0]
                
                return {
                    'total_records': total_records,
                    'total_stocks': total_stocks,
                    'latest_date': latest_date,
                    'earliest_date': earliest_date,
                    'db_size': f"{Path(self.db_path).stat().st_size / 1024:.2f} KB"
                }
                
        except Exception as e:
            logger.error(f"❌ 获取缓存统计失败: {e}")
            return {}
    
    def clear_expired(self, days: int = 90) -> int:
        """
        清理过期缓存数据
        
        Args:
            days: 保留天数（默认90天）
            
        Returns:
            删除的记录数
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM fund_flow_daily
                    WHERE date < ?
                ''', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"✅ 清理过期缓存: {deleted_count} 条记录")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ 清理过期缓存失败: {e}")
            return 0
    
    def clear_stock(self, stock_code: str) -> int:
        """
        清理指定股票的缓存数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            删除的记录数
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM fund_flow_daily
                    WHERE stock_code = ?
                ''', (stock_code,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"✅ 清理股票缓存: {stock_code} ({deleted_count} 条记录)")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"❌ 清理股票缓存失败 {stock_code}: {e}")
            return 0


# 单例模式
_cache_instance: Optional[FundFlowCache] = None


def get_fund_flow_cache(db_path: str = 'data/fund_flow_cache.db') -> FundFlowCache:
    """
    获取 FundFlowCache 单例实例
    
    Args:
        db_path: SQLite 数据库路径
        
    Returns:
        FundFlowCache 实例
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = FundFlowCache(db_path)
    return _cache_instance