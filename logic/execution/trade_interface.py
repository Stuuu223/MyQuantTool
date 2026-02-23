# -*- coding: utf-8 -*-
"""
交易接口抽象层 - 支持模拟盘和实盘无缝切换

功能：
- 抽象基类 TradeInterface：定义统一的交易接口契约
- 模拟盘 SimulatedTrading：本地模拟交易，无风险测试
- 实盘 QMTTrading：QMT实盘接口（预留，待实现）
- 工厂函数 create_trader：一键切换模拟/实盘模式

Author: MyQuantTool Team
Date: 2026-02-23
Version: V1.0.0 - 工程化交易接口

使用示例:
    >>> # 老板使用模拟盘测试
    >>> trader = create_trader('simulated', initial_cash=20000.0)
    >>> trader.connect()
    >>> 
    >>> # 买入
    >>> order = TradeOrder('300986.SZ', 'BUY', 100, 13.42)
    >>> result = trader.buy(order)
    >>> 
    >>> # 查看持仓和资金
    >>> print(f"持仓: {trader.get_positions()}")
    >>> print(f"资金: {trader.get_cash()}")
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
import logging

# 尝试导入项目logger，失败则使用标准库
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    # 独立运行时的fallback
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


class OrderDirection(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """订单类型"""
    LIMIT = "LIMIT"      # 限价单
    MARKET = "MARKET"    # 市价单


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"      # 待处理
    FILLED = "FILLED"        # 完全成交
    PARTIAL = "PARTIAL"      # 部分成交
    REJECTED = "REJECTED"    # 被拒绝
    CANCELLED = "CANCELLED"  # 已撤销


@dataclass
class TradeOrder:
    """
    交易订单数据类
    
    Attributes:
        stock_code: 股票代码，如 '300986.SZ'
        direction: 交易方向，'BUY' 或 'SELL'
        quantity: 交易数量（必须是100的整数倍）
        price: 委托价格
        order_type: 订单类型，默认限价单
        strategy_id: 策略标识（可选，用于追踪）
        remark: 备注（可选）
    """
    stock_code: str
    direction: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    order_type: str = 'LIMIT'  # LIMIT, MARKET
    strategy_id: str = ''
    remark: str = ''
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """验证订单参数"""
        if self.direction not in ['BUY', 'SELL']:
            raise ValueError(f"交易方向必须是 'BUY' 或 'SELL'， got {self.direction}")
        if self.quantity <= 0:
            raise ValueError(f"交易数量必须大于0， got {self.quantity}")
        if self.price <= 0:
            raise ValueError(f"交易价格必须大于0， got {self.price}")


@dataclass
class TradeResult:
    """
    交易结果数据类
    
    Attributes:
        order_id: 订单唯一标识
        status: 订单状态
        filled_quantity: 成交数量
        filled_price: 成交均价
        timestamp: 成交时间
        message: 状态信息/错误原因
        commission: 手续费
        stamp_duty: 印花税（卖出时）
    """
    order_id: str
    status: str  # FILLED, PARTIAL, REJECTED
    filled_quantity: int
    filled_price: float
    timestamp: datetime
    message: str
    commission: float = 0.0
    stamp_duty: float = 0.0
    
    def __repr__(self) -> str:
        return (f"TradeResult(order_id={self.order_id}, status={self.status}, "
                f"filled={self.filled_quantity}@{self.filled_price:.3f})")


class OrderValidator:
    """
    订单验证器 - 防止错误下单
    
    检查项：
    - 价格合理性（>0）
    - 数量合理性（100的整数倍）
    - 单笔金额限制（默认不超过总资金50%）
    - 持仓检查（卖出时）
    """
    
    # 交易费用率
    COMMISSION_RATE = 0.0003      # 佣金率 0.03%
    MIN_COMMISSION = 5.0          # 最低佣金5元
    STAMP_DUTY_RATE = 0.0005      # 印花税率 0.05%（仅卖出）
    
    # 风险控制参数
    MAX_SINGLE_ORDER_RATIO = 0.5  # 单笔最大占总资金比例
    
    def __init__(self, total_capital: float = 20000.0):
        """
        初始化验证器
        
        Args:
            total_capital: 总资金，用于计算单笔限额
        """
        self.total_capital = total_capital
    
    def validate_buy_order(self, order: TradeOrder) -> Tuple[bool, str]:
        """
        验证买入订单
        
        Args:
            order: 买入订单
            
        Returns:
            (is_valid, error_message)
        """
        # 检查1: 价格合理性
        if order.price <= 0:
            return False, f'买入价格异常: {order.price}'
        
        # 检查2: 数量合理性（A股必须是100的整数倍）
        if order.quantity <= 0:
            return False, f'买入数量必须大于0: {order.quantity}'
        if order.quantity % 100 != 0:
            return False, f'买入数量必须是100的整数倍: {order.quantity}'
        
        # 检查3: 单次买入金额限制
        order_amount = order.price * order.quantity
        max_single_order = self.total_capital * self.MAX_SINGLE_ORDER_RATIO
        if order_amount > max_single_order:
            return False, (f'单笔买入金额过大: {order_amount:.2f}, '
                          f'超过限制{max_single_order:.2f} ({self.MAX_SINGLE_ORDER_RATIO*100:.0f}%)')
        
        # 检查4: 价格涨跌幅限制（±10% for ST, ±20% for 创业板/科创板）
        # TODO: 接入实时价格校验
        
        return True, '验证通过'
    
    def validate_sell_order(self, order: TradeOrder, current_position: int) -> Tuple[bool, str]:
        """
        验证卖出订单
        
        Args:
            order: 卖出订单
            current_position: 当前持仓数量
            
        Returns:
            (is_valid, error_message)
        """
        # 检查1: 价格合理性
        if order.price <= 0:
            return False, f'卖出价格异常: {order.price}'
        
        # 检查2: 数量合理性
        if order.quantity <= 0:
            return False, f'卖出数量必须大于0: {order.quantity}'
        if order.quantity % 100 != 0:
            return False, f'卖出数量必须是100的整数倍: {order.quantity}'
        
        # 检查3: 持仓检查
        if current_position <= 0:
            return False, f'未持有该股票: {order.stock_code}'
        if order.quantity > current_position:
            return False, f'卖出数量超过持仓: 卖出{order.quantity}, 持仓{current_position}'
        
        return True, '验证通过'
    
    def calculate_buy_cost(self, price: float, quantity: int) -> Dict[str, float]:
        """
        计算买入总成本
        
        Args:
            price: 买入价格
            quantity: 买入数量
            
        Returns:
            {
                'amount': 成交金额,
                'commission': 佣金,
                'total_cost': 总成本
            }
        """
        amount = price * quantity
        commission = max(amount * self.COMMISSION_RATE, self.MIN_COMMISSION)
        total_cost = amount + commission
        
        return {
            'amount': amount,
            'commission': commission,
            'total_cost': total_cost
        }
    
    def calculate_sell_proceeds(self, price: float, quantity: int) -> Dict[str, float]:
        """
        计算卖出净收入
        
        Args:
            price: 卖出价格
            quantity: 卖出数量
            
        Returns:
            {
                'amount': 成交金额,
                'commission': 佣金,
                'stamp_duty': 印花税,
                'net_proceeds': 净收入
            }
        """
        amount = price * quantity
        commission = max(amount * self.COMMISSION_RATE, self.MIN_COMMISSION)
        stamp_duty = amount * self.STAMP_DUTY_RATE
        net_proceeds = amount - commission - stamp_duty
        
        return {
            'amount': amount,
            'commission': commission,
            'stamp_duty': stamp_duty,
            'net_proceeds': net_proceeds
        }


class TradeInterface(ABC):
    """
    交易接口抽象基类
    
    定义统一的交易接口契约，支持模拟盘和实盘两种实现无缝切换。
    所有交易操作都必须通过此接口进行，确保策略代码与底层交易实现解耦。
    
    子类必须实现：
    - connect(): 连接交易服务器
    - disconnect(): 断开连接
    - buy(): 买入操作
    - sell(): 卖出操作
    - get_positions(): 获取持仓
    - get_cash(): 获取可用资金
    
    使用示例:
        >>> class MyTrader(TradeInterface):
        ...     def connect(self) -> bool:
        ...         # 实现连接逻辑
        ...         pass
        ...     # 实现其他抽象方法...
    """
    
    def __init__(self, name: str = "BaseTrader"):
        """
        初始化交易接口
        
        Args:
            name: 交易器名称，用于日志标识
        """
        self.name = name
        self.connected = False
        self.order_history: List[Dict] = []
        logger.info(f"[{self.name}] 交易接口初始化完成")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        连接交易服务器
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开交易服务器连接
        
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @abstractmethod
    def buy(self, order: TradeOrder) -> TradeResult:
        """
        买入股票
        
        Args:
            order: 买入订单，包含股票代码、数量、价格等信息
            
        Returns:
            TradeResult: 交易结果，包含成交状态、数量、价格等
            
        Raises:
            ConnectionError: 未连接时调用
        """
        pass
    
    @abstractmethod
    def sell(self, order: TradeOrder) -> TradeResult:
        """
        卖出股票
        
        Args:
            order: 卖出订单，包含股票代码、数量、价格等信息
            
        Returns:
            TradeResult: 交易结果，包含成交状态、数量、价格等
            
        Raises:
            ConnectionError: 未连接时调用
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict[str, int]:
        """
        获取当前持仓
        
        Returns:
            Dict[str, int]: 持仓字典，{股票代码: 持仓数量}
        """
        pass
    
    @abstractmethod
    def get_cash(self) -> float:
        """
        获取可用资金
        
        Returns:
            float: 可用资金余额
        """
        pass
    
    def is_connected(self) -> bool:
        """
        检查连接状态
        
        Returns:
            bool: 是否已连接
        """
        return self.connected


