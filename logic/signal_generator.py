"""
向量化信号生成器 - 高性能技术指标计算
"""

import numpy as np
import pandas as pd
import streamlit as st
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SignalGeneratorVectorized:
    """向量化信号生成器"""
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_ma_signals(close, fast_window=5, slow_window=20):
        """
        向量化 MA 跨越信号
        
        Args:
            close: 收盘价数据 (Series 或 array)
            fast_window: 快线窗口
            slow_window: 慢线窗口
        
        Returns:
            信号数组 (1=做多, 0=空仓)
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        sma_fast = pd.Series(close_array).rolling(window=fast_window).mean().values
        sma_slow = pd.Series(close_array).rolling(window=slow_window).mean().values
        
        signals = np.where(sma_fast > sma_slow, 1, 0)
        return signals
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_macd_signals(close, fast=12, slow=26, signal=9):
        """
        向量化 MACD 信号
        
        Args:
            close: 收盘价数据
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        
        Returns:
            信号数组
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        
        # MACD 计算
        ema_fast = pd.Series(close_array).ewm(span=fast).mean().values
        ema_slow = pd.Series(close_array).ewm(span=slow).mean().values
        macd = ema_fast - ema_slow
        
        # 信号线
        signal_line = pd.Series(macd).ewm(span=signal).mean().values
        
        # 信号: MACD > 信号线 = 买入
        signals = np.where(macd > signal_line, 1, 0)
        
        return signals
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_rsi_signals(close, period=14, overbought=70, oversold=30):
        """
        向量化 RSI 信号
        
        Args:
            close: 收盘价数据
            period: RSI 周期
            overbought: 超买阈值
            oversold: 超卖阈值
        
        Returns:
            信号数组
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        
        # 计算价格变化
        delta = np.diff(close_array)
        
        # 分离涨跌
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)
        
        # 平均涨跌幅
        avg_gains = pd.Series(gains).rolling(window=period).mean().values
        avg_losses = pd.Series(losses).rolling(window=period).mean().values
        
        # RSI 计算
        rs = np.where(avg_losses != 0, avg_gains / avg_losses, 0)
        rsi = 100 - (100 / (1 + rs))
        
        # 信号: RSI < 超卖 = 买入, RSI > 超买 = 卖出
        signals = np.where(rsi < oversold, 1, np.where(rsi > overbought, -1, 0))
        
        return signals
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_bollinger_signals(close, window=20, std_dev=2):
        """
        向量化布林带信号
        
        Args:
            close: 收盘价数据
            window: 移动平均窗口
            std_dev: 标准差倍数
        
        Returns:
            信号数组
        """
        close_array = close.values if isinstance(close, pd.Series) else close
        
        # 布林带计算
        sma = pd.Series(close_array).rolling(window=window).mean().values
        std = pd.Series(close_array).rolling(window=window).std().values
        
        upper_band = sma + std_dev * std
        lower_band = sma - std_dev * std
        
        # 信号: 价格跌破下轨 = 买入, 突破上轨 = 卖出
        signals = np.where(close_array < lower_band, 1, np.where(close_array > upper_band, -1, 0))
        
        return signals
    
    @staticmethod
    def generate_signals(df, signal_type, **kwargs):
        """
        统一信号生成接口
        
        Args:
            df: 数据 DataFrame
            signal_type: 信号类型 ('MA', 'MACD', 'RSI', 'BOLL')
            **kwargs: 其他参数
        
        Returns:
            信号数组
        """
        if 'close' not in df.columns:
            raise ValueError("数据中缺少 'close' 列")
        
        close = df['close']
        
        if signal_type == 'MA':
            return SignalGeneratorVectorized.generate_ma_signals(
                close, 
                kwargs.get('fast_window', 5),
                kwargs.get('slow_window', 20)
            )
        elif signal_type == 'MACD':
            return SignalGeneratorVectorized.generate_macd_signals(
                close,
                kwargs.get('fast', 12),
                kwargs.get('slow', 26),
                kwargs.get('signal', 9)
            )
        elif signal_type == 'RSI':
            return SignalGeneratorVectorized.generate_rsi_signals(
                close,
                kwargs.get('period', 14),
                kwargs.get('overbought', 70),
                kwargs.get('oversold', 30)
            )
        elif signal_type == 'BOLL':
            return SignalGeneratorVectorized.generate_bollinger_signals(
                close,
                kwargs.get('window', 20),
                kwargs.get('std_dev', 2)
            )
        else:
            raise ValueError(f"不支持的信号类型: {signal_type}")


# 全局实例
_signal_generator = None


def get_signal_generator() -> SignalGeneratorVectorized:
    """获取信号生成器实例（单例）"""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = SignalGeneratorVectorized()
    return _signal_generator