"""
深度特征工程模块（增强版）
从原始 OHLCV 数据转化为具备预测能力的 Alpha 因子
整合经典技术指标、Alpha 因子、相对强弱、微观结构特征
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    高级特征工程器（增强版）
    将原始 K 线数据转化为机器学习可用的特征
    
    特征类别：
    1. 经典技术指标（RSI、MACD、KDJ、ATR等）
    2. 趋势特征（均线、斜率、动量）
    3. Alpha 因子（订单不平衡、板块排名）
    4. 截面特征（相对强弱、RSRS）
    5. 微观结构特征（量价关系、买卖盘）
    6. 时间特征（星期几、月初月末）
    """
    
    def __init__(self, lookback: int = 20, use_technical: bool = True, use_alpha: bool = True):
        """
        初始化特征工程器
        
        Args:
            lookback: 默认回看窗口
            use_technical: 是否使用经典技术指标
            use_alpha: 是否使用 Alpha 因子
        """
        self.lookback = lookback
        self.use_technical = use_technical
        self.use_alpha = use_alpha
        self.feature_list = None
    
    def transform(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        主转换函数 - 一键生成所有特征
        
        Args:
            df: 包含 OHLCV 的数据
            benchmark_df: 大盘或板块指数数据（可选）
            
        Returns:
            添加了所有特征的 DataFrame
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 1. 经典技术指标
        if self.use_technical:
            df = self._add_trend_features(df)
            df = self._add_momentum_features(df)
            df = self._add_volatility_features(df)
            df = self._add_volume_features(df)
        
        # 2. Alpha 因子
        if self.use_alpha:
            df = self._add_alpha_features(df)
        
        # 3. 截面特征（相对强弱）
        if benchmark_df is not None:
            df = self._add_relative_strength(df, benchmark_df)
        
        # 4. 统计特征
        df = self._add_statistical_features(df)
        
        # 5. 时间特征
        df = self._add_time_features(df)
        
        # 6. 清洗数据
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        return df
    
    def _add_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """趋势特征：均线系统、MACD、趋势强度"""
        # 均线系统
        for window in [5, 10, 20, 60]:
            df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
            # 均线乖离率
            df[f'bias_{window}'] = (df['close'] - df[f'ma_{window}']) / df[f'ma_{window}']
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        df['macd_momentum'] = df['macd'].diff()
        
        # 趋势强度
        df['trend_strength'] = self._calculate_trend_strength(df, self.lookback)
        
        return df
    
    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """动量特征：RSI、ROC、KDJ"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_slope'] = df['rsi'].diff()
        
        # ROC（变动率）
        df['roc_10'] = df['close'].pct_change(periods=10)
        df['roc_20'] = df['close'].pct_change(periods=20)
        
        # KDJ
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        df['kdj_k'] = rsv.ewm(com=2).mean()
        df['kdj_d'] = df['kdj_k'].ewm(com=2).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        # 价格动量
        df['price_momentum_5d'] = df['close'].pct_change(5)
        df['price_momentum_10d'] = df['close'].pct_change(10)
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """波动率特征：历史波动率、ATR"""
        # 历史波动率
        df['hist_vol_20'] = df['close'].pct_change().rolling(window=20).std()
        df['hist_vol_60'] = df['close'].pct_change().rolling(window=60).std()
        
        # ATR（平均真实波幅）
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr_14'] = true_range.rolling(window=14).mean()
        
        # 归一化 ATR
        df['natr_14'] = df['atr_14'] / df['close']
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """成交量特征：量比、量价相关性"""
        # 量比
        df['vol_ma_5'] = df['volume'].rolling(window=5).mean()
        df['vol_ma_20'] = df['volume'].rolling(window=20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma_5']
        
        # 量价相关性
        df['pv_corr_10'] = df['close'].rolling(window=10).corr(df['volume'])
        df['pv_corr_20'] = df['close'].rolling(window=20).corr(df['volume'])
        
        # 成交额比率
        if 'amount' in df.columns:
            df['amount_ma_5'] = df['amount'].rolling(window=5).mean()
            df['amount_ratio'] = df['amount'] / df['amount_ma_5']
        
        return df
    
    def _add_alpha_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Alpha 因子：订单不平衡、买卖盘比率"""
        # 订单不平衡（如果有 Level-2 数据）
        if 'bid1_vol' in df.columns and 'ask1_vol' in df.columns:
            df['order_imbalance'] = (df['bid1_vol'] - df['ask1_vol']) / (df['bid1_vol'] + df['ask1_vol'])
            df['bid_ask_ratio'] = df['bid1_vol'] / df['ask1_vol']
        else:
            # 用成交量变化率替代
            df['order_imbalance'] = np.nan
            df['bid_ask_ratio'] = np.nan
        
        # 板块排名
        if 'sector' in df.columns:
            df['rank_in_sector'] = df.groupby('sector')['close'].transform(
                lambda x: x.pct_change().rank(pct=True)
            )
        
        return df
    
    def _add_relative_strength(self, df: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
        """截面特征：相对强弱、RSRS"""
        # 确保索引对齐
        common_idx = df.index.intersection(benchmark.index)
        if len(common_idx) < 10:
            return df
        
        stock_ret = df.loc[common_idx, 'close'].pct_change()
        bench_ret = benchmark.loc[common_idx, 'close'].pct_change()
        
        # 相对收益率
        df.loc[common_idx, 'rel_return'] = stock_ret - bench_ret
        
        # 相对波动率
        stock_vol = stock_ret.rolling(20).std()
        bench_vol = bench_ret.rolling(20).std()
        df.loc[common_idx, 'rel_volatility'] = stock_vol / bench_vol
        
        # RSRS（阻力支撑相对强度）
        df.loc[common_idx, 'price_rel_index'] = df.loc[common_idx, 'close'] / benchmark.loc[common_idx, 'close']
        
        return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """统计特征：滞后收益率"""
        # 滞后收益率
        for lag in [1, 2, 3, 5, 10]:
            df[f'ret_lag_{lag}'] = df['close'].pct_change(periods=lag).shift(1)
        
        return df
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """时间特征：星期几、月初月末"""
        # 获取日期
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
        elif hasattr(df.index, 'to_pydatetime'):
            dates = pd.to_datetime(df.index)
        else:
            dates = pd.to_datetime(df.index)
        
        # 星期几（0=周一, 4=周五）
        df['weekday'] = dates.dayofweek
        
        # 月初/月末
        df['is_month_start'] = dates.is_month_start.astype(int)
        df['is_month_end'] = dates.is_month_end.astype(int)
        
        return df
    
    def calculate_multi_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算多目标标签
        
        Args:
            df: 包含 OHLCV 的数据
            
        Returns:
            添加了多目标的 DataFrame
        """
        df = df.copy()
        
        # 1. 1日涨跌幅
        df['target_next_return'] = df['close'].pct_change().shift(-1) * 100
        
        # 2. 5日涨跌幅（趋势）
        df['target_5d_return'] = (df['close'].shift(-5) / df['close'] - 1) * 100
        
        # 3. 5日波动率（风险）
        df['target_5d_volatility'] = df['close'].pct_change().shift(-5).rolling(5).std() * 100
        
        # 4. 涨停概率
        df['target_limit_up'] = (df['close'].shift(-1) / df['close'] - 1) > 0.095
        df['target_limit_up'] = df['target_limit_up'].astype(int)
        
        # 5. 跌停概率
        df['target_limit_down'] = (df['close'].shift(-1) / df['close'] - 1) < -0.095
        df['target_limit_down'] = df['target_limit_down'].astype(int)
        
        return df
    
    def get_feature_list(self) -> List[str]:
        """
        获取特征列表
        
        Returns:
            特征名称列表
        """
        if self.feature_list is None:
            # 完整特征列表
            self.feature_list = [
                # 趋势特征
                'ma_5', 'ma_10', 'ma_20', 'ma_60',
                'bias_5', 'bias_10', 'bias_20', 'bias_60',
                'macd', 'macd_signal', 'macd_hist', 'macd_momentum',
                'trend_strength',
                # 动量特征
                'rsi', 'rsi_slope',
                'roc_10', 'roc_20',
                'kdj_k', 'kdj_d', 'kdj_j',
                'price_momentum_5d', 'price_momentum_10d',
                # 波动率特征
                'hist_vol_20', 'hist_vol_60',
                'atr_14', 'natr_14',
                # 成交量特征
                'vol_ratio', 'pv_corr_10', 'pv_corr_20', 'amount_ratio',
                # Alpha 因子
                'order_imbalance', 'bid_ask_ratio', 'rank_in_sector',
                # 截面特征
                'rel_return', 'rel_volatility', 'price_rel_index',
                # 统计特征
                'ret_lag_1', 'ret_lag_2', 'ret_lag_3', 'ret_lag_5', 'ret_lag_10',
                # 时间特征
                'weekday', 'is_month_start', 'is_month_end'
            ]
        
        return self.feature_list
    
    def _calculate_trend_strength(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算趋势强度（价格斜率）"""
        def calc_slope(window):
            if len(window) < 2:
                return 0
            x = np.arange(len(window))
            y = window.values
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

    # 计算特征
    df_features = engineer.transform(df)
    
    # 计算多目标
    df_targets = engineer.calculate_multi_targets(df_features)
    
    print(f"原始数据: {df.shape}")
    print(f"特征数据: {df_features.shape}")
    print(f"特征数量: {len(engineer.get_feature_list())}")
    print(f"\n特征列表: {engineer.get_feature_list()}")