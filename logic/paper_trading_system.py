"""
模拟交易系统 - 完整的交易模拟
功能：
- 订单管理（限价单/市价单）
- 持仓管理
- T+1结算
- 账户报表
- 实时盈亏计算
- 风险管理
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from logic.logger import get_logger

logger = get_logger(__name__)


class OrderType(Enum):
    """订单类型"""
    MARKET = "市价单"
    LIMIT = "限价单"
    STOP = "止损单"


class OrderDirection(Enum):
    """订单方向"""
    BUY = "买入"
    SELL = "卖出"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "待成交"
    FILLED = "已成交"
    PARTIAL = "部分成交"
    CANCELLED = "已取消"
    REJECTED = "已拒绝"
    EXPIRED = "已过期"


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    direction: OrderDirection
    order_type: OrderType
    quantity: int
    price: float
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: float = 0.0
    commission: float = 0.0
    create_time: str = ""
    update_time: str = ""
    expire_time: Optional[str] = None
    # 🛡️ 防守斧：场景检查相关字段
    scenario_type: Optional[str] = None
    is_tail_rally: Optional[bool] = None
    is_potential_trap: Optional[bool] = None
    stock_name: Optional[str] = None


@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: int
    avg_cost: float
    market_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    open_time: str = ""


@dataclass
class Trade:
    """成交记录"""
    trade_id: str
    order_id: str
    symbol: str
    direction: OrderDirection
    quantity: int
    price: float
    commission: float
    trade_time: str
    pnl: float = 0.0


@dataclass
class AccountStatus:
    """账户状态"""
    cash_balance: float
    total_equity: float
    positions_count: int
    total_market_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    margin_used: float
    margin_available: float
    risk_level: str


class PaperTradingSystem:
    """模拟交易系统"""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.001,
        t_plus_one: bool = True,
        risk_limit: float = 0.95  # 最大仓位比例
    ):
        """
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            t_plus_one: 是否启用T+1交易
            risk_limit: 风险限制（最大仓位比例）
        """
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.commission_rate = commission_rate
        self.t_plus_one = t_plus_one
        self.risk_limit = risk_limit
        
        # 交易状态
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        self.order_counter = 0
        self.trade_counter = 0
        
        # T+1 待清算持仓
        self.pending_positions: Dict[str, Tuple[int, float, str]] = {}
        
        # 历史记录
        self.equity_history: List[Dict] = []
        self.equity_curve: List[float] = [initial_capital]  # 净值曲线，用于实时监控，初始值为初始资金
    
    def submit_order(
        self,
        symbol: str,
        order_type: OrderType,
        direction: OrderDirection,
        quantity: int,
        price: float = 0.0,
        stop_price: Optional[float] = None,
        expire_days: Optional[int] = None,
        # 🛡️ 防守斧：场景检查参数
        scenario_type: Optional[str] = None,
        is_tail_rally: Optional[bool] = None,
        is_potential_trap: Optional[bool] = None,
        stock_name: Optional[str] = None
    ) -> str:
        """
        提交订单（带防守斧拦截）

        Args:
            symbol: 股票代码
            order_type: 订单类型
            direction: 订单方向
            quantity: 数量（手）
            price: 价格（限价单必须）
            stop_price: 止损价格
            expire_days: 有效天数
            scenario_type: 场景类型（防守斧检查用）
            is_tail_rally: 是否补涨尾声（防守斧检查用）
            is_potential_trap: 是否拉高出货陷阱（防守斧检查用）
            stock_name: 股票名称（防守斧日志用）

        Returns:
            订单ID

        Raises:
            RuntimeError: 如果场景检查失败，抛出异常拒绝下单
        """
        # 验证订单
        if order_type == OrderType.LIMIT and price <= 0:
            raise ValueError("限价单必须指定价格")

        if quantity <= 0:
            raise ValueError("数量必须大于0")

        # 🛡️ 防守斧：场景检查（买入订单）
        if direction == OrderDirection.BUY:
            can_open, reason = self._check_scenario_for_order(
                symbol, scenario_type, is_tail_rally, is_potential_trap, stock_name
            )
            if not can_open:
                logger.error(f"🛡️ [防守斧拒绝下单] {symbol} ({stock_name or 'N/A'})")
                logger.error(f"   {reason}")
                logger.error(f"   拦截位置: 模拟交易系统 (paper_trading_system.py)")
                raise RuntimeError(f"🛡️ 防守斧拦截: {reason}")

        # 风险检查
        if direction == OrderDirection.BUY:
            required_capital = quantity * 100 * price * (1 + self.commission_rate)
            if required_capital > self.cash_balance:
                raise ValueError(f"资金不足，需要 ¥{required_capital:.2f}，可用 ¥{self.cash_balance:.2f}")

        # 创建订单
        self.order_counter += 1
        order_id = f"ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.order_counter}"

        create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        expire_time = None
        if expire_days:
            expire_dt = datetime.now() + pd.Timedelta(days=expire_days)
            expire_time = expire_dt.strftime('%Y-%m-%d %H:%M:%S')

        order = Order(
            order_id=order_id,
            symbol=symbol,
            direction=direction,
            order_type=order_type,
            quantity=quantity * 100,  # 转换为股数
            price=price,
            stop_price=stop_price,
            create_time=create_time,
            update_time=create_time,
            expire_time=expire_time,
            # 🛡️ 防守斧：保存场景信息
            scenario_type=scenario_type,
            is_tail_rally=is_tail_rally,
            is_potential_trap=is_potential_trap,
            stock_name=stock_name
        )

        self.orders[order_id] = order

        return order_id

    def _check_scenario_for_order(
        self,
        symbol: str,
        scenario_type: Optional[str],
        is_tail_rally: Optional[bool],
        is_potential_trap: Optional[bool],
        stock_name: Optional[str]
    ) -> Tuple[bool, str]:
        """
        🛡️ 防守斧：场景检查 - 模拟交易系统拦截

        严格禁止 TAIL_RALLY/TRAP 场景开仓

        Args:
            symbol: 股票代码
            scenario_type: 场景类型
            is_tail_rally: 是否补涨尾声
            is_potential_trap: 是否拉高出货陷阱
            stock_name: 股票名称

        Returns:
            (can_open, reason)
            can_open: 是否允许开仓
            reason: 拒绝原因或允许原因
        """
        # 导入硬编码禁止场景列表
        from logic.risk_control import FORBIDDEN_SCENARIOS

        code = symbol
        name = stock_name or 'N/A'
        scenario_type = scenario_type or ''
        is_tail_rally = is_tail_rally or False
        is_potential_trap = is_potential_trap or False

        # 硬编码禁止规则
        if scenario_type in FORBIDDEN_SCENARIOS:
            reason = f"🛡️ [防守斧] 禁止场景: {scenario_type}"
            logger.warning(f"🛡️ [防守斧拦截-模拟交易] {code} ({name})")
            logger.warning(f"   场景类型: {scenario_type}")
            logger.warning(f"   拦截位置: 模拟交易系统 (paper_trading_system.py)")
            return False, reason

        # 兼容旧版：通过布尔值检查
        if is_tail_rally:
            reason = "🛡️ [防守斧] 补涨尾声场景，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截-模拟交易] {code} ({name})")
            logger.warning(f"   is_tail_rally: {is_tail_rally}")
            logger.warning(f"   拦截位置: 模拟交易系统 (paper_trading_system.py)")
            return False, reason

        if is_potential_trap:
            reason = "🛡️ [防守斧] 拉高出货陷阱，严禁开仓"
            logger.warning(f"🛡️ [防守斧拦截-模拟交易] {code} ({name})")
            logger.warning(f"   is_potential_trap: {is_potential_trap}")
            logger.warning(f"   拦截位置: 模拟交易系统 (paper_trading_system.py)")
            return False, reason

        # 通过检查
        return True, "OK"
    
    def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否成功取消
        """
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False
        
        order.status = OrderStatus.CANCELLED
        order.update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 如果是买单，释放冻结资金
        if order.direction == OrderDirection.BUY:
            frozen_capital = order.quantity * order.price * (1 + self.commission_rate)
            self.cash_balance += frozen_capital
        
        return True
    
    def fill_order(
        self,
        order_id: str,
        filled_price: float,
        filled_quantity: Optional[int] = None
    ) -> bool:
        """
        成交订单
        
        Args:
            order_id: 订单ID
            filled_price: 成交价格
            filled_quantity: 成交数量（如果不指定则全部成交）
        
        Returns:
            是否成功成交
        """
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.status != OrderStatus.PENDING:
            return False
        
        # 确定成交数量
        if filled_quantity is None:
            filled_quantity = order.quantity
        else:
            filled_quantity = min(filled_quantity, order.quantity)
        
        # 计算手续费
        commission = filled_quantity * filled_price * self.commission_rate
        
        # 处理T+1
        if self.t_plus_one and order.direction == OrderDirection.BUY:
            # 买入的股票需要T+1才能卖出
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.pending_positions[order.symbol] = (filled_quantity, filled_price, current_time)
            
            # 扣除资金
            total_cost = filled_quantity * filled_price + commission
            self.cash_balance -= total_cost
            
            order.status = OrderStatus.FILLED
            order.filled_quantity = filled_quantity
            order.filled_price = filled_price
            order.commission = commission
            order.update_time = current_time
        else:
            # 直接成交
            self._execute_order(order, filled_price, filled_quantity, commission)
        
        return True
    
    def _execute_order(
        self,
        order: Order,
        filled_price: float,
        filled_quantity: int,
        commission: float
    ):
        """执行订单"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if order.direction == OrderDirection.BUY:
            # 买入
            self.cash_balance -= filled_quantity * filled_price + commission
            
            # 更新持仓
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_quantity = pos.quantity + filled_quantity
                total_cost = pos.avg_cost * pos.quantity + filled_price * filled_quantity
                pos.quantity = total_quantity
                pos.avg_cost = total_cost / total_quantity
                pos.market_price = filled_price
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=filled_quantity,
                    avg_cost=filled_price,
                    market_price=filled_price,
                    open_time=current_time
                )
        else:
            # 卖出
            self.cash_balance += filled_quantity * filled_price - commission
            
            # 计算盈亏
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                pnl = (filled_price - pos.avg_cost) * filled_quantity
                pos.realized_pnl += pnl
                
                # 更新持仓
                pos.quantity -= filled_quantity
                if pos.quantity <= 0:
                    del self.positions[order.symbol]
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = filled_quantity
        order.filled_price = filled_price
        order.commission = commission
        order.update_time = current_time
        
        # 记录成交
        self.trade_counter += 1
        trade = Trade(
            trade_id=f"TRADE_{self.trade_counter}",
            order_id=order.order_id,
            symbol=order.symbol,
            direction=order.direction,
            quantity=filled_quantity,
            price=filled_price,
            commission=commission,
            trade_time=current_time,
            pnl=getattr(self.positions.get(order.symbol, Position('', 0, 0)), 'realized_pnl', 0)
        )
        self.trades.append(trade)
    
    def process_t_plus_one(self, current_time: str):
        """
        处理T+1持仓清算
        
        Args:
            current_time: 当前时间
        """
        to_remove = []
        
        for symbol, (quantity, cost, buy_time) in self.pending_positions.items():
            # 检查是否可以卖出（T+1）
            if self._is_t_plus_one_ready(buy_time, current_time):
                # 加入持仓
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    total_quantity = pos.quantity + quantity
                    total_cost = pos.avg_cost * pos.quantity + cost * quantity
                    pos.quantity = total_quantity
                    pos.avg_cost = total_cost / total_quantity
                else:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=quantity,
                        avg_cost=cost,
                        open_time=current_time
                    )
                to_remove.append(symbol)
        
        for symbol in to_remove:
            del self.pending_positions[symbol]
    
    def _is_t_plus_one_ready(self, buy_time: str, current_time: str) -> bool:
        """检查是否满足T+1条件"""
        try:
            buy_dt = pd.to_datetime(buy_time)
            current_dt = pd.to_datetime(current_time)
            return (current_dt - buy_dt).days >= 1
        except:
            return True
    
    def update_market_prices(self, prices: Dict[str, float]):
        """
        更新市场价格
        
        Args:
            prices: 股票代码到价格的映射
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.market_price = price
                pos.market_value = pos.quantity * price
                pos.unrealized_pnl = (price - pos.avg_cost) * pos.quantity
        
        # 更新净值曲线
        status = self.get_account_status()
        self.equity_curve.append(status.total_equity)
    
    def get_account_status(self) -> AccountStatus:
        """
        获取账户状态
        
        Returns:
            账户状态
        """
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_equity = self.cash_balance + total_market_value
        
        # 计算风险等级
        position_ratio = total_market_value / total_equity if total_equity > 0 else 0
        if position_ratio > self.risk_limit:
            risk_level = "高风险"
        elif position_ratio > self.risk_limit * 0.8:
            risk_level = "中风险"
        else:
            risk_level = "低风险"
        
        return AccountStatus(
            cash_balance=self.cash_balance,
            total_equity=total_equity,
            positions_count=len(self.positions),
            total_market_value=total_market_value,
            total_unrealized_pnl=total_unrealized_pnl,
            total_realized_pnl=total_realized_pnl,
            margin_used=total_market_value,
            margin_available=total_equity * (1 - self.risk_limit) - total_market_value,
            risk_level=risk_level
        )
    
    def get_positions(self) -> List[Position]:
        """
        获取所有持仓
        
        Returns:
            持仓列表
        """
        return list(self.positions.values())
    
    def get_trades(self) -> List[Trade]:
        """
        获取所有成交记录
        
        Returns:
            成交记录列表
        """
        return self.trades
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """
        获取订单列表
        
        Args:
            status: 订单状态（None表示所有订单）
        
        Returns:
            订单列表
        """
        orders = list(self.orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return orders
    
    def generate_account_statement(self) -> Dict:
        """
        生成账户报表
        
        Returns:
            账户报表
        """
        status = self.get_account_status()
        positions = self.get_positions()
        trades = self.get_trades()
        
        # 计算统计指标
        if trades:
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl < 0]
            
            win_rate = len(winning_trades) / len(trades) if trades else 0
            avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(sum(t.pnl for t in winning_trades) / sum(t.pnl for t in losing_trades)) if losing_trades else 0
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        return {
            'account_status': {
                'cash_balance': status.cash_balance,
                'total_equity': status.total_equity,
                'positions_count': status.positions_count,
                'total_market_value': status.total_market_value,
                'total_unrealized_pnl': status.total_unrealized_pnl,
                'total_realized_pnl': status.total_realized_pnl,
                'total_return': (status.total_equity - self.initial_capital) / self.initial_capital * 100,
                'risk_level': status.risk_level
            },
            'positions': [
                {
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'avg_cost': pos.avg_cost,
                    'market_price': pos.market_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'pnl_pct': (pos.unrealized_pnl / (pos.avg_cost * pos.quantity)) * 100 if pos.quantity > 0 else 0
                }
                for pos in positions
            ],
            'trading_statistics': {
                'total_trades': len(trades),
                'winning_trades': len(winning_trades) if trades else 0,
                'losing_trades': len(losing_trades) if trades else 0,
                'win_rate': win_rate * 100,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor
            },
            'recent_trades': [
                {
                    'trade_id': t.trade_id,
                    'symbol': t.symbol,
                    'direction': t.direction.value,
                    'quantity': t.quantity,
                    'price': t.price,
                    'commission': t.commission,
                    'pnl': t.pnl,
                    'trade_time': t.trade_time
                }
                for t in trades[-10:]  # 最近10笔交易
            ]
        }
    
    def save_to_file(self, filepath: str):
        """
        保存账户状态到文件
        
        Args:
            filepath: 文件路径
        """
        data = {
            'initial_capital': self.initial_capital,
            'cash_balance': self.cash_balance,
            'positions': [
                {
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'avg_cost': pos.avg_cost,
                    'market_price': pos.market_price,
                    'realized_pnl': pos.realized_pnl
                }
                for pos in self.positions.values()
            ],
            'orders': [
                {
                    'order_id': order.order_id,
                    'symbol': order.symbol,
                    'direction': order.direction.value,
                    'order_type': order.order_type.value,
                    'quantity': order.quantity,
                    'price': order.price,
                    'status': order.status.value,
                    'filled_quantity': order.filled_quantity,
                    'filled_price': order.filled_price
                }
                for order in self.orders.values()
            ],
            'trades': [
                {
                    'trade_id': t.trade_id,
                    'order_id': t.order_id,
                    'symbol': t.symbol,
                    'direction': t.direction.value,
                    'quantity': t.quantity,
                    'price': t.price,
                    'commission': t.commission,
                    'pnl': t.pnl,
                    'trade_time': t.trade_time
                }
                for t in self.trades
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str):
        """
        从文件加载账户状态
        
        Args:
            filepath: 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.initial_capital = data['initial_capital']
        self.cash_balance = data['cash_balance']
        
        # 恢复持仓
        self.positions = {}
        for pos_data in data['positions']:
            self.positions[pos_data['symbol']] = Position(
                symbol=pos_data['symbol'],
                quantity=pos_data['quantity'],
                avg_cost=pos_data['avg_cost'],
                market_price=pos_data['market_price'],
                realized_pnl=pos_data['realized_pnl']
            )
        
        # 恢复订单
        self.orders = {}
        for order_data in data['orders']:
            self.orders[order_data['order_id']] = Order(
                order_id=order_data['order_id'],
                symbol=order_data['symbol'],
                direction=OrderDirection(order_data['direction']),
                order_type=OrderType(order_data['order_type']),
                quantity=order_data['quantity'],
                price=order_data['price'],
                status=OrderStatus(order_data['status']),
                filled_quantity=order_data['filled_quantity'],
                filled_price=order_data['filled_price']
            )
        
        # 恢复成交记录
        self.trades = []
        for trade_data in data['trades']:
            self.trades.append(Trade(
                trade_id=trade_data['trade_id'],
                order_id=trade_data['order_id'],
                symbol=trade_data['symbol'],
                direction=OrderDirection(trade_data['direction']),
                quantity=trade_data['quantity'],
                price=trade_data['price'],
                commission=trade_data['commission'],
                pnl=trade_data['pnl'],
                trade_time=trade_data['trade_time']
            ))


def get_paper_trading_system(
    initial_capital: float = 100000.0,
    commission_rate: float = 0.001,
    t_plus_one: bool = True,
    risk_limit: float = 0.95
) -> PaperTradingSystem:
    """
    获取模拟交易系统实例
    
    Args:
        initial_capital: 初始资金
        commission_rate: 手续费率
        t_plus_one: 是否启用T+1交易
        risk_limit: 风险限制
    
    Returns:
        PaperTradingSystem实例
    """
    return PaperTradingSystem(
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        t_plus_one=t_plus_one,
        risk_limit=risk_limit
    )


class SignalPool:
    """
    V16.2 信号池 - 解决资金碰撞和"平庸优先"陷阱
    
    实现策略：Collect -> Rank -> Execute
    1. 收集所有 BUY 信号
    2. 按分数排序（降序）
    3. 执行直到资金耗尽
    """
    
    def __init__(self, trading_system: PaperTradingSystem):
        """
        初始化信号池
        
        Args:
            trading_system: 交易系统实例
        """
        self.trading_system = trading_system
        self.signals = []  # 存储所有信号 {"symbol": str, "score": float, "price": float, "quantity": int, "reason": str}
        logger.info("✅ V16.2: 信号池已初始化")
    
    def add_signal(self, symbol: str, score: float, price: float, quantity: int = 0, reason: str = ""):
        """
        添加信号到池中
        
        Args:
            symbol: 股票代码
            score: 信号分数（0-100）
            price: 参考价格
            quantity: 数量（手），如果为 0 则自动计算
            reason: 信号原因
        """
        self.signals.append({
            "symbol": symbol,
            "score": score,
            "price": price,
            "quantity": quantity,
            "reason": reason
        })
        logger.info(f"✅ [信号池] 添加信号: {symbol} 分数={score:.1f} 价格={price:.2f} 原因={reason}")
    
    def clear_signals(self):
        """清空信号池"""
        self.signals = []
        logger.info("✅ [信号池] 信号池已清空")
    
    def execute_signals(self, max_positions: int = 5, position_size: float = 0.2) -> Dict[str, Any]:
        """
        执行信号池中的信号（Collect -> Rank -> Execute）
        
        Args:
            max_positions: 最大持仓数
            position_size: 单只股票仓位比例（0-1）
        
        Returns:
            执行结果统计
        """
        if not self.signals:
            logger.warning("⚠️ [信号池] 信号池为空，无需执行")
            return {"total_signals": 0, "executed": 0, "rejected": 0}
        
        # Step 1: Rank - 按分数排序（降序）
        sorted_signals = sorted(self.signals, key=lambda x: x["score"], reverse=True)
        logger.info(f"🔄 [信号池] 开始执行，共 {len(sorted_signals)} 个信号，已按分数排序")
        
        # Step 2: Execute - 按顺序执行直到资金耗尽
        executed_count = 0
        rejected_count = 0
        total_capital = self.trading_system.cash_balance
        
        for signal in sorted_signals:
            # 检查是否已达到最大持仓数
            if len(self.trading_system.positions) >= max_positions:
                logger.warning(f"⚠️ [信号池] 已达到最大持仓数 {max_positions}，停止执行")
                # 统计剩余信号为被拒绝
                remaining_signals = len(sorted_signals) - sorted_signals.index(signal)
                rejected_count += remaining_signals
                break
            
            # 检查是否已有持仓
            if signal["symbol"] in self.trading_system.positions:
                logger.info(f"⏭️ [信号池] {signal['symbol']} 已有持仓，跳过")
                rejected_count += 1
                continue
            
            # 计算仓位大小
            if signal["quantity"] == 0:
                # 自动计算仓位：position_size * 可用资金
                position_capital = total_capital * position_size
                signal["quantity"] = int(position_capital / (signal["price"] * 100))  # 转换为手数
                if signal["quantity"] == 0:
                    logger.warning(f"⚠️ [信号池] {signal['symbol']} 资金不足，跳过")
                    rejected_count += 1
                    continue
            
            # 检查资金是否充足
            required_capital = signal["quantity"] * 100 * signal["price"] * (1 + self.trading_system.commission_rate)
            if required_capital > self.trading_system.cash_balance:
                logger.warning(f"⚠️ [信号池] {signal['symbol']} 资金不足（需要 ¥{required_capital:.2f}，可用 ¥{self.trading_system.cash_balance:.2f}），跳过")
                rejected_count += 1
                continue
            
            # 执行买入
            try:
                order_id = self.trading_system.submit_order(
                    symbol=signal["symbol"],
                    order_type=OrderType.LIMIT,
                    direction=OrderDirection.BUY,
                    quantity=signal["quantity"],
                    price=signal["price"]
                )
                
                # 模拟成交
                self.trading_system.fill_order(
                    order_id=order_id,
                    filled_price=signal["price"],
                    filled_quantity=signal["quantity"] * 100
                )
                
                executed_count += 1
                logger.info(f"✅ [信号池] {signal['symbol']} 买入成功，分数={signal['score']:.1f} 数量={signal['quantity']}手 价格={signal['price']:.2f}")
                
            except Exception as e:
                logger.error(f"❌ [信号池] {signal['symbol']} 买入失败: {e}")
                rejected_count += 1
        
        # 清空信号池
        self.clear_signals()
        
        result = {
            "total_signals": len(sorted_signals),
            "executed": executed_count,
            "rejected": rejected_count,
            "remaining_capital": self.trading_system.cash_balance
        }
        
        logger.info(f"📊 [信号池] 执行完成：{result}")
        return result