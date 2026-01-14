"""
盘口微操模块

Tick-level 微结构分析，用于 20cm 股票的扫板决策
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from collections import deque
from datetime import datetime, timedelta
from logic.logger import get_logger
from logic.data_manager import DataManager
from logic.data_cleaner import DataCleaner

logger = get_logger(__name__)


class OrderImbalance:
    """
    订单不平衡分析器
    
    功能：
    1. 计算买卖单不平衡度
    2. 分析大单净量
    3. 监控委托队列变化
    4. 识别扫板信号
    """
    
    # 参数配置
    LARGE_ORDER_THRESHOLD = 1000000  # 大单阈值（100万）
    TIME_WINDOW = 300  # 时间窗口（5分钟，单位：秒）
    ORDER_QUEUE_WINDOW = 60  # 委托队列窗口（1分钟）
    
    def __init__(self):
        """初始化订单不平衡分析器"""
        self.db = DataManager()
        self.order_flow_history = {}  # 股票代码 -> 订单流历史
        self.order_queue_history = {}  # 股票代码 -> 委托队列历史
    
    def analyze_order_imbalance(self, stock_code: str) -> Dict:
        """
        分析订单不平衡
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: {
                'imbalance_ratio': 不平衡比率,
                'large_order_net': 大单净量,
                'buy_pressure': 买压强度,
                'sell_pressure': 卖压强度,
                'signal': 交易信号,
                'suggestion': 操作建议
            }
        """
        try:
            # 获取实时数据
            realtime_data = self._get_realtime_data(stock_code)
            
            if not realtime_data:
                return {
                    'imbalance_ratio': 0,
                    'large_order_net': 0,
                    'buy_pressure': 0,
                    'sell_pressure': 0,
                    'signal': 'NO_DATA',
                    'suggestion': '无法获取数据'
                }
            
            # 1. 计算买卖单不平衡度
            imbalance_ratio = self._calculate_imbalance_ratio(realtime_data)
            
            # 2. 计算大单净量
            large_order_net = self._calculate_large_order_net(stock_code)
            
            # 3. 分析买压和卖压
            buy_pressure, sell_pressure = self._analyze_pressure(realtime_data)
            
            # 4. 生成交易信号
            signal, suggestion = self._generate_signal(
                imbalance_ratio, large_order_net, buy_pressure, sell_pressure
            )
            
            return {
                'imbalance_ratio': imbalance_ratio,
                'large_order_net': large_order_net,
                'buy_pressure': buy_pressure,
                'sell_pressure': sell_pressure,
                'signal': signal,
                'suggestion': suggestion
            }
        
        except Exception as e:
            logger.error(f"分析订单不平衡失败: {e}")
            return {
                'imbalance_ratio': 0,
                'large_order_net': 0,
                'buy_pressure': 0,
                'sell_pressure': 0,
                'signal': 'ERROR',
                'suggestion': '分析失败'
            }
    
    def _get_realtime_data(self, stock_code: str) -> Optional[Dict]:
        """
        获取实时数据
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: 实时数据
        """
        try:
            # 获取实时行情
            realtime_data = self.db.get_fast_price([stock_code])
            
            if not realtime_data:
                return None
            
            stock_data = realtime_data.get(stock_code, {})
            
            # 清洗数据
            cleaned_data = DataCleaner.clean_realtime_data(stock_data)
            
            return cleaned_data
        
        except Exception as e:
            logger.error(f"获取实时数据失败: {e}")
            return None
    
    def _calculate_imbalance_ratio(self, realtime_data: Dict) -> float:
        """
        计算买卖单不平衡度
        
        Args:
            realtime_data: 实时数据
        
        Returns:
            float: 不平衡比率（正数表示买压，负数表示卖压）
        """
        try:
            # 获取买卖盘数据
            buy_orders = realtime_data.get('buy_orders', [])
            sell_orders = realtime_data.get('sell_orders', [])
            
            # 计算买盘总量
            buy_volume = sum(order.get('volume', 0) for order in buy_orders)
            
            # 计算卖盘总量
            sell_volume = sum(order.get('volume', 0) for order in sell_orders)
            
            # 计算不平衡比率
            total_volume = buy_volume + sell_volume
            
            if total_volume == 0:
                return 0.0
            
            imbalance_ratio = (buy_volume - sell_volume) / total_volume
            
            return imbalance_ratio
        
        except Exception as e:
            logger.error(f"计算不平衡比率失败: {e}")
            return 0.0
    
    def _calculate_large_order_net(self, stock_code: str) -> float:
        """
        计算大单净量
        
        Args:
            stock_code: 股票代码
        
        Returns:
            float: 大单净量（正数表示净买入，负数表示净卖出）
        """
        try:
            # 获取最近的订单流数据
            order_flow = self._get_order_flow(stock_code)
            
            if not order_flow:
                return 0.0
            
            # 计算大单净量
            large_buy = sum(
                flow['volume'] * flow['price']
                for flow in order_flow
                if flow['type'] == 'buy' and flow['volume'] * flow['price'] >= self.LARGE_ORDER_THRESHOLD
            )
            
            large_sell = sum(
                flow['volume'] * flow['price']
                for flow in order_flow
                if flow['type'] == 'sell' and flow['volume'] * flow['price'] >= self.LARGE_ORDER_THRESHOLD
            )
            
            large_order_net = large_buy - large_sell
            
            return large_order_net
        
        except Exception as e:
            logger.error(f"计算大单净量失败: {e}")
            return 0.0
    
    def _get_order_flow(self, stock_code: str) -> List[Dict]:
        """
        获取订单流数据
        
        Args:
            stock_code: 股票代码
        
        Returns:
            list: 订单流数据
        """
        # 简化处理，返回模拟数据
        # 实际应该从数据库或L2数据接口获取
        return []
    
    def _analyze_pressure(self, realtime_data: Dict) -> Tuple[float, float]:
        """
        分析买压和卖压
        
        Args:
            realtime_data: 实时数据
        
        Returns:
            tuple: (买压强度, 卖压强度)
        """
        try:
            # 获取买卖盘数据
            buy_orders = realtime_data.get('buy_orders', [])
            sell_orders = realtime_data.get('sell_orders', [])
            
            # 计算买压强度（买盘加权平均价格）
            if buy_orders:
                buy_pressure = sum(
                    order.get('volume', 0) * order.get('price', 0)
                    for order in buy_orders
                ) / sum(order.get('volume', 1) for order in buy_orders)
            else:
                buy_pressure = 0.0
            
            # 计算卖压强度（卖盘加权平均价格）
            if sell_orders:
                sell_pressure = sum(
                    order.get('volume', 0) * order.get('price', 0)
                    for order in sell_orders
                ) / sum(order.get('volume', 1) for order in sell_orders)
            else:
                sell_pressure = 0.0
            
            return buy_pressure, sell_pressure
        
        except Exception as e:
            logger.error(f"分析买卖压失败: {e}")
            return 0.0, 0.0
    
    def _generate_signal(
        self,
        imbalance_ratio: float,
        large_order_net: float,
        buy_pressure: float,
        sell_pressure: float
    ) -> Tuple[str, str]:
        """
        生成交易信号
        
        Args:
            imbalance_ratio: 不平衡比率
            large_order_net: 大单净量
            buy_pressure: 买压强度
            sell_pressure: 卖压强度
        
        Returns:
            tuple: (信号类型, 操作建议)
        """
        # 强买入信号
        if imbalance_ratio > 0.7 and large_order_net > 0:
            return 'STRONG_BUY', '🔥 强买入信号：买压极强，大单净流入，建议扫板'
        
        # 买入信号
        elif imbalance_ratio > 0.5 and large_order_net > 0:
            return 'BUY', '⚡ 买入信号：买压较强，大单净流入，建议关注'
        
        # 强卖出信号
        elif imbalance_ratio < -0.7 and large_order_net < 0:
            return 'STRONG_SELL', '🧊 强卖出信号：卖压极强，大单净流出，建议回避'
        
        # 卖出信号
        elif imbalance_ratio < -0.5 and large_order_net < 0:
            return 'SELL', '⚡ 卖出信号：卖压较强，大单净流出，建议谨慎'
        
        # 中性信号
        else:
            return 'NEUTRAL', '📊 中性信号：买卖平衡，观望为主'
    
    def monitor_order_queue(self, stock_code: str) -> Dict:
        """
        监控委托队列变化
        
        Args:
            stock_code: 股票代码
        
        Returns:
            dict: 委托队列变化信息
        """
        try:
            # 获取实时数据
            realtime_data = self._get_realtime_data(stock_code)
            
            if not realtime_data:
                return {
                    'buy1_volume': 0,
                    'sell1_volume': 0,
                    'buy1_change': 0,
                    'sell1_change': 0,
                    'signal': 'NO_DATA'
                }
            
            # 获取买一和卖一
            buy_orders = realtime_data.get('buy_orders', [])
            sell_orders = realtime_data.get('sell_orders', [])
            
            buy1_volume = buy_orders[0].get('volume', 0) if buy_orders else 0
            sell1_volume = sell_orders[0].get('volume', 0) if sell_orders else 0
            
            # 计算变化（需要历史数据）
            buy1_change = self._calculate_queue_change(stock_code, 'buy1', buy1_volume)
            sell1_change = self._calculate_queue_change(stock_code, 'sell1', sell1_volume)
            
            # 生成信号
            signal = self._generate_queue_signal(buy1_change, sell1_change)
            
            return {
                'buy1_volume': buy1_volume,
                'sell1_volume': sell1_volume,
                'buy1_change': buy1_change,
                'sell1_change': sell1_change,
                'signal': signal
            }
        
        except Exception as e:
            logger.error(f"监控委托队列失败: {e}")
            return {
                'buy1_volume': 0,
                'sell1_volume': 0,
                'buy1_change': 0,
                'sell1_change': 0,
                'signal': 'ERROR'
            }
    
    def _calculate_queue_change(self, stock_code: str, queue_type: str, current_volume: int) -> int:
        """
        计算委托队列变化
        
        Args:
            stock_code: 股票代码
            queue_type: 队列类型（'buy1' 或 'sell1'）
            current_volume: 当前成交量
        
        Returns:
            int: 变化量
        """
        try:
            # 获取历史数据
            if stock_code not in self.order_queue_history:
                self.order_queue_history[stock_code] = {}
            
            queue_history = self.order_queue_history[stock_code].get(queue_type, deque(maxlen=10))
            
            if not queue_history:
                queue_history.append(current_volume)
                self.order_queue_history[stock_code][queue_type] = queue_history
                return 0
            
            previous_volume = queue_history[-1]
            change = current_volume - previous_volume
            
            queue_history.append(current_volume)
            self.order_queue_history[stock_code][queue_type] = queue_history
            
            return change
        
        except Exception as e:
            logger.error(f"计算队列变化失败: {e}")
            return 0
    
    def _generate_queue_signal(self, buy1_change: int, sell1_change: int) -> str:
        """
        生成委托队列信号
        
        Args:
            buy1_change: 买一变化量
            sell1_change: 卖一变化量
        
        Returns:
            str: 信号
        """
        # 卖一突然大增（压单）
        if sell1_change > 1000:
            return 'SELL_PRESSURE: 卖一压单大增，注意风险'
        
        # 卖一突然减少（被吃掉）
        elif sell1_change < -1000:
            return 'BUY_SIGNAL: 卖一被吃掉，可能是买入信号'
        
        # 买一突然大增（托单）
        elif buy1_change > 1000:
            return 'BUY_SUPPORT: 买一托单大增，有支撑'
        
        # 买一突然减少（撤单）
        elif buy1_change < -1000:
            return 'SELL_SIGNAL: 买一撤单，注意风险'
        
        else:
            return 'NEUTRAL: 委托队列无明显变化'
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()