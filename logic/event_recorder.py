#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件记录器 - 自动记录事件数据

功能：
1. 自动记录事件到数据库
2. 记录事件触发时的完整信息
3. 支持后续更新（收盘涨幅、次日开盘等）
4. 导出为Excel/CSV表格
5. 支持统计分析（胜率、平均收益等）

Author: iFlow CLI
Version: V2.0
"""

import os
import json
import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from logic.event_detector import EventType, TradingEvent
from logic.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EventRecord:
    """事件记录数据结构"""
    id: Optional[int] = None
    event_time: str = ""  # 事件触发时间
    event_type: str = ""  # 事件类型
    stock_code: str = ""  # 股票代码
    description: str = ""  # 事件描述
    confidence: float = 0.0  # 置信度
    trigger_conditions: str = ""  # 触发条件（JSON字符串）
    
    # 价格数据（事件触发时）
    yesterday_close: float = 0.0  # 昨收价
    open_price: float = 0.0  # 开盘价
    current_price: float = 0.0  # 当前价
    
    # 后续数据（需要更新）
    day_close: Optional[float] = None  # 当日收盘价
    day_close_pct: Optional[float] = None  # 当日收盘涨幅
    next_day_open: Optional[float] = None  # 次日开盘价
    next_day_open_pct: Optional[float] = None  # 次日开盘涨幅
    max_gain_3days: Optional[float] = None  # 3天内最大涨幅
    max_loss_3days: Optional[float] = None  # 3天内最大跌幅
    
    # 分析结果
    is_profitable: Optional[bool] = None  # 是否赚钱（3天内）
    profit_amount: Optional[float] = None  # 盈利金额
    notes: str = ""  # 备注
    
    # 数据库字段
    created_at: Optional[str] = None  # 创建时间
    updated_at: Optional[str] = None  # 更新时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 移除None值
        return {k: v for k, v in data.items() if v is not None}


class EventRecorder:
    """
    事件记录器
    
    负责记录和管理事件数据
    """
    
    def __init__(self, db_path: str = "data/event_records.db"):
        """
        初始化事件记录器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self._init_database()
        
        logger.info(f"✅ 事件记录器初始化成功: {db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # 创建事件记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT NOT NULL,
                event_type TEXT NOT NULL,
                stock_code TEXT NOT NULL,
                description TEXT,
                confidence REAL,
                trigger_conditions TEXT,
                
                yesterday_close REAL,
                open_price REAL,
                current_price REAL,
                
                day_close REAL,
                day_close_pct REAL,
                next_day_open REAL,
                next_day_open_pct REAL,
                max_gain_3days REAL,
                max_loss_3days REAL,
                
                is_profitable INTEGER,
                profit_amount REAL,
                notes TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_time ON event_records(event_time)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_code ON event_records(stock_code)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type ON event_records(event_type)
        """)
        
        self.conn.commit()
        logger.info("✅ 数据库表初始化完成")
    
    def record_event(self, event: TradingEvent, tick_data: Dict[str, Any]) -> int:
        """
        记录事件
        
        Args:
            event: 交易事件
            tick_data: Tick数据
        
        Returns:
            记录ID
        """
        cursor = self.conn.cursor()
        
        record = EventRecord(
            event_time=event.timestamp.isoformat(),
            event_type=event.event_type.value,
            stock_code=event.stock_code,
            description=event.description,
            confidence=event.confidence,
            trigger_conditions=json.dumps(event.data, ensure_ascii=False),
            yesterday_close=tick_data.get('close', 0),
            open_price=tick_data.get('open', 0),
            current_price=tick_data.get('now', 0)
        )
        
        cursor.execute("""
            INSERT INTO event_records (
                event_time, event_type, stock_code, description, confidence,
                trigger_conditions, yesterday_close, open_price, current_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.event_time,
            record.event_type,
            record.stock_code,
            record.description,
            record.confidence,
            record.trigger_conditions,
            record.yesterday_close,
            record.open_price,
            record.current_price
        ))
        
        self.conn.commit()
        
        record_id = cursor.lastrowid
        logger.info(f"💾 记录事件: {event.stock_code} - {event.description} (ID: {record_id})")
        
        return record_id
    
    def update_day_close(self, record_id: int, day_close: float):
        """
        更新当日收盘价
        
        Args:
            record_id: 记录ID
            day_close: 当日收盘价
        """
        cursor = self.conn.cursor()
        
        # 先获取昨收价
        cursor.execute("SELECT yesterday_close FROM event_records WHERE id = ?", (record_id,))
        result = cursor.fetchone()
        
        if result:
            yesterday_close = result[0]
            day_close_pct = (day_close - yesterday_close) / yesterday_close if yesterday_close > 0 else 0
            
            cursor.execute("""
                UPDATE event_records 
                SET day_close = ?, day_close_pct = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (day_close, day_close_pct, record_id))
            
            self.conn.commit()
            logger.info(f"📝 更新收盘价: ID {record_id}, 收盘 {day_close}, 涨幅 {day_close_pct*100:.2f}%")
    
    def update_next_day_open(self, record_id: int, next_day_open: float):
        """
        更新次日开盘价
        
        Args:
            record_id: 记录ID
            next_day_open: 次日开盘价
        """
        cursor = self.conn.cursor()
        
        # 先获取昨收价
        cursor.execute("SELECT yesterday_close FROM event_records WHERE id = ?", (record_id,))
        result = cursor.fetchone()
        
        if result:
            yesterday_close = result[0]
            next_day_open_pct = (next_day_open - yesterday_close) / yesterday_close if yesterday_close > 0 else 0
            
            cursor.execute("""
                UPDATE event_records 
                SET next_day_open = ?, next_day_open_pct = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (next_day_open, next_day_open_pct, record_id))
            
            self.conn.commit()
            logger.info(f"📝 更新次日开盘: ID {record_id}, 开盘 {next_day_open}, 涨幅 {next_day_open_pct*100:.2f}%")
    
    def update_3days_performance(
        self,
        record_id: int,
        max_gain: float,
        max_loss: float,
        is_profitable: bool,
        profit_amount: float
    ):
        """
        更新3天表现
        
        Args:
            record_id: 记录ID
            max_gain: 3天内最大涨幅
            max_loss: 3天内最大跌幅
            is_profitable: 是否赚钱
            profit_amount: 盈利金额
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            UPDATE event_records 
            SET max_gain_3days = ?, max_loss_3days = ?, is_profitable = ?, profit_amount = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (max_gain, max_loss, 1 if is_profitable else 0, profit_amount, record_id))
        
        self.conn.commit()
        logger.info(f"📝 更新3天表现: ID {record_id}, 盈利 {is_profitable}, 盈利金额 {profit_amount}")
    
    def get_records(
        self,
        event_type: Optional[str] = None,
        stock_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[EventRecord]:
        """
        获取事件记录
        
        Args:
            event_type: 事件类型过滤
            stock_code: 股票代码过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制
        
        Returns:
            事件记录列表
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM event_records WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)
        
        if start_date:
            query += " AND event_time >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND event_time <= ?"
            params.append(end_date)
        
        query += " ORDER BY event_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 获取列名
        columns = [desc[0] for desc in cursor.description]
        
        # 转换为EventRecord对象
        records = []
        for row in rows:
            record_dict = dict(zip(columns, row))
            # 转换is_profitable为布尔值
            if record_dict.get('is_profitable') is not None:
                record_dict['is_profitable'] = bool(record_dict['is_profitable'])
            records.append(EventRecord(**record_dict))
        
        return records
    
    def export_to_csv(self, output_path: str = "data/event_records.csv"):
        """
        导出为CSV文件
        
        Args:
            output_path: 输出文件路径
        """
        import csv
        
        records = self.get_records(limit=1000)
        
        if not records:
            logger.warning("⚠️  没有记录可导出")
            return
        
        # 转换为字典
        data = [record.to_dict() for record in records]
        
        # 写入CSV
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"✅ 导出CSV: {output_path}, 共 {len(records)} 条记录")
    
    def export_to_excel(self, output_path: str = "data/event_records.xlsx"):
        """
        导出为Excel文件
        
        Args:
            output_path: 输出文件路径
        """
        try:
            import pandas as pd
            
            records = self.get_records(limit=1000)
            
            if not records:
                logger.warning("⚠️  没有记录可导出")
                return
            
            # 转换为DataFrame
            data = [record.to_dict() for record in records]
            df = pd.DataFrame(data)
            
            # 格式化列名（中文）
            column_map = {
                'event_time': '时间',
                'stock_code': '股票代码',
                'event_type': '事件类型',
                'description': '事件描述',
                'confidence': '置信度',
                'trigger_conditions': '触发条件',
                'yesterday_close': '昨收价',
                'open_price': '开盘价',
                'current_price': '当前价',
                'day_close': '收盘价',
                'day_close_pct': '收盘涨幅',
                'next_day_open': '次日开盘',
                'next_day_open_pct': '次日开盘涨幅',
                'max_gain_3days': '3天最大涨幅',
                'max_loss_3days': '3天最大跌幅',
                'is_profitable': '是否赚钱',
                'profit_amount': '盈利金额',
                'notes': '备注'
            }
            
            df.rename(columns=column_map, inplace=True)
            
            # 写入Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            logger.info(f"✅ 导出Excel: {output_path}, 共 {len(records)} 条记录")
            
        except ImportError:
            logger.error("❌ 需要安装 pandas 和 openpyxl: pip install pandas openpyxl")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计数据
        
        Returns:
            统计数据字典
        """
        cursor = self.conn.cursor()
        
        # 总记录数
        cursor.execute("SELECT COUNT(*) FROM event_records")
        total_records = cursor.fetchone()[0]
        
        # 按事件类型统计
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM event_records
            GROUP BY event_type
        """)
        event_type_stats = dict(cursor.fetchall())
        
        # 盈利统计
        cursor.execute("SELECT COUNT(*) FROM event_records WHERE is_profitable = 1")
        profitable_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM event_records WHERE is_profitable = 0 AND is_profitable IS NOT NULL")
        loss_count = cursor.fetchone()[0]
        
        # 平均盈利/亏损
        cursor.execute("SELECT AVG(profit_amount) FROM event_records WHERE is_profitable = 1")
        avg_profit = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(profit_amount) FROM event_records WHERE is_profitable = 0")
        avg_loss = cursor.fetchone()[0] or 0
        
        # 胜率
        win_rate = profitable_count / (profitable_count + loss_count) if (profitable_count + loss_count) > 0 else 0
        
        stats = {
            'total_records': total_records,
            'event_type_stats': event_type_stats,
            'profitable_count': profitable_count,
            'loss_count': loss_count,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'win_rate': win_rate
        }
        
        return stats
    
    def print_statistics(self):
        """打印统计数据"""
        stats = self.get_statistics()
        
        print("\n" + "=" * 80)
        print("📊 事件记录统计")
        print("=" * 80)
        print(f"总记录数: {stats['total_records']}")
        print(f"\n按事件类型统计:")
        for event_type, count in stats['event_type_stats'].items():
            print(f"   {event_type}: {count} 次")
        
        print(f"\n盈利统计:")
        print(f"   盈利次数: {stats['profitable_count']}")
        print(f"   亏损次数: {stats['loss_count']}")
        print(f"   平均盈利: {stats['avg_profit']:.2f}")
        print(f"   平均亏损: {stats['avg_loss']:.2f}")
        print(f"   胜率: {stats['win_rate']*100:.2f}%")
        print("=" * 80)
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("✅ 数据库连接已关闭")


# 创建全局实例（单例）
_event_recorder_instance = None


def get_event_recorder() -> EventRecorder:
    """
    获取事件记录器单例
    
    Returns:
        EventRecorder实例
    """
    global _event_recorder_instance
    
    if _event_recorder_instance is None:
        _event_recorder_instance = EventRecorder()
    
    return _event_recorder_instance


if __name__ == "__main__":
    # 快速测试
    recorder = EventRecorder()
    
    print("✅ 事件记录器测试")
    print(f"   数据库路径: {recorder.db_path}")
    
    # 打印统计
    recorder.print_statistics()
    
    # 导出CSV
    recorder.export_to_csv()
    
    # 尝试导出Excel
    recorder.export_to_excel()
    
    recorder.close()
