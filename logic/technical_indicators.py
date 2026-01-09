"""
技术指标计算模块

功能：计算MACD、KDJ、RSI等技术指标
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast_period: int = 12, 
                       slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            df: 包含收盘价的数据框
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            pd.DataFrame: 包含MACD指标的数据框
        """
        try:
            if 'close' not in df.columns:
                # 尝试其他可能的列名
                close_col = None
                for col in ['收盘', '收盘价', 'close', 'Close']:
                    if col in df.columns:
                        close_col = col
                        break
                if close_col is None:
                    logger.warning("找不到收盘价列")
                    return df
                df = df.copy()
                df['close'] = df[close_col]
            
            # 计算EMA
            ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
            
            # 计算DIF
            dif = ema_fast - ema_slow
            
            # 计算DEA
            dea = dif.ewm(span=signal_period, adjust=False).mean()
            
            # 计算MACD柱
            macd = (dif - dea) * 2
            
            df['macd_dif'] = dif
            df['macd_dea'] = dea
            df['macd_hist'] = macd
            
            return df
            
        except Exception as e:
            logger.error(f"计算MACD失败: {e}")
            return df
    
    @staticmethod
    def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """
        计算KDJ指标
        
        Args:
            df: 包含开高低收的数据框
            n: RSV周期
            m1: K值平滑周期
            m2: D值平滑周期
            
        Returns:
            pd.DataFrame: 包含KDJ指标的数据框
        """
        try:
            # 查找列名
            high_col = None
            low_col = None
            close_col = None
            
            for col in ['high', 'High', '最高', '最高价']:
                if col in df.columns:
                    high_col = col
                    break
            
            for col in ['low', 'Low', '最低', '最低价']:
                if col in df.columns:
                    low_col = col
                    break
                    
            for col in ['close', 'Close', '收盘', '收盘价']:
                if col in df.columns:
                    close_col = col
                    break
            
            if None in [high_col, low_col, close_col]:
                logger.warning("找不到开高低收列")
                return df
            
            df = df.copy()
            
            # 计算RSV
            low_n = df[low_col].rolling(window=n).min()
            high_n = df[high_col].rolling(window=n).max()
            rsv = (df[close_col] - low_n) / (high_n - low_n) * 100
            
            # 计算K值
            k = rsv.ewm(com=m1 - 1, adjust=False).mean()
            
            # 计算D值
            d = k.ewm(com=m2 - 1, adjust=False).mean()
            
            # 计算J值
            j = 3 * k - 2 * d
            
            df['kdj_k'] = k
            df['kdj_d'] = d
            df['kdj_j'] = j
            
            return df
            
        except Exception as e:
            logger.error(f"计算KDJ失败: {e}")
            return df
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算RSI指标
        
        Args:
            df: 包含收盘价的数据框
            period: RSI周期
            
        Returns:
            pd.DataFrame: 包含RSI指标的数据框
        """
        try:
            if 'close' not in df.columns:
                # 尝试其他可能的列名
                close_col = None
                for col in ['收盘', '收盘价', 'close', 'Close']:
                    if col in df.columns:
                        close_col = col
                        break
                if close_col is None:
                    logger.warning("找不到收盘价列")
                    return df
                df = df.copy()
                df['close'] = df[close_col]
            
            # 计算价格变化
            delta = df['close'].diff()
            
            # 分离上涨和下跌
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # 计算平均上涨和下跌
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # 计算RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            df['rsi'] = rsi
            
            return df
            
        except Exception as e:
            logger.error(f"计算RSI失败: {e}")
            return df
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标
        
        Args:
            df: K线数据
            
        Returns:
            pd.DataFrame: 包含所有技术指标的数据框
        """
        df = TechnicalIndicators.calculate_macd(df)
        df = TechnicalIndicators.calculate_kdj(df)
        df = TechnicalIndicators.calculate_rsi(df)
        
        return df


if __name__ == "__main__":
    # 测试
    from logic.akshare_data_loader import AKShareDataLoader
    
    # 获取板块K线数据
    loader = AKShareDataLoader()
    kline = loader.get_sector_index_kline("BK0447")
    
    if not kline.empty:
        print("原始K线数据:")
        print(kline.head())
        
        # 计算技术指标
        kline_with_indicators = TechnicalIndicators.calculate_all_indicators(kline)
        
        print("\n包含技术指标的数据:")
        print(kline_with_indicators.head())
        
        print("\n技术指标列:")
        print(kline_with_indicators.columns.tolist())
    else:
        print("K线数据为空")