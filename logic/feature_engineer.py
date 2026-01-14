"""
特征工程模块（深度优化版）
从"拟合数据"进化为"寻找 Alpha"
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    特征工程器
    计算高级特征，让模型更懂市场
    """

    def __init__(self, lookback: int = 20):
        """
        初始化特征工程器

        Args:
            lookback: 默认回看窗口
        """
        self.lookback = lookback

    def calculate_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标特征（增强版）

        Args:
            df: K线数据

        Returns:
            添加了特征的 DataFrame
        """
        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)

        # ===== 基础技术指标 =====
        # 移动平均
        df['ma_short'] = df['close'].rolling(window=5).mean()
        df['ma_long'] = df['close'].rolling(window=self.lookback).mean()
        df['ma_diff'] = (df['ma_short'] - df['ma_long']) / df['ma_long']

        # RSI 及其衍生特征
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # RSI 斜率（动量特征）
        df['rsi_slope'] = df['rsi'].diff(3)  # 3日RSI变化率
        df['rsi_divergence'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) - (df['rsi'] - df['rsi'].shift(5)) / 100

        # MACD 及其衍生特征
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        df['macd_momentum'] = df['macd_hist'].diff()

        # 布林带及衍生特征
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # KDJ
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        df['kdj_k'] = rsv.ewm(com=2).mean()
        df['kdj_d'] = df['kdj_k'].ewm(com=2).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']

        # ===== 高级技术特征 =====
        # 动量指标
        df['momentum'] = df['close'] - df['close'].shift(self.lookback)
        df['roc'] = (df['close'] - df['close'].shift(self.lookback)) / df['close'].shift(self.lookback) * 100

        # 波动率
        df['volatility'] = df['close'].pct_change().rolling(window=self.lookback).std()
        df['atr'] = self._calculate_atr(df, 14)

        # 成交量特征
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        df['volume_price_trend'] = (df['close'] - df['close'].shift(1)) / df['close'].shift(1) * (df['volume'] / df['volume'].shift(1))

        # 价格形态
        df['amplitude'] = (df['high'] - df['low']) / df['close'] * 100
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close'] * 100
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close'] * 100

        # 趋势强度
        df['trend_strength'] = self._calculate_trend_strength(df, self.lookback)

        # 支撑阻力
        df['support_distance'] = (df['close'] - df['low'].rolling(window=20).min()) / df['close']
        df['resistance_distance'] = (df['high'].rolling(window=20).max() - df['close']) / df['close']

        return df

    def calculate_cross_sectional_features(self,
                                          df: pd.DataFrame,
                                          sector_index: Optional[pd.DataFrame] = None,
                                          sector_stocks: Optional[List[str]] = None) -> pd.DataFrame:
        """
        计算截面特征（相对强弱、板块排名）

        Args:
            df: 个股数据
            sector_index: 板块指数数据（可选）
            sector_stocks: 板块内所有股票数据（可选）

        Returns:
            添加了截面特征的 DataFrame
        """
        df = df.copy()

        # 相对强弱（相对于大盘或板块）
        if sector_index is not None and 'close' in sector_index.columns:
            # 对齐日期
            sector_aligned = sector_index.set_index('date').reindex(df['date'])
            if not sector_aligned['close'].isna().all():
                df['rel_strength'] = df['close'] / sector_aligned['close'] * 100
                df['rel_strength_change'] = df['rel_strength'].pct_change() * 100
            else:
                df['rel_strength'] = df['close'] / df['close'].rolling(window=60).mean() * 100
                df['rel_strength_change'] = df['rel_strength'].pct_change() * 100
        else:
            # 如果没有板块数据，用自身均线作为基准
            df['rel_strength'] = df['close'] / df['close'].rolling(window=60).mean() * 100
            df['rel_strength_change'] = df['rel_strength'].pct_change() * 100

        # 相对排名（如果有板块内其他股票数据）
        if sector_stocks is not None and len(sector_stocks) > 0:
            # 计算每日涨幅排名
            df['daily_return'] = df['close'].pct_change() * 100

            # 这里简化处理，实际需要所有股票的当日涨幅
            # df['rank_in_sector'] = df.groupby('date')['daily_return'].rank(pct=True)
            # 暂时用相对强弱代替
            df['rank_in_sector'] = df['rel_strength_change'].rolling(window=5).rank(pct=True)
        else:
            # 如果没有板块数据，用历史排名代替
            df['daily_return'] = df['close'].pct_change() * 100
            df['rank_in_sector'] = df['daily_return'].rolling(window=20).rank(pct=True)

        # Beta（相对于大盘的波动率）
        if sector_index is not None and 'close' in sector_index.columns:
            sector_aligned = sector_index.set_index('date').reindex(df['date'])
            if not sector_aligned['close'].isna().all():
                stock_returns = df['close'].pct_change()
                sector_returns = sector_aligned['close'].pct_change()
                covariance = stock_returns.rolling(window=60).cov(sector_returns)
                variance = sector_returns.rolling(window=60).var()
                df['beta'] = covariance / variance
            else:
                df['beta'] = 1.0
        else:
            df['beta'] = 1.0

        return df

    def calculate_microstructure_features(self,
                                         df: pd.DataFrame,
                                         order_book: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        计算微观结构特征（订单不平衡等）

        Args:
            df: K线数据
            order_book: 订单簿数据（可选，包含 bid1_vol, ask1_vol 等）

        Returns:
            添加了微观结构特征的 DataFrame
        """
        df = df.copy()

        if order_book is not None and 'bid1_vol' in order_book.columns and 'ask1_vol' in order_book.columns:
            # 订单不平衡（最强预测因子之一）
            df['order_imbalance'] = (order_book['bid1_vol'] - order_book['ask1_vol']) / (order_book['bid1_vol'] + order_book['ask1_vol'])

            # 买卖压力
            df['buy_pressure'] = order_book['bid1_vol'] / (order_book['bid1_vol'] + order_book['ask1_vol'])
            df['sell_pressure'] = order_book['ask1_vol'] / (order_book['bid1_vol'] + order_book['ask1_vol'])

            # 价差
            df['spread_ratio'] = (order_book['ask1'] - order_book['bid1']) / df['close'] if 'ask1' in order_book.columns else 0
        else:
            # 如果没有订单簿数据，用成交量分布模拟
            df['order_imbalance'] = 0.0
            df['buy_pressure'] = 0.5
            df['sell_pressure'] = 0.5
            df['spread_ratio'] = 0.0

        # 成交量分布（用振幅模拟）
        df['volume_distribution'] = (df['close'] - df['open']) / df['amplitude'] if 'amplitude' in df.columns else 0

        return df

    def calculate_multi_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算多目标预测标签

        Args:
            df: K线数据

        Returns:
            添加了多目标标签的 DataFrame
        """
        df = df.copy()

        # 目标1：明天涨跌幅（回归）
        df['target_next_return'] = df['close'].pct_change().shift(-1) * 100

        # 目标2：未来5天涨跌幅（趋势）
        df['target_5d_return'] = df['close'].shift(-5) / df['close'] - 1

        # 目标3：未来波动率（风险）
        df['target_5d_volatility'] = df['close'].pct_change().rolling(window=5).std().shift(-5)

        # 目标4：未来是否涨停（分类）
        df['target_limit_up'] = (df['close'].shift(-1) / df['close'] - 1) > 0.095

        # 目标5：未来是否跌停（分类）
        df['target_limit_down'] = (df['close'].shift(-1) / df['close'] - 1) < -0.095

        return df

    def get_feature_list(self) -> List[str]:
        """
        获取所有特征名称列表

        Returns:
            特征名称列表
        """
        features = []

        # 技术指标特征
        features.extend([
            'ma_short', 'ma_long', 'ma_diff',
            'rsi', 'rsi_slope', 'rsi_divergence',
            'macd', 'macd_signal', 'macd_hist', 'macd_momentum',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
            'kdj_k', 'kdj_d', 'kdj_j',
            'momentum', 'roc',
            'volatility', 'atr',
            'volume_ma', 'volume_ratio', 'volume_price_trend',
            'amplitude', 'upper_shadow', 'lower_shadow',
            'trend_strength',
            'support_distance', 'resistance_distance'
        ])

        # 截面特征
        features.extend([
            'rel_strength', 'rel_strength_change',
            'rank_in_sector', 'beta'
        ])

        # 微观结构特征
        features.extend([
            'order_imbalance', 'buy_pressure', 'sell_pressure',
            'spread_ratio', 'volume_distribution'
        ])

        return features

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算平均真实波幅（ATR）

        Args:
            df: K线数据
            period: 周期

        Returns:
            ATR 值
        """
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    def _calculate_trend_strength(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算趋势强度（价格斜率）"""
        # 使用线性回归斜率
        def calc_slope(window):
            if len(window) < 2:
                return 0
            x = np.arange(len(window))
            y = window.values
            # 使用最小二乘法计算斜率
            try:
                slope = np.polyfit(x, y, 1)[0]
                return slope
            except:
                return 0

        return df['close'].rolling(window=period).apply(calc_slope, raw=False)


# 使用示例
if __name__ == "__main__":
    # 创建模拟数据
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=1000)
    returns = np.random.randn(1000) * 0.02
    prices = 100 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.randn(1000) * 0.005),
        'high': prices * (1 + np.abs(np.random.randn(1000)) * 0.01),
        'low': prices * (1 - np.abs(np.random.randn(1000)) * 0.01),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 1000)
    })

    # 创建特征工程器
    engineer = FeatureEngineer(lookback=20)

    # 计算技术特征
    df = engineer.calculate_technical_features(df)
    print("技术特征计算完成")

    # 计算截面特征
    df = engineer.calculate_cross_sectional_features(df)
    print("截面特征计算完成")

    # 计算微观结构特征
    df = engineer.calculate_microstructure_features(df)
    print("微观结构特征计算完成")

    # 计算多目标
    df = engineer.calculate_multi_targets(df)
    print("多目标计算完成")

    # 获取特征列表
    features = engineer.get_feature_list()
    print(f"\n总特征数: {len(features)}")
    print("\n特征列表:")
    for i, feature in enumerate(features, 1):
        print(f"{i}. {feature}")

    # 显示前几行
    print(f"\n数据形状: {df.shape}")
    print("\n前5行数据:")
    print(df.head())