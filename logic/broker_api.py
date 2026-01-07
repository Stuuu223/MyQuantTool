"""
券商API集成模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from abc import ABC, abstractmethod

from logic.live_trading_interface import LiveOrder, LivePosition, OrderStatus, OrderDirection, OrderType

logger = logging.getLogger(__name__)


class BrokerAPIBase(ABC):
    """
    券商API基类
    
    所有券商API的抽象基类
    """
    
    def __init__(self, config: Dict):
        """
        初始化券商API
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """连接券商API"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def place_order(self, order: LiveOrder) -> bool:
        """下单"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[LivePosition]:
        """获取持仓"""
        pass
    
    @abstractmethod
    def get_orders(self) -> List[LiveOrder]:
        """获取订单"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """获取行情数据"""
        pass


class FutuAPI(BrokerAPIBase):
    """
    富途牛牛API集成
    
    需要安装: pip install futu-api
    """
    
    def __init__(self, config: Dict):
        """
        初始化富途API
        
        Args:
            config: 配置参数
                - host: 服务器地址 (默认 127.0.0.1)
                - port: 端口 (默认 11111)
                - password: 密码
        """
        super().__init__(config)
        self.quote_ctx = None
        self.trade_ctx = None
    
    def connect(self) -> bool:
        """
        连接富途API
        
        Returns:
            是否成功
        """
        try:
            from futu import OpenQuoteContext, OpenSecTradeContext, TrdEnv, SecurityFirm
            
            host = self.config.get('host', '127.0.0.1')
            port = self.config.get('port', 11111)
            password = self.config.get('password', '')
            
            # 连接行情接口
            self.quote_ctx = OpenQuoteContext(host=host, port=port)
            
            # 连接交易接口
            self.trade_ctx = OpenSecTradeContext(
                host=host,
                port=port,
                security_firm=SecurityFirm.FUTUSECURITIES,
                password=password,
                env=TrdEnv.SIMULATE  # 模拟环境
            )
            
            self.connected = True
            logger.info("富途API连接成功")
            return True
        
        except ImportError:
            logger.error("未安装 futu-api，请运行: pip install futu-api")
            return False
        except Exception as e:
            logger.error(f"富途API连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.quote_ctx:
            self.quote_ctx.close()
        if self.trade_ctx:
            self.trade_ctx.close()
        self.connected = False
        logger.info("富途API已断开")
    
    def place_order(self, order: LiveOrder) -> bool:
        """
        下单
        
        Args:
            order: 订单
        
        Returns:
            是否成功
        """
        if not self.connected:
            logger.error("未连接到富途API")
            return False
        
        try:
            from futu import TrdSide, OrderType as FutuOrderType, TrdMarket
            
            # 转换订单类型
            if order.direction == OrderDirection.BUY:
                trd_side = TrdSide.BUY
            else:
                trd_side = TrdSide.SELL
            
            # 转换订单类型
            if order.order_type == OrderType.MARKET:
                futu_order_type = FutuOrderType.MARKET
            elif order.order_type == OrderType.LIMIT:
                futu_order_type = FutuOrderType.NORMAL
            else:
                futu_order_type = FutuOrderType.NORMAL
            
            # 下单
            ret, data = self.trade_ctx.place_order(
                price=order.price,
                qty=order.quantity,
                code=order.symbol,
                trd_side=trd_side,
                order_type=futu_order_type,
                trd_market=TrdMarket.HK  # 默认港股
            )
            
            if ret == 0:
                logger.info(f"富途下单成功: {order.order_id}")
                return True
            else:
                logger.error(f"富途下单失败: {data}")
                return False
        
        except Exception as e:
            logger.error(f"富途下单异常: {e}")
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if not self.connected:
            return False
        
        try:
            # 提取订单ID中的数字部分
            order_num = int(order_id.split('_')[1])
            
            ret, data = self.trade_ctx.cancel_order(order_id=order_num)
            
            if ret == 0:
                logger.info(f"富途撤单成功: {order_id}")
                return True
            else:
                logger.error(f"富途撤单失败: {data}")
                return False
        
        except Exception as e:
            logger.error(f"富途撤单异常: {e}")
            return False
    
    def get_positions(self) -> List[LivePosition]:
        """获取持仓"""
        if not self.connected:
            return []
        
        try:
            ret, data = self.trade_ctx.position_list_query()
            
            if ret == 0:
                positions = []
                for _, row in data.iterrows():
                    pos = LivePosition(row['code'])
                    pos.quantity = row['qty']
                    pos.avg_price = row['can_open_price']
                    pos.market_value = row['market_val']
                    positions.append(pos)
                return positions
        
        except Exception as e:
            logger.error(f"富途查询持仓异常: {e}")
        
        return []
    
    def get_orders(self) -> List[LiveOrder]:
        """获取订单"""
        if not self.connected:
            return []
        
        try:
            ret, data = self.trade_ctx.order_list_query()
            
            if ret == 0:
                orders = []
                for _, row in data.iterrows():
                    order = LiveOrder(
                        order_id=f"ORDER_{row['order_id']}",
                        symbol=row['code'],
                        direction=OrderDirection.BUY if row['trd_side'] == 'BUY' else OrderDirection.SELL,
                        order_type=OrderType.MARKET if row['order_type'] == 'MARKET' else OrderType.LIMIT,
                        quantity=row['qty'],
                        price=row['price']
                    )
                    order.status = OrderStatus.FILLED if row['order_status'] == 'FILLED_ALL' else OrderStatus.PENDING
                    order.filled_quantity = row['dealt_qty']
                    orders.append(order)
                return orders
        
        except Exception as e:
            logger.error(f"富途查询订单异常: {e}")
        
        return []
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        if not self.connected:
            return {}
        
        try:
            ret, data = self.trade_ctx.accinfo_query()
            
            if ret == 0:
                return {
                    'total_assets': data.iloc[0]['total_assets'],
                    'cash': data.iloc[0]['cash'],
                    'market_val': data.iloc[0]['market_val'],
                    'power': data.iloc[0]['power']
                }
        
        except Exception as e:
            logger.error(f"富途查询账户异常: {e}")
        
        return {}
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """获取行情数据"""
        if not self.connected:
            return None
        
        try:
            from futu import SubType, KLType
            
            ret, data = self.quote_ctx.get_market_snapshot([symbol])
            
            if ret == 0:
                return {
                    'symbol': symbol,
                    'price': data.iloc[0]['last_price'],
                    'volume': data.iloc[0]['volume'],
                    'high': data.iloc[0]['high'],
                    'low': data.iloc[0]['low'],
                    'open': data.iloc[0]['open'],
                    'timestamp': data.iloc[0]['update_time']
                }
        
        except Exception as e:
            logger.error(f"富途查询行情异常: {e}")
        
        return None


class EastMoneyAPI(BrokerAPIBase):
    """
    东方财富API集成
    
    基于东方财富的模拟交易接口
    """
    
    def __init__(self, config: Dict):
        """
        初始化东方财富API
        
        Args:
            config: 配置参数
                - account: 账号
                - password: 密码
        """
        super().__init__(config)
        self.account = config.get('account', '')
        self.password = config.get('password', '')
    
    def connect(self) -> bool:
        """
        连接东方财富API
        
        Returns:
            是否成功
        """
        # 模拟连接
        logger.warning("东方财富API为模拟实现，需要对接真实接口")
        self.connected = True
        return True
    
    def disconnect(self):
        """断开连接"""
        self.connected = False
        logger.info("东方财富API已断开")
    
    def place_order(self, order: LiveOrder) -> bool:
        """下单"""
        if not self.connected:
            return False
        
        logger.info(f"东方财富下单 (模拟): {order.order_id} {order.direction.value} {order.symbol} {order.quantity}股 @ {order.price}")
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if not self.connected:
            return False
        
        logger.info(f"东方财富撤单 (模拟): {order_id}")
        return True
    
    def get_positions(self) -> List[LivePosition]:
        """获取持仓"""
        if not self.connected:
            return []
        
        # 模拟返回空持仓
        return []
    
    def get_orders(self) -> List[LiveOrder]:
        """获取订单"""
        if not self.connected:
            return []
        
        # 模拟返回空订单
        return []
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        if not self.connected:
            return {}
        
        # 模拟账户信息
        return {
            'total_assets': 1000000.0,
            'cash': 500000.0,
            'market_val': 500000.0,
            'power': 500000.0
        }
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """获取行情数据"""
        if not self.connected:
            return None
        
        # 模拟行情数据
        return {
            'symbol': symbol,
            'price': 100.0,
            'volume': 1000000,
            'high': 105.0,
            'low': 95.0,
            'open': 98.0,
            'timestamp': pd.Timestamp.now()
        }


class BrokerAPIFactory:
    """
    券商API工厂
    
    用于创建不同券商的API实例
    """
    
    @staticmethod
    def create_api(broker_type: str, config: Dict) -> Optional[BrokerAPIBase]:
        """
        创建券商API实例
        
        Args:
            broker_type: 券商类型 (futu, eastmoney)
            config: 配置参数
        
        Returns:
            API实例
        """
        if broker_type.lower() == 'futu':
            return FutuAPI(config)
        elif broker_type.lower() == 'eastmoney':
            return EastMoneyAPI(config)
        else:
            logger.error(f"不支持的券商类型: {broker_type}")
            return None