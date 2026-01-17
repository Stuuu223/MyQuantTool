"""
实时信号推送系统
功能：
- 多游资信号氫渫
- 自动分级
- 多途径推送 (邮件/Webhook/数据库)
- 信号历史跟踪
"""

import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import json
import sqlite3
from pathlib import Path
import threading
from queue import Queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import time

logger = logging.getLogger(__name__)


class SignalLevel(Enum):
    """信号等级"""
    CRITICAL = 1  # 紅色警报
    HIGH = 2      # 橙色警报
    MEDIUM = 3    # 黄色警报
    LOW = 4       # 绿色信号


class SignalType(Enum):
    """信号类型"""
    LSTM_PREDICT = "LSTM预测"
    KLINE_BREAKOUT = "K线突破"
    NETWORK_HUB = "网络中心"
    CAPITAL_COOPERATION = "游资合作"
    LEADER_DETECTION = "龙头棍法"
    AUCTION_LAYOUT = "集合窾价"
    REVERSAL_SIGNAL = "反转信号"


class PushChannel(Enum):
    """推送渠道"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    DATABASE = "database"
    LOG = "log"


@dataclass
class Signal:
    """
    信号数据类
    """
    signal_type: SignalType
    level: SignalLevel
    stock_code: str
    stock_name: str
    title: str
    content: str
    score: float  # 0-100
    recommendation: str  # 建议操作
    risk_level: str  # 低/中/高
    timestamp: datetime = None
    data: Dict = None  # 额外数据
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['signal_type'] = self.signal_type.value
        data['level'] = self.level.name
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_email_html(self) -> str:
        """转换为HTML体格邮件"""
        level_colors = {
            SignalLevel.CRITICAL: '#FF0000',
            SignalLevel.HIGH: '#FF9900',
            SignalLevel.MEDIUM: '#FFCC00',
            SignalLevel.LOW: '#00AA00'
        }
        
        color = level_colors.get(self.level, '#CCCCCC')
        
        html = f"""
        <div style="border-left: 5px solid {color}; padding: 15px; background: #f9f9f9; margin: 10px 0;">
            <h3 style="margin: 0 0 10px 0; color: {color};">
                [{self.level.name}] {self.signal_type.value}
            </h3>
            <p style="margin: 5px 0;"><strong>{self.stock_code} {self.stock_name}</strong></p>
            <p style="margin: 5px 0;"><strong>信号上为：</strong>{self.title}</p>
            <p style="margin: 5px 0;"><strong>详细描述：</strong>{self.content}</p>
            <p style="margin: 5px 0;"><strong>推莉指数：</strong>{self.score:.1f}/100</p>
            <p style="margin: 5px 0;"><strong>建议干预：</strong>{self.recommendation}</p>
            <p style="margin: 5px 0;"><strong>风险级别：</strong>{self.risk_level}</p>
            <p style="margin: 5px 0; color: #999; font-size: 12px;">时間：{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """
        return html


class SignalPusher:
    """
    中心推送引擎
    """
    
    def __init__(
        self,
        db_path: str = 'data/signals.db',
        email_config: Optional[Dict] = None,
        webhook_url: Optional[str] = None,
    ):
        """
        Args:
            db_path: 信号数据库路径
            email_config: 邮件配置
            webhook_url: Webhook URL (用于重延介DingTalk/企业微信等)
        """
        self.db_path = db_path
        self.email_config = email_config or {}
        self.webhook_url = webhook_url
        self.signal_queue = Queue()
        self.callbacks: Dict[SignalType, List[Callable]] = {}
        
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # 启动背景线程
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_signals, daemon=True)
        self.worker_thread.start()
    
    def _init_db(self) -> None:
        """初始化信号数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY,
                    signal_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT,
                    title TEXT,
                    content TEXT,
                    score REAL,
                    recommendation TEXT,
                    risk_level TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending'  -- pending/sent/failed
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_logs (
                    id INTEGER PRIMARY KEY,
                    signal_id INTEGER,
                    channel TEXT,
                    status TEXT,  -- success/failed
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_date ON signals(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_level ON signals(level)")
            conn.commit()
    
    def register_callback(
        self,
        signal_type: SignalType,
        callback: Callable[[Signal], None]
    ) -> None:
        """
        注册信号回调函数
        
        Args:
            signal_type: 信号类型
            callback: 回调函数
        """
        if signal_type not in self.callbacks:
            self.callbacks[signal_type] = []
        self.callbacks[signal_type].append(callback)
        logger.info(f"✅ 特定筹百取上报: {signal_type.value}")
    
    def emit_signal(self, signal: Signal) -> None:
        """
        发送信号箱
        
        Args:
            signal: Signal 对象
        """
        self.signal_queue.put(signal)
        logger.info(f"📨 新信号入库: {signal.stock_code} - {signal.signal_type.value} (\u7ea7别: {signal.level.name})")
    
    def _process_signals(self) -> None:
        """"背景业务上推送"""
        while self.running:
            try:
                signal = self.signal_queue.get(timeout=1)
                self._push_signal(signal)
            except:
                continue
    
    def _push_signal(self, signal: Signal) -> None:
        """
        推送一条信号到所有渠道
        """
        # 1. 存储到数据库
        signal_id = self._save_signal_db(signal)
        
        # 2. 执行回调
        if signal.signal_type in self.callbacks:
            for callback in self.callbacks[signal.signal_type]:
                try:
                    callback(signal)
                except Exception as e:
                    logger.error(f"回调执行失败: {str(e)}")
        
        # 3. 推送到渠道
        for channel in [PushChannel.EMAIL, PushChannel.WEBHOOK, PushChannel.LOG]:
            try:
                self._push_to_channel(signal, channel, signal_id)
            except Exception as e:
                logger.error(f"推送到 {channel.value} 失败: {str(e)}")
    
    def _save_signal_db(self, signal: Signal) -> int:
        """保存信号到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO signals
                (signal_type, level, stock_code, stock_name, title, content, score, recommendation, risk_level, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.signal_type.value,
                signal.level.name,
                signal.stock_code,
                signal.stock_name,
                signal.title,
                signal.content,
                signal.score,
                signal.recommendation,
                signal.risk_level,
                signal.timestamp
            ))
            conn.commit()
            return cursor.lastrowid
    
    def _push_to_channel(
        self,
        signal: Signal,
        channel: PushChannel,
        signal_id: int
    ) -> None:
        """推送到指定渠道"""
        status = 'failed'
        message = ''
        
        try:
            if channel == PushChannel.EMAIL:
                self._push_email(signal)
                status = 'success'
                message = 'Email sent'
            
            elif channel == PushChannel.WEBHOOK:
                self._push_webhook(signal)
                status = 'success'
                message = 'Webhook called'
            
            elif channel == PushChannel.LOG:
                self._push_log(signal)
                status = 'success'
                message = 'Logged'
        
        except Exception as e:
            message = str(e)
        
        # 记录推送日志
        self._save_push_log(signal_id, channel, status, message)
    
    def _push_email(self, signal: Signal) -> None:
        """邮件推送"""
        if not self.email_config.get('smtp_server'):
            logger.warning("⚠️ 未配置邮件引数")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[🔴 {signal.level.name}] {signal.stock_code} {signal.signal_type.value}"
            msg['From'] = self.email_config['sender']
            msg['To'] = self.email_config['receiver']
            
            html = signal.to_email_html()
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP_SSL(
                self.email_config['smtp_server'],
                self.email_config.get('smtp_port', 465)
            ) as server:
                server.login(
                    self.email_config['username'],
                    self.email_config['password']
                )
                server.send_message(msg)
            
            logger.info(f"✅ 邮件已发送: {signal.stock_code}")
        
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            raise
    
    def _push_webhook(self, signal: Signal) -> None:
        """Webhook 推送 (DingTalk/企业微信)"""
        if not self.webhook_url:
            return
        
        try:
            payload = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': f"[{signal.level.name}] {signal.signal_type.value}",
                    'text': f"""
### {signal.signal_type.value} - {signal.stock_code}

**股票**: {signal.stock_name}

**标题**: {signal.title}

**描述**: {signal.content}

**推莉指数**: {signal.score:.1f}/100

**建议**: {signal.recommendation}

**风险**: {signal.risk_level}

**时间**: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                    """
                }
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"✅ Webhook 已发送: {signal.stock_code}")
        
        except Exception as e:
            logger.error(f"Webhook 发送失败: {str(e)}")
            raise
    
    def _push_log(self, signal: Signal) -> None:
        """日志输出"""
        msg = f"""
        📨 [{signal.level.name}] {signal.signal_type.value}
        股票: {signal.stock_code} {signal.stock_name}
        标题: {signal.title}
        内容: {signal.content}
        分数: {signal.score:.1f}/100
        建议: {signal.recommendation}
        风险: {signal.risk_level}
        时间: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        """
        logger.info(msg)
    
    def _save_push_log(
        self,
        signal_id: int,
        channel: PushChannel,
        status: str,
        message: str
    ) -> None:
        """保存推送日志"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO signal_logs (signal_id, channel, status, message)
                VALUES (?, ?, ?, ?)
            """, (signal_id, channel.value, status, message))
            conn.commit()
    
    def get_recent_signals(
        self,
        hours: int = 24,
        level: Optional[SignalLevel] = None
    ) -> List[Dict]:
        """
        获取最近的信号
        
        Args:
            hours: 小时范围
            level: 信号等级 (可选)
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM signals
                WHERE timestamp > datetime('now', '-' || ? || ' hours')
            """
            params = [hours]
            
            if level:
                query += " AND level = ?"
                params.append(level.name)
            
            query += " ORDER BY timestamp DESC"
            
            cursor = conn.execute(query, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def stop(self) -> None:
        """停止推送系统"""
        self.running = False
        self.worker_thread.join(timeout=5)
        logger.info("✅ 推送系统已停止")