class SimulatedTrading(TradeInterface):
    """
    模拟盘交易实现
    
    功能完整的本地模拟交易系统，老板可以先在这个模式下无风险测试策略。
    模拟真实交易环境，包括：
    - 资金管理和持仓追踪
    - 交易费用计算（佣金、印花税）
    - 订单验证（数量、价格、持仓检查）
    - 交易历史记录
    
    特性：
    - 初始资金可配置（默认2万）
    - 自动计算交易费用
    - 支持持久化账户状态
    
    Attributes:
        cash: 可用资金
        positions: 持仓字典 {stock_code: quantity}
        order_history: 订单历史列表
        validator: 订单验证器
    
    使用示例:
        >>> trader = SimulatedTrading(initial_cash=20000.0)
        >>> trader.connect()
        >>> 
        >>> # 买入
        >>> order = TradeOrder('300986.SZ', 'BUY', 100, 13.42)
        >>> result = trader.buy(order)
        >>> 
        >>> # 查看账户
        >>> print(f"持仓: {trader.get_positions()}")
        >>> print(f"资金: {trader.get_cash():.2f}")
        >>> print(f"总资产: {trader.get_portfolio_value(current_prices):.2f}")
    """
    
    def __init__(self, initial_cash: float = 20000.0, save_path: Optional[str] = None):
        """
        初始化模拟交易器
        
        Args:
            initial_cash: 初始资金，默认2万元
            save_path: 账户状态保存路径（可选），用于持久化
        """
        super().__init__(name="SimulatedTrading")
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, int] = {}  # {stock_code: quantity}
        self.order_history: List[Dict] = []
        self.validator = OrderValidator(total_capital=initial_cash)
        self.save_path = save_path
        self.order_counter = 0
        
        # 尝试加载之前的状态
        if save_path and os.path.exists(save_path):
            self._load_state()
    
    def connect(self) -> bool:
        """
        启动模拟盘
        
        模拟盘无需实际连接，此方法仅做状态检查和日志输出。
        
        Returns:
            bool: 始终返回True
        """
        self.connected = True
        logger.info(f"[模拟盘] 已启动，初始资金: {self.cash:.2f}元")
        logger.info(f"[模拟盘] 当前持仓: {self.positions}")
        return True
    
    def disconnect(self) -> bool:
        """
        关闭模拟盘
        
        如有配置save_path，会保存当前账户状态。
        
        Returns:
            bool: 始终返回True
        """
        if self.save_path:
            self._save_state()
        self.connected = False
        logger.info("[模拟盘] 已关闭")
        return True
    
    def _generate_order_id(self) -> str:
        """生成模拟订单ID"""
        self.order_counter += 1
        return f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.order_counter:04d}"
    
    def buy(self, order: TradeOrder) -> TradeResult:
        """
        模拟买入
        
        执行流程：
        1. 检查连接状态
        2. 订单验证（价格、数量、金额限制）
        3. 资金检查
        4. 计算交易费用
        5. 更新资金和持仓
        6. 记录交易历史
        
        Args:
            order: 买入订单
            
        Returns:
            TradeResult: 买入结果
        """
        if not self.connected:
            raise ConnectionError("[模拟盘] 未连接，请先调用connect()")
        
        order_id = self._generate_order_id()
        
        # 1. 订单验证
        is_valid, msg = self.validator.validate_buy_order(order)
        if not is_valid:
            logger.warning(f"[模拟盘] 买入订单验证失败: {msg}")
            return TradeResult(
                order_id=order_id,
                status=OrderStatus.REJECTED.value,
                filled_quantity=0,
                filled_price=0,
                timestamp=datetime.now(),
                message=msg
            )
        
        # 2. 计算交易成本
        cost_info = self.validator.calculate_buy_cost(order.price, order.quantity)
        required_cash = cost_info['total_cost']
        
        # 3. 资金检查
        if required_cash > self.cash:
            msg = f'资金不足: 需要{required_cash:.2f}(含手续费), 可用{self.cash:.2f}'
            logger.warning(f"[模拟盘] {msg}")
            return TradeResult(
                order_id=order_id,
                status=OrderStatus.REJECTED.value,
                filled_quantity=0,
                filled_price=0,
                timestamp=datetime.now(),
                message=msg
            )
        
        # 4. 执行买入
        self.cash -= required_cash
        self.positions[order.stock_code] = self.positions.get(order.stock_code, 0) + order.quantity
        
        result = TradeResult(
            order_id=order_id,
            status=OrderStatus.FILLED.value,
            filled_quantity=order.quantity,
            filled_price=order.price,
            timestamp=datetime.now(),
            message='模拟买入成功',
            commission=cost_info['commission']
        )
        
        # 5. 记录历史
        self.order_history.append({
            'type': 'BUY',
            'order': order,
            'result': result,
            'cost_info': cost_info
        })
        
        logger.info(f"[模拟盘买入] {order.stock_code} {order.quantity}股 @ {order.price:.3f}元，"
                   f"手续费:{cost_info['commission']:.2f}，剩余资金:{self.cash:.2f}")
        return result
    
    def sell(self, order: TradeOrder) -> TradeResult:
        """
        模拟卖出
        
        执行流程：
        1. 检查连接状态
        2. 订单验证（价格、数量、持仓检查）
        3. 持仓检查
        4. 计算交易费用（含印花税）
        5. 更新资金和持仓
        6. 记录交易历史
        
        Args:
            order: 卖出订单
            
        Returns:
            TradeResult: 卖出结果
        """
        if not self.connected:
            raise ConnectionError("[模拟盘] 未连接，请先调用connect()")
        
        order_id = self._generate_order_id()
        current_position = self.positions.get(order.stock_code, 0)
        
        # 1. 订单验证
        is_valid, msg = self.validator.validate_sell_order(order, current_position)
        if not is_valid:
            logger.warning(f"[模拟盘] 卖出订单验证失败: {msg}")
            return TradeResult(
                order_id=order_id,
                status=OrderStatus.REJECTED.value,
                filled_quantity=0,
                filled_price=0,
                timestamp=datetime.now(),
                message=msg
            )
        
        # 2. 计算卖出收入
        proceeds_info = self.validator.calculate_sell_proceeds(order.price, order.quantity)
        
        # 3. 执行卖出
        self.cash += proceeds_info['net_proceeds']
        self.positions[order.stock_code] -= order.quantity
        
        # 清理空仓
        if self.positions[order.stock_code] == 0:
            del self.positions[order.stock_code]
        
        result = TradeResult(
            order_id=order_id,
            status=OrderStatus.FILLED.value,
            filled_quantity=order.quantity,
            filled_price=order.price,
            timestamp=datetime.now(),
            message='模拟卖出成功',
            commission=proceeds_info['commission'],
            stamp_duty=proceeds_info['stamp_duty']
        )
        
        # 4. 记录历史
        self.order_history.append({
            'type': 'SELL',
            'order': order,
            'result': result,
            'proceeds_info': proceeds_info
        })
        
        logger.info(f"[模拟盘卖出] {order.stock_code} {order.quantity}股 @ {order.price:.3f}元，"
                   f"手续费:{proceeds_info['commission']:.2f}，印花税:{proceeds_info['stamp_duty']:.2f}，"
                   f"剩余资金:{self.cash:.2f}")
        return result
    
    def get_positions(self) -> Dict[str, int]:
        """
        获取当前持仓
        
        Returns:
            Dict[str, int]: 持仓字典的副本
        """
        return self.positions.copy()
    
    def get_cash(self) -> float:
        """
        获取可用资金
        
        Returns:
            float: 可用资金
        """
        return self.cash
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        计算总资产
        
        总资产 = 可用资金 + 持仓市值
        
        Args:
            current_prices: 当前价格字典 {股票代码: 价格}
            
        Returns:
            float: 总资产
        """
        stock_value = sum(
            qty * current_prices.get(code, 0)
            for code, qty in self.positions.items()
        )
        return self.cash + stock_value
    
    def get_order_history(self) -> List[Dict]:
        """
        获取交易历史
        
        Returns:
            List[Dict]: 交易历史列表
        """
        return self.order_history.copy()
    
    def get_account_summary(self, current_prices: Optional[Dict[str, float]] = None) -> Dict:
        """
        获取账户摘要
        
        Args:
            current_prices: 当前价格（可选），提供时可计算总资产
            
        Returns:
            Dict: 账户信息
        """
        summary = {
            'initial_cash': self.initial_cash,
            'cash': self.cash,
            'positions': self.positions.copy(),
            'position_count': len(self.positions),
            'total_orders': len(self.order_history),
            'timestamp': datetime.now().isoformat()
        }
        
        if current_prices:
            total_value = self.get_portfolio_value(current_prices)
            summary['total_value'] = total_value
            summary['profit_loss'] = total_value - self.initial_cash
            summary['profit_loss_pct'] = (total_value - self.initial_cash) / self.initial_cash * 100
        
        return summary
    
    def reset(self):
        """重置账户状态（清空所有持仓和资金）"""
        self.cash = self.initial_cash
        self.positions = {}
        self.order_history = []
        self.order_counter = 0
        logger.info("[模拟盘] 账户已重置")
    
    def _save_state(self):
        """保存账户状态到文件"""
        state = {
            'initial_cash': self.initial_cash,
            'cash': self.cash,
            'positions': self.positions,
            'order_history': [
                {
                    'type': h['type'],
                    'order': {
                        'stock_code': h['order'].stock_code,
                        'direction': h['order'].direction,
                        'quantity': h['order'].quantity,
                        'price': h['order'].price,
                        'order_type': h['order'].order_type,
                        'strategy_id': h['order'].strategy_id,
                        'remark': h['order'].remark,
                        'created_at': h['order'].created_at.isoformat()
                    },
                    'result': {
                        'order_id': h['result'].order_id,
                        'status': h['result'].status,
                        'filled_quantity': h['result'].filled_quantity,
                        'filled_price': h['result'].filled_price,
                        'timestamp': h['result'].timestamp.isoformat(),
                        'message': h['result'].message,
                        'commission': h['result'].commission,
                        'stamp_duty': h['result'].stamp_duty
                    }
                }
                for h in self.order_history
            ],
            'order_counter': self.order_counter,
            'saved_at': datetime.now().isoformat()
        }
        
        try:
            with open(self.save_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            logger.info(f"[模拟盘] 账户状态已保存到: {self.save_path}")
        except Exception as e:
            logger.error(f"[模拟盘] 保存状态失败: {e}")
    
    def _load_state(self):
        """从文件加载账户状态"""
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.initial_cash = state.get('initial_cash', self.initial_cash)
            self.cash = state.get('cash', self.initial_cash)
            self.positions = state.get('positions', {})
            self.order_counter = state.get('order_counter', 0)
            
            logger.info(f"[模拟盘] 账户状态已从 {self.save_path} 加载")
            logger.info(f"[模拟盘] 加载后资金: {self.cash:.2f}, 持仓: {self.positions}")
        except Exception as e:
            logger.error(f"[模拟盘] 加载状态失败: {e}")


class QMTTrading(TradeInterface):
    """
    QMT实盘交易实现（预留接口，待实现）
    
    警告：此实现目前为占位符，所有交易方法会抛出 NotImplementedError。
    老板测试模拟盘无误后，再实现此类接入实盘。
    
    待实现功能：
    - QMT API连接和认证
    - 实时行情订阅
    - 委托下单/撤单
    - 成交回报处理
    - 持仓和资金查询
    - 异常处理和重连
    
    Attributes:
        account_id: 资金账号
        qmt_config: QMT配置
        
    TODO:
        - 实现QMT API调用
        - 添加风控检查
        - 实现异步回调处理
    """
    
    def __init__(self, account_id: str, config: Optional[Dict] = None):
        """
        初始化QMT实盘交易器
        
        Args:
            account_id: 资金账号
            config: QMT配置字典（可选）
        """
        super().__init__(name="QMTTrading")
        self.account_id = account_id
        self.qmt_config = config or {}
        self.api = None  # QMT API实例占位符
    
    def connect(self) -> bool:
        """
        连接QMT实盘
        
        TODO: 实现QMT连接逻辑
        
        Returns:
            bool: 连接是否成功
        
        Raises:
            NotImplementedError: 尚未实现
        """
        logger.info(f"[QMT实盘] 尝试连接账户: {self.account_id}")
        raise NotImplementedError("QMT实盘接口待实现，请先使用模拟盘(mode='simulated')")
    
    def disconnect(self) -> bool:
        """
        断开QMT连接
        
        TODO: 实现断开逻辑
        
        Returns:
            bool: 断开是否成功
        """
        raise NotImplementedError("QMT实盘接口待实现，请先使用模拟盘(mode='simulated')")
    
    def buy(self, order: TradeOrder) -> TradeResult:
        """
        实盘买入
        
        TODO: 调用QMT API实现
        
        Args:
            order: 买入订单
            
        Returns:
            TradeResult: 买入结果
            
        Raises:
            NotImplementedError: 尚未实现
        """
        raise NotImplementedError("实盘买入接口待实现，请先使用模拟盘(mode='simulated')")
    
    def sell(self, order: TradeOrder) -> TradeResult:
        """
        实盘卖出
        
        TODO: 调用QMT API实现
        
        Args:
            order: 卖出订单
            
        Returns:
            TradeResult: 卖出结果
            
        Raises:
            NotImplementedError: 尚未实现
        """
        raise NotImplementedError("实盘卖出接口待实现，请先使用模拟盘(mode='simulated')")
    
    def get_positions(self) -> Dict[str, int]:
        """
        获取实盘持仓
        
        TODO: 调用QMT API查询
        
        Returns:
            Dict[str, int]: 持仓字典
        """
        raise NotImplementedError("实盘持仓查询接口待实现，请先使用模拟盘(mode='simulated')")
    
    def get_cash(self) -> float:
        """
        获取实盘资金
        
        TODO: 调用QMT API查询
        
        Returns:
            float: 可用资金
        """
        raise NotImplementedError("实盘资金查询接口待实现，请先使用模拟盘(mode='simulated')")


# ============================================================================
# 工厂函数
# ============================================================================

def create_trader(mode: str = 'simulated', **kwargs) -> TradeInterface:
    """
    创建交易接口实例（工厂函数）
    
    通过此函数统一创建交易接口，支持在模拟盘和实盘之间无缝切换。
    建议所有策略代码使用此函数创建交易器，避免直接实例化具体类。
    
    Args:
        mode: 交易模式
            - 'simulated': 模拟盘（默认），用于测试策略
            - 'live': 实盘，连接QMT
        **kwargs: 传递给具体交易器构造函数的参数
            - simulated模式: initial_cash(初始资金), save_path(状态保存路径)
            - live模式: account_id(资金账号), config(QMT配置)
    
    Returns:
        TradeInterface: 交易接口实例
    
    Raises:
        ValueError: 不支持的交易模式
    
    使用示例:
        >>> # 创建模拟盘交易器（初始资金2万）
        >>> sim_trader = create_trader('simulated', initial_cash=20000.0)
        >>> 
        >>> # 创建带状态持久化的模拟盘
        >>> sim_trader = create_trader('simulated', 
        ...                            initial_cash=50000.0,
        ...                            save_path='data/sim_account.json')
        >>> 
        >>> # 创建实盘交易器（预留）
        >>> live_trader = create_trader('live', account_id='123456')
    """
    mode = mode.lower()
    
    if mode == 'simulated':
        initial_cash = kwargs.get('initial_cash', 20000.0)
        save_path = kwargs.get('save_path')
        logger.info(f"[工厂] 创建模拟盘交易器，初始资金: {initial_cash:.2f}")
        return SimulatedTrading(initial_cash=initial_cash, save_path=save_path)
    
    elif mode == 'live':
        account_id = kwargs.get('account_id', '')
        config = kwargs.get('config', {})
        logger.info(f"[工厂] 创建QMT实盘交易器，账户: {account_id}")
        logger.warning("[工厂] 警告：实盘接口尚未完全实现，建议先用模拟盘测试")
        return QMTTrading(account_id=account_id, config=config)
    
    else:
        raise ValueError(f"不支持的交易模式: {mode}。支持的模式: 'simulated', 'live'")


# ============================================================================
# 快捷使用函数
# ============================================================================

def quick_sim_trade(stock_code: str, direction: str, quantity: int, price: float,
                   initial_cash: float = 20000.0) -> TradeResult:
    """
    快速模拟交易（用于测试）
    
    一站式完成：创建模拟盘 -> 连接 -> 下单
    
    Args:
        stock_code: 股票代码
        direction: 'BUY' 或 'SELL'
        quantity: 数量
        price: 价格
        initial_cash: 初始资金
        
    Returns:
        TradeResult: 交易结果
        
    使用示例:
        >>> result = quick_sim_trade('300986.SZ', 'BUY', 100, 13.42)
        >>> print(result)
    """
    trader = create_trader('simulated', initial_cash=initial_cash)
    trader.connect()
    
    order = TradeOrder(stock_code, direction, quantity, price)
    
    if direction == 'BUY':
        return trader.buy(order)
    else:
        return trader.sell(order)


# ============================================================================
# 模块测试
# ============================================================================

if __name__ == '__main__':
    # 添加项目根目录到路径
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # 简单测试
    print("=" * 60)
    print("交易接口模块测试")
    print("=" * 60)
    
    # 测试模拟盘
    print("\n1. 测试模拟盘...")
    trader = create_trader('simulated', initial_cash=20000.0)
    trader.connect()
    
    # 买入测试
    print("\n--- 买入测试 ---")
    order1 = TradeOrder('300986.SZ', 'BUY', 100, 13.42)
    result1 = trader.buy(order1)
    print(f"买入结果: {result1}")
    
    # 持仓查询
    print(f"\n持仓: {trader.get_positions()}")
    print(f"资金: {trader.get_cash():.2f}")
    
    # 卖出测试
    print("\n--- 卖出测试 ---")
    order2 = TradeOrder('300986.SZ', 'SELL', 100, 15.00)
    result2 = trader.sell(order2)
    print(f"卖出结果: {result2}")
    
    print(f"\n最终资金: {trader.get_cash():.2f}")
    
    # 账户摘要
    summary = trader.get_account_summary()
    print(f"\n账户摘要: {json.dumps(summary, indent=2, ensure_ascii=False)}")
    
    # 测试无效订单
    print("\n2. 测试无效订单...")
    invalid_order = TradeOrder('300986.SZ', 'BUY', 50, 13.42)  # 数量非100整数倍
    result3 = trader.buy(invalid_order)
    print(f"无效订单结果: {result3}")
    
    trader.disconnect()
    print("\n测试完成!")