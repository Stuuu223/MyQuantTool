"""PaperTradingSystem - 纸上交易系统

Version: 1.0.0
Feature: 实时模拟交易, 按毁日清算, 浅介密粹

核心职责:
- 实时上下单
- 订单管理 + 执行程序
- 账户管理 (T+1 立知)
- 绩效上报
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class OrderType(Enum):
    BUY = 'BUY'
    SELL = 'SELL'


class OrderStatus(Enum):
    PENDING = 'PENDING'
    FILLED = 'FILLED'
    CANCELLED = 'CANCELLED'
    PARTIAL = 'PARTIAL'


@dataclass
class Order:
    """Trade order record"""
    order_id: str
    code: str
    order_type: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    timestamp: str
    status: str  # 'PENDING', 'FILLED', 'CANCELLED'
    filled_quantity: int = 0
    filled_price: float = 0.0
    commission: float = 0.0


@dataclass
class Position:
    """Current position record"""
    code: str
    quantity: int
    avg_cost: float
    market_price: float
    market_value: float
    profit_loss: float
    profit_loss_pct: float
    timestamp: str


class PaperTradingSystem:
    """A股纸上交易系统
    
    设计原则:
    - 实时上下单 (limit order / market order)
    - T+1 清算 (A股三下五 09:30-11:30, 13:00-15:00)
    - 余额管理 (車余 = 可用余额)
    - 中订管理 (每天 10:00/14:00 检查一次)
    """

    def __init__(self, initial_capital: float = 100000):
        """Initialize paper trading system
        
        Args:
            initial_capital: Initial account balance
        """
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Dict] = []
        self.daily_history = []
        self.order_counter = 0
        
        logger.info(f"📄 PaperTradingSystem initialized (capital={initial_capital})")

    def submit_order(self, code: str, order_type: str, quantity: int, 
                    price: float, order_kind: str = 'LIMIT') -> str:
        """Submit a trading order
        
        Args:
            code: Stock code
            order_type: 'BUY' or 'SELL'
            quantity: Order quantity (must be 100 multiples)
            price: Order price
            order_kind: 'LIMIT' or 'MARKET'
            
        Returns:
            Order ID
        """
        try:
            # Validate
            if quantity % 100 != 0:
                logger.warning(f"⚠️ Quantity {quantity} not 100 multiple. Adjusted to {quantity // 100 * 100}")
                quantity = quantity // 100 * 100
            
            if order_type == 'BUY':
                required_cash = quantity * price * 1.001  # +0.1% commission
                if self.cash_balance < required_cash:
                    logger.warning(f"⚠️ Insufficient cash. Available: {self.cash_balance:.2f}, Required: {required_cash:.2f}")
                    return ''
            
            elif order_type == 'SELL':
                if code not in self.positions or self.positions[code].quantity < quantity:
                    logger.warning(f"⚠️ Insufficient position for {code}")
                    return ''
            
            # Create order
            self.order_counter += 1
            order_id = f"ORD{datetime.now().strftime('%Y%m%d')}{self.order_counter:06d}"
            
            order = Order(
                order_id=order_id,
                code=code,
                order_type=order_type,
                quantity=quantity,
                price=price,
                timestamp=datetime.now().isoformat(),
                status='PENDING',
                filled_quantity=0,
                filled_price=0.0,
                commission=0.0
            )
            
            self.orders.append(order)
            logger.info(f"✅ Order submitted: {order_id} - {order_type} {quantity} @ {price:.2f}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"❌ submit_order failed: {e}")
            return ''

    def fill_order(self, order_id: str, filled_price: float, filled_quantity: Optional[int] = None) -> bool:
        """Fill a submitted order
        
        Args:
            order_id: Order ID to fill
            filled_price: Execution price
            filled_quantity: Filled quantity (if None, fill entire order)
            
        Returns:
            Success flag
        """
        try:
            # Find order
            order = None
            for o in self.orders:
                if o.order_id == order_id:
                    order = o
                    break
            
            if not order:
                logger.warning(f"⚠️ Order {order_id} not found")
                return False
            
            filled_qty = filled_quantity if filled_quantity else order.quantity
            commission = filled_qty * filled_price * 0.001  # 0.1% commission
            
            if order.order_type == 'BUY':
                # Update cash balance
                cost = filled_qty * filled_price + commission
                if self.cash_balance < cost:
                    logger.warning(f"⚠️ Insufficient cash for fill")
                    return False
                
                self.cash_balance -= cost
                
                # Update position
                if order.code in self.positions:
                    pos = self.positions[order.code]
                    new_qty = pos.quantity + filled_qty
                    pos.avg_cost = (pos.avg_cost * pos.quantity + filled_qty * filled_price) / new_qty
                    pos.quantity = new_qty
                else:
                    self.positions[order.code] = Position(
                        code=order.code,
                        quantity=filled_qty,
                        avg_cost=filled_price,
                        market_price=filled_price,
                        market_value=filled_qty * filled_price,
                        profit_loss=0,
                        profit_loss_pct=0,
                        timestamp=datetime.now().isoformat()
                    )
                
            elif order.order_type == 'SELL':
                # Update cash balance
                revenue = filled_qty * filled_price - commission
                self.cash_balance += revenue
                
                # Update position
                if order.code in self.positions:
                    pos = self.positions[order.code]
                    profit_loss = (filled_price - pos.avg_cost) * filled_qty
                    
                    pos.quantity -= filled_qty
                    if pos.quantity == 0:
                        del self.positions[order.code]
                        logger.info(f"💎 Position closed for {order.code}")
                    else:
                        pos.market_price = filled_price
                    
                    # Record trade
                    self.trades.append({
                        'code': order.code,
                        'entry_price': pos.avg_cost,
                        'exit_price': filled_price,
                        'quantity': filled_qty,
                        'profit_loss': profit_loss,
                        'profit_loss_pct': (profit_loss / (filled_qty * pos.avg_cost)) * 100,
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Update order
            order.status = 'FILLED' if filled_qty == order.quantity else 'PARTIAL'
            order.filled_quantity = filled_qty
            order.filled_price = filled_price
            order.commission = commission
            
            logger.info(f"✅ Order filled: {order_id} - {filled_qty} @ {filled_price:.2f} (commission: {commission:.2f})")
            return True
            
        except Exception as e:
            logger.error(f"❌ fill_order failed: {e}")
            return False

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order"""
        try:
            for order in self.orders:
                if order.order_id == order_id:
                    if order.status == 'PENDING':
                        order.status = 'CANCELLED'
                        logger.info(f"✅ Order cancelled: {order_id}")
                        return True
                    else:
                        logger.warning(f"⚠️ Order {order_id} already {order.status}")
                        return False
            
            logger.warning(f"⚠️ Order {order_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"❌ cancel_order failed: {e}")
            return False

    def get_account_status(self) -> Dict[str, Any]:
        """Get current account status"""
        try:
            total_positions_value = sum(pos.market_value for pos in self.positions.values())
            total_equity = self.cash_balance + total_positions_value
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cash_balance': float(self.cash_balance),
                'total_positions_value': float(total_positions_value),
                'total_equity': float(total_equity),
                'equity_ratio': float(self.cash_balance / total_equity) if total_equity > 0 else 0,
                'positions_count': len(self.positions),
                'pending_orders': len([o for o in self.orders if o.status == 'PENDING'])
            }
            
        except Exception as e:
            logger.error(f"❌ get_account_status failed: {e}")
            return {}

    def get_positions(self) -> pd.DataFrame:
        """Get current positions"""
        if not self.positions:
            return pd.DataFrame()
        
        return pd.DataFrame([asdict(p) for p in self.positions.values()])

    def get_orders(self) -> pd.DataFrame:
        """Get all orders"""
        if not self.orders:
            return pd.DataFrame()
        
        return pd.DataFrame([asdict(o) for o in self.orders])

    def get_trades(self) -> pd.DataFrame:
        """Get all completed trades"""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trades)


def get_paper_trading_system(initial_capital: float = 100000) -> PaperTradingSystem:
    """Get or create PaperTradingSystem instance"""
    return PaperTradingSystem(initial_capital=initial_capital)
