"""
滑点与冲击成本优化模型

功能：
- 基于市场微观结构的滑点建模
- 订单簿动态模拟
- 冲击成本预测与优化
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

@dataclass
class MarketDepth:
    """市场深度数据"""
    bid_prices: List[float]      # 买价
    bid_volumes: List[int]       # 买量
    ask_prices: List[float]      # 卖价
    ask_volumes: List[int]       # 卖量
    timestamp: datetime

@dataclass
class ExecutionCost:
    """执行成本分析"""
    slippage: float              # 滑点
    impact_cost: float           # 冲击成本
    total_cost: float            # 总成本
    price_impact: float          # 价格影响
    volume_weighted_cost: float  # 成交量加权成本

class SlippageModel:
    """滑点模型"""
    
    def __init__(self):
        self.base_spread_factor = 0.0005  # 基础价差因子
        self.volume_impact_factor = 0.0001  # 成交量影响因子
        self.order_book_memory = []  # 订单簿历史
        self.max_memory = 100  # 最大历史记录数
    
    def calculate_market_slippage(self, order_quantity: int, side: str, market_depth: MarketDepth) -> float:
        """
        基于订单簿的滑点计算
        
        Args:
            order_quantity: 订单数量
            side: 订单方向 ('buy' or 'sell')
            market_depth: 市场深度数据
            
        Returns:
            滑点（百分比）
        """
        remaining_quantity = order_quantity
        total_cost = 0
        avg_price = 0
        
        if side == 'buy':
            # 买单需要吃掉卖盘
            for price, volume in zip(market_depth.ask_prices, market_depth.ask_volumes):
                if remaining_quantity <= 0:
                    break
                    
                fill_volume = min(remaining_quantity, volume)
                total_cost += fill_volume * price
                remaining_quantity -= fill_volume
        
        else:  # sell
            # 卖单需要吃掉买盘
            for price, volume in zip(market_depth.bid_prices, market_depth.bid_volumes):
                if remaining_quantity <= 0:
                    break
                    
                fill_volume = min(remaining_quantity, volume)
                total_cost += fill_volume * price
                remaining_quantity -= fill_volume
        
        if order_quantity > 0:
            avg_fill_price = total_cost / order_quantity
            if side == 'buy':
                reference_price = market_depth.ask_prices[0]  # 使用最优卖价作为参考
            else:
                reference_price = market_depth.bid_prices[0]  # 使用最优买价作为参考
            
            slippage = (avg_fill_price - reference_price) / reference_price
            if side == 'sell':
                slippage = -slippage  # 卖单的滑点方向相反
                
            return slippage
        else:
            return 0.0
    
    def estimate_impact_cost(self, order_size: float, daily_volume: float, volatility: float) -> float:
        """
        估计冲击成本
        
        Args:
            order_size: 订单规模
            daily_volume: 日均成交量
            volatility: 市场波动率
            
        Returns:
            冲击成本（百分比）
        """
        if daily_volume == 0:
            return 1.0  # 如果没有成交量，冲击成本极高
        
        # 订单规模占比
        volume_ratio = order_size / daily_volume
        
        # 使用Almgren-Chriss模型的简化版本
        # 冲击成本 = gamma * sigma * (order_size / daily_volume)^beta
        gamma = 0.1  # 市场影响系数
        beta = 0.5   # 非线性影响指数
        
        impact_cost = gamma * volatility * (volume_ratio ** beta)
        
        # 添加流动性影响
        liquidity_factor = max(0.1, 1.0 - volume_ratio)  # 流动性越差影响越大
        impact_cost = impact_cost / liquidity_factor
        
        return min(impact_cost, 0.1)  # 限制最大冲击成本为10%
    
    def optimize_execution_strategy(self, 
                                  total_quantity: int, 
                                  side: str, 
                                  market_depth: MarketDepth,
                                  execution_time_minutes: int,
                                  daily_volume: float,
                                  volatility: float) -> Tuple[List[Tuple[int, float]], ExecutionCost]:
        """
        优化执行策略
        
        Args:
            total_quantity: 总订单量
            side: 订单方向
            market_depth: 市场深度
            execution_time_minutes: 执行时间（分钟）
            daily_volume: 日均成交量
            volatility: 波动率
            
        Returns:
            (执行计划列表(数量,时间), 执行成本)
        """
        # 计算最优分批大小
        optimal_batch_size = self._calculate_optimal_batch_size(
            total_quantity, daily_volume, volatility
        )
        
        # 生成执行计划
        remaining_quantity = total_quantity
        execution_plan = []
        time_intervals = execution_time_minutes
        
        while remaining_quantity > 0:
            batch_size = min(optimal_batch_size, remaining_quantity)
            execution_plan.append((batch_size, 1))  # 每批次执行1分钟
            remaining_quantity -= batch_size
        
        # 计算预期执行成本
        estimated_cost = self.estimate_execution_cost(
            execution_plan, market_depth, daily_volume, volatility
        )
        
        return execution_plan, estimated_cost
    
    def _calculate_optimal_batch_size(self, total_quantity: int, daily_volume: float, volatility: float) -> int:
        """计算最优批次大小"""
        # 基于总订单规模和日成交量的比例
        volume_ratio = total_quantity / daily_volume if daily_volume > 0 else 0.1
        base_batch = max(100, int(total_quantity * 0.1))  # 最小100股，最大10%
        
        # 考虑波动率调整
        volatility_factor = max(0.5, min(2.0, 1.0 + volatility))
        optimal_size = int(base_batch / volatility_factor)
        
        return max(100, min(optimal_size, total_quantity))
    
    def estimate_execution_cost(self, 
                              execution_plan: List[Tuple[int, float]], 
                              market_depth: MarketDepth,
                              daily_volume: float,
                              volatility: float) -> ExecutionCost:
        """估计执行成本"""
        total_slippage = 0
        total_impact_cost = 0
        total_volume = sum(batch[0] for batch in execution_plan)
        
        for batch_quantity, _ in execution_plan:
            # 计算滑点
            batch_slippage = self.calculate_market_slippage(batch_quantity, 'buy', market_depth)
            total_slippage += abs(batch_slippage) * (batch_quantity / total_volume)
            
            # 计算冲击成本
            order_value = batch_quantity * market_depth.ask_prices[0]  # 使用当前价格估算
            batch_impact = self.estimate_impact_cost(order_value, daily_volume, volatility)
            total_impact_cost += batch_impact * (batch_quantity / total_volume)
        
        total_cost = total_slippage + total_impact_cost
        price_impact = total_impact_cost  # 价格影响主要由冲击成本造成
        
        # 计算成交量加权成本
        volume_weighted_cost = total_cost
        
        return ExecutionCost(
            slippage=total_slippage,
            impact_cost=total_impact_cost,
            total_cost=total_cost,
            price_impact=price_impact,
            volume_weighted_cost=volume_weighted_cost
        )

class AdvancedSlippagePredictor:
    """高级滑点预测器"""
    
    def __init__(self):
        self.historical_slippage = []
        self.max_history = 1000
    
    def predict_slippage(self, 
                        order_size: float, 
                        market_conditions: Dict[str, float],
                        time_of_day: float) -> Tuple[float, float]:  # (expected_slippage, confidence)
        """
        预测滑点
        
        Args:
            order_size: 订单规模
            market_conditions: 市场条件字典
            time_of_day: 一天中的时间 (0.0-1.0)
            
        Returns:
            (预期滑点, 置信度)
        """
        # 基于历史数据的预测
        historical_avg = np.mean([s[0] for s in self.historical_slippage[-50:]]) if self.historical_slippage else 0.001
        
        # 考虑订单规模影响
        size_factor = math.log10(max(1, order_size / 10000)) * 0.001
        
        # 考虑市场波动率
        vol_factor = market_conditions.get('volatility', 0.02) * 0.1
        
        # 考虑时间因素（开盘和收盘时滑点通常更大）
        time_factor = abs(0.5 - time_of_day) * 0.0005  # 中午时段滑点较小
        
        predicted_slippage = historical_avg + size_factor + vol_factor + time_factor
        
        # 计算置信度（基于历史数据量）
        confidence = min(1.0, len(self.historical_slippage) / 50.0)
        
        return predicted_slippage, confidence
    
    def update_historical_data(self, actual_slippage: float, order_data: Dict):
        """更新历史数据"""
        self.historical_slippage.append((actual_slippage, order_data))
        if len(self.historical_slippage) > self.max_history:
            self.historical_slippage.pop(0)

class MarketImpactSimulator:
    """市场冲击模拟器"""
    
    def __init__(self):
        self.order_book_state = None
    
    def simulate_order_execution(self, 
                               order_quantity: int, 
                               side: str, 
                               initial_order_book: MarketDepth,
                               order_flow_intensity: float = 1.0) -> Tuple[MarketDepth, float]:
        """
        模拟订单执行对订单簿的影响
        
        Args:
            order_quantity: 订单数量
            side: 订单方向
            initial_order_book: 初始订单簿状态
            order_flow_intensity: 订单流强度
            
        Returns:
            (更新后的订单簿, 实际滑点)
        """
        # 复制订单簿状态
        new_order_book = MarketDepth(
            bid_prices=initial_order_book.bid_prices.copy(),
            bid_volumes=initial_order_book.bid_volumes.copy(),
            ask_prices=initial_order_book.ask_prices.copy(),
            ask_volumes=initial_order_book.ask_volumes.copy(),
            timestamp=datetime.now()
        )
        
        remaining_quantity = order_quantity
        total_cost = 0
        executed_at_prices = []
        
        if side == 'buy':
            # 执行买单，消耗卖盘
            level_idx = 0
            while remaining_quantity > 0 and level_idx < len(new_order_book.ask_volumes):
                available_volume = new_order_book.ask_volumes[level_idx]
                price = new_order_book.ask_prices[level_idx]
                
                if available_volume >= remaining_quantity:
                    # 当前档位可以完全满足订单
                    new_order_book.ask_volumes[level_idx] -= remaining_quantity
                    total_cost += remaining_quantity * price
                    executed_at_prices.extend([price] * remaining_quantity)
                    remaining_quantity = 0
                else:
                    # 部分满足，进入下一档
                    total_cost += available_volume * price
                    executed_at_prices.extend([price] * available_volume)
                    remaining_quantity -= available_volume
                    level_idx += 1
            
            # 如果还有剩余订单量，可能需要更新订单簿
            if remaining_quantity > 0:
                # 这里简化处理，实际上可能需要添加新的订单到买盘
                pass
            
        else:  # sell
            # 执行卖单，消耗买盘
            level_idx = 0
            while remaining_quantity > 0 and level_idx < len(new_order_book.bid_volumes):
                available_volume = new_order_book.bid_volumes[level_idx]
                price = new_order_book.bid_prices[level_idx]
                
                if available_volume >= remaining_quantity:
                    new_order_book.bid_volumes[level_idx] -= remaining_quantity
                    total_cost += remaining_quantity * price
                    executed_at_prices.extend([price] * remaining_quantity)
                    remaining_quantity = 0
                else:
                    total_cost += available_volume * price
                    executed_at_prices.extend([price] * available_volume)
                    remaining_quantity -= available_volume
                    level_idx += 1
        
        # 计算平均成交价格和滑点
        if order_quantity > 0 and executed_at_prices:
            avg_execution_price = np.mean(executed_at_prices)
            if side == 'buy':
                reference_price = initial_order_book.ask_prices[0]
            else:
                reference_price = initial_order_book.bid_prices[0]
            
            slippage = (avg_execution_price - reference_price) / reference_price
            if side == 'sell':
                slippage = -slippage
                
            return new_order_book, slippage
        else:
            return new_order_book, 0.0

# 使用示例
def demo_slippage_model():
    """演示滑点模型使用"""
    # 创建滑点模型
    slippage_model = SlippageModel()
    
    # 模拟市场深度数据
    market_depth = MarketDepth(
        bid_prices=[29.95, 29.94, 29.93],
        bid_volumes=[1000, 1500, 2000],
        ask_prices=[29.96, 29.97, 29.98],
        ask_volumes=[800, 1200, 1600],
        timestamp=datetime.now()
    )
    
    # 计算滑点
    slippage = slippage_model.calculate_market_slippage(2500, 'buy', market_depth)
    print(f"买单滑点: {slippage:.4f}")
    
    # 估计冲击成本
    impact_cost = slippage_model.estimate_impact_cost(1000000, 50000000, 0.02)
    print(f"冲击成本: {impact_cost:.4f}")
    
    # 优化执行策略
    execution_plan, cost = slippage_model.optimize_execution_strategy(
        total_quantity=5000,
        side='buy',
        market_depth=market_depth,
        execution_time_minutes=30,
        daily_volume=50000000,
        volatility=0.02
    )
    
    print(f"执行计划: {execution_plan}")
    print(f"执行成本: 滑点={cost.slippage:.4f}, 冲击={cost.impact_cost:.4f}, 总成本={cost.total_cost:.4f}")
    
    # 高级滑点预测器
    predictor = AdvancedSlippagePredictor()
    predicted_slippage, confidence = predictor.predict_slippage(
        order_size=1000000,
        market_conditions={'volatility': 0.025, 'spread': 0.01},
        time_of_day=0.3  # 上午
    )
    print(f"预测滑点: {predicted_slippage:.4f}, 置信度: {confidence:.2f}")
    
    # 市场冲击模拟
    simulator = MarketImpactSimulator()
    new_book, actual_slippage = simulator.simulate_order_execution(
        order_quantity=3000,
        side='buy',
        initial_order_book=market_depth
    )
    print(f"模拟执行滑点: {actual_slippage:.4f}")
    print(f"执行后卖盘: {list(zip(new_book.ask_prices[:3], new_book.ask_volumes[:3]))}")

class RealisticSlippage(SlippageModel):
    """现实滑点模型 - 模拟真实市场中的滑点行为"""
    
    def __init__(self, base_slippage_rate: float = 0.001):
        """
        初始化现实滑点模型
        
        Args:
            base_slippage_rate: 基础滑点率
        """
        super().__init__()
        self.base_slippage_rate = base_slippage_rate
        self.slippage_history = []
    
    def calculate_realistic_slippage(self, 
                                    order_size: float,
                                    price: float,
                                    is_buy: bool,
                                    market_condition: str = 'normal') -> float:
        """
        计算现实滑点
        
        Args:
            order_size: 订单规模（金额）
            price: 当前价格
            is_buy: 是否为买单
            market_condition: 市场条件 ('normal', 'volatile', 'illiquid')
            
        Returns:
            滑点金额
        """
        # 基础滑点
        base_slippage = price * self.base_slippage_rate
        
        # 订单规模影响
        size_factor = min(0.01, order_size / 10000000)  # 最大1%的额外滑点
        
        # 市场条件影响
        condition_factor = {
            'normal': 1.0,
            'volatile': 1.5,
            'illiquid': 2.0
        }.get(market_condition, 1.0)
        
        # 随机波动（模拟市场噪声）
        import random
        noise_factor = random.uniform(0.9, 1.1)
        
        total_slippage = base_slippage * (1 + size_factor) * condition_factor * noise_factor
        
        # 记录历史
        self.slippage_history.append(total_slippage)
        if len(self.slippage_history) > 100:
            self.slippage_history.pop(0)
        
        return total_slippage
    
    def get_average_slippage(self) -> float:
        """获取平均滑点"""
        if not self.slippage_history:
            return 0.0
        return sum(self.slippage_history) / len(self.slippage_history)


class DynamicSlippage(SlippageModel):
    """动态滑点模型 - 根据市场状态动态调整滑点"""
    
    def __init__(self):
        """初始化动态滑点模型"""
        super().__init__()
        self.current_volatility = 0.02
        self.current_spread = 0.001
        self.liquidity_score = 1.0
    
    def update_market_state(self, 
                           volatility: float,
                           spread: float,
                           liquidity_score: float):
        """
        更新市场状态
        
        Args:
            volatility: 波动率
            spread: 买卖价差
            liquidity_score: 流动性得分（0-1，1表示最高流动性）
        """
        self.current_volatility = volatility
        self.current_spread = spread
        self.liquidity_score = liquidity_score
    
    def calculate_dynamic_slippage(self,
                                  order_size: float,
                                  price: float,
                                  is_buy: bool) -> float:
        """
        计算动态滑点
        
        Args:
            order_size: 订单规模
            price: 当前价格
            is_buy: 是否为买单
            
        Returns:
            滑点金额
        """
        # 基础滑点基于价差
        base_slippage = price * self.current_spread * 0.5
        
        # 波动率调整
        volatility_factor = 1 + (self.current_volatility - 0.02) * 10
        
        # 流动性调整（流动性越差，滑点越大）
        liquidity_factor = 2 - self.liquidity_score
        
        # 订单规模调整
        size_impact = min(0.02, order_size / 5000000)  # 最大2%的额外滑点
        
        # 综合计算
        total_slippage = base_slippage * volatility_factor * liquidity_factor * (1 + size_impact)
        
        return total_slippage
    
    def estimate_execution_time(self, order_size: float, market_depth: MarketDepth) -> float:
        """
        估计执行时间（分钟）
        
        Args:
            order_size: 订单规模
            market_depth: 市场深度
            
        Returns:
            预计执行时间（分钟）
        """
        # 计算订单簿总深度
        total_bid_volume = sum(market_depth.bid_volumes)
        total_ask_volume = sum(market_depth.ask_volumes)
        total_depth = total_bid_volume + total_ask_volume
        
        if total_depth == 0:
            return 60.0  # 如果没有深度，估计需要60分钟
        
        # 订单占深度比例
        depth_ratio = order_size / total_depth
        
        # 基础执行时间
        base_time = 5.0  # 5分钟
        
        # 根据比例调整
        execution_time = base_time * (1 + depth_ratio * 10)
        
        # 流动性调整
        execution_time /= self.liquidity_score
        
        return min(execution_time, 240.0)  # 最多4小时


class VWAPExecutor:
    """
    🆕 V8.0: VWAP (成交量加权平均价) 算法交易执行器
    
    功能：
    1. 将大单拆分成多个小单
    2. 根据成交量分布智能执行
    3. 降低冲击成本
    """
    
    def __init__(self, db):
        """
        初始化VWAP执行器
        
        Args:
            db: DataManager实例
        """
        self.db = db
        self.execution_history = []
    
    def calculate_vwap_schedule(self, 
                               symbol: str, 
                               total_quantity: int,
                               side: str,
                               execution_window_minutes: int = 30,
                               num_slices: int = 10) -> List[Dict[str, Any]]:
        """
        计算VWAP执行计划
        
        Args:
            symbol: 股票代码
            total_quantity: 总数量
            side: 交易方向 ('buy' or 'sell')
            execution_window_minutes: 执行窗口（分钟）
            num_slices: 拆分份数
        
        Returns:
            list: 执行计划列表
                [{
                    'slice_index': int,
                    'quantity': int,
                    'target_time': datetime,
                    'method': str
                }]
        """
        from datetime import datetime, timedelta
        
        # 获取历史成交量分布（模拟）
        volume_distribution = self._get_historical_volume_distribution(symbol, execution_window_minutes)
        
        # 根据成交量分布分配订单
        schedule = []
        remaining_quantity = total_quantity
        start_time = datetime.now()
        
        for i in range(num_slices):
            if remaining_quantity <= 0:
                break
            
            # 根据历史成交量比例分配
            if i < len(volume_distribution):
                volume_ratio = volume_distribution[i]
            else:
                volume_ratio = 1.0 / num_slices
            
            slice_quantity = int(total_quantity * volume_ratio)
            slice_quantity = min(slice_quantity, remaining_quantity)
            
            target_time = start_time + timedelta(minutes=i * execution_window_minutes / num_slices)
            
            schedule.append({
                'slice_index': i,
                'quantity': slice_quantity,
                'target_time': target_time,
                'method': 'VWAP',
                'side': side,
                'symbol': symbol
            })
            
            remaining_quantity -= slice_quantity
        
        return schedule
    
    def _get_historical_volume_distribution(self, symbol: str, window_minutes: int) -> List[float]:
        """
        获取历史成交量分布（模拟）
        
        Args:
            symbol: 股票代码
            window_minutes: 时间窗口（分钟）
        
        Returns:
            list: 成交量分布比例列表
        """
        # 简化处理：返回均匀分布
        # 实际应该从数据库查询历史分钟K线数据
        num_slices = 10
        return [1.0 / num_slices] * num_slices
    
    def execute_vwap_order(self, 
                          schedule: List[Dict[str, Any]],
                          market_depth: MarketDepth) -> Dict[str, Any]:
        """
        执行VWAP订单
        
        Args:
            schedule: 执行计划
            market_depth: 市场深度
        
        Returns:
            dict: 执行结果
        """
        total_quantity = sum(slice['quantity'] for slice in schedule)
        total_cost = 0
        executed_quantity = 0
        
        for slice_order in schedule:
            quantity = slice_order['quantity']
            side = slice_order['side']
            
            # 计算该笔订单的滑点
            slippage = self.calculate_market_slippage(quantity, side, market_depth)
            
            # 模拟执行
            if side == 'buy':
                avg_price = market_depth.ask_prices[0] * (1 + slippage)
            else:
                avg_price = market_depth.bid_prices[0] * (1 - slippage)
            
            total_cost += quantity * avg_price
            executed_quantity += quantity
        
        avg_execution_price = total_cost / executed_quantity if executed_quantity > 0 else 0
        
        return {
            'total_quantity': total_quantity,
            'executed_quantity': executed_quantity,
            'avg_execution_price': avg_execution_price,
            'total_cost': total_cost,
            'execution_method': 'VWAP'
        }


class TWAPExecutor:
    """
    🆕 V8.0: TWAP (时间加权平均价) 算法交易执行器
    
    功能：
    1. 将大单均匀拆分成多个小单
    2. 按时间间隔均匀执行
    3. 降低冲击成本
    """
    
    def __init__(self):
        """初始化TWAP执行器"""
        self.execution_history = []
    
    def calculate_twap_schedule(self, 
                               total_quantity: int,
                               side: str,
                               execution_window_minutes: int = 30,
                               num_slices: int = 10) -> List[Dict[str, Any]]:
        """
        计算TWAP执行计划
        
        Args:
            total_quantity: 总数量
            side: 交易方向 ('buy' or 'sell')
            execution_window_minutes: 执行窗口（分钟）
            num_slices: 拆分份数
        
        Returns:
            list: 执行计划列表
        """
        from datetime import datetime, timedelta
        
        schedule = []
        start_time = datetime.now()
        slice_quantity = total_quantity // num_slices
        remaining_quantity = total_quantity
        
        for i in range(num_slices):
            if i == num_slices - 1:
                # 最后一单处理剩余数量
                slice_quantity = remaining_quantity
            
            target_time = start_time + timedelta(minutes=i * execution_window_minutes / num_slices)
            
            schedule.append({
                'slice_index': i,
                'quantity': slice_quantity,
                'target_time': target_time,
                'method': 'TWAP',
                'side': side
            })
            
            remaining_quantity -= slice_quantity
        
        return schedule
    
    def execute_twap_order(self, 
                          schedule: List[Dict[str, Any]],
                          current_price: float,
                          slippage_rate: float = 0.002) -> Dict[str, Any]:
        """
        执行TWAP订单
        
        Args:
            schedule: 执行计划
            current_price: 当前价格
            slippage_rate: 滑点率
        
        Returns:
            dict: 执行结果
        """
        total_quantity = sum(slice['quantity'] for slice in schedule)
        total_cost = 0
        executed_quantity = 0
        
        for slice_order in schedule:
            quantity = slice_order['quantity']
            side = slice_order['side']
            
            # 计算该笔订单的价格（包含滑点）
            if side == 'buy':
                execution_price = current_price * (1 + slippage_rate)
            else:
                execution_price = current_price * (1 - slippage_rate)
            
            total_cost += quantity * execution_price
            executed_quantity += quantity
        
        avg_execution_price = total_cost / executed_quantity if executed_quantity > 0 else 0
        
        return {
            'total_quantity': total_quantity,
            'executed_quantity': executed_quantity,
            'avg_execution_price': avg_execution_price,
            'total_cost': total_cost,
            'execution_method': 'TWAP'
        }


class OrderSplitter:
    """
    🆕 V8.0: 大单拆分器
    
    功能：
    1. 智能拆分大单
    2. 根据市场状况选择拆分策略
    3. 避免冲击成本
    """
    
    def __init__(self):
        """初始化大单拆分器"""
        self.split_history = []
    
    def calculate_optimal_split(self, 
                               order_quantity: int,
                               order_value: float,
                               market_condition: str = 'normal') -> Dict[str, Any]:
        """
        计算最优拆分策略
        
        Args:
            order_quantity: 订单数量
            order_value: 订单金额
            market_condition: 市场条件
        
        Returns:
            dict: 拆分策略
                {
                    'num_slices': int,
                    'slice_quantity': int,
                    'execution_method': 'VWAP' | 'TWAP' | 'MARKET',
                    'execution_window_minutes': int,
                    'reason': str
                }
        """
        # 判断是否需要拆分
        if order_value < 100000:  # 10万以下，直接市价单
            return {
                'num_slices': 1,
                'slice_quantity': order_quantity,
                'execution_method': 'MARKET',
                'execution_window_minutes': 0,
                'reason': '订单规模较小，直接市价单执行'
            }
        
        elif order_value < 500000:  # 10万-50万，TWAP拆分
            num_slices = min(10, order_quantity // 100)  # 最多10笔，每笔至少100股
            
            return {
                'num_slices': num_slices,
                'slice_quantity': order_quantity // num_slices,
                'execution_method': 'TWAP',
                'execution_window_minutes': 15,
                'reason': '订单规模中等，使用TWAP均匀拆分'
            }
        
        elif order_value < 2000000:  # 50万-200万，VWAP拆分
            num_slices = min(20, order_quantity // 100)
            
            return {
                'num_slices': num_slices,
                'slice_quantity': order_quantity // num_slices,
                'execution_method': 'VWAP',
                'execution_window_minutes': 30,
                'reason': '订单规模较大，使用VWAP智能拆分'
            }
        
        else:  # 200万以上，深度拆分
            num_slices = min(50, order_quantity // 100)
            
            return {
                'num_slices': num_slices,
                'slice_quantity': order_quantity // num_slices,
                'execution_method': 'VWAP',
                'execution_window_minutes': 60,
                'reason': '订单规模很大，使用VWAP深度拆分，降低冲击成本'
            }


class EmergencyExitExecutor:
    """
    🆕 V8.0: 紧急清仓执行器
    
    功能：
    1. 闪崩时的紧急清仓
    2. 智能选择清仓策略
    3. 避免地板价成交
    """
    
    def __init__(self):
        """初始化紧急清仓执行器"""
        self.exit_history = []
    
    def calculate_emergency_exit_strategy(self, 
                                        positions: List[Dict[str, Any]],
                                        market_condition: str = 'flash_crash') -> Dict[str, Any]:
        """
        计算紧急清仓策略
        
        Args:
            positions: 持仓列表
                [{
                    'code': '股票代码',
                    'name': '股票名称',
                    'quantity': '持仓数量',
                    'current_price': '当前价格',
                    'cost_price': '成本价'
                }]
            market_condition: 市场条件
        
        Returns:
            dict: 清仓策略
                {
                    'exit_method': 'MARKET' | 'LIMIT' | 'ICEBERG',
                    'exit_speed': 'IMMEDIATE' | 'FAST' | 'MODERATE',
                    'slippage_allowance': float,
                    'reason': str
                }
        """
        if market_condition == 'flash_crash':
            # 闪崩情况：使用冰山单，避免地板价
            return {
                'exit_method': 'ICEBERG',
                'exit_speed': 'FAST',
                'slippage_allowance': 0.02,  # 允许2%滑点
                'reason': '闪崩情况，使用冰山单逐步清仓，避免地板价成交'
            }
        
        elif market_condition == 'panic':
            # 恐慌性抛售：市价单快速清仓
            return {
                'exit_method': 'MARKET',
                'exit_speed': 'IMMEDIATE',
                'slippage_allowance': 0.05,  # 允许5%滑点
                'reason': '恐慌性抛售，市价单快速清仓，保命第一'
            }
        
        else:
            # 一般清仓：限价单
            return {
                'exit_method': 'LIMIT',
                'exit_speed': 'MODERATE',
                'slippage_allowance': 0.01,  # 允许1%滑点
                'reason': '一般清仓，使用限价单逐步卖出'
            }
    
    def execute_emergency_exit(self, 
                             positions: List[Dict[str, Any]],
                             exit_strategy: Dict[str, Any],
                             market_depth: MarketDepth) -> Dict[str, Any]:
        """
        执行紧急清仓
        
        Args:
            positions: 持仓列表
            exit_strategy: 清仓策略
            market_depth: 市场深度
        
        Returns:
            dict: 清仓结果
        """
        total_value = 0
        total_cost = 0
        exit_details = []
        
        for position in positions:
            code = position['code']
            quantity = position['quantity']
            current_price = position['current_price']
            
            if exit_strategy['exit_method'] == 'MARKET':
                # 市价单清仓
                exit_price = current_price * (1 - exit_strategy['slippage_allowance'])
            
            elif exit_strategy['exit_method'] == 'LIMIT':
                # 限价单清仓：挂在Ask1 - 0.5%的位置
                if market_depth.ask_prices and len(market_depth.ask_prices) > 0:
                    limit_price = market_depth.ask_prices[0] * 0.995
                else:
                    limit_price = current_price * 0.995
                exit_price = limit_price
            
            elif exit_strategy['exit_method'] == 'ICEBERG':
                # 冰山单清仓：每次只卖10%
                slice_quantity = quantity // 10
                exit_price = current_price * (1 - exit_strategy['slippage_allowance'] * 0.5)
            
            exit_value = slice_quantity * exit_price if exit_strategy['exit_method'] == 'ICEBERG' else quantity * exit_price
            total_value += exit_value
            
            exit_details.append({
                'code': code,
                'quantity': quantity,
                'exit_price': exit_price,
                'exit_value': exit_value
            })
        
        return {
            'total_value': total_value,
            'exit_details': exit_details,
            'exit_strategy': exit_strategy
        }


if __name__ == "__main__":
    demo_slippage_model()