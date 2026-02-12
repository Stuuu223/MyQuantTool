#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易信号记录器

记录每天的扫描结果、买入信号、交易结果

Author: MyQuantTool Team
Date: 2026-02-12
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from logic.logger import get_logger

logger = get_logger(__name__)


class SignalRecorder:
    """
    信号记录器

    功能：
    1. 记录竞价候选池
    2. 记录买入信号
    3. 记录当日交易结果
    4. 生成统计报告
    """

    def __init__(self, db_path: str = "data/signal_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 表1: 竞价候选池
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auction_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                reason TEXT,
                decision_tag TEXT,
                risk_score REAL,
                hot_score REAL,
                sector_name TEXT,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, code)
            )
        ''')

        # 表2: 买入信号
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buy_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                signal_time TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                entry_price REAL,
                decision_tag TEXT,
                risk_score REAL,
                ratio REAL,
                confidence REAL,
                reason TEXT,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, code, signal_time)
            )
        ''')

        # 表3: 交易结果
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                entry_price REAL,
                exit_price REAL,
                pct_change REAL,
                hold_days INTEGER,
                result TEXT,  -- 'WIN' / 'LOSS' / 'BREAK_EVEN'
                exit_reason TEXT,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, code)
            )
        ''')

        # 表4: 每日统计
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL UNIQUE,
                candidate_count INTEGER,
                buy_signal_count INTEGER,
                win_count INTEGER,
                loss_count INTEGER,
                win_rate REAL,
                avg_return REAL,
                max_drawdown REAL,
                create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

        logger.info(f"✅ 信号记录数据库初始化完成: {self.db_path}")

    def record_auction_candidate(
        self,
        code: str,
        name: str,
        reason: str,
        decision_tag: str,
        risk_score: float,
        hot_score: float = 0.0,
        sector_name: str = ""
    ):
        """
        记录竞价候选

        Args:
            code: 股票代码
            name: 股票名称
            reason: 入选原因
            decision_tag: 决策标签（FOCUS✅/WATCH👀/PASS❌）
            risk_score: 风险评分
            hot_score: 热门评分
            sector_name: 板块名称
        """
        trade_date = datetime.now().strftime('%Y-%m-%d')

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO auction_candidates
                (trade_date, code, name, reason, decision_tag, risk_score, hot_score, sector_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_date, code, name, reason, decision_tag, risk_score, hot_score, sector_name))

            conn.commit()
            conn.close()

            logger.debug(f"📝 记录竞价候选: {code} {name} ({decision_tag})")

        except Exception as e:
            logger.error(f"❌ 记录竞价候选失败 {code}: {e}")

    def record_buy_signal(
        self,
        code: str,
        name: str,
        entry_price: float,
        decision_tag: str,
        risk_score: float,
        ratio: float,
        confidence: float,
        reason: str
    ):
        """
        记录买入信号

        Args:
            code: 股票代码
            name: 股票名称
            entry_price: 入场价格
            decision_tag: 决策标签
            risk_score: 风险评分
            ratio: 资金推动力比值
            confidence: 系统置信度
            reason: 买入理由
        """
        trade_date = datetime.now().strftime('%Y-%m-%d')
        signal_time = datetime.now().strftime('%H:%M:%S')

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO buy_signals
                (trade_date, signal_time, code, name, entry_price, decision_tag,
                 risk_score, ratio, confidence, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_date, signal_time, code, name, entry_price, decision_tag,
                  risk_score, ratio, confidence, reason))

            conn.commit()
            conn.close()

            logger.info(f"🎯 记录买入信号: {code} {name} @{entry_price:.2f} ({decision_tag})")

        except Exception as e:
            logger.error(f"❌ 记录买入信号失败 {code}: {e}")

    def record_trade_result(
        self,
        code: str,
        name: str,
        entry_price: float,
        exit_price: float,
        hold_days: int,
        exit_reason: str
    ):
        """
        记录交易结果

        Args:
            code: 股票代码
            name: 股票名称
            entry_price: 入场价格
            exit_price: 出场价格
            hold_days: 持仓天数
            exit_reason: 出场原因（止盈/止损/到期）
        """
        trade_date = datetime.now().strftime('%Y-%m-%d')
        pct_change = (exit_price - entry_price) / entry_price * 100

        # 判断结果
        if pct_change > 0.5:
            result = 'WIN'
        elif pct_change < -0.5:
            result = 'LOSS'
        else:
            result = 'BREAK_EVEN'

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO trade_results
                (trade_date, code, name, entry_price, exit_price, pct_change,
                 hold_days, result, exit_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_date, code, name, entry_price, exit_price, pct_change,
                  hold_days, result, exit_reason))

            conn.commit()
            conn.close()

            emoji = "✅" if result == 'WIN' else "❌" if result == 'LOSS' else "⚪"
            logger.info(f"{emoji} 记录交易结果: {code} {pct_change:+.2f}% ({exit_reason})")

        except Exception as e:
            logger.error(f"❌ 记录交易结果失败 {code}: {e}")

    def get_statistics(self, days: int = 30) -> Dict:
        """
        获取统计数据

        Args:
            days: 统计最近N天

        Returns:
            dict: 统计结果
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 统计买入信号
            cursor.execute('''
                SELECT COUNT(*) FROM buy_signals
                WHERE date(create_time) >= date('now', '-{} days')
            '''.format(days))
            total_signals = cursor.fetchone()[0]

            # 统计交易结果
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    AVG(pct_change) as avg_return,
                    MIN(pct_change) as max_loss,
                    MAX(pct_change) as max_gain
                FROM trade_results
                WHERE date(create_time) >= date('now', '-{} days')
            '''.format(days))

            stats = cursor.fetchone()
            conn.close()

            total, wins, losses, avg_return, max_loss, max_gain = stats
            win_rate = wins / total * 100 if total > 0 else 0

            return {
                'total_signals': total_signals,
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'avg_return': avg_return or 0,
                'max_loss': max_loss or 0,
                'max_gain': max_gain or 0
            }

        except Exception as e:
            logger.error(f"❌ 统计数据获取失败: {e}")
            return {}

    def export_report(self, days: int = 30, output_path: str = "data/signal_report.json"):
        """
        导出统计报告

        Args:
            days: 统计最近N天
            output_path: 输出文件路径
        """
        stats = self.get_statistics(days)

        report = {
            'report_date': datetime.now().isoformat(),
            'period_days': days,
            'statistics': stats
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"📊 统计报告已导出: {output_path}")
        logger.info(f"   总信号: {stats['total_signals']}")
        logger.info(f"   总交易: {stats['total_trades']}")
        logger.info(f"   胜率: {stats['win_rate']:.1f}%")
        logger.info(f"   平均收益: {stats['avg_return']:+.2f}%")


# 全局单例
_recorder_instance: Optional[SignalRecorder] = None


def get_signal_recorder() -> SignalRecorder:
    """获取全局信号记录器实例"""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = SignalRecorder()
    return _recorder_instance