"""
多策略融合模块
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class MultiStrategyFusion:
    """
    多策略融合器
    
    融合多个信号源，提高策略稳定性
    """
    
    def __init__(self, strategies: List[str] = None):
        """
        初始化多策略融合器
        
        Args:
            strategies: 策略列表
        """
        self.strategies = strategies or ['MA', 'MACD', 'RSI']
        self.weights = np.ones(len(self.strategies)) / len(self.strategies)
    
    def set_weights(self, weights: List[float]):
        """
        设置策略权重
        
        Args:
            weights: 权重列表
        """
        if len(weights) != len(self.strategies):
            raise ValueError(f"权重数量 {len(weights)} 与策略数量 {len(self.strategies)} 不匹配")
        
        self.weights = np.array(weights) / np.sum(weights)
        logger.info(f"策略权重已更新: {dict(zip(self.strategies, self.weights))}")
    
    def fuse_signals(
        self,
        signals_dict: Dict[str, pd.Series]
    ) -> pd.Series:
        """
        融合多个信号
        
        Args:
            signals_dict: 信号字典 {策略名: 信号Series}
        
        Returns:
            融合后的信号
        """
        if not signals_dict:
            raise ValueError("信号字典为空")
        
        # 确保所有信号长度一致
        first_signal = list(signals_dict.values())[0]
        index = first_signal.index
        
        # 加权融合
        fused_signal = pd.Series(0.0, index=index)
        
        for i, (strategy, signal) in enumerate(signals_dict.items()):
            if strategy in self.strategies:
                weight = self.weights[self.strategies.index(strategy)]
                fused_signal += signal * weight
        
        # 二值化: >0.5 为买入, <-0.5 为卖出, 否则持有
        final_signal = pd.Series(0, index=index)
        final_signal[fused_signal > 0.5] = 1
        final_signal[fused_signal < -0.5] = -1
        
        return final_signal
    
    def vote_fusion(
        self,
        signals_dict: Dict[str, pd.Series]
    ) -> pd.Series:
        """
        投票融合 (少数服从多数)
        
        Args:
            signals_dict: 信号字典
        
        Returns:
            融合后的信号
        """
        if not signals_dict:
            raise ValueError("信号字典为空")
        
        first_signal = list(signals_dict.values())[0]
        index = first_signal.index
        
        # 投票
        buy_votes = pd.Series(0, index=index)
        sell_votes = pd.Series(0, index=index)
        
        for signal in signals_dict.values():
            buy_votes += (signal == 1).astype(int)
            sell_votes += (signal == -1).astype(int)
        
        # 多数投票
        final_signal = pd.Series(0, index=index)
        final_signal[buy_votes > sell_votes] = 1
        final_signal[sell_votes > buy_votes] = -1
        
        return final_signal
    
    def adaptive_fusion(
        self,
        signals_dict: Dict[str, pd.Series],
        performance_dict: Dict[str, float]
    ) -> pd.Series:
        """
        自适应融合 (根据历史表现调整权重)
        
        Args:
            signals_dict: 信号字典
            performance_dict: 策略表现 {策略名: 夏普比率}
        
        Returns:
            融合后的信号
        """
        if not signals_dict:
            raise ValueError("信号字典为空")
        
        # 根据表现计算权重
        weights = []
        for strategy in self.strategies:
            perf = performance_dict.get(strategy, 0)
            # 使用 softmax 转换为概率
            weights.append(np.exp(perf))
        
        weights = np.array(weights) / np.sum(weights)
        
        # 加权融合
        first_signal = list(signals_dict.values())[0]
        index = first_signal.index
        
        fused_signal = pd.Series(0.0, index=index)
        
        for i, (strategy, signal) in enumerate(signals_dict.items()):
            if strategy in self.strategies:
                fused_signal += signal * weights[i]
        
        # 二值化
        final_signal = pd.Series(0, index=index)
        final_signal[fused_signal > 0.5] = 1
        final_signal[fused_signal < -0.5] = -1
        
        return final_signal
    
    def calculate_consensus(
        self,
        signals_dict: Dict[str, pd.Series]
    ) -> pd.Series:
        """
        计算信号一致性
        
        Args:
            signals_dict: 信号字典
        
        Returns:
            一致性分数 (0-1)
        """
        if not signals_dict:
            return pd.Series()
        
        first_signal = list(signals_dict.values())[0]
        index = first_signal.index
        
        # 计算每个时间点的信号一致性
        consensus = pd.Series(0.0, index=index)
        
        for i in range(len(index)):
            signals_at_i = [signal.iloc[i] for signal in signals_dict.values()]
            
            # 计算一致性
            if all(s == 1 for s in signals_at_i):
                consensus.iloc[i] = 1.0
            elif all(s == -1 for s in signals_at_i):
                consensus.iloc[i] = 1.0
            elif all(s == 0 for s in signals_at_i):
                consensus.iloc[i] = 1.0
            else:
                # 部分一致
                unique_signals = set(signals_at_i)
                consensus.iloc[i] = 1.0 / len(unique_signals)
        
        return consensus


class EnsembleStrategy:
    """
    集成策略
    
    结合多个子策略，提升整体表现
    """
    
    def __init__(self, sub_strategies: List[Dict]):
        """
        初始化集成策略
        
        Args:
            sub_strategies: 子策略列表 [{'name': 'MA', 'params': {...}}, ...]
        """
        self.sub_strategies = sub_strategies
        self.fusion_method = 'weighted'  # weighted, vote, adaptive
    
    def set_fusion_method(self, method: str):
        """
        设置融合方法
        
        Args:
            method: 融合方法 (weighted, vote, adaptive)
        """
        if method not in ['weighted', 'vote', 'adaptive']:
            raise ValueError(f"不支持的融合方法: {method}")
        
        self.fusion_method = method
        logger.info(f"融合方法已设置为: {method}")
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        signal_generator
    ) -> pd.Series:
        """
        生成集成信号
        
        Args:
            df: K线数据
            signal_generator: 信号生成器
        
        Returns:
            集成信号
        """
        signals_dict = {}
        
        # 生成各子策略信号
        for strategy in self.sub_strategies:
            name = strategy['name']
            params = strategy.get('params', {})
            
            try:
                if name == 'MA':
                    fast = params.get('fast_window', 5)
                    slow = params.get('slow_window', 20)
                    signals_dict[name] = signal_generator.generate_ma_signals(
                        df['close'], fast, slow
                    )
                elif name == 'MACD':
                    fast = params.get('fast_period', 12)
                    slow = params.get('slow_period', 26)
                    signal_period = params.get('signal_period', 9)
                    signals_dict[name] = signal_generator.generate_macd_signals(
                        df['close'], fast, slow, signal_period
                    )
                elif name == 'RSI':
                    period = params.get('period', 14)
                    signals_dict[name] = signal_generator.generate_rsi_signals(
                        df['close'], period
                    )
                elif name == 'Bollinger':
                    period = params.get('period', 20)
                    std_dev = params.get('std_dev', 2)
                    signals_dict[name] = signal_generator.generate_bollinger_signals(
                        df['close'], period, std_dev
                    )
            except Exception as e:
                logger.error(f"生成 {name} 信号失败: {e}")
                continue
        
        # 融合信号
        fusion = MultiStrategyFusion(list(signals_dict.keys()))
        
        if self.fusion_method == 'weighted':
            return fusion.fuse_signals(signals_dict)
        elif self.fusion_method == 'vote':
            return fusion.vote_fusion(signals_dict)
        elif self.fusion_method == 'adaptive':
            # 简化版: 使用等权重
            return fusion.fuse_signals(signals_dict)
        
        return pd.Series(0, index=df.index)
    
    def get_strategy_count(self) -> int:
        """获取子策略数量"""
        return len(self.sub_strategies)