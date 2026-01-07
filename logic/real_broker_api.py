"""
华泰、中信真实API对接
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
import requests
import json
from datetime import datetime

from logic.broker_api import BrokerAPIBase, LiveOrder, LivePosition, OrderStatus, OrderDirection, OrderType

logger = logging.getLogger(__name__)


class HuataiRealAPI(BrokerAPIBase):
    """
    华泰证券真实API对接
    
    基于华泰证券的OpenAPI
    """
    
    def __init__(self, config: Dict):
        """
        初始化华泰真实API
        
        Args:
            config: 配置参数
                - app_id: 应用ID
                - app_secret: 应用密钥
                - account: 账号
                - password: 密码
                - server_url: 服务器地址
        """
        super().__init__(config)
        self.app_id = config.get('app_id', '')
        self.app_secret = config.get('app_secret', '')
        self.account = config.get('account', '')
        self.password = config.get('password', '')
        self.server_url = config.get('server_url', 'https://open.htsec.com')
        
        self.token = None
        self.session = requests.Session()
    
    def connect(self) -> bool:
        """
        连接华泰API
        
        Returns:
            是否成功
        """
        try:
            # 登录获取token
            login_url = f"{self.server_url}/api/v1/login"
            
            payload = {
                'app_id': self.app_id,
                'app_secret': self.app_secret,
                'account': self.account,
                'password': self.password
            }
            
            response = self.session.post(login_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    self.token = data.get('data', {}).get('token')
                    self.connected = True
                    
                    # 设置请求头
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.token}',
                        'Content-Type': 'application/json'
                    })
                    
                    logger.info("华泰API连接成功")
                    return True
                else:
                    logger.error(f"华泰API登录失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"华泰API请求失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"华泰API连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.token:
            try:
                logout_url = f"{self.server_url}/api/v1/logout"
                self.session.post(logout_url, timeout=10)
            except Exception as e:
                logger.error(f"华泰API登出失败: {e}")
        
        self.connected = False
        self.token = None
        logger.info("华泰API已断开")
    
    def place_order(self, order: LiveOrder) -> bool:
        """
        下单
        
        Args:
            order: 订单
        
        Returns:
            是否成功
        """
        if not self.connected:
            logger.error("未连接到华泰API")
            return False
        
        try:
            order_url = f"{self.server_url}/api/v1/order"
            
            # 转换订单方向
            direction_map = {
                OrderDirection.BUY: 'buy',
                OrderDirection.SELL: 'sell'
            }
            
            # 转换订单类型
            order_type_map = {
                OrderType.MARKET: 'market',
                OrderType.LIMIT: 'limit',
                OrderType.STOP: 'stop'
            }
            
            payload = {
                'account': self.account,
                'symbol': order.symbol,
                'direction': direction_map.get(order.direction, 'buy'),
                'order_type': order_type_map.get(order.order_type, 'market'),
                'quantity': order.quantity,
                'price': order.price if order.order_type == OrderType.LIMIT else 0
            }
            
            response = self.session.post(order_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    logger.info(f"华泰下单成功: {order.order_id}")
                    return True
                else:
                    logger.error(f"华泰下单失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"华泰下单请求失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"华泰下单异常: {e}")
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤单
        
        Args:
            order_id: 订单ID
        
        Returns:
            是否成功
        """
        if not self.connected:
            return False
        
        try:
            cancel_url = f"{self.server_url}/api/v1/order/cancel"
            
            payload = {
                'account': self.account,
                'order_id': order_id
            }
            
            response = self.session.post(cancel_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    logger.info(f"华泰撤单成功: {order_id}")
                    return True
                else:
                    logger.error(f"华泰撤单失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"华泰撤单请求失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"华泰撤单异常: {e}")
            return False
    
    def get_positions(self) -> List[LivePosition]:
        """
        获取持仓
        
        Returns:
            持仓列表
        """
        if not self.connected:
            return []
        
        try:
            position_url = f"{self.server_url}/api/v1/position"
            
            params = {'account': self.account}
            
            response = self.session.get(position_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    positions = []
                    
                    for item in data.get('data', []):
                        pos = LivePosition(item.get('symbol', ''))
                        pos.quantity = item.get('quantity', 0)
                        pos.avg_price = item.get('avg_price', 0)
                        pos.market_value = item.get('market_value', 0)
                        pos.pnl = item.get('pnl', 0)
                        pos.pnl_ratio = item.get('pnl_ratio', 0)
                        
                        positions.append(pos)
                    
                    return positions
        
        except Exception as e:
            logger.error(f"华泰查询持仓异常: {e}")
        
        return []
    
    def get_orders(self) -> List[LiveOrder]:
        """
        获取订单
        
        Returns:
            订单列表
        """
        if not self.connected:
            return []
        
        try:
            order_url = f"{self.server_url}/api/v1/orders"
            
            params = {'account': self.account}
            
            response = self.session.get(order_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    orders = []
                    
                    for item in data.get('data', []):
                        # 转换订单方向
                        direction_map = {
                            'buy': OrderDirection.BUY,
                            'sell': OrderDirection.SELL
                        }
                        
                        # 转换订单类型
                        order_type_map = {
                            'market': OrderType.MARKET,
                            'limit': OrderType.LIMIT,
                            'stop': OrderType.STOP
                        }
                        
                        # 转换订单状态
                        status_map = {
                            'pending': OrderStatus.PENDING,
                            'partial_filled': OrderStatus.PARTIAL_FILLED,
                            'filled': OrderStatus.FILLED,
                            'cancelled': OrderStatus.CANCELLED,
                            'rejected': OrderStatus.REJECTED
                        }
                        
                        order = LiveOrder(
                            order_id=item.get('order_id', ''),
                            symbol=item.get('symbol', ''),
                            direction=direction_map.get(item.get('direction', 'buy'), OrderDirection.BUY),
                            order_type=order_type_map.get(item.get('order_type', 'market'), OrderType.MARKET),
                            quantity=item.get('quantity', 0),
                            price=item.get('price', 0),
                            status=status_map.get(item.get('status', 'pending'), OrderStatus.PENDING)
                        )
                        
                        order.filled_quantity = item.get('filled_quantity', 0)
                        order.filled_price = item.get('filled_price', 0)
                        
                        orders.append(order)
                    
                    return orders
        
        except Exception as e:
            logger.error(f"华泰查询订单异常: {e}")
        
        return []
    
    def get_account_info(self) -> Dict:
        """
        获取账户信息
        
        Returns:
            账户信息
        """
        if not self.connected:
            return {}
        
        try:
            account_url = f"{self.server_url}/api/v1/account"
            
            params = {'account': self.account}
            
            response = self.session.get(account_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    account_data = data.get('data', {})
                    
                    return {
                        'total_assets': account_data.get('total_assets', 0),
                        'cash': account_data.get('cash', 0),
                        'market_val': account_data.get('market_val', 0),
                        'power': account_data.get('power', 0)
                    }
        
        except Exception as e:
            logger.error(f"华泰查询账户异常: {e}")
        
        return {}
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        获取行情数据
        
        Args:
            symbol: 股票代码
        
        Returns:
            行情数据
        """
        if not self.connected:
            return None
        
        try:
            quote_url = f"{self.server_url}/api/v1/quote"
            
            params = {'symbol': symbol}
            
            response = self.session.get(quote_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    quote_data = data.get('data', {})
                    
                    return {
                        'symbol': symbol,
                        'price': quote_data.get('price', 0),
                        'volume': quote_data.get('volume', 0),
                        'high': quote_data.get('high', 0),
                        'low': quote_data.get('low', 0),
                        'open': quote_data.get('open', 0),
                        'timestamp': pd.Timestamp.now()
                    }
        
        except Exception as e:
            logger.error(f"华泰查询行情异常: {e}")
        
        return None


class CiticRealAPI(BrokerAPIBase):
    """
    中信证券真实API对接
    
    基于中信证券的OpenAPI
    """
    
    def __init__(self, config: Dict):
        """
        初始化中信真实API
        
        Args:
            config: 配置参数
                - app_id: 应用ID
                - app_secret: 应用密钥
                - account: 账号
                - password: 密码
                - server_url: 服务器地址
        """
        super().__init__(config)
        self.app_id = config.get('app_id', '')
        self.app_secret = config.get('app_secret', '')
        self.account = config.get('account', '')
        self.password = config.get('password', '')
        self.server_url = config.get('server_url', 'https://open.citics.com')
        
        self.token = None
        self.session = requests.Session()
    
    def connect(self) -> bool:
        """
        连接中信API
        
        Returns:
            是否成功
        """
        try:
            # 登录获取token
            login_url = f"{self.server_url}/api/v1/login"
            
            payload = {
                'app_id': self.app_id,
                'app_secret': self.app_secret,
                'account': self.account,
                'password': self.password
            }
            
            response = self.session.post(login_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    self.token = data.get('data', {}).get('token')
                    self.connected = True
                    
                    # 设置请求头
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.token}',
                        'Content-Type': 'application/json'
                    })
                    
                    logger.info("中信API连接成功")
                    return True
                else:
                    logger.error(f"中信API登录失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"中信API请求失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"中信API连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.token:
            try:
                logout_url = f"{self.server_url}/api/v1/logout"
                self.session.post(logout_url, timeout=10)
            except Exception as e:
                logger.error(f"中信API登出失败: {e}")
        
        self.connected = False
        self.token = None
        logger.info("中信API已断开")
    
    def place_order(self, order: LiveOrder) -> bool:
        """下单"""
        if not self.connected:
            return False
        
        try:
            order_url = f"{self.server_url}/api/v1/order"
            
            direction_map = {
                OrderDirection.BUY: 'buy',
                OrderDirection.SELL: 'sell'
            }
            
            order_type_map = {
                OrderType.MARKET: 'market',
                OrderType.LIMIT: 'limit',
                OrderType.STOP: 'stop'
            }
            
            payload = {
                'account': self.account,
                'symbol': order.symbol,
                'direction': direction_map.get(order.direction, 'buy'),
                'order_type': order_type_map.get(order.order_type, 'market'),
                'quantity': order.quantity,
                'price': order.price if order.order_type == OrderType.LIMIT else 0
            }
            
            response = self.session.post(order_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    logger.info(f"中信下单成功: {order.order_id}")
                    return True
                else:
                    logger.error(f"中信下单失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"中信下单请求失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"中信下单异常: {e}")
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if not self.connected:
            return False
        
        try:
            cancel_url = f"{self.server_url}/api/v1/order/cancel"
            
            payload = {
                'account': self.account,
                'order_id': order_id
            }
            
            response = self.session.post(cancel_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    logger.info(f"中信撤单成功: {order_id}")
                    return True
                else:
                    logger.error(f"中信撤单失败: {data.get('message')}")
                    return False
            else:
                logger.error(f"中信撤单请求失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"中信撤单异常: {e}")
            return False
    
    def get_positions(self) -> List[LivePosition]:
        """获取持仓"""
        if not self.connected:
            return []
        
        try:
            position_url = f"{self.server_url}/api/v1/position"
            
            params = {'account': self.account}
            
            response = self.session.get(position_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    positions = []
                    
                    for item in data.get('data', []):
                        pos = LivePosition(item.get('symbol', ''))
                        pos.quantity = item.get('quantity', 0)
                        pos.avg_price = item.get('avg_price', 0)
                        pos.market_value = item.get('market_value', 0)
                        pos.pnl = item.get('pnl', 0)
                        pos.pnl_ratio = item.get('pnl_ratio', 0)
                        
                        positions.append(pos)
                    
                    return positions
        
        except Exception as e:
            logger.error(f"中信查询持仓异常: {e}")
        
        return []
    
    def get_orders(self) -> List[LiveOrder]:
        """获取订单"""
        if not self.connected:
            return []
        
        try:
            order_url = f"{self.server_url}/api/v1/orders"
            
            params = {'account': self.account}
            
            response = self.session.get(order_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    orders = []
                    
                    for item in data.get('data', []):
                        direction_map = {
                            'buy': OrderDirection.BUY,
                            'sell': OrderDirection.SELL
                        }
                        
                        order_type_map = {
                            'market': OrderType.MARKET,
                            'limit': OrderType.LIMIT,
                            'stop': OrderType.STOP
                        }
                        
                        status_map = {
                            'pending': OrderStatus.PENDING,
                            'partial_filled': OrderStatus.PARTIAL_FILLED,
                            'filled': OrderStatus.FILLED,
                            'cancelled': OrderStatus.CANCELLED,
                            'rejected': OrderStatus.REJECTED
                        }
                        
                        order = LiveOrder(
                            order_id=item.get('order_id', ''),
                            symbol=item.get('symbol', ''),
                            direction=direction_map.get(item.get('direction', 'buy'), OrderDirection.BUY),
                            order_type=order_type_map.get(item.get('order_type', 'market'), OrderType.MARKET),
                            quantity=item.get('quantity', 0),
                            price=item.get('price', 0),
                            status=status_map.get(item.get('status', 'pending'), OrderStatus.PENDING)
                        )
                        
                        order.filled_quantity = item.get('filled_quantity', 0)
                        order.filled_price = item.get('filled_price', 0)
                        
                        orders.append(order)
                    
                    return orders
        
        except Exception as e:
            logger.error(f"中信查询订单异常: {e}")
        
        return []
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        if not self.connected:
            return {}
        
        try:
            account_url = f"{self.server_url}/api/v1/account"
            
            params = {'account': self.account}
            
            response = self.session.get(account_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    account_data = data.get('data', {})
                    
                    return {
                        'total_assets': account_data.get('total_assets', 0),
                        'cash': account_data.get('cash', 0),
                        'market_val': account_data.get('market_val', 0),
                        'power': account_data.get('power', 0)
                    }
        
        except Exception as e:
            logger.error(f"中信查询账户异常: {e}")
        
        return {}
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """获取行情数据"""
        if not self.connected:
            return None
        
        try:
            quote_url = f"{self.server_url}/api/v1/quote"
            
            params = {'symbol': symbol}
            
            response = self.session.get(quote_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 0:
                    quote_data = data.get('data', {})
                    
                    return {
                        'symbol': symbol,
                        'price': quote_data.get('price', 0),
                        'volume': quote_data.get('volume', 0),
                        'high': quote_data.get('high', 0),
                        'low': quote_data.get('low', 0),
                        'open': quote_data.get('open', 0),
                        'timestamp': pd.Timestamp.now()
                    }
        
        except Exception as e:
            logger.error(f"中信查询行情异常: {e}")
        
        return None