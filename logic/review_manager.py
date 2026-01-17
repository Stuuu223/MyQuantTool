#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V11 核心组件：复盘管理器 (Review Manager)
负责管理'隔日记忆'，计算连板高度和昨日溢价
"""

import pandas as pd
import json
from datetime import datetime
from logic.database_manager import get_db_manager
from logic.logger import get_logger
import akshare as ak

logger = get_logger(__name__)


class ReviewManager:
    """
    V11 核心组件：复盘管理器
    负责管理'隔日记忆'，计算连板高度和昨日溢价
    """
    
    def __init__(self):
        self.db = get_db_manager()
        self._init_tables()
    
    def _init_tables(self):
        """初始化复盘数据表 (SQLite)"""
        # 创建每日市场概况表 (Metadata)
        sql_summary = """
        CREATE TABLE IF NOT EXISTS market_summary (
            date TEXT PRIMARY KEY,
            highest_board INTEGER,      -- 最高连板数
            limit_up_count INTEGER,     -- 涨停家数
            limit_down_count INTEGER,   -- 跌停家数
            limit_up_list TEXT,         -- 涨停股名单 (JSON)
            created_at TEXT
        )
        """
        self.db.sqlite_execute(sql_summary)
        logger.info("✅ V11 复盘数据库表结构已就绪")
    
    def run_daily_review(self, date=None):
        """
        执行每日复盘 (建议每日 15:30 运行)
        获取当日涨停数据并存入 DB
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        logger.info(f"🔄 开始执行 {date} 每日复盘归档...")
        
        try:
            # 1. 获取当日涨停池 (来自 AkShare)
            df = ak.stock_zt_pool_em(date=date)
            
            if df is None or df.empty:
                logger.warning(f"⚠️ {date} 没有获取到涨停数据 (可能是休市或数据未更新)")
                return False
            
            # 2. 提取核心数据
            # 连板高度 (连板数那一列的最大值)
            highest_board = int(df['连板数'].max()) if '连板数' in df.columns else 1
            limit_up_count = len(df)
            
            # 提取涨停名单 (只存代码，节省空间)
            # 格式: ["000001", "600519", ...]
            limit_up_list = df['代码'].tolist()
            
            # 3. 存入数据库
            sql = """
            INSERT OR REPLACE INTO market_summary 
            (date, highest_board, limit_up_count, limit_down_count, limit_up_list, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            self.db.sqlite_execute(sql, (
                date, 
                highest_board, 
                limit_up_count, 
                0,  # 跌停数暂时填0，后续可扩充
                json.dumps(limit_up_list), 
                datetime.now().isoformat()
            ))
            
            logger.info(f"✅ 复盘归档完成! 日期: {date}, 最高板: {highest_board}, 涨停: {limit_up_count}家")
            return True
            
        except Exception as e:
            logger.error(f"❌ 复盘归档失败: {e}")
            return False
    
    def get_yesterday_stats(self):
        """
        获取昨日市场状态 (供今日实盘使用)
        """
        # 获取最近的一个交易日记录
        sql = "SELECT * FROM market_summary ORDER BY date DESC LIMIT 1"
        results = self.db.sqlite_query(sql)
        
        if not results:
            return None
        
        row = results[0]
        # 解析数据
        return {
            'date': row[0],
            'highest_board': row[1],
            'limit_up_count': row[2],
            'limit_up_list': json.loads(row[4])  # 这是一个代码列表
        }


# 单例测试
if __name__ == "__main__":
    rm = ReviewManager()
    # 尝试跑一下最近一个交易日的数据 (注意：如果是周末可能取不到今天的，akshare通常延迟)
    # 我们可以尝试取上周五的数据测试
    rm.run_daily_review(date='20260116')
    
    # 读取测试
    stats = rm.get_yesterday_stats()
    print("读取到的昨日状态:", stats)