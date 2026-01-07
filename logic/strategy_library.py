"""
策略模板库
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class StrategyTemplate(ABC):
    """
    策略模板基类
    
    所有策略的抽象基类
    """
    
    def __init__(self, name: str, params: Dict = None):
        """
        初始化策略模板
        
        Args:
            name: 策略名称
            params: 策略参数
        """
        self.name = name
        self.params = params or {}
        self.description = ""
        self.category = ""
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        生成交易信号
        
        Args:
            df: K线数据
        
        Returns:
            交易信号 (1: 买入, -1: 卖出, 0: 持有)
        """
        pass
    
    @abstractmethod
    def get_default_params(self) -> Dict:
        """
        获取默认参数
        
        Returns:
            默认参数字典
        """
        pass
    
    def validate_params(self, params: Dict) -> bool:
        """
        验证参数
        
        Args:
            params: 参数字典
        
        Returns:
            是否有效
        """
        return True
    
    def get_info(self) -> Dict:
        """
        获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'params': self.params,
            'default_params': self.get_default_params()
        }


class MAStrategy(StrategyTemplate):
    """
    均线策略模板
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("MA策略", params)
        self.description = "基于移动平均线的趋势跟踪策略"
        self.category = "趋势跟踪"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast_window = self.params.get('fast_window', 5)
        slow_window = self.params.get('slow_window', 20)
        
        sma_fast = df['close'].rolling(window=fast_window).mean()
        sma_slow = df['close'].rolling(window=slow_window).mean()
        
        signals = pd.Series(0, index=df.index)
        signals[sma_fast > sma_slow] = 1
        signals[sma_fast < sma_slow] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'fast_window': 5,
            'slow_window': 20
        }


class MACDStrategy(StrategyTemplate):
    """
    MACD策略模板
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("MACD策略", params)
        self.description = "基于MACD指标的趋势跟踪策略"
        self.category = "趋势跟踪"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast_period = self.params.get('fast_period', 12)
        slow_period = self.params.get('slow_period', 26)
        signal_period = self.params.get('signal_period', 9)
        
        ema_fast = df['close'].ewm(span=fast_period).mean()
        ema_slow = df['close'].ewm(span=slow_period).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period).mean()
        
        signals = pd.Series(0, index=df.index)
        signals[macd > signal] = 1
        signals[macd < signal] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9
        }


class RSIStrategy(StrategyTemplate):
    """
    RSI策略模板
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("RSI策略", params)
        self.description = "基于RSI指标的超买超卖策略"
        self.category = "均值回归"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get('period', 14)
        overbought = self.params.get('overbought', 70)
        oversold = self.params.get('oversold', 30)
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        signals = pd.Series(0, index=df.index)
        signals[rsi < oversold] = 1
        signals[rsi > overbought] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'period': 14,
            'overbought': 70,
            'oversold': 30
        }


class BollingerStrategy(StrategyTemplate):
    """
    布林带策略模板
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("布林带策略", params)
        self.description = "基于布林带的均值回归策略"
        self.category = "均值回归"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get('period', 20)
        std_dev = self.params.get('std_dev', 2)
        
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper_band = sma + std * std_dev
        lower_band = sma - std * std_dev
        
        signals = pd.Series(0, index=df.index)
        signals[df['close'] < lower_band] = 1
        signals[df['close'] > upper_band] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'period': 20,
            'std_dev': 2
        }


class DualMAProfitStrategy(StrategyTemplate):
    """
    双均线止盈策略
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("双均线止盈策略", params)
        self.description = "双均线趋势跟踪 + 动态止盈"
        self.category = "趋势跟踪"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast_window = self.params.get('fast_window', 5)
        slow_window = self.params.get('slow_window', 20)
        profit_ratio = self.params.get('profit_ratio', 0.05)  # 5% 止盈
        
        sma_fast = df['close'].rolling(window=fast_window).mean()
        sma_slow = df['close'].rolling(window=slow_window).mean()
        
        signals = pd.Series(0, index=df.index)
        
        # 金叉买入
        signals[(sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))] = 1
        
        # 死叉卖出
        signals[(sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))] = -1
        
        # 动态止盈
        # 计算买入后的最高价
        buy_signals = signals == 1
        highest_since_buy = df['close'].where(buy_signals.cumsum() > 0).ffill()
        
        # 如果当前价格比最高价下跌超过止盈比例，卖出
        profit_sell = (df['close'] < highest_since_buy * (1 - profit_ratio)) & (buy_signals.cumsum() > 0)
        signals[profit_sell] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'fast_window': 5,
            'slow_window': 20,
            'profit_ratio': 0.05
        }


