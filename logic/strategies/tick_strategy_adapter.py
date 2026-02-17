#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tick策略适配器
将ITickStrategy接口适配到backtestengine的接口
"""

from typing import List, Dict, Any, Callable
import pandas as pd
from logic.strategies.tick_strategy_interface import ITickStrategy
from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy


class TickStrategyAdapter:
    """
    Tick策略适配器
    将ITickStrategy接口适配到backtestengine使用的策略函数接口
    """
    
    def __init__(self, tick_strategy: ITickStrategy, params: Dict[str, Any] = None):
        """
        初始化适配器
        
        Args:
            tick_strategy: ITickStrategy实现
            params: 策略参数
        """
        self.tick_strategy = tick_strategy
        self.params = params or {}
        self.signals = []  # 存储产生的信号
        
    def to_backtest_func(self) -> Callable:
        """
        转换为backtestengine可使用的策略函数
        
        Returns:
            Callable: backtestengine使用的策略函数
        """
        def strategy_func(date: str, daily_data: Dict, strategy_params: Dict) -> List[Dict]:
            """
            backtestengine策略函数接口
            """
            signals = []
            
            # 遍历当日所有股票数据
            for code, data in daily_data.items():
                # 将K线数据转换为Tick格式进行回测
                # 这里我们使用分钟线数据来模拟Tick数据
                tick_data_list = self._convert_kline_to_ticks(data, date)
                
                # 为每只股票创建独立的策略实例以保持状态
                strategy_instance = self._create_strategy_instance()
                
                # 逐个Tick处理
                for tick_data in tick_data_list:
                    tick_signals = strategy_instance.on_tick(tick_data)
                    
                    # 将策略信号转换为backtest信号
                    for signal in tick_signals:
                        backtest_signal = {
                            'date': date,
                            'code': code,
                            'action': 'BUY',  # 默认为买入
                            'signal_score': signal.strength,
                            'stop_loss_ratio': self.params.get('stop_loss_ratio', 0.05),
                            'take_profit_ratio': self.params.get('take_profit_ratio', 0.20),
                            'extra_info': signal.extra_info
                        }
                        signals.append(backtest_signal)
            
            return signals
        
        return strategy_func
    
    def _convert_kline_to_ticks(self, kline_data: Dict, date: str) -> List:
        """
        将K线数据转换为Tick数据列表
        这里使用简单的分钟数据来模拟，实际应用中应使用真实Tick数据
        
        Args:
            kline_data: K线数据
            date: 日期
            
        Returns:
            List: Tick数据列表
        """
        from logic.strategies.tick_strategy_interface import TickData
        import pandas as pd
        
        # 构建一个简单的分钟数据来模拟Tick流
        # 实际应用中应从tick数据源读取真实tick数据
        ticks = []
        
        # 假设我们有开盘价、收盘价等基本数据
        open_price = kline_data.get('open', 0)
        close_price = kline_data.get('close', 0)
        high_price = kline_data.get('high', 0)
        low_price = kline_data.get('low', 0)
        volume = kline_data.get('volume', 0)
        amount = kline_data.get('amount', 0)
        
        if open_price <= 0:
            return ticks
        
        # 简单模拟分钟数据
        # 在实际应用中，这应该从真实tick数据提供器中获取
        import time
        base_time = pd.to_datetime(f"{date} 09:30:00").timestamp() * 1000  # 毫秒时间戳
        
        # 如果有历史分钟数据，使用更真实的模拟
        # 否则简单创建几个价格点
        if high_price > 0 and low_price > 0:
            # 创建几个价格点来模拟价格波动
            for i in range(10):  # 简单创建10个虚拟tick
                # 在开盘价和收盘价之间随机波动
                import random
                price = open_price + (close_price - open_price) * (i / 9) + random.uniform(-0.1, 0.1)
                vol_increment = volume / 10  # 平均分配成交量
                time_increment = i * 60 * 1000  # 每分钟一个tick
                
                tick = TickData(
                    time=int(base_time + time_increment),
                    last_price=price,
                    volume=vol_increment * (i + 1),  # 累计成交量
                    amount=amount * (i / 10),  # 累计成交额
                    bid_price=kline_data.get('bid_price', price * 0.999),
                    ask_price=kline_data.get('ask_price', price * 1.001),
                    bid_vol=kline_data.get('bid_vol', 100),
                    ask_vol=kline_data.get('ask_vol', 100)
                )
                ticks.append(tick)
        
        return ticks
    
    def _create_strategy_instance(self) -> ITickStrategy:
        """
        创建策略实例（用于保持每只股票独立的状态）
        
        Returns:
            ITickStrategy: 策略实例
        """
        # 对于Halfway策略，我们重新创建一个实例
        if isinstance(self.tick_strategy, HalfwayTickStrategy):
            return HalfwayTickStrategy(self.params)
        else:
            # 对于其他策略，可以根据类型创建相应实例
            # 這里需要根据具体策略类型来实现
            return self.tick_strategy


class TickDataFeed:
    """
    Tick数据提供器
    为backtestengine提供Tick数据流接口
    """
    
    def __init__(self, stock_codes: List[str], start_date: str, end_date: str, params: Dict[str, Any] = None):
        """
        初始化Tick数据提供器
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            params: 参数
        """
        self.stock_codes = stock_codes
        self.start_date = start_date
        self.end_date = end_date
        self.params = params or {}
        
    def get_tick_data_for_date(self, date: str) -> Dict[str, List]:
        """
        获取指定日期的Tick数据
        
        Args:
            date: 日期
            
        Returns:
            Dict: {股票代码: [TickData列表]}
        """
        from logic.qmt_historical_provider import QMTHistoricalProvider
        from datetime import datetime
        import pandas as pd
        
        tick_data_dict = {}
        
        for code in self.stock_codes:
            try:
                # 使用QMTHistoricalProvider获取真实Tick数据
                provider = QMTHistoricalProvider(
                    stock_code=code,
                    start_time=f"{date.replace('-', '')}093000",
                    end_time=f"{date.replace('-', '')}150000",
                    period="tick"
                )
                
                # 获取Tick迭代器
                ticks = []
                for tick_dict in provider.iter_ticks():
                    # 将字典转换为TickData对象
                    from logic.strategies.tick_strategy_interface import TickData
                    tick_data = TickData(
                        time=tick_dict['time'],
                        last_price=tick_dict['last_price'],
                        volume=tick_dict['volume'],
                        amount=tick_dict['amount'],
                        bid_price=tick_dict.get('bid_price', 0),
                        ask_price=tick_dict.get('ask_price', 0),
                        bid_vol=tick_dict.get('bid_vol', 0),
                        ask_vol=tick_dict.get('ask_vol', 0)
                    )
                    ticks.append(tick_data)
                
                tick_data_dict[code] = ticks
                
            except Exception as e:
                print(f"获取{code}的Tick数据失败: {e}")
                tick_data_dict[code] = []
        
        return tick_data_dict


def create_tick_backtest_strategy(tick_strategy: ITickStrategy, params: Dict[str, Any] = None):
    """
    创建Tick回测策略
    
    Args:
        tick_strategy: ITickStrategy实现
        params: 策略参数
        
    Returns:
        Callable: backtestengine使用的策略函数
    """
    adapter = TickStrategyAdapter(tick_strategy, params)
    return adapter.to_backtest_func()


if __name__ == "__main__":
    # 测试适配器
    from logic.strategies.halfway_tick_strategy import HalfwayTickStrategy
    
    params = {
        'volatility_threshold': 0.03,
        'volume_surge': 1.5,
        'breakout_strength': 0.01
    }
    
    halfway_strategy = HalfwayTickStrategy(params)
    adapter = TickStrategyAdapter(halfway_strategy, params)
    
    print("✅ Tick策略适配器测试完成")
    print(f"策略名称: {halfway_strategy.get_strategy_name()}")