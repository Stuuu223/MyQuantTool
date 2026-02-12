#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 铁律预警系统
在接近铁律阈值时提前预警，给用户足够的时间做出决策
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from logic.utils.logger import get_logger
from logic.database_manager import get_db_manager
from logic.monitors.iron_rule_monitor import IronRuleMonitor
from logic.position_manager import PositionManager

logger = get_logger(__name__)


class IronRuleAlert:
    """
    V13 铁律预警系统
    
    功能：
    1. 实时监控预警
    2. 多级预警（预警、危险、熔断）
    3. 预警通知
    4. 预警历史记录
    """
    
    # 预警级别
    ALERT_LEVEL_INFO = 0      # 信息
    ALERT_LEVEL_WARNING = 1  # 预警
    ALERT_LEVEL_DANGER = 2   # 危险
    ALERT_LEVEL_CRITICAL = 3 # 熔断
    
    # 预警类型
    ALERT_TYPE_LOGIC_REFUTED = "逻辑证伪"
    ALERT_TYPE_CAPITAL_OUTFLOW = "资金流出"
    ALERT_TYPE_LOSS_WARNING = "亏损预警"
    ALERT_TYPE_STOP_LOSS = "强制止损"
    
    def __init__(self):
        self.db = get_db_manager()
        self.monitor = IronRuleMonitor()
        self.position_manager = PositionManager()
        self.alert_callbacks = []  # 预警回调函数列表
        
        # 初始化数据库表
        self._init_tables()
    
    def _init_tables(self):
        """初始化预警数据库表"""
        try:
            # 创建预警历史表
            create_sql = """
            CREATE TABLE IF NOT EXISTS iron_rule_alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                alert_level INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                alert_message TEXT NOT NULL,
                alert_data TEXT,
                timestamp TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
            self.db.sqlite_execute(create_sql)
            
            # 创建预警配置表
            config_sql = """
            CREATE TABLE IF NOT EXISTS iron_rule_alert_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                threshold REAL NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
            self.db.sqlite_execute(config_sql)
            
        except Exception as e:
            logger.error(f"初始化预警数据库表失败: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """
        添加预警回调函数
        
        Args:
            callback: 回调函数，参数为 (code, alert_level, alert_type, alert_message)
        """
        self.alert_callbacks.append(callback)
    
    def check_stock_alerts(self, code: str) -> List[Dict]:
        """
        检查股票的预警
        
        Args:
            code: 股票代码
        
        Returns:
            list: 预警列表
        """
        alerts = []
        
        try:
            # 获取股票铁律状态
            iron_status = self.monitor.get_stock_iron_status(code)
            
            # 1. 检查逻辑证伪预警
            if iron_status['logic_status'] == '逻辑证伪':
                alert_level = self.ALERT_LEVEL_CRITICAL
                alert_type = self.ALERT_TYPE_LOGIC_REFUTED
                alert_message = f"🚨 逻辑证伪：发现关键词 {', '.join(iron_status['news_keywords'])}"
                alerts.append(self._create_alert(code, alert_level, alert_type, alert_message, iron_status))
            
            # 2. 检查资金流出预警
            dde_net_flow = iron_status.get('dde_net_flow', 0)
            if dde_net_flow < self.monitor.DANGER_THRESHOLD:
                alert_level = self.ALERT_LEVEL_DANGER
                alert_type = self.ALERT_TYPE_CAPITAL_OUTFLOW
                alert_message = f"⚠️ 资金大幅流出：DDE净流出 {dde_net_flow:.2f}亿"
                alerts.append(self._create_alert(code, alert_level, alert_type, alert_message, iron_status))
            elif dde_net_flow < self.monitor.WARNING_THRESHOLD:
                alert_level = self.ALERT_LEVEL_WARNING
                alert_type = self.ALERT_TYPE_CAPITAL_OUTFLOW
                alert_message = f"⚡ 资金流出预警：DDE净流出 {dde_net_flow:.2f}亿"
                alerts.append(self._create_alert(code, alert_level, alert_type, alert_message, iron_status))
            
            # 3. 检查亏损预警（需要获取持仓数据）
            # 这里暂时跳过，因为需要获取当前持仓数据
            
            # 4. 检查铁律锁定
            if iron_status['is_locked']:
                alert_level = self.ALERT_LEVEL_CRITICAL
                alert_type = "铁律锁定"
                alert_message = f"🔒 铁律锁定：{iron_status['lock_reason']}"
                alerts.append(self._create_alert(code, alert_level, alert_type, alert_message, iron_status))
            
            # 触发回调
            for alert in alerts:
                self._trigger_alert_callback(alert)
            
        except Exception as e:
            logger.error(f"检查股票 {code} 预警失败: {e}")
        
        return alerts
    
    def _create_alert(self, code: str, alert_level: int, alert_type: str, alert_message: str, alert_data: Dict) -> Dict:
        """
        创建预警对象
        
        Args:
            code: 股票代码
            alert_level: 预警级别
            alert_type: 预警类型
            alert_message: 预警消息
            alert_data: 预警数据
        
        Returns:
            dict: 预警对象
        """
        alert = {
            'code': code,
            'alert_level': alert_level,
            'alert_type': alert_type,
            'alert_message': alert_message,
            'alert_data': alert_data,
            'timestamp': datetime.now().isoformat()
        }
        
        # 记录预警历史
        self._record_alert(alert)
        
        return alert
    
    def _record_alert(self, alert: Dict):
        """
        记录预警历史
        
        Args:
            alert: 预警对象
        """
        try:
            import json
            insert_sql = """
            INSERT INTO iron_rule_alert_history 
            (code, alert_level, alert_type, alert_message, alert_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            self.db.sqlite_execute(insert_sql, (
                alert['code'],
                alert['alert_level'],
                alert['alert_type'],
                alert['alert_message'],
                json.dumps(alert['alert_data'], ensure_ascii=False),
                alert['timestamp']
            ))
            
        except Exception as e:
            logger.error(f"记录预警历史失败: {e}")
    
    def _trigger_alert_callback(self, alert: Dict):
        """
        触发预警回调
        
        Args:
            alert: 预警对象
        """
        for callback in self.alert_callbacks:
            try:
                callback(
                    alert['code'],
                    alert['alert_level'],
                    alert['alert_type'],
                    alert['alert_message']
                )
            except Exception as e:
                logger.error(f"预警回调失败: {e}")
    
    def get_alert_history(self, code: str = None, days: int = 7) -> List[Dict]:
        """
        获取预警历史
        
        Args:
            code: 股票代码（可选，为空则查询所有）
            days: 查询天数
        
        Returns:
            list: 预警历史列表
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            if code:
                query_sql = """
                SELECT * FROM iron_rule_alert_history
                WHERE code = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                """
                results = self.db.sqlite_query(query_sql, (code, start_date))
            else:
                query_sql = """
                SELECT * FROM iron_rule_alert_history
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                """
                results = self.db.sqlite_query(query_sql, (start_date,))
            
            history = []
            for row in results:
                import json
                history.append({
                    'id': row[0],
                    'code': row[1],
                    'alert_level': row[2],
                    'alert_type': row[3],
                    'alert_message': row[4],
                    'alert_data': json.loads(row[5]) if row[5] else {},
                    'timestamp': row[6],
                    'is_read': bool(row[7]),
                    'created_at': row[8]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取预警历史失败: {e}")
            return []
    
    def mark_as_read(self, alert_id: int):
        """
        标记预警为已读
        
        Args:
            alert_id: 预警ID
        """
        try:
            update_sql = "UPDATE iron_rule_alert_history SET is_read = 1 WHERE id = ?"
            self.db.sqlite_execute(update_sql, (alert_id,))
        except Exception as e:
            logger.error(f"标记预警为已读失败: {e}")
    
    def get_unread_alerts(self) -> List[Dict]:
        """
        获取未读预警
        
        Returns:
            list: 未读预警列表
        """
        try:
            query_sql = """
            SELECT * FROM iron_rule_alert_history
            WHERE is_read = 0
            ORDER BY timestamp DESC
            LIMIT 100
            """
            results = self.db.sqlite_query(query_sql)
            
            alerts = []
            for row in results:
                import json
                alerts.append({
                    'id': row[0],
                    'code': row[1],
                    'alert_level': row[2],
                    'alert_type': row[3],
                    'alert_message': row[4],
                    'alert_data': json.loads(row[5]) if row[5] else {},
                    'timestamp': row[6],
                    'is_read': bool(row[7]),
                    'created_at': row[8]
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"获取未读预警失败: {e}")
            return []


# 单例测试
if __name__ == "__main__":
    alert_system = IronRuleAlert()
    
    # 测试添加回调
    def test_callback(code, alert_level, alert_type, alert_message):
        print(f"回调触发: {code} - {alert_type} ({alert_level}) - {alert_message}")
    
    alert_system.add_alert_callback(test_callback)
    
    # 测试检查预警
    print("测试检查预警")
    alerts = alert_system.check_stock_alerts('600519')
    print(f"预警数量: {len(alerts)}")
    for alert in alerts:
        print(f"  {alert['code']}: {alert['alert_type']} - {alert['alert_message']}")
    
    # 测试获取预警历史
    print("\n测试获取预警历史")
    history = alert_system.get_alert_history(days=7)
    print(f"预警历史记录数: {len(history)}")
    
    # 测试获取未读预警
    print("\n测试获取未读预警")
    unread_alerts = alert_system.get_unread_alerts()
    print(f"未读预警数量: {len(unread_alerts)}")
