"""
风控管理器 - 通用风控规则模块
"""
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from logic.utils.logger import get_logger

logger = get_logger(__name__)


# 硬编码禁止场景列表
FORBIDDEN_SCENARIOS = [
    "TAIL_RALLY",                    # 补涨尾声
    "TRAP_PUMP_DUMP",                # 拉高出货
    "FORBIDDEN_10CM_TAIL_RALLY",     # 10cm补涨尾声（禁止）
    "FORBIDDEN_10CM_TRAP",           # 10cm拉高出货（禁止）
]


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

    def can_open_position_by_scenario(
        self,
        stock_code: str,
        scenario_type: Optional[str] = None,
        is_tail_rally: Optional[bool] = None,
        is_potential_trap: Optional[bool] = None,
        stock_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        🛡️ 防守斧：场景检查 - 严格禁止 TAIL_RALLY/TRAP 场景开仓

        这是执行层的兜底检查，确保即使监控层漏掉，执行层也会拦截。

        Args:
            stock_code: 股票代码
            scenario_type: 场景类型（从全市场扫描结果获取）
            is_tail_rally: 是否补涨尾声
            is_potential_trap: 是否拉高出货陷阱
            stock_name: 股票名称（用于日志）

        Returns:
            (can_open, reason)
            can_open: 是否允许开仓
            reason: 拒绝原因或允许原因
        """
        # 硬编码禁止规则
        if scenario_type in FORBIDDEN_SCENARIOS:
            reason = f"🛡️ [防守斧] 禁止场景: {scenario_type}"
            logger.warning(f"🛡️ [防守斧拦截] {stock_code} ({stock_name or 'N/A'}) - {reason}")
            logger.warning(f"   场景类型: {scenario_type}")
            logger.warning(f"   拦截位置: 执行层风控 (risk_control.py)")
            return False, reason

        # 兼容旧版：通过布尔值检查
        if is_tail_rally:
            reason = "🛡️ [防守斧] 补涨尾声场景，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截] {stock_code} ({stock_name or 'N/A'}) - {reason}")
            logger.warning(f"   is_tail_rally: {is_tail_rally}")
            logger.warning(f"   拦截位置: 执行层风控 (risk_control.py)")
            return False, reason

        if is_potential_trap:
            reason = "🛡️ [防守斧] 拉高出货陷阱，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截] {stock_code} ({stock_name or 'N/A'}) - {reason}")
            logger.warning(f"   is_potential_trap: {is_potential_trap}")
            logger.warning(f"   拦截位置: 执行层风控 (risk_control.py)")
            return False, reason

        # 通过检查
        return True, "OK"

    def check_all_constraints(
        self,
        stock_code: str,
        total_equity: float,
        positions: Dict[str, float],
        new_position_value: float,
        scenario_type: Optional[str] = None,
        is_tail_rally: Optional[bool] = None,
        is_potential_trap: Optional[bool] = None,
        stock_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        综合检查所有约束条件（仓位约束 + 场景约束）

        Args:
            stock_code: 股票代码
            total_equity: 总资金
            positions: 当前持仓字典 {symbol: position_value}
            new_position_value: 新开仓的市值
            scenario_type: 场景类型
            is_tail_rally: 是否补涨尾声
            is_potential_trap: 是否拉高出货陷阱
            stock_name: 股票名称

        Returns:
            (can_open, reason)
            can_open: 是否可以开仓
            reason: 检查结果
        """
        # 第1关：场景检查（最高优先级）
        can_open_by_scenario, scenario_reason = self.can_open_position_by_scenario(
            stock_code=stock_code,
            scenario_type=scenario_type,
            is_tail_rally=is_tail_rally,
            is_potential_trap=is_potential_trap,
            stock_name=stock_name,
        )
        if not can_open_by_scenario:
            return False, scenario_reason

        # 第2关：仓位约束检查
        can_open_by_position, position_reason = self.can_open_position(
            total_equity=total_equity,
            positions=positions,
            new_position_value=new_position_value,
        )
        if not can_open_by_position:
            return False, position_reason

        # 所有检查通过
        return True, "OK"