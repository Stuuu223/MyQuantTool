"""
邮件告警服务模块
属性：
- 高风险自动发送邮件
- 高机会通知邮件
- 日线打底提示邮件
- 打并升突破邮件
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


@dataclass
class AlertEmail:
    """告警邮件数据类"""
    alert_type: str  # 'risk', 'opportunity', 'breakout', 'daily'
    title: str
    body: str
    recipient: str
    priority: str  # 'high', 'medium', 'low'
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EmailAlertService:
    """邮件告警服务"""
    
    def __init__(
        self,
        smtp_server: str = 'smtp.gmail.com',
        smtp_port: int = 587,
        sender_email: str = None,
        sender_password: str = None
    ):
        """
        初始化邮件服务
        
        Args:
            smtp_server: SMTP服务器
            smtp_port: SMTP端口
            sender_email: 发件者邮箱
            sender_password: 发件者密码/app_password
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.enabled = sender_email is not None and sender_password is not None
        self.sent_alerts = []  # 已发送告警日志
        
        if not self.enabled:
            logger.warning("邮件告警未配置,功能禁用")
    
    def send_risk_alert(
        self,
        capital_name: str,
        risk_score: float,
        risk_level: str,
        risk_factors: List[str],
        recipient: str
    ) -> bool:
        """发送高风险告警"""
        if not self.enabled:
            logger.warning("邮件未配置,无法发送")
            return False
        
        title = f"🚨 高风险告警: {capital_name} - {risk_level}"
        
        body = f"""
<html>
<body style="font-family: Arial; font-size: 14px;">
    <div style="background: #fff5f5; border-left: 4px solid #ff5459; padding: 15px;">
        <h2 style="color: #ff5459; margin: 0;">高风险告警</h2>
        <p><strong>游资名称:</strong> {capital_name}</p>
        <p><strong>风险评分:</strong> {risk_score:.0f}/100 ({risk_level})</p>
        <p><strong>风险因素:</strong></p>
        <ul>
            {chr(10).join([f'<li>{factor}</li>' for factor in risk_factors])}
        </ul>
        <p style="color: #999; font-size: 12px;">告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
        """
        
        return self._send_email(
            recipient=recipient,
            subject=title,
            body=body,
            alert_type='risk',
            priority='high'
        )
    
    def send_opportunity_alert(
        self,
        predicted_capitals: List[str],
        activity_score: int,
        predicted_stocks: List[str],
        recipient: str
    ) -> bool:
        """发送高机会通知"""
        if not self.enabled:
            return False
        
        title = f"🟢 高机会提醒: 明日龙虎榜活跃度{activity_score}/100"
        
        body = f"""
<html>
<body style="font-family: Arial; font-size: 14px;">
    <div style="background: #f0fdf4; border-left: 4px solid #32b898; padding: 15px;">
        <h2 style="color: #32b898; margin: 0;">高机会提醒</h2>
        <p><strong>活跃度评分:</strong> {activity_score}/100</p>
        
        <p><strong>预期活跃游资:</strong></p>
        <ul>
            {chr(10).join([f'<li>{cap}</li>' for cap in predicted_capitals[:5]])}
        </ul>
        
        <p><strong>高概率股票:</strong></p>
        <ul>
            {chr(10).join([f'<li>{stock}</li>' for stock in predicted_stocks[:5]])}
        </ul>
        
        <p style="color: #999; font-size: 12px;">告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
        """
        
        return self._send_email(
            recipient=recipient,
            subject=title,
            body=body,
            alert_type='opportunity',
            priority='high'
        )
    
    def send_breakout_alert(
        self,
        stock_code: str,
        stock_name: str,
        breakout_price: float,
        breakout_type: str,
        capitals: List[str],
        recipient: str
    ) -> bool:
        """发送打板突破告警"""
        if not self.enabled:
            return False
        
        emoji = '📈' if breakout_type == 'up' else '📉'
        direction = '上升突破' if breakout_type == 'up' else '下跌突破'
        
        title = f"{emoji} 打板突破: {stock_name}({stock_code}) {direction}到 {breakout_price:.2f}"
        
        body = f"""
<html>
<body style="font-family: Arial; font-size: 14px;">
    <div style="background: #fef3c7; border-left: 4px solid #e68a2c; padding: 15px;">
        <h2 style="color: #e68a2c; margin: 0;">打板突破告警</h2>
        <p><strong>股票:</strong> {stock_name} ({stock_code})</p>
        <p><strong>突破类型:</strong> {direction}</p>
        <p><strong>突破价格:</strong> {breakout_price:.2f}</p>
        <p><strong>活跃游资:</strong></p>
        <ul>
            {chr(10).join([f'<li>{cap}</li>' for cap in capitals[:5]])}
        </ul>
        <p style="color: #999; font-size: 12px;">告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
        """
        
        return self._send_email(
            recipient=recipient,
            subject=title,
            body=body,
            alert_type='breakout',
            priority='high'
        )
    
    def send_daily_summary(
        self,
        date: str,
        limit_up_count: int,
        limit_down_count: int,
        top_gainers: Dict,
        top_losers: Dict,
        top_capitals: Dict,
        recipient: str
    ) -> bool:
        """发送日线总结"""
        if not self.enabled:
            return False
        
        title = f"📊 {date} 龙虎榜日线总结"
        
        gainers_html = chr(10).join([
            f'<li>{code}: {name} {change:.2f}%</li>'
            for code, (name, change) in list(top_gainers.items())[:5]
        ])
        
        losers_html = chr(10).join([
            f'<li>{code}: {name} {change:.2f}%</li>'
            for code, (name, change) in list(top_losers.items())[:5]
        ])
        
        capitals_html = chr(10).join([
            f'<li>{cap}: {amount:,.0f}元</li>'
            for cap, amount in list(top_capitals.items())[:5]
        ])
        
        body = f"""
<html>
<body style="font-family: Arial; font-size: 14px;">
    <div style="background: #f0f9ff; border-left: 4px solid #667eea; padding: 15px;">
        <h2 style="color: #667eea; margin: 0;">{date} 龙虎榜日线总结</h2>
        
        <div style="margin: 15px 0;">
            <p><strong>市场统计:</strong></p>
            <ul>
                <li>涨停数: <span style="color: #ff5459;">{limit_up_count}</span></li>
                <li>跌停数: <span style="color: #32b898;">{limit_down_count}</span></li>
            </ul>
        </div>
        
        <div style="margin: 15px 0;">
            <p><strong>涨幅排行:</strong></p>
            <ul>
                {gainers_html}
            </ul>
        </div>
        
        <div style="margin: 15px 0;">
            <p><strong>跌幅排行:</strong></p>
            <ul>
                {losers_html}
            </ul>
        </div>
        
        <div style="margin: 15px 0;">
            <p><strong>游资排行:</strong></p>
            <ul>
                {capitals_html}
            </ul>
        </div>
        
        <p style="color: #999; font-size: 12px;">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
        """
        
        return self._send_email(
            recipient=recipient,
            subject=title,
            body=body,
            alert_type='daily',
            priority='low'
        )
    
    def _send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        alert_type: str,
        priority: str
    ) -> bool:
        """发送邮件的内部方法"""
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['X-Priority'] = '1' if priority == 'high' else '3'
            
            # 添加HTML部分
            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            # 记录已发送
            self.sent_alerts.append({
                'type': alert_type,
                'recipient': recipient,
                'subject': subject,
                'timestamp': datetime.now()
            })
            
            logger.info(f"邮件已发送: {recipient} - {subject}")
            return True
        
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP认证失败,请检查邮箱和密码")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP错误: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return False
    
    def get_sent_alerts(self, alert_type: str = None) -> List[Dict]:
        """获取已发送的告警列表"""
        if alert_type:
            return [a for a in self.sent_alerts if a['type'] == alert_type]
        return self.sent_alerts
    
    def configure(
        self,
        sender_email: str,
        sender_password: str,
        smtp_server: str = 'smtp.gmail.com',
        smtp_port: int = 587
    ):
        """配置邮件服务"""
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.enabled = True
        logger.info(f"邮件服务已配置: {sender_email}")
