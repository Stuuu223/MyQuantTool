# -*- coding: utf-8 -*-
"""
资金服务 - 统一资金流数据门面 (Capital Service)

整合所有资金流数据源：
- Level2逐笔
- Level1盘口
- 东财T-1数据

禁止直接访问logic.data_providers.fund_flow_*, 必须通过此服务。
"""

from typing import List, Dict, Optional
from datetime import datetime

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class CapitalService:
    """
    资金服务 - 统一门面
    
    使用示例:
        service = CapitalService()
        flow = service.get_realtime_flow('300017.SZ')
        history = service.get_history_flow('300017.SZ', days=5)
    """
    
    def __init__(self):
        self._factory = None
    
    def get_realtime_flow(self, stock_code: str) -> Optional[Dict]:
        """
        获取实时资金流向
        
        Args:
            stock_code: 股票代码
        
        Returns:
            资金流向数据，包含主力净流入、散户净流入等
        """
        logger.info(f"获取{stock_code}实时资金流向")
        
        # TODO: 实现实际的资金流向获取
        # 这里应该调用ICapitalFlowProvider
        
        return {
            'stock_code': stock_code,
            'main_inflow': 0.0,
            'retail_inflow': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_history_flow(
        self,
        stock_code: str,
        days: int = 5
    ) -> Optional[List[Dict]]:
        """
        获取历史资金流向
        
        Args:
            stock_code: 股票代码
            days: 天数
        
        Returns:
            历史资金流向列表
        """
        logger.info(f"获取{stock_code}近{days}日资金流向")
        
        # TODO: 实现实际的历史数据获取
        
        return []
    
    def calculate_attack_score(
        self,
        stock_code: str,
        circ_mv: float
    ) -> float:
        """
        计算资金攻击评分
        
        Args:
            stock_code: 股票代码
            circ_mv: 流通市值
        
        Returns:
            攻击评分 (0-1)
        """
        logger.info(f"计算{stock_code}资金攻击评分")
        
        # TODO: 调用TrueAttackDetector逻辑
        
        return 0.0
