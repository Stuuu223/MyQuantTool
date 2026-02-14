"""
实盘交易接口模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "待成交"
    PARTIAL_FILLED = "部分成交"
    FILLED = "已成交"
    CANCELLED = "已撤销"
    REJECTED = "已拒绝"


class OrderDirection(Enum):
    """订单方向"""
    BUY = "买入"
    SELL = "卖出"


class OrderType(Enum):
    """订单类型"""
    MARKET = "市价单"
    LIMIT = "限价单"
    STOP = "止损单"


class LiveOrder:
    """实盘订单"""
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        direction: OrderDirection,
        order_type: OrderType,
        quantity: int,
        price: float,
        status: OrderStatus = OrderStatus.PENDING
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.direction = direction
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.status = status
        self.filled_quantity = 0
        self.filled_price = 0.0
        self.create_time = datetime.now()
        self.update_time = datetime.now()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S')
        }


class LivePosition:
    """实盘持仓"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.quantity = 0
        self.avg_price = 0.0
        self.market_value = 0.0
        self.pnl = 0.0
        self.pnl_ratio = 0.0
    
    def update(self, current_price: float):
        """更新持仓"""
        if self.quantity > 0:
            self.market_value = self.quantity * current_price
            self.pnl = (current_price - self.avg_price) * self.quantity
            self.pnl_ratio = (current_price - self.avg_price) / self.avg_price if self.avg_price > 0 else 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'market_value': self.market_value,
            'pnl': self.pnl,
            'pnl_ratio': self.pnl_ratio
        }


