# -*- coding: utf-8 -*-
"""
策略服务 - 统一策略检测门面 (Strategy Service)

整合所有战法策略：
- HALFWAY (半路突破)
- LEADER (龙头候选)
- TRUE_ATTACK (资金攻击)
- TRAP (诱多检测)

禁止直接访问logic.strategies.*，必须通过此服务。
"""

from typing import List, Dict, Optional, Any
import pandas as pd

from logic.strategies.unified_warfare_core import UnifiedWarfareCore
from logic.strategies.true_attack_detector import TrueAttackDetector
from logic.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyService:
    """
    策略服务 - 统一门面
    
    使用示例:
        service = StrategyService()
        events = service.detect_events(tick_data, context)
        
        # 或检测特定策略
        halfway_signal = service.check_halfway(stock_code, tick_data)
    """
    
    def __init__(self):
        self._warfare_core = None
        self._attack_detector = None
    
    def _get_warfare_core(self) -> UnifiedWarfareCore:
        """懒加载UnifiedWarfareCore"""
        if self._warfare_core is None:
            self._warfare_core = UnifiedWarfareCore()
        return self._warfare_core
    
    def _get_attack_detector(self) -> TrueAttackDetector:
        """懒加载TrueAttackDetector"""
        if self._attack_detector is None:
            self._attack_detector = TrueAttackDetector()
        return self._attack_detector
    
    def detect_events(
        self,
        tick_data: Dict[str, Any],
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        检测所有战法事件
        
        Args:
            tick_data: Tick数据
            context: 上下文信息（含流通市值等）
        
        Returns:
            事件列表
        """
        try:
            core = self._get_warfare_core()
            events = core.process_tick(tick_data, context or {})
            return events
        
        except Exception as e:
            logger.error(f"检测事件失败: {e}")
            return []
    
    def check_halfway(
        self,
        stock_code: str,
        price_history: pd.DataFrame,
        volume_history: pd.DataFrame
    ) -> Optional[Dict]:
        """
        检查HALFWAY信号
        
        Args:
            stock_code: 股票代码
            price_history: 价格历史
            volume_history: 成交量历史
        
        Returns:
            HALFWAY信号或None
        """
        logger.info(f"检查{stock_code} HALFWAY信号")
        
        # TODO: 调用HALFWAY检测逻辑
        
        return None
    
    def check_leader(
        self,
        stock_code: str,
        change_pct: float,
        volume_ratio: float
    ) -> Optional[Dict]:
        """
        检查龙头候选信号
        
        Args:
            stock_code: 股票代码
            change_pct: 涨幅
            volume_ratio: 量比
        
        Returns:
            龙头信号或None
        """
        logger.info(f"检查{stock_code} 龙头信号")
        
        # 龙头条件：涨幅>7%，量比>2
        if change_pct > 7.0 and volume_ratio > 2.0:
            return {
                'stock_code': stock_code,
                'signal_type': 'LEADER_CANDIDATE',
                'confidence': min(change_pct / 10.0, 1.0),
                'factors': {
                    'change_pct': change_pct,
                    'volume_ratio': volume_ratio
                }
            }
        
        return None
    
    def check_true_attack(
        self,
        stock_code: str,
        main_inflow: float,
        circ_mv: float,
        price_strength: float
    ) -> Optional[Dict]:
        """
        检查真资金攻击信号
        
        Args:
            stock_code: 股票代码
            main_inflow: 主力净流入
            circ_mv: 流通市值
            price_strength: 价格强度
        
        Returns:
            攻击信号或None
        """
        try:
            detector = self._get_attack_detector()
            
            # 构建flow_data
            flow_data = {
                'main_inflow': main_inflow,
                'circ_mv': circ_mv,
                'price_strength': price_strength
            }
            
            is_attack = detector.is_true_attack(stock_code, flow_data)
            
            if is_attack:
                return {
                    'stock_code': stock_code,
                    'signal_type': 'TRUE_ATTACK',
                    'confidence': detector.calculate_score(main_inflow, price_strength),
                    'factors': flow_data
                }
            
            return None
        
        except Exception as e:
            logger.error(f"检查资金攻击失败: {e}")
            return None
