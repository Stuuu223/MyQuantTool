# -*- coding: utf-8 -*-
"""
风险服务 - 统一风险控制门面 (Risk Service)

整合所有风险检测：
- 诱多检测 (TrapDetector)
- 回撤控制
- 仓位管理

禁止直接访问logic.risk.*，必须通过此服务。
"""

from typing import Dict, Optional, List

from logic.utils.logger import get_logger

logger = get_logger(__name__)


class RiskService:
    """
    风险服务 - 统一门面
    
    使用示例:
        service = RiskService()
        
        # 检查诱多
        is_trap = service.check_trap(stock_code, price_data, capital_data)
        
        # 计算止损价
        stop_price = service.calculate_stop_loss(entry_price, atr=2.0)
    """
    
    def __init__(self):
        pass
    
    def check_trap(
        self,
        stock_code: str,
        price_data: Dict,
        capital_data: Optional[Dict] = None
    ) -> Dict:
        """
        检查诱多陷阱
        
        Args:
            stock_code: 股票代码
            price_data: 价格数据
            capital_data: 资金数据（可选）
        
        Returns:
            风险检查结果
        """
        logger.info(f"检查{stock_code}诱多风险")
        
        # TODO: 调用TrapDetector
        
        return {
            'stock_code': stock_code,
            'is_trap': False,
            'risk_score': 0.0,
            'factors': {}
        }
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: Optional[float] = None,
        fixed_pct: Optional[float] = None
    ) -> float:
        """
        计算止损价
        
        Args:
            entry_price: 入场价
            atr: ATR值（动态止损）
            fixed_pct: 固定百分比（如0.02表示2%）
        
        Returns:
            止损价
        """
        if fixed_pct:
            return entry_price * (1 - fixed_pct)
        elif atr:
            return entry_price - 2 * atr
        else:
            # 默认2%止损
            return entry_price * 0.98
    
    def calculate_position_size(
        self,
        total_capital: float,
        risk_per_trade: float,
        stop_loss_pct: float
    ) -> int:
        """
        计算仓位大小
        
        Args:
            total_capital: 总资金
            risk_per_trade: 单笔风险金额
            stop_loss_pct: 止损百分比
        
        Returns:
            建议股数
        """
        if stop_loss_pct <= 0:
            return 0
        
        position_value = risk_per_trade / stop_loss_pct
        max_position = total_capital * 0.5  # 最大50%仓位
        
        return int(min(position_value, max_position))
    
    def check_sector_resonance(
        self,
        stock_code: str,
        sector_codes: List[str]
    ) -> Dict:
        """
        检查板块共振
        
        Args:
            stock_code: 股票代码
            sector_codes: 板块内股票列表
        
        Returns:
            共振分析结果
        """
        logger.info(f"检查{stock_code}板块共振")
        
        # TODO: 调用WindFilter或SectorResonance逻辑
        
        return {
            'stock_code': stock_code,
            'resonance_score': 0.0,
            'sector_strength': 'neutral',
            'leaders_in_sector': []
        }
