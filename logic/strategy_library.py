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


class ATRStrategy(StrategyTemplate):
    """
    ATR (Average True Range) 策略
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("ATR策略", params)
        self.description = "基于ATR指标的波动率突破策略"
        self.category = "波动率"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get('period', 14)
        atr_multiplier = self.params.get('atr_multiplier', 2.0)
        
        # 计算ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # 计算ATR通道
        upper_band = df['close'].shift(1) + atr * atr_multiplier
        lower_band = df['close'].shift(1) - atr * atr_multiplier
        
        signals = pd.Series(0, index=df.index)
        
        # 突破上轨买入
        signals[df['close'] > upper_band] = 1
        
        # 跌破下轨卖出
        signals[df['close'] < lower_band] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'period': 14,
            'atr_multiplier': 2.0
        }


class KDJStrategy(StrategyTemplate):
    """
    KDJ策略
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("KDJ策略", params)
        self.description = "基于KDJ指标的超买超卖策略"
        self.category = "技术指标"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        n = self.params.get('period', 9)
        m1 = self.params.get('m1', 3)
        m2 = self.params.get('m2', 3)
        overbought = self.params.get('overbought', 80)
        oversold = self.params.get('oversold', 20)
        
        # 计算KDJ
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        
        k = rsv.ewm(com=m1-1, adjust=False).mean()
        d = k.ewm(com=m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        signals = pd.Series(0, index=df.index)
        
        # KDJ金叉买入
        signals[(k > d) & (k.shift(1) <= d.shift(1))] = 1
        
        # KDJ死叉卖出
        signals[(k < d) & (k.shift(1) >= d.shift(1))] = -1
        
        # 超买超卖
        signals[j > overbought] = -1
        signals[j < oversold] = 1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'period': 9,
            'm1': 3,
            'm2': 3,
            'overbought': 80,
            'oversold': 20
        }


class WilliamStrategy(StrategyTemplate):
    """
    威廉指标 (WR) 策略
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("威廉指标策略", params)
        self.description = "基于威廉指标的超买超卖策略"
        self.category = "技术指标"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get('period', 14)
        overbought = self.params.get('overbought', -20)
        oversold = self.params.get('oversold', -80)
        
        # 计算威廉指标
        high_n = df['high'].rolling(window=period).max()
        low_n = df['low'].rolling(window=period).min()
        
        wr = -100 * (high_n - df['close']) / (high_n - low_n)
        
        signals = pd.Series(0, index=df.index)
        
        # 超买
        signals[wr > overbought] = -1
        
        # 超卖
        signals[wr < oversold] = 1
        
        # 金叉死叉
        signals[(wr > wr.shift(1)) & (wr.shift(1) < wr.shift(2))] = 1
        signals[(wr < wr.shift(1)) & (wr.shift(1) > wr.shift(2))] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'period': 14,
            'overbought': -20,
            'oversold': -80
        }


class CCIStrategy(StrategyTemplate):
    """
    CCI (Commodity Channel Index) 策略
    """
    
    def __init__(self, params: Dict = None):
        super().__init__("CCI策略", params)
        self.description = "基于CCI指标的趋势跟踪策略"
        self.category = "技术指标"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        period = self.params.get('period', 20)
        overbought = self.params.get('overbought', 100)
        oversold = self.params.get('oversold', -100)
        
        # 计算CCI
        tp = (df['high'] + df['low'] + df['close']) / 3
        ma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (tp - ma_tp) / (0.015 * mad)
        
        signals = pd.Series(0, index=df.index)
        
        # 超买
        signals[cci > overbought] = -1
        
        # 超卖
        signals[cci < oversold] = 1
        
        # 零轴穿越
        signals[(cci > 0) & (cci.shift(1) <= 0)] = 1
        signals[(cci < 0) & (cci.shift(1) >= 0)] = -1
        
        return signals
    
    def get_default_params(self) -> Dict:
        return {
            'period': 20,
            'overbought': 100,
            'oversold': -100
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
        self.register_strategy(ATRStrategy())
        self.register_strategy(KDJStrategy())
        self.register_strategy(WilliamStrategy())
        self.register_strategy(CCIStrategy())
    
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