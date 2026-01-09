"""
半路战法模块：识别个股在上涨过程中的回调买点

参考文献：
- https://zhuanlan.zhihu.com/p/524017080
- https://xueqiu.com/8189550582/174332015
- http://www.10huang.cn/zhangting/54879.html

核心逻辑：
1. 股价突破关键位置后回调
2. 回调到支撑位附近
3. 成交量萎缩后重新放量
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import talib


@dataclass
class MidwaySignal:
    """半路战法信号"""
    stock_code: str
    stock_name: str
    signal_date: str
    entry_price: float
    stop_loss: float
    target_price: float
    signal_strength: float  # 信号强度 0-1
    risk_level: str  # 风险等级: '低', '中', '高'
    reasons: List[str]  # 信号理由
    confidence: float  # 置信度 0-1


class MidwayStrategyAnalyzer:
    """半路战法分析器"""

    def __init__(self, lookback_days: int = 30):
        """
        初始化半路战法分析器

        Args:
            lookback_days: 回看天数
        """
        self.lookback_days = lookback_days

    def analyze_midway_opportunity(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[MidwaySignal]:
        """
        分析半路战法机会

        Args:
            df: 股票历史数据 (包含 open, high, low, close, volume)
            stock_code: 股票代码
            stock_name: 股票名称

        Returns:
            MidwaySignal: 半路战法信号，如果没有信号则返回None
        """
        if len(df) < self.lookback_days:
            return None

        # 计算技术指标
        df = self._calculate_indicators(df)

        # 检查是否满足半路战法条件
        signal = self._check_midway_conditions(df, stock_code, stock_name)

        return signal

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        # 确保数据类型为float64（talib要求）
        df = df.copy()
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # 移动平均线
        df['ma5'] = talib.SMA(df['close'].values, timeperiod=5)
        df['ma10'] = talib.SMA(df['close'].values, timeperiod=10)
        df['ma20'] = talib.SMA(df['close'].values, timeperiod=20)

        # 布林带
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
            df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )

        # RSI
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)

        # MACD
        df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(
            df['close'].values, fastperiod=12, slowperiod=26, signalperiod=9
        )

        # 成交量指标
        df['volume_ma5'] = talib.SMA(df['volume'].values, timeperiod=5)
        df['volume_ratio'] = df['volume'] / df['volume_ma5']

        # 波动率
        df['volatility'] = df['close'].rolling(window=10).std()

        return df

    def _check_midway_conditions(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[MidwaySignal]:
        """检查半路战法条件"""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        prev2 = df.iloc[-3] if len(df) >= 3 else prev

        # 条件1: 近期有明显上涨（突破关键位置）
        recent_high = df['high'].tail(10).max()
        current_close = latest['close']
        price_rally = (current_close - recent_high) / recent_high

        # 条件2: 当前处于回调状态（从高点回调一定幅度，但未破位）
        recent_peak = df['close'].tail(5).max()
        pullback_ratio = (recent_peak - current_close) / recent_peak

        # 条件3: 回调到支撑位附近（如MA10, MA20, 布林带下轨等）
        support_nearby = self._check_support_resistance(latest, current_close)

        # 条件4: 成交量萎缩后重新放量
        volume_condition = self._check_volume_pattern(df)

        # 条件5: RSI在合理区间（不超买不超卖）
        rsi_condition = 30 <= latest['rsi'] <= 60

        # 条件6: MACD有底背离或金叉迹象
        macd_condition = self._check_macd_condition(df)

        # 综合判断
        if (price_rally > 0.05 and  # 近期上涨超过5%
            0.02 < pullback_ratio < 0.15 and  # 回调幅度适中
            support_nearby and
            volume_condition and
            rsi_condition and
            macd_condition):

            # 计算入场点、止损点和目标价
            entry_price = current_close
            stop_loss = min(latest['low'], latest['ma10'], latest['bb_lower'])  # 取最低的支撑位
            target_price = current_close * 1.08  # 暂定8%目标

            # 计算信号强度
            signal_strength = self._calculate_signal_strength(
                pullback_ratio, volume_condition, rsi_condition, macd_condition
            )

            # 风险等级
            risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)

            # 信号理由
            reasons = self._generate_signal_reasons(df)

            return MidwaySignal(
                stock_code=stock_code,
                stock_name=stock_name,
                signal_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
                entry_price=entry_price,
                stop_loss=stop_loss,
                target_price=target_price,
                signal_strength=signal_strength,
                risk_level=risk_level,
                reasons=reasons,
                confidence=min(signal_strength, 1.0)
            )

        return None

    def _check_support_resistance(self, latest: pd.Series, current_price: float) -> bool:
        """检查是否接近支撑位"""
        # 检查是否接近均线支撑
        ma_support = abs(current_price - latest['ma10']) / latest['ma10'] < 0.03 or \
                     abs(current_price - latest['ma20']) / latest['ma20'] < 0.03

        # 检查是否接近布林带下轨支撑
        bb_support = abs(current_price - latest['bb_lower']) / latest['bb_lower'] < 0.02

        return ma_support or bb_support

    def _check_volume_pattern(self, df: pd.DataFrame) -> bool:
        """检查成交量模式（萎缩后放量）"""
        recent_volumes = df['volume'].tail(5).values
        if len(recent_volumes) < 5:
            return False

        # 前几日成交量萎缩，最新一日放量
        volume_shrink = recent_volumes[-3] < recent_volumes[-4] and recent_volumes[-2] < recent_volumes[-4]
        volume_expand = recent_volumes[-1] > recent_volumes[-2] * 1.2 and recent_volumes[-1] > df['volume_ma5'].iloc[-1]

        return volume_shrink and volume_expand

    def _check_macd_condition(self, df: pd.DataFrame) -> bool:
        """检查MACD条件"""
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        # MACD金叉或接近金叉
        golden_cross = (latest['macdsignal'] > latest['macd']) and (prev['macdsignal'] <= prev['macd'])
        # 或者MACD柱状图由负转正
        hist_positive = latest['macdhist'] > 0 and prev['macdhist'] <= 0

        return golden_cross or hist_positive

    def _calculate_signal_strength(self, pullback_ratio: float, volume_condition: bool, rsi_condition: bool, macd_condition: bool) -> float:
        """计算信号强度"""
        strength = 0.5  # 基础强度

        # 回调幅度适中加分
        if 0.05 <= pullback_ratio <= 0.10:
            strength += 0.2
        elif 0.02 <= pullback_ratio <= 0.15:
            strength += 0.1

        # 各条件满足加分
        if volume_condition:
            strength += 0.1
        if rsi_condition:
            strength += 0.1
        if macd_condition:
            strength += 0.1

        return min(strength, 1.0)

    def _determine_risk_level(self, signal_strength: float, stop_loss: float, entry_price: float) -> str:
        """确定风险等级"""
        risk_ratio = abs(entry_price - stop_loss) / entry_price

        if signal_strength >= 0.8 and risk_ratio <= 0.05:
            return '低'
        elif signal_strength >= 0.6 and risk_ratio <= 0.08:
            return '中'
        else:
            return '高'

    def _generate_signal_reasons(self, df: pd.DataFrame) -> List[str]:
        """生成信号理由"""
        latest = df.iloc[-1]
        reasons = []

        # 根据当前指标状态生成理由
        if latest['rsi'] < 40:
            reasons.append("RSI处于相对低位，下跌动能减弱")
        if latest['macdhist'] > 0:
            reasons.append("MACD柱状图转正，上涨动能增强")
        if latest['volume_ratio'] > 1.5:
            reasons.append("成交量明显放大，资金关注度提升")
        if abs(latest['close'] - latest['ma10']) / latest['ma10'] < 0.02:
            reasons.append("价格接近MA10支撑")

        return reasons or ["技术面出现阶段性企稳迹象"]

    def scan_midway_opportunities(self, stock_data: Dict[str, pd.DataFrame], stock_info: Dict[str, str]) -> List[MidwaySignal]:
        """
        扫描所有股票的半路战法机会

        Args:
            stock_data: 股票数据字典 {股票代码: DataFrame}
            stock_info: 股票信息字典 {股票代码: 股票名称}

        Returns:
            List[MidwaySignal]: 半路战法信号列表
        """
        signals = []

        for code, df in stock_data.items():
            if code in stock_info:
                signal = self.analyze_midway_opportunity(df, code, stock_info[code])
                if signal:
                    signals.append(signal)

        # 按信号强度排序
        signals.sort(key=lambda x: x.signal_strength, reverse=True)

        return signals