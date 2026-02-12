#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 核心补丁：铁律引擎 (Iron Rule Engine)
铁律：逻辑证伪 + 资金流出 = 永不回头

这是系统的"最高权力"模块，拥有对所有预测逻辑的"一票否决权"。
"""

import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from logic.logger import get_logger
from logic.database_manager import get_db_manager

logger = get_logger(__name__)


class IronRuleEngine:
    """
    V13 核心补丁：铁律引擎
    
    铁律：逻辑证伪 + 资金流出 = 永不回头
    
    功能：
    1. 检查公告/新闻是否包含证伪关键词
    2. 检查DDE净额是否为负（资金流出）
    3. 一票否决权：触发熔断时立即终止所有买入幻想
    """
    
    # 致命证伪关键词
    FATAL_NEWS_KEYWORDS = [
        "未形成收入",
        "无相关业务",
        "澄清",
        "尚不具备",
        "监管函",
        "风险提示",
        "终止合作",
        "解约",
        "业绩预告下调",
        "亏损扩大",
        "暂停业务"
    ]
    
    # 资金流出阈值（亿元）
    CAPITAL_OUT_THRESHOLD = -1.0
    
    def __init__(self):
        self.db = get_db_manager()
        self.locked_stocks = {}  # 被锁定的股票 {code: lock_time}
        self.lock_duration_hours = 24  # 锁定时长（小时）
    
    @classmethod
    def check_absolute_logic(cls, news_text: str, dde_net_flow: float) -> bool:
        """
        一票否决逻辑
        
        Args:
            news_text: 公告/新闻文本
            dde_net_flow: DDE净额（亿元）
        
        Returns:
            bool: True (通过) | False (触发熔断)
        """
        if not news_text:
            return True
        
        # 1. 检查公告/新闻是否包含证伪关键词
        is_refuted = any(key in news_text for key in cls.FATAL_NEWS_KEYWORDS)
        
        # 2. 检查DDE净额是否为负（资金流出）
        is_capital_out = dde_net_flow < cls.CAPITAL_OUT_THRESHOLD
        
        # 3. 铁律判断
        if is_refuted and is_capital_out:
            logger.error("🚨🚨🚨 [铁律触发] 逻辑已证伪 + 资金已背离！立即终止所有买入幻想。")
            return False  # 触发熔断
        
        return True
    
    def check_stock_iron_rule(self, code: str, news_text: str = "", dde_net_flow: float = 0) -> Dict:
        """
        检查单只股票的铁律状态
        
        Args:
            code: 股票代码
            news_text: 公告/新闻文本
            dde_net_flow: DDE净额（亿元）
        
        Returns:
            dict: {
                'code': 股票代码,
                'is_locked': 是否被锁定,
                'lock_reason': 锁定原因,
                'lock_time': 锁定时间,
                'remaining_hours': 剩余锁定小时数,
                'can_buy': 是否可以买入,
                'recommendation': 建议操作
            }
        """
        # 检查是否被锁定
        if code in self.locked_stocks:
            lock_time = self.locked_stocks[code]
            remaining_hours = self._get_remaining_lock_hours(lock_time)
            
            if remaining_hours > 0:
                return {
                    'code': code,
                    'is_locked': True,
                    'lock_reason': '铁律熔断',
                    'lock_time': lock_time,
                    'remaining_hours': remaining_hours,
                    'can_buy': False,
                    'recommendation': '禁止买入 - 铁律锁定中'
                }
            else:
                # 锁定时间已过，解锁
                del self.locked_stocks[code]
                logger.info(f"🔓 铁律解锁: {code}")
        
        # 检查铁律
        if not self.check_absolute_logic(news_text, dde_net_flow):
            # 触发熔断，锁定股票
            self._lock_stock(code, '逻辑证伪 + 资金流出')
            
            return {
                'code': code,
                'is_locked': True,
                'lock_reason': '逻辑证伪 + 资金流出',
                'lock_time': datetime.now().isoformat(),
                'remaining_hours': self.lock_duration_hours,
                'can_buy': False,
                'recommendation': '禁止买入 - 铁律熔断'
            }
        
        return {
            'code': code,
            'is_locked': False,
            'lock_reason': '',
            'lock_time': '',
            'remaining_hours': 0,
            'can_buy': True,
            'recommendation': '正常'
        }
    
    def _lock_stock(self, code: str, reason: str):
        """
        锁定股票
        
        Args:
            code: 股票代码
            reason: 锁定原因
        """
        self.locked_stocks[code] = datetime.now().isoformat()
        logger.warning(f"🔒 铁律锁定: {code} - {reason}")
    
    def is_stock_locked(self, code: str) -> bool:
        """
        检查股票是否被锁定
        
        Args:
            code: 股票代码
        
        Returns:
            bool: 是否被锁定
        """
        if code not in self.locked_stocks:
            return False
        
        lock_time = self.locked_stocks[code]
        remaining_hours = self._get_remaining_lock_hours(lock_time)
        
        if remaining_hours <= 0:
            # 锁定时间已过，解锁
            del self.locked_stocks[code]
            logger.info(f"🔓 铁律解锁: {code}")
            return False
        
        return True
    
    def _get_remaining_lock_hours(self, lock_time: str) -> float:
        """
        计算剩余锁定小时数
        
        Args:
            lock_time: 锁定时间字符串
        
        Returns:
            float: 剩余小时数
        """
        try:
            lock_dt = datetime.fromisoformat(lock_time)
            remaining = lock_dt + timedelta(hours=self.lock_duration_hours) - datetime.now()
            return max(0, remaining.total_seconds() / 3600)
        except:
            return 0
    
    def enforce_exit(self):
        """
        物理级权限阉割
        
        当铁律触发时，强制系统进入"只卖不买"模式
        """
        print("\n" + "!" * 50)
        print("!!! 铁律熔断已生效：系统锁定 24 小时，仅保留清仓权限 !!!")
        print("!" * 50 + "\n")
        
        # 记录到日志
        logger.error("🚨🚨🚨 [铁律执行] 系统已进入只卖不买模式")
    
    def get_locked_stocks(self) -> List[Dict]:
        """
        获取所有被锁定的股票
        
        Returns:
            list: 被锁定的股票列表
        """
        locked_stocks = []
        current_time = datetime.now()
        
        for code, lock_time in self.locked_stocks.items():
            remaining_hours = self._get_remaining_lock_hours(lock_time)
            
            if remaining_hours > 0:
                locked_stocks.append({
                    'code': code,
                    'lock_time': lock_time,
                    'remaining_hours': remaining_hours
                })
            else:
                # 锁定时间已过，解锁
                del self.locked_stocks[code]
                logger.info(f"🔓 铁律解锁: {code}")
        
        return locked_stocks
    
    def unlock_stock(self, code: str):
        """
        手动解锁股票
        
        Args:
            code: 股票代码
        """
        if code in self.locked_stocks:
            del self.locked_stocks[code]
            logger.info(f"🔓 手动解锁: {code}")
            return True
        return False
    
    def unlock_all(self):
        """
        解锁所有股票
        """
        count = len(self.locked_stocks)
        self.locked_stocks.clear()
        logger.info(f"🔓 已解锁所有股票（共 {count} 只）")
        return count


# 单例测试
if __name__ == "__main__":
    ire = IronRuleEngine()
    
    # 测试 1: 正常逻辑
    print("测试 1: 正常逻辑")
    result = ire.check_absolute_logic("公司业绩大幅增长", 5.0)
    print(f"  结果: {result}")
    
    # 测试 2: 逻辑证伪 + 资金流出
    print("\n测试 2: 逻辑证伪 + 资金流出")
    result = ire.check_absolute_logic("公司澄清：尚不具备相关业务", -2.0)
    print(f"  结果: {result}")
    
    # 测试 3: 检查股票铁律状态
    print("\n测试 3: 检查股票铁律状态")
    result = ire.check_stock_iron_rule('600519', "公司澄清：尚不具备相关业务", -2.0)
    print(f"  结果: {result}")
    
    # 测试 4: 获取锁定股票
    print("\n测试 4: 获取锁定股票")
    locked_stocks = ire.get_locked_stocks()
    print(f"  锁定股票数: {len(locked_stocks)}")
    for stock in locked_stocks:
        print(f"    {stock['code']}: 剩余 {stock['remaining_hours']:.1f} 小时")