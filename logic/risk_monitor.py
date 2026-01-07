"""
实时风险监控和告警模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "信息"
    WARNING = "警告"
    CRITICAL = "严重"
    EMERGENCY = "紧急"


class RiskMonitor:
    """
    实时风险监控器
    
    监控持仓、账户、市场等风险指标
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化风险监控器
        
        Args:
            config: 配置参数
                - max_position_ratio: 最大持仓比例
                - max_daily_loss_ratio: 单日最大亏损比例
                - max_drawdown_ratio: 最大回撤比例
                - max_consecutive_losses: 最大连续亏损次数
        """
        self.config = config or {}
        self.max_position_ratio = self.config.get('max_position_ratio', 0.95)
        self.max_daily_loss_ratio = self.config.get('max_daily_loss_ratio', 0.05)
        self.max_drawdown_ratio = self.config.get('max_drawdown_ratio', 0.20)
        self.max_consecutive_losses = self.config.get('max_consecutive_losses', 5)
        
        self.alerts: List[Dict] = []
        self.alert_handlers: List[Callable] = []
        
        # 风险指标历史
        self.risk_history: List[Dict] = []
    
    def add_alert_handler(self, handler: Callable):
        """
        添加告警处理器
        
        Args:
            handler: 告警处理函数
        """
        self.alert_handlers.append(handler)
    
    def _trigger_alert(
        self,
        level: AlertLevel,
        message: str,
        data: Dict = None
    ):
        """
        触发告警
        
        Args:
            level: 告警级别
            message: 告警消息
            data: 附加数据
        """
        alert = {
            'timestamp': datetime.now(),
            'level': level,
            'message': message,
            'data': data or {}
        }
        
        self.alerts.append(alert)
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        logger.warning(f"[{level.value}] {message}")
    
    def monitor_position(
        self,
        symbol: str,
        position_value: float,
        total_equity: float
    ):
        """
        监控持仓风险
        
        Args:
            symbol: 股票代码
            position_value: 持仓市值
            total_equity: 总权益
        """
        if total_equity == 0:
            return
        
        position_ratio = position_value / total_equity
        
        # 检查持仓比例
        if position_ratio > self.max_position_ratio:
            self._trigger_alert(
                AlertLevel.CRITICAL,
                f"持仓比例过高: {symbol} 占比 {position_ratio:.2%} > {self.max_position_ratio:.2%}",
                {'symbol': symbol, 'ratio': position_ratio}
            )
        elif position_ratio > self.max_position_ratio * 0.9:
            self._trigger_alert(
                AlertLevel.WARNING,
                f"持仓比例接近上限: {symbol} 占比 {position_ratio:.2%}",
                {'symbol': symbol, 'ratio': position_ratio}
            )
    
    def monitor_daily_loss(
        self,
        daily_pnl: float,
        initial_capital: float
    ):
        """
        监控单日亏损
        
        Args:
            daily_pnl: 当日盈亏
            initial_capital: 初始资金
        """
        if initial_capital == 0:
            return
        
        loss_ratio = daily_pnl / initial_capital
        
        # 检查单日亏损
        if loss_ratio < -self.max_daily_loss_ratio:
            self._trigger_alert(
                AlertLevel.EMERGENCY,
                f"单日亏损过大: {loss_ratio:.2%} < -{self.max_daily_loss_ratio:.2%}",
                {'loss_ratio': loss_ratio}
            )
        elif loss_ratio < -self.max_daily_loss_ratio * 0.7:
            self._trigger_alert(
                AlertLevel.CRITICAL,
                f"单日亏损较大: {loss_ratio:.2%}",
                {'loss_ratio': loss_ratio}
            )
    
    def monitor_drawdown(
        self,
        current_equity: float,
        peak_equity: float
    ):
        """
        监控回撤
        
        Args:
            current_equity: 当前权益
            peak_equity: 历史最高权益
        """
        if peak_equity == 0:
            return
        
        drawdown = (current_equity - peak_equity) / peak_equity
        
        # 检查回撤
        if drawdown < -self.max_drawdown_ratio:
            self._trigger_alert(
                AlertLevel.EMERGENCY,
                f"回撤过大: {drawdown:.2%} < -{self.max_drawdown_ratio:.2%}",
                {'drawdown': drawdown}
            )
        elif drawdown < -self.max_drawdown_ratio * 0.8:
            self._trigger_alert(
                AlertLevel.CRITICAL,
                f"回撤较大: {drawdown:.2%}",
                {'drawdown': drawdown}
            )
    
    def monitor_consecutive_losses(
        self,
        consecutive_losses: int
    ):
        """
        监控连续亏损
        
        Args:
            consecutive_losses: 连续亏损次数
        """
        if consecutive_losses >= self.max_consecutive_losses:
            self._trigger_alert(
                AlertLevel.CRITICAL,
                f"连续亏损次数过多: {consecutive_losses} 次 >= {self.max_consecutive_losses} 次",
                {'consecutive_losses': consecutive_losses}
            )
        elif consecutive_losses >= self.max_consecutive_losses * 0.7:
            self._trigger_alert(
                AlertLevel.WARNING,
                f"连续亏损次数较多: {consecutive_losses} 次",
                {'consecutive_losses': consecutive_losses}
            )
    
    def monitor_market_volatility(
        self,
        symbol: str,
        returns: pd.Series
    ):
        """
        监控市场波动率
        
        Args:
            symbol: 股票代码
            returns: 收益率序列
        """
        if len(returns) < 20:
            return
        
        # 计算20日波动率
        volatility = returns.tail(20).std() * np.sqrt(252)
        
        # 波动率过高 (> 50%)
        if volatility > 0.5:
            self._trigger_alert(
                AlertLevel.WARNING,
                f"市场波动率过高: {symbol} 波动率 {volatility:.2%}",
                {'symbol': symbol, 'volatility': volatility}
            )
    
    def monitor_correlation(
        self,
        returns_dict: Dict[str, pd.Series]
    ):
        """
        监控持仓相关性
        
        Args:
            returns_dict: 收益率字典 {symbol: returns}
        """
        if len(returns_dict) < 2:
            return
        
        # 计算相关性矩阵
        df = pd.DataFrame(returns_dict)
        corr_matrix = df.corr()
        
        # 检查高相关性 (> 0.8)
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr = corr_matrix.iloc[i, j]
                if corr > 0.8:
                    high_corr_pairs.append((
                        corr_matrix.columns[i],
                        corr_matrix.columns[j],
                        corr
                    ))
        
        if high_corr_pairs:
            self._trigger_alert(
                AlertLevel.WARNING,
                f"发现高相关性持仓: {len(high_corr_pairs)} 对",
                {'high_corr_pairs': high_corr_pairs}
            )
    
    def record_risk_metrics(self, metrics: Dict):
        """
        记录风险指标
        
        Args:
            metrics: 风险指标字典
        """
        metrics['timestamp'] = datetime.now()
        self.risk_history.append(metrics)
        
        # 只保留最近1000条记录
        if len(self.risk_history) > 1000:
            self.risk_history = self.risk_history[-1000:]
    
    def get_risk_summary(self) -> Dict:
        """
        获取风险摘要
        
        Returns:
            风险摘要
        """
        if not self.risk_history:
            return {}
        
        latest = self.risk_history[-1]
        
        return {
            'latest_metrics': latest,
            'alert_count': len(self.alerts),
            'critical_alerts': len([a for a in self.alerts if a['level'] in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]]),
            'warning_alerts': len([a for a in self.alerts if a['level'] == AlertLevel.WARNING]),
            'recent_alerts': self.alerts[-10:] if len(self.alerts) > 10 else self.alerts
        }
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        获取告警列表
        
        Args:
            level: 告警级别过滤
            since: 起始时间
        
        Returns:
            告警列表
        """
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a['level'] == level]
        
        if since:
            alerts = [a for a in alerts if a['timestamp'] >= since]
        
        return alerts
    
    def clear_alerts(self):
        """清空告警记录"""
        self.alerts.clear()


class EmailAlertHandler:
    """
    邮件告警处理器
    
    通过邮件发送告警通知
    """
    
    def __init__(self, smtp_config: Dict):
        """
        初始化邮件告警处理器
        
        Args:
            smtp_config: SMTP配置
                - host: SMTP服务器
                - port: 端口
                - username: 用户名
                - password: 密码
                - from_addr: 发件人
                - to_addrs: 收件人列表
        """
        self.smtp_config = smtp_config
    
    def __call__(self, alert: Dict):
        """
        发送邮件告警
        
        Args:
            alert: 告警信息
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.header import Header
            
            # 构建邮件内容
            subject = f"[{alert['level'].value}] 风险告警"
            content = f"""
时间: {alert['timestamp']}
级别: {alert['level'].value}
消息: {alert['message']}
数据: {alert['data']}
            """
            
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['From'] = self.smtp_config.get('from_addr')
            msg['To'] = ', '.join(self.smtp_config.get('to_addrs', []))
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 发送邮件
            with smtplib.SMTP(
                self.smtp_config.get('host'),
                self.smtp_config.get('port')
            ) as server:
                server.starttls()
                server.login(
                    self.smtp_config.get('username'),
                    self.smtp_config.get('password')
                )
                server.send_message(msg)
            
            logger.info(f"邮件告警已发送: {alert['message']}")
        
        except Exception as e:
            logger.error(f"邮件告警发送失败: {e}")


class LogAlertHandler:
    """
    日志告警处理器
    
    记录告警到日志文件
    """
    
    def __init__(self, log_file: str = 'risk_alerts.log'):
        """
        初始化日志告警处理器
        
        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file
        
        # 配置日志
        logging.basicConfig(
            filename=log_file,
            level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def __call__(self, alert: Dict):
        """
        记录告警到日志
        
        Args:
            alert: 告警信息
        """
        logger.warning(
            f"[{alert['level'].value}] {alert['message']} | Data: {alert['data']}"
        )