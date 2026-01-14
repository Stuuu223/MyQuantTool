"""
交易日志模块

记录所有交易信号,实现自动复盘和反馈闭环
构建 RAG 交易日记,让 AI 拥有记忆
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from logic.logger import get_logger

logger = get_logger(__name__)


class TradeLog:
    """
    交易日志管理器
    
    功能:
    1. 记录买入/卖出信号
    2. 自动计算盈亏
    3. 标记成功/失败案例
    4. 检索相似案例
    """
    
    def __init__(self, db_path='data/trade_log.db'):
        """
        初始化交易日志管理器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                action TEXT NOT NULL,  -- 'BUY' or 'SELL'
                price REAL NOT NULL,
                shares INTEGER NOT NULL,
                amount REAL NOT NULL,
                signal_source TEXT,  -- 信号来源（dragon/trend/halfway）
                signal_score REAL,   -- 信号评分
                market_regime TEXT,  -- 市场环境
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                strategy_params TEXT,  -- 策略参数（JSON）
                ai_reasoning TEXT,    -- AI推理过程
                status TEXT DEFAULT 'OPEN'  -- 'OPEN', 'CLOSED', 'PROFIT', 'LOSS'
            )
        ''')
        
        # 创建盈亏记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profit_loss (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                buy_price REAL,
                sell_price REAL,
                shares INTEGER,
                profit REAL,
                profit_ratio REAL,
                hold_days INTEGER,
                close_date DATETIME,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        ''')
        
        # 创建案例标记表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                case_type TEXT NOT NULL,  -- 'SUCCESS' or 'FAILURE'
                reason TEXT,
                lesson TEXT,
                similar_cases TEXT,  -- 相似案例（JSON）
                tags TEXT,  -- 标签（JSON）
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_trade(self, code: str, name: str, action: str, price: float, shares: int,
                  signal_source: str = None, signal_score: float = None,
                  market_regime: str = None, strategy_params: Dict = None,
                  ai_reasoning: str = None) -> int:
        """
        记录交易
        
        Args:
            code: 股票代码
            name: 股票名称
            action: 操作类型（'BUY' or 'SELL'）
            price: 价格
            shares: 股数
            signal_source: 信号来源
            signal_score: 信号评分
            market_regime: 市场环境
            strategy_params: 策略参数
            ai_reasoning: AI推理过程
        
        Returns:
            int: 交易ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        amount = price * shares
        
        cursor.execute('''
            INSERT INTO trades 
            (code, name, action, price, shares, amount, signal_source, signal_score, 
             market_regime, strategy_params, ai_reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code, name, action, price, shares, amount, signal_source, signal_score,
            market_regime, json.dumps(strategy_params) if strategy_params else None,
            ai_reasoning
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"记录交易: {action} {name}({code}) {shares}股 @ {price:.2f}")
        
        return trade_id
    
    def calculate_profit_loss(self, trade_id: int, sell_price: float) -> Dict:
        """
        计算盈亏
        
        Args:
            trade_id: 交易ID
            sell_price: 卖出价格
        
        Returns:
            dict: 盈亏信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取买入记录
        cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
        trade = cursor.fetchone()
        
        if not trade or trade[3] != 'BUY':
            conn.close()
            return None
        
        buy_price = trade[4]
        shares = trade[5]
        buy_date = datetime.now()  # 简化处理，使用当前时间
        sell_date = datetime.now()
        
        # 计算盈亏
        profit = (sell_price - buy_price) * shares
        profit_ratio = (sell_price - buy_price) / buy_price * 100
        hold_days = (sell_date - buy_date).days
        
        # 记录盈亏
        cursor.execute('''
            INSERT INTO profit_loss 
            (trade_id, buy_price, sell_price, shares, profit, profit_ratio, hold_days, close_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trade_id, buy_price, sell_price, shares, profit, profit_ratio, hold_days, sell_date))
        
        # 更新交易状态
        status = 'PROFIT' if profit > 0 else 'LOSS'
        cursor.execute('UPDATE trades SET status = ? WHERE id = ?', (status, trade_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"计算盈亏: {trade_id} 盈亏={profit:.2f} 比例={profit_ratio:.2f}%")
        
        return {
            'trade_id': trade_id,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'shares': shares,
            'profit': profit,
            'profit_ratio': profit_ratio,
            'hold_days': hold_days,
            'status': status
        }
    
    def mark_case(self, trade_id: int, case_type: str, reason: str = None,
                  lesson: str = None, tags: List[str] = None):
        """
        标记案例（成功/失败）
        
        Args:
            trade_id: 交易ID
            case_type: 案例类型（'SUCCESS' or 'FAILURE'）
            reason: 原因
            lesson: 教训
            tags: 标签
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO cases 
            (trade_id, case_type, reason, lesson, tags)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            trade_id, case_type, reason, lesson,
            json.dumps(tags) if tags else None
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"标记案例: {trade_id} 类型={case_type}")
    
    def get_recent_cases(self, case_type: str = None, limit: int = 5) -> List[Dict]:
        """
        获取最近的案例
        
        Args:
            case_type: 案例类型（'SUCCESS' or 'FAILURE'）
            limit: 返回数量
        
        Returns:
            list: 案例列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if case_type:
            cursor.execute('''
                SELECT c.*, t.code, t.name, t.signal_score, t.market_regime, 
                       pl.profit_ratio, pl.hold_days
                FROM cases c
                JOIN trades t ON c.trade_id = t.id
                LEFT JOIN profit_loss pl ON c.trade_id = pl.trade_id
                WHERE c.case_type = ?
                ORDER BY c.timestamp DESC
                LIMIT ?
            ''', (case_type, limit))
        else:
            cursor.execute('''
                SELECT c.*, t.code, t.name, t.signal_score, t.market_regime,
                       pl.profit_ratio, pl.hold_days
                FROM cases c
                JOIN trades t ON c.trade_id = t.id
                LEFT JOIN profit_loss pl ON c.trade_id = pl.trade_id
                ORDER BY c.timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        cases = []
        for row in rows:
            cases.append({
                'id': row[0],
                'trade_id': row[1],
                'case_type': row[2],
                'reason': row[3],
                'lesson': row[4],
                'code': row[7],
                'name': row[8],
                'signal_score': row[9],
                'market_regime': row[10],
                'profit_ratio': row[11],
                'hold_days': row[12]
            })
        
        return cases
    
    def get_similar_cases(self, code: str, signal_score: float, 
                         market_regime: str, limit: int = 3) -> List[Dict]:
        """
        获取相似案例
        
        Args:
            code: 股票代码
            signal_score: 信号评分
            market_regime: 市场环境
            limit: 返回数量
        
        Returns:
            list: 相似案例列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 简化版：只查询相同市场环境的案例
        cursor.execute('''
            SELECT c.*, t.code, t.name, t.signal_score, t.market_regime,
                   pl.profit_ratio, pl.hold_days
            FROM cases c
            JOIN trades t ON c.trade_id = t.id
            LEFT JOIN profit_loss pl ON c.trade_id = pl.trade_id
            WHERE t.market_regime = ?
            ORDER BY ABS(t.signal_score - ?) ASC
            LIMIT ?
        ''', (market_regime, signal_score, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        cases = []
        for row in rows:
            cases.append({
                'id': row[0],
                'trade_id': row[1],
                'case_type': row[2],
                'reason': row[3],
                'lesson': row[4],
                'code': row[7],
                'name': row[8],
                'signal_score': row[9],
                'market_regime': row[10],
                'profit_ratio': row[11],
                'hold_days': row[12]
            })
        
        return cases
    
    def get_statistics(self) -> Dict:
        """
        获取交易统计
        
        Returns:
            dict: 统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总交易次数
        cursor.execute('SELECT COUNT(*) FROM trades')
        total_trades = cursor.fetchone()[0]
        
        # 盈利交易次数
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = "PROFIT"')
        profit_trades = cursor.fetchone()[0]
        
        # 亏损交易次数
        cursor.execute('SELECT COUNT(*) FROM trades WHERE status = "LOSS"')
        loss_trades = cursor.fetchone()[0]
        
        # 平均盈亏比例
        cursor.execute('SELECT AVG(profit_ratio) FROM profit_loss')
        avg_profit_ratio = cursor.fetchone()[0] or 0
        
        # 成功案例数
        cursor.execute('SELECT COUNT(*) FROM cases WHERE case_type = "SUCCESS"')
        success_cases = cursor.fetchone()[0]
        
        # 失败案例数
        cursor.execute('SELECT COUNT(*) FROM cases WHERE case_type = "FAILURE"')
        failure_cases = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'profit_trades': profit_trades,
            'loss_trades': loss_trades,
            'win_rate': profit_trades / total_trades if total_trades > 0 else 0,
            'avg_profit_ratio': avg_profit_ratio,
            'success_cases': success_cases,
            'failure_cases': failure_cases
        }
    
    def get_learning_context(self, limit: int = 5) -> str:
        """
        获取学习上下文（用于注入到 AI Prompt）
        
        Args:
            limit: 返回案例数量
        
        Returns:
            str: 学习上下文文本
        """
        # 获取最近的失败案例
        failure_cases = self.get_recent_cases('FAILURE', limit)
        
        # 获取最近的成功案例
        success_cases = self.get_recent_cases('SUCCESS', limit)
        
        context = "## 历史交易教训\n\n"
        
        if failure_cases:
            context += "### 最近失败案例:\n"
            for case in failure_cases:
                context += f"- {case['name']}({case['code']}): {case['reason']}\n"
                if case['lesson']:
                    context += f"  教训: {case['lesson']}\n"
                context += f"  评分: {case['signal_score']}, 市场: {case['market_regime']}\n\n"
        
        if success_cases:
            context += "### 最近成功案例:\n"
            for case in success_cases:
                profit_ratio = case.get('profit_ratio', 0)
                if isinstance(profit_ratio, (int, float)):
                    context += f"- {case['name']}({case['code']}): 盈利 {profit_ratio:.2f}%\n"
                else:
                    context += f"- {case['name']}({case['code']}): 盈利 {profit_ratio}%\n"
                context += f"  评分: {case['signal_score']}, 市场: {case['market_regime']}\n\n"
        
        return context