class VolumePriceStrategy(StrategyTemplate):
    """
    量价配合策略
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("量价配合策略", params)
        self.description = "基于成交量与价格配合的策略"
        self.category = "量价分析"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        ma_window = self.params.get('ma_window', 20)
        volume_ratio = self.params.get('volume_ratio', 1.5)  # 成交量倍数
        
        sma = df['close'].rolling(window=ma_window).mean()
        volume_ma = df['volume'].rolling(window=ma_window).mean()
        
        signals = pd.Series(0, index=df.index)
        
        # 放量上涨
        signals[(df['close'] > sma) & (df['volume'] > volume_ma * volume_ratio)] = 1
        
        # 缩量下跌
        signals[(df['close'] < sma) & (df['volume'] < volume_ma * 0.8)] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'ma_window': 20,
            'volume_ratio': 1.5
        }


class StrategyLibrary:
    """
    策略库
    
    管理所有策略模板
    """
    
    def __init__(self):
        """初始化策略库"""
        self.strategies: Dict[str, StrategyTemplate] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认策略"""
        self.register_strategy(MAStrategy())
        self.register_strategy(MACDStrategy())
        self.register_strategy(RSIStrategy())
        self.register_strategy(BollingerStrategy())
        self.register_strategy(DualMAProfitStrategy())
        self.register_strategy(VolumePriceStrategy())
    
    def register_strategy(self, strategy: StrategyTemplate):
        """
        注册策略
        
        Args:
            strategy: 策略实例
        """
        self.strategies[strategy.name] = strategy
        logger.info(f"策略已注册: {strategy.name}")
    
    def get_strategy(self, name: str) -> Optional[StrategyTemplate]:
        """
        获取策略
        
        Args:
            name: 策略名称
        
        Returns:
            策略实例
        """
        return self.strategies.get(name)
    
    def list_strategies(self) -> List[Dict]:
        """
        列出所有策略
        
        Returns:
            策略信息列表
        """
        return [strategy.get_info() for strategy in self.strategies.values()]
    
    def list_strategies_by_category(self, category: str) -> List[Dict]:
        """
        按类别列出策略
        
        Args:
            category: 策略类别
        
        Returns:
            策略信息列表
        """
        return [
            strategy.get_info()
            for strategy in self.strategies.values()
            if strategy.category == category
        ]
    
    def create_strategy(
        self,
        name: str,
        params: Dict = None
    ) -> Optional[StrategyTemplate]:
        """
        创建策略实例
        
        Args:
            name: 策略名称
            params: 策略参数
        
        Returns:
            策略实例
        """
        strategy_template = self.get_strategy(name)
        
        if not strategy_template:
            logger.error(f"策略不存在: {name}")
            return None
        
        # 验证参数
        if params and not strategy_template.validate_params(params):
            logger.error(f"参数验证失败: {params}")
            return None
        
        # 创建新实例
        new_strategy = type(strategy_template)(params or strategy_template.get_default_params())
        
        return new_strategy
    
    def search_strategies(
        self,
        keyword: str
    ) -> List[Dict]:
        """
        搜索策略
        
        Args:
            keyword: 关键词
        
        Returns:
            策略信息列表
        """
        keyword = keyword.lower()
        
        return [
            strategy.get_info()
            for strategy in self.strategies.values()
            if keyword in strategy.name.lower() or
               keyword in strategy.description.lower() or
               keyword in strategy.category.lower()
        ]


# 全局策略库实例
strategy_library = StrategyLibrary()