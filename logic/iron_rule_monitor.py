#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 实时铁律监控模块
实时监控股票的铁律状态，提供预警和历史回溯
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from logic.logger import get_logger
from logic.database_manager import get_db_manager
from logic.iron_rule_engine import IronRuleEngine
from logic.news_crawler import NewsCrawler
from logic.data_manager import DataManager

logger = get_logger(__name__)


class IronRuleMonitor:
    """
    V13 实时铁律监控器
    
    功能：
    1. 实时监控股票的铁律状态
    2. 提供接近阈值时的预警
    3. 记录铁律触发历史
    4. 多维度验证逻辑证伪
    """
    
    # 预警阈值
    WARNING_THRESHOLD = -0.5  # DDE净流出超过-0.5亿时预警
    DANGER_THRESHOLD = -0.8   # DDE净流出超过-0.8亿时警告
    
    # 亏损预警阈值
    LOSS_WARNING_THRESHOLD = -0.02  # 亏损-2%时预警
    LOSS_DANGER_THRESHOLD = -0.025  # 亏损-2.5%时警告
    
    def __init__(self):
        self.db = get_db_manager()
        self.iron_engine = IronRuleEngine()
        self.news_crawler = NewsCrawler()
        self.data_manager = DataManager()
        
    def get_stock_iron_status(self, code: str) -> Dict:
        """
        获取单只股票的铁律状态
        
        Args:
            code: 股票代码
        
        Returns:
            dict: {
                'code': 股票代码,
                'is_locked': 是否被锁定,
                'lock_reason': 锁定原因,
                'lock_time': 锁定时间,
                'remaining_hours': 剩余锁定小时数,
                'can_buy': 是否可以买入,
                'warning_level': 预警级别 (0: 正常, 1: 预警, 2: 危险, 3: 熔断),
                'warning_messages': 预警消息列表,
                'dde_net_flow': DDE净额,
                'logic_status': 逻辑状态,
                'news_keywords': 新闻关键词,
                'recommendation': 建议操作
            }
        """
        status = {
            'code': code,
            'is_locked': False,
            'lock_reason': '',
            'lock_time': '',
            'remaining_hours': 0,
            'can_buy': True,
            'warning_level': 0,
            'warning_messages': [],
            'dde_net_flow': 0,
            'logic_status': '正常',
            'news_keywords': [],
            'recommendation': '正常'
        }
        
        try:
            # 1. 获取实时数据
            realtime_data = self.data_manager.get_realtime_data(code)
            if realtime_data:
                # 获取 DDE 净额（单位：亿元）
                dde_net_flow = realtime_data.get('dde_net_flow', 0)
                status['dde_net_flow'] = dde_net_flow
                
                # 2. 获取新闻数据
                news_data = self.news_crawler.get_stock_news(code, limit=5)
                news_text = ' '.join([news.get('title', '') + news.get('content', '') for news in news_data])
                
                # 3. 检查铁律
                iron_result = self.iron_engine.check_stock_iron_rule(code, news_text, dde_net_flow)
                status.update(iron_result)
                
                # 4. 检查预警级别
                warning_level, warning_messages = self._check_warning_level(code, dde_net_flow, news_text)
                status['warning_level'] = warning_level
                status['warning_messages'] = warning_messages
                
                # 5. 检查逻辑状态
                logic_status, news_keywords = self._check_logic_status(news_text)
                status['logic_status'] = logic_status
                status['news_keywords'] = news_keywords
                
                # 6. 生成建议
                status['recommendation'] = self._generate_recommendation(status)
                
                # 7. 记录监控历史
                self._record_monitor_history(status)
                
        except Exception as e:
            logger.error(f"获取股票 {code} 铁律状态失败: {e}")
            status['warning_messages'].append(f"获取铁律状态失败: {e}")
        
        return status
    
    def _check_warning_level(self, code: str, dde_net_flow: float, news_text: str) -> Tuple[int, List[str]]:
        """
        检查预警级别
        
        Args:
            code: 股票代码
            dde_net_flow: DDE净额
            news_text: 新闻文本
        
        Returns:
            tuple: (预警级别, 预警消息列表)
        """
        warning_level = 0
        warning_messages = []
        
        # 检查 DDE 净流出
        if dde_net_flow < self.iron_engine.CAPITAL_OUT_THRESHOLD:
            warning_level = 3
            warning_messages.append(f"🚨 DDE净流出 {dde_net_flow:.2f}亿，超过熔断阈值")
        elif dde_net_flow < self.DANGER_THRESHOLD:
            warning_level = max(warning_level, 2)
            warning_messages.append(f"⚠️ DDE净流出 {dde_net_flow:.2f}亿，接近熔断阈值")
        elif dde_net_flow < self.WARNING_THRESHOLD:
            warning_level = max(warning_level, 1)
            warning_messages.append(f"⚡ DDE净流出 {dde_net_flow:.2f}亿，需要注意")
        
        # 检查逻辑证伪关键词
        fatal_keywords_found = [key for key in self.iron_engine.FATAL_NEWS_KEYWORDS if key in news_text]
        if fatal_keywords_found:
            warning_level = 3
            warning_messages.append(f"🚨 发现逻辑证伪关键词: {', '.join(fatal_keywords_found)}")
        
        return warning_level, warning_messages
    
    def _check_logic_status(self, news_text: str) -> Tuple[str, List[str]]:
        """
        检查逻辑状态
        
        Args:
            news_text: 新闻文本
        
        Returns:
            tuple: (逻辑状态, 关键词列表)
        """
        if not news_text:
            return '正常', []
        
        # 检查致命关键词
        fatal_keywords = [key for key in self.iron_engine.FATAL_NEWS_KEYWORDS if key in news_text]
        if fatal_keywords:
            return '逻辑证伪', fatal_keywords
        
        # 检查其他关注关键词
        attention_keywords = ['业绩', '利润', '收入', '营收', '订单', '合作', '投资']
        found_keywords = [key for key in attention_keywords if key in news_text]
        
        if found_keywords:
            return '需要关注', found_keywords
        
        return '正常', []
    
    def _generate_recommendation(self, status: Dict) -> str:
        """
        生成建议操作
        
        Args:
            status: 铁律状态
        
        Returns:
            str: 建议操作
        """
        if status['is_locked']:
            return '禁止买入 - 铁律锁定'
        
        if status['warning_level'] == 3:
            return '禁止买入 - 触发熔断'
        elif status['warning_level'] == 2:
            return '谨慎操作 - 接近熔断'
        elif status['warning_level'] == 1:
            return '注意风险 - 需要关注'
        else:
            return '正常'
    
    def _record_monitor_history(self, status: Dict):
        """
        记录监控历史
        
        Args:
            status: 铁律状态
        """
        try:
            # 创建监控历史表
            create_sql = """
            CREATE TABLE IF NOT EXISTS iron_rule_monitor_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_locked INTEGER NOT NULL,
                lock_reason TEXT,
                warning_level INTEGER NOT NULL,
                dde_net_flow REAL NOT NULL,
                logic_status TEXT NOT NULL,
                news_keywords TEXT,
                recommendation TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
            self.db.sqlite_execute(create_sql)
            
            # 插入监控记录
            insert_sql = """
            INSERT INTO iron_rule_monitor_history 
            (code, timestamp, is_locked, lock_reason, warning_level, dde_net_flow, logic_status, news_keywords, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db.sqlite_execute(insert_sql, (
                status['code'],
                datetime.now().isoformat(),
                1 if status['is_locked'] else 0,
                status['lock_reason'],
                status['warning_level'],
                status['dde_net_flow'],
                status['logic_status'],
                ','.join(status['news_keywords']) if status['news_keywords'] else '',
                status['recommendation']
            ))
            
        except Exception as e:
            logger.error(f"记录监控历史失败: {e}")
    
    def get_monitor_history(self, code: str, days: int = 7) -> List[Dict]:
        """
        获取监控历史
        
        Args:
            code: 股票代码
            days: 查询天数
        
        Returns:
            list: 监控历史列表
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            query_sql = """
            SELECT * FROM iron_rule_monitor_history
            WHERE code = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            """
            
            results = self.db.sqlite_query(query_sql, (code, start_date))
            
            history = []
            for row in results:
                history.append({
                    'id': row[0],
                    'code': row[1],
                    'timestamp': row[2],
                    'is_locked': bool(row[3]),
                    'lock_reason': row[4],
                    'warning_level': row[5],
                    'dde_net_flow': row[6],
                    'logic_status': row[7],
                    'news_keywords': row[8].split(',') if row[8] else [],
                    'recommendation': row[9],
                    'created_at': row[10]
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取监控历史失败: {e}")
            return []
    
    def get_all_locked_stocks(self) -> List[Dict]:
        """
        获取所有被锁定的股票
        
        Returns:
            list: 被锁定的股票列表
        """
        return self.iron_engine.get_locked_stocks()
    
    def get_warning_stocks(self, warning_level: int = 1) -> List[Dict]:
        """
        获取预警股票列表
        
        Args:
            warning_level: 预警级别 (1: 预警, 2: 危险, 3: 熔断)
        
        Returns:
            list: 预警股票列表
        """
        # 这里需要从自选股或监控列表中获取
        # 暂时返回空列表
        return []
    
    # ============================================================================
    # V16.3: 内部人防御盾 (Insider Shield)
    # ============================================================================
    
    def check_insider_selling(self, stock_code: str, days: int = 90) -> Dict:
        """
        检查内部人减持风险
        
        Args:
            stock_code: 股票代码
            days: 查询天数，默认 90 天
        
        Returns:
            dict: {
                'has_risk': bool,  # 是否存在风险
                'risk_level': str,  # 风险等级 (LOW, MEDIUM, HIGH)
                'total_decrease_ratio': float,  # 总减持比例 (%)
                'total_decrease_value': float,  # 总减持金额（万元）
                'decrease_records': list,  # 减持记录列表
                'reason': str  # 风险原因
            }
        """
        try:
            from logic.akshare_data_loader import AKShareDataLoader
            
            # 获取内部人减持风险分析
            risk_data = AKShareDataLoader.get_insider_selling_risk(stock_code, days)
            
            # 记录监控历史
            if risk_data['has_risk']:
                logger.warning(f"⚠️ [内部人风险] {stock_code} {risk_data['reason']}")
            else:
                logger.info(f"✅ [内部人安全] {stock_code} {risk_data['reason']}")
            
            return risk_data
            
        except Exception as e:
            logger.error(f"检查内部人减持风险失败: {e}")
            return {
                'has_risk': False,
                'risk_level': 'LOW',
                'total_decrease_ratio': 0.0,
                'total_decrease_value': 0.0,
                'decrease_records': [],
                'reason': f'检查失败: {e}'
            }
    
    def get_insider_risk_summary(self, stock_codes: List[str], days: int = 90) -> Dict:
        """
        获取多只股票的内部人风险摘要
        
        Args:
            stock_codes: 股票代码列表
            days: 查询天数，默认 90 天
        
        Returns:
            dict: {
                'total_stocks': int,  # 总股票数
                'high_risk_stocks': list,  # 高风险股票列表
                'medium_risk_stocks': list,  # 中风险股票列表
                'low_risk_stocks': list,  # 低风险股票列表
                'risk_details': dict  # 详细风险信息
            }
        """
        summary = {
            'total_stocks': len(stock_codes),
            'high_risk_stocks': [],
            'medium_risk_stocks': [],
            'low_risk_stocks': [],
            'risk_details': {}
        }
        
        for stock_code in stock_codes:
            risk_data = self.check_insider_selling(stock_code, days)
            
            # 分类
            if risk_data['risk_level'] == 'HIGH':
                summary['high_risk_stocks'].append(stock_code)
            elif risk_data['risk_level'] == 'MEDIUM':
                summary['medium_risk_stocks'].append(stock_code)
            else:
                summary['low_risk_stocks'].append(stock_code)
            
            # 记录详细信息
            summary['risk_details'][stock_code] = risk_data
        
        return summary


# 单例测试
if __name__ == "__main__":
    monitor = IronRuleMonitor()
    
    # 测试获取股票铁律状态
    print("测试获取股票铁律状态")
    status = monitor.get_stock_iron_status('600519')
    print(f"股票 600519 铁律状态: {status}")
    
    # 测试获取监控历史
    print("\n测试获取监控历史")
    history = monitor.get_monitor_history('600519', days=7)
    print(f"监控历史记录数: {len(history)}")
    
    # 测试获取所有锁定股票
    print("\n测试获取所有锁定股票")
    locked_stocks = monitor.get_all_locked_stocks()
    print(f"锁定股票数: {len(locked_stocks)}")
    for stock in locked_stocks:
        print(f"  {stock['code']}: 剩余 {stock['remaining_hours']:.1f} 小时")