class PaperTradingSystem:
    """
    模拟实盘交易系统
    
    用于策略实盘前的模拟测试
    """
    
    def __init__(self, initial_capital: float = 100000):
        """
        初始化模拟交易系统
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: Dict[str, LivePosition] = {}
        self.orders: List[LiveOrder] = []
        self.order_counter = 0
        self.commission_rate = 0.001
        self.slippage_rate = 0.001
        self.t_plus_one = True  # T+1 交易
    
    def place_order(
        self,
        symbol: str,
        direction: OrderDirection,
        order_type: OrderType,
        quantity: int,
        price: Optional[float] = None
    ) -> Optional[LiveOrder]:
        """
        下单
        
        Args:
            symbol: 股票代码
            direction: 买卖方向
            order_type: 订单类型
            quantity: 数量
            price: 价格 (限价单必填)
        
        Returns:
            订单对象
        """
        # 验证
        if order_type == OrderType.LIMIT and price is None:
            logger.error("限价单必须指定价格")
            return None
        
        if direction == OrderDirection.BUY:
            required_capital = quantity * price * (1 + self.commission_rate) if price else 0
            if required_capital > self.capital:
                logger.error(f"资金不足: 需要 {required_capital}, 可用 {self.capital}")
                return None
        
        if direction == OrderDirection.SELL:
            if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                logger.error(f"持仓不足: 需要 {quantity}, 可用 {self.positions.get(symbol, LivePosition(symbol)).quantity}")
                return None
        
        # 创建订单
        self.order_counter += 1
        order = LiveOrder(
            order_id=f"ORDER_{self.order_counter}",
            symbol=symbol,
            direction=direction,
            order_type=order_type,
            quantity=quantity,
            price=price or 0.0
        )
        
        self.orders.append(order)
        logger.info(f"订单已创建: {order.order_id} {direction.value} {symbol} {quantity}股 @ {price}")
        
        return order
    
    def execute_order(
        self,
        order: LiveOrder,
        market_price: float,
        limit_up_price: float = None
    ) -> bool:
        """
        执行订单
        
        Args:
            order: 订单
            market_price: 市场价格
            limit_up_price: 涨停价（V16.2 新增）
        
        Returns:
            是否成功
        """
        if order.status != OrderStatus.PENDING:
            return False
        
        # V16.2 新增：涨停板抢筹逻辑 - 强制使用限价单
        if order.direction == OrderDirection.BUY and limit_up_price is not None:
            # 检查是否接近涨停价（涨幅 > 9.5%）
            if market_price >= limit_up_price * 0.99:
                logger.info(f"🚀 [涨停抢筹] {order.symbol} 接近涨停价，强制使用限价单 @ {limit_up_price}")
                order.order_type = OrderType.LIMIT
                order.price = limit_up_price
        
        # 计算成交价格
        if order.order_type == OrderType.MARKET:
            execution_price = market_price * (1 + self.slippage_rate if order.direction == OrderDirection.BUY else 1 - self.slippage_rate)
        else:
            execution_price = order.price
        
        # 计算手续费
        commission = order.quantity * execution_price * self.commission_rate
        
        # 执行交易
        if order.direction == OrderDirection.BUY:
            total_cost = order.quantity * execution_price + commission
            if total_cost > self.capital:
                order.status = OrderStatus.REJECTED
                logger.error(f"订单 {order.order_id} 资金不足")
                return False
            
            self.capital -= total_cost
            
            # 更新持仓
            if order.symbol not in self.positions:
                self.positions[order.symbol] = LivePosition(order.symbol)
            
            position = self.positions[order.symbol]
            total_value = position.quantity * position.avg_price + order.quantity * execution_price
            position.quantity += order.quantity
            position.avg_price = total_value / position.quantity if position.quantity > 0 else 0
        
        else:  # SELL
            total_proceeds = order.quantity * execution_price - commission
            
            self.capital += total_proceeds
            
            # 更新持仓
            if order.symbol in self.positions:
                position = self.positions[order.symbol]
                position.quantity -= order.quantity
                
                if position.quantity == 0:
                    del self.positions[order.symbol]
        
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = execution_price
        order.update_time = datetime.now()
        
        # V16.2 新增：释放 pending_orders 缓存
        if order.symbol in self.pending_orders:
            self.pending_orders.remove(order.symbol)
            logger.info(f"✅ [机关枪防护] {order.symbol} 订单已成交，从 pending_orders 缓存中移除")
        
        logger.info(f"订单 {order.order_id} 成交 @ {execution_price:.2f}, 手续费 {commission:.2f}")
        
        return True
    
    def update_positions(self, market_data: Dict[str, float]):
        """
        更新持仓市值
        
        Args:
            market_data: 市场价格 {symbol: price}
        """
        for symbol, position in self.positions.items():
            if symbol in market_data:
                position.update(market_data[symbol])
    
    def get_account_summary(self) -> Dict:
        """
        获取账户摘要
        
        Returns:
            账户信息
        """
        total_market_value = sum(pos.market_value for pos in self.positions.values())
        total_equity = self.capital + total_market_value
        total_pnl = sum(pos.pnl for pos in self.positions.values())
        
        return {
            'capital': self.capital,
            'market_value': total_market_value,
            'total_equity': total_equity,
            'total_pnl': total_pnl,
            'pnl_ratio': (total_equity - self.initial_capital) / self.initial_capital if self.initial_capital > 0 else 0,
            'position_count': len(self.positions),
            'order_count': len(self.orders)
        }
    
    def get_positions(self) -> List[Dict]:
        """获取持仓列表"""
        return [pos.to_dict() for pos in self.positions.values()]
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Dict]:
        """
        获取订单列表
        
        Args:
            status: 筛选状态 (None 表示全部)
        
        Returns:
            订单列表
        """
        if status:
            return [order.to_dict() for order in self.orders if order.status == status]
        return [order.to_dict() for order in self.orders]


class LiveTradingInterface:
    """
    实盘交易接口 (抽象类)
    
    实际使用时需要对接具体的券商 API
    """
    
    def __init__(self, config: Dict):
        """
        初始化实盘接口
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.connected = False
        
        # V16.2 新增：pending_orders 缓存（防止机关枪走火）
        self.pending_orders = set()  # 存储待成交订单的股票代码
        self.order_status_cache = {}  # 存储订单状态（用于释放 pending_orders）
        
        logger.info("✅ V16.2: pending_orders 缓存已初始化")
    
    def connect(self) -> bool:
        """
        连接交易接口
        
        Returns:
            是否成功
        """
        raise NotImplementedError("需要实现具体的连接逻辑")
    
    def disconnect(self):
        """断开连接"""
        raise NotImplementedError("需要实现具体的断开逻辑")
    
    def place_order(self, order: LiveOrder) -> bool:
        """
        下单
        
        Args:
            order: 订单
        
        Returns:
            是否成功
        """
        # V16.2 新增：防止机关枪走火 - 检查是否已有待成交订单
        if order.symbol in self.pending_orders:
            logger.warning(f"⚠️ [机关枪防护] {order.symbol} 已有待成交订单，禁止重复下单")
            return False
        
        # 添加到 pending_orders 缓存
        self.pending_orders.add(order.symbol)
        logger.info(f"✅ [机关枪防护] {order.symbol} 已加入 pending_orders 缓存")
        
        raise NotImplementedError("需要实现具体的下单逻辑")
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否成功
        """
        raise NotImplementedError("需要实现具体的撤单逻辑")
    
    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        raise NotImplementedError("需要实现具体的持仓查询逻辑")
    
    def get_orders(self) -> List[Dict]:
        """获取订单"""
        raise NotImplementedError("需要实现具体的订单查询逻辑")
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        raise NotImplementedError("需要实现具体的账户查询逻辑")