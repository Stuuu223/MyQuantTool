"""
风控管理器 - 通用风控规则模块
"""
from datetime import datetime
from typing import Dict, Tuple


class RiskControlManager:
    """
    通用风控管理器
    
    核心规则：
    1. 价格止损：从入场价回撤 -5%
    2. 时间止损：持仓 3-5 天且收益 < +5%
    3. 仓位限制：单票不超过 25%，总数不超过 3 只
    """
    
    def __init__(
        self,
        price_stop_pct: float = -5.0,
        time_stop_min_days: int = 3,
        time_stop_max_days: int = 5,
        time_stop_min_profit: float = 5.0,
        max_position_per_stock: float = 0.25,
        max_holdings: int = 3,
    ):
        """
        初始化风控参数
        
        Args:
            price_stop_pct: 价格止损阈值（百分比，默认 -5.0%）
            time_stop_min_days: 时间止损最小天数（默认 3 天）
            time_stop_max_days: 时间止损最大天数（默认 5 天）
            time_stop_min_profit: 时间止损最小收益要求（默认 +5.0%）
            max_position_per_stock: 单票最大仓位占比（默认 25%）
            max_holdings: 最大持仓数量（默认 3 只）
        """
        self.price_stop_pct = price_stop_pct
        self.time_stop_min_days = time_stop_min_days
        self.time_stop_max_days = time_stop_max_days
        self.time_stop_min_profit = time_stop_min_profit
        self.max_position_per_stock = max_position_per_stock
        self.max_holdings = max_holdings
    
    def check_exit(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        entry_date: str,
        current_date: str,
    ) -> Tuple[bool, str]:
        """
        检查单个持仓是否应该卖出
        
        Args:
            symbol: 股票代码
            entry_price: 入场价格
            current_price: 当前价格
            entry_date: 入场日期 (YYYY-MM-DD)
            current_date: 当前日期 (YYYY-MM-DD)
        
        Returns:
            (should_exit, reason)
            should_exit: 是否应该卖出
            reason: 卖出原因，可选值:
                - "PRICE_STOP": 价格止损
                - "TIME_STOP": 时间止损
                - "NONE": 不需要卖出
        """
        # 计算浮动收益率
        pnl_pct = (current_price - entry_price) / entry_price * 100
        
        # 计算持仓天数
        entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
        current_dt = datetime.strptime(current_date, "%Y-%m-%d")
        holding_days = (current_dt - entry_dt).days
        
        # 规则1：价格止损
        if pnl_pct <= self.price_stop_pct:
            return True, "PRICE_STOP"
        
        # 规则2：时间止损
        if holding_days >= self.time_stop_min_days:
            # 达到最小观察期，检查收益是否达标
            if pnl_pct < self.time_stop_min_profit:
                return True, "TIME_STOP"
            # 超过最大持仓天数，强制平仓
            elif holding_days >= self.time_stop_max_days:
                return True, "TIME_STOP"
        
        # 不触发任何止损条件
        return False, "NONE"
    
    def check_portfolio_constraints(
        self,
        total_equity: float,
        positions: Dict[str, float],
    ) -> Tuple[bool, str]:
        """
        检查整个组合是否违反仓位约束
        
        Args:
            total_equity: 总资金
            positions: 持仓字典 {symbol: position_value}
        
        Returns:
            (ok, reason)
            ok: 是否允许加新仓
            reason: 检查结果，可选值:
                - "OK": 允许加新仓
                - "TOO_MANY_POS": 持仓数量过多
                - "POSITION_TOO_LARGE": 单票仓位过大
        """
        # 规则1：检查持仓数量
        if len(positions) >= self.max_holdings:
            return False, "TOO_MANY_POS"
        
        # 规则2：检查单票仓位
        max_position_value = total_equity * self.max_position_per_stock
        for symbol, position_value in positions.items():
            if position_value > max_position_value:
                return False, "POSITION_TOO_LARGE"
        
        # 所有检查通过
        return True, "OK"
    
    def can_open_position(
        self,
        total_equity: float,
        positions: Dict[str, float],
        new_position_value: float,
    ) -> Tuple[bool, str]:
        """
        检查是否可以开新仓（包括新开仓是否会违反单票限制）
        
        Args:
            total_equity: 总资金
            positions: 当前持仓字典 {symbol: position_value}
            new_position_value: 新开仓的市值
        
        Returns:
            (ok, reason)
            ok: 是否可以开新仓
            reason: 检查结果
        """
        # 先检查组合约束
        ok, reason = self.check_portfolio_constraints(total_equity, positions)
        if not ok:
            return False, reason
        
        # 检查新开仓是否会超过单票限制
        max_position_value = total_equity * self.max_position_per_stock
        if new_position_value > max_position_value:
            return False, "POSITION_TOO_LARGE"
        
        return True, "OK"