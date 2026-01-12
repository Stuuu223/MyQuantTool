"""
半路战法模块：识别个股在上涨过程中的回调买点

参考文献：
- https://zhuanlan.zhihu.com/p/524017080
- https://xueqiu.com/8189550582/174332015
- http://www.10huang.cn/zhangting/54879.html

四大核心模式：
1. 平台突破战法（胜率最高）
2. 上影线反包战法
3. 阴线反包战法
4. 涨停加一阳战法（乌云盖顶/空中加油）

核心逻辑：
- 逻辑面 > 情绪面 > 资金面 > 技术面
- 大盘 > 板块 > 个股
- 日线结构是大方向，分时是切入点
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
    signal_type: str  # 信号类型：平台突破、上影线反包、阴线反包、涨停加一阳
    entry_price: float
    stop_loss: float
    target_price: float
    signal_strength: float  # 信号强度 0-1
    risk_level: str  # 风险等级: '低', '中', '高'
    reasons: List[str]  # 信号理由
    confidence: float  # 置信度 0-1
    technical_indicators: Dict[str, float]  # 关键技术指标


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
        if len(df) < 20:  # 至少需要20天数据
            print(f"[{stock_code}] 数据不足: {len(df)} < 20")
            return None

        # 计算技术指标
        df = self._calculate_indicators(df)

        # 检查是否是衰竭形态（必须规避）
        if self._check_exhaustion_pattern(df):
            print(f"[{stock_code}] 衰竭形态，规避")
            return None

        # 检查四大核心模式
        signals = []

        # 1. 平台突破战法
        platform_signal = self._check_platform_breakout(df, stock_code, stock_name)
        if platform_signal:
            signals.append(platform_signal)

        # 2. 上影线反包战法
        shadow_signal = self._check_shadow_reversal(df, stock_code, stock_name)
        if shadow_signal:
            signals.append(shadow_signal)

        # 3. 阴线反包战法
        bearish_signal = self._check_bearish_reversal(df, stock_code, stock_name)
        if bearish_signal:
            signals.append(bearish_signal)

        # 4. 涨停加一阳战法
        limit_up_signal = self._check_limit_up_one_yang(df, stock_code, stock_name)
        if limit_up_signal:
            signals.append(limit_up_signal)

        # 选择评分最高的信号
        if signals:
            best_signal = max(signals, key=lambda x: x.signal_strength)
            return best_signal

        print(f"[{stock_code}] 未发现任何模式信号")
        return None

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        # 确保数据类型为float64（talib要求）
        df = df.copy()
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # 如果有date列但没有设置为索引，则设置为索引
        if 'date' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

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

        # 检查最新数据是否有NaN值
        latest = df.iloc[-1]
        nan_cols = [col for col in ['ma5', 'ma10', 'ma20', 'rsi', 'macd', 'volume_ratio'] if pd.isna(latest.get(col, None))]
        if nan_cols:
            print(f"[警告] {len(df)} 行数据中，最新行存在NaN值的列: {nan_cols}")

        return df

    def _check_exhaustion_pattern(self, df: pd.DataFrame) -> bool:
        """检查是否是衰竭形态（必须规避）"""
        if len(df) < 10:
            return False

        latest = df.iloc[-1]
        recent_high = df['high'].tail(10).max()

        # 检查是否创了近期新高但出现回落上影或放量阴线
        if latest['high'] >= recent_high:
            # 检查是否是上影线
            upper_shadow = latest['high'] - max(latest['open'], latest['close'])
            body = abs(latest['close'] - latest['open'])

            # 上影线远长于实体，且放量
            if upper_shadow > body * 2 and latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
                return True

            # 检查是否是放量阴线
            if latest['close'] < latest['open'] and latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
                return True

        return False

    def _check_platform_breakout(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[MidwaySignal]:
        """检查平台突破战法（胜率最高）"""
        if len(df) < 20:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 检查是否突破平台
        # 定义平台：最近5-10天价格在窄幅震荡
        recent_prices = df['close'].tail(10).values
        price_range = (recent_prices.max() - recent_prices.min()) / recent_prices.mean()

        # 价格震荡幅度小于3%，认为是平台
        if price_range > 0.03:
            print(f"[{stock_code}] 平台突破: 价格震荡幅度过大 {price_range*100:.1f}%")
            return None

        # 检查今天是否突破
        if latest['close'] <= recent_prices.max():
            print(f"[{stock_code}] 平台突破: 未突破平台高点 {latest['close']:.2f} <= {recent_prices.max():.2f}")
            return None

        # 检查成交量是否放大
        if latest['volume'] < df['volume_ma5'].iloc[-1] * 1.2:
            print(f"[{stock_code}] 平台突破: 成交量不足 {latest['volume']:.0f} < {df['volume_ma5'].iloc[-1]*1.2:.0f}")
            return None

        # 检查RSI是否合理
        if latest['rsi'] > 80:
            print(f"[{stock_code}] 平台突破: RSI过高 {latest['rsi']:.1f}")
            return None

        # 计算信号强度
        signal_strength = 0.6  # 基础分

        # 成交量越大，信号越强
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 2:
            signal_strength += 0.2
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.1

        # RSI在合理区间加分
        if 40 < latest['rsi'] < 70:
            signal_strength += 0.1

        # MACD配合加分
        if latest['macdhist'] > 0:
            signal_strength += 0.1

        signal_strength = min(signal_strength, 1.0)

        # 计算入场点、止损点和目标价
        entry_price = latest['close']
        stop_loss = recent_prices.min()  # 平台下沿
        target_price = entry_price * 1.10  # 10%目标

        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)

        reasons = [
            f"突破{10}天平台，平台震荡幅度{price_range*100:.1f}%",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
            f"RSI={latest['rsi']:.1f}，处于合理区间"
        ]

        print(f"[平台突破] {stock_code} - 信号强度: {signal_strength:.2f}")

        return MidwaySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            signal_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='平台突破',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            }
        )

    def _check_shadow_reversal(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[MidwaySignal]:
        """检查上影线反包战法"""
        if len(df) < 5:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 检查前一天是否是长上影线
        prev_upper_shadow = prev['high'] - max(prev['open'], prev['close'])
        prev_body = abs(prev['close'] - prev['open'])

        # 上影线长度大于实体2倍
        if prev_upper_shadow < prev_body * 2:
            return None

        # 检查今天是否反包（收盘价超过前一天的最高价）
        if latest['close'] <= prev['high']:
            return None

        # 检查成交量
        if latest['volume'] < df['volume_ma5'].iloc[-1]:
            return None

        # 检查RSI
        if latest['rsi'] > 75:
            return None

        # 计算信号强度
        signal_strength = 0.5  # 基础分

        # 上影线越长，信号越强
        if prev_upper_shadow > prev_body * 3:
            signal_strength += 0.15
        elif prev_upper_shadow > prev_body * 2:
            signal_strength += 0.1

        # 成交量放大加分
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.15
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.2:
            signal_strength += 0.1

        # RSI合理加分
        if 40 < latest['rsi'] < 70:
            signal_strength += 0.1

        # MACD配合加分
        if latest['macdhist'] > 0:
            signal_strength += 0.1

        signal_strength = min(signal_strength, 1.0)

        # 计算入场点、止损点和目标价
        entry_price = latest['close']
        stop_loss = prev['low']  # 前一天最低价
        target_price = entry_price * 1.10  # 10%目标

        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)

        reasons = [
            f"上影线反包，上影线长度{prev_upper_shadow:.2f}，实体{prev_body:.2f}",
            f"收盘价突破前高{prev['high']:.2f}",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍"
        ]

        print(f"[上影线反包] {stock_code} - 信号强度: {signal_strength:.2f}")

        return MidwaySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            signal_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='上影线反包',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            }
        )

    def _check_bearish_reversal(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[MidwaySignal]:
        """检查阴线反包战法"""
        if len(df) < 5:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 检查前一天是否是阴线
        if prev['close'] >= prev['open']:
            return None

        # 检查前一天是否缩量
        if prev['volume'] > df['volume_ma5'].iloc[-2] * 1.2:
            return None

        # 检查今天是否反包（收盘价超过前一天的开盘价）
        if latest['close'] <= prev['open']:
            return None

        # 检查今天是否放量
        if latest['volume'] < df['volume_ma5'].iloc[-1] * 1.2:
            return None

        # 检查RSI
        if latest['rsi'] > 75:
            return None

        # 计算信号强度
        signal_strength = 0.5  # 基础分

        # 前一天缩量越多，信号越强
        if prev['volume'] < df['volume_ma5'].iloc[-2] * 0.7:
            signal_strength += 0.15
        elif prev['volume'] < df['volume_ma5'].iloc[-2] * 0.9:
            signal_strength += 0.1

        # 今天放量越多，信号越强
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 2:
            signal_strength += 0.15
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.1

        # RSI合理加分
        if 35 < latest['rsi'] < 65:
            signal_strength += 0.1

        # MACD配合加分
        if latest['macdhist'] > 0:
            signal_strength += 0.1

        signal_strength = min(signal_strength, 1.0)

        # 计算入场点、止损点和目标价
        entry_price = latest['close']
        stop_loss = prev['low']  # 前一天最低价
        target_price = entry_price * 1.10  # 10%目标

        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)

        reasons = [
            f"阴线反包，前一天缩量下跌{abs(prev['close']-prev['open'])/prev['open']*100:.1f}%",
            f"今天放量反包，成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍",
            f"RSI={latest['rsi']:.1f}，处于合理区间"
        ]

        print(f"[阴线反包] {stock_code} - 信号强度: {signal_strength:.2f}")

        return MidwaySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            signal_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='阴线反包',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            }
        )

    def _check_limit_up_one_yang(self, df: pd.DataFrame, stock_code: str, stock_name: str) -> Optional[MidwaySignal]:
        """检查涨停加一阳战法（空中加油/乌云盖顶）"""
        if len(df) < 5:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) >= 3 else None

        # 检查前2天是否涨停（涨幅接近10%）
        if prev2 is None:
            return None

        prev2_change = (prev2['close'] - prev2['open']) / prev2['open']
        if prev2_change < 0.09:  # 涨幅小于9%，不算涨停
            return None

        # 检查前一天是否是上影线或小阳线
        prev_upper_shadow = prev['high'] - max(prev['open'], prev['close'])
        prev_body = abs(prev['close'] - prev['open'])

        # 前一天是上影线或小阳线（上涨但涨幅不大）
        if prev['close'] < prev['open']:  # 阴线也可以，但要是高开低走的假阴
            return None

        # 检查今天是否上涨
        if latest['close'] <= prev['close']:
            return None

        # 检查成交量
        if latest['volume'] < df['volume_ma5'].iloc[-1]:
            return None

        # 检查RSI
        if latest['rsi'] > 80:
            return None

        # 计算信号强度
        signal_strength = 0.5  # 基础分

        # 前一天上影线加分
        if prev_upper_shadow > prev_body:
            signal_strength += 0.1

        # 成交量放大加分
        if latest['volume'] > df['volume_ma5'].iloc[-1] * 1.5:
            signal_strength += 0.15
        elif latest['volume'] > df['volume_ma5'].iloc[-1] * 1.2:
            signal_strength += 0.1

        # RSI合理加分
        if 40 < latest['rsi'] < 70:
            signal_strength += 0.15
        elif 30 < latest['rsi'] <= 40:
            signal_strength += 0.1

        # MACD配合加分
        if latest['macdhist'] > 0:
            signal_strength += 0.1

        signal_strength = min(signal_strength, 1.0)

        # 计算入场点、止损点和目标价
        entry_price = latest['close']
        stop_loss = prev2['low']  # 涨停日的最低价
        target_price = entry_price * 1.12  # 12%目标（空中加油模式目标更高）

        risk_level = self._determine_risk_level(signal_strength, stop_loss, entry_price)

        reasons = [
            f"涨停加一阳，前日涨停{prev2_change*100:.1f}%",
            f"昨日调整后今日上涨{abs(latest['close']-prev['close'])/prev['close']*100:.1f}%",
            f"成交量放大{latest['volume']/df['volume_ma5'].iloc[-1]:.2f}倍"
        ]

        print(f"[涨停加一阳] {stock_code} - 信号强度: {signal_strength:.2f}")

        return MidwaySignal(
            stock_code=stock_code,
            stock_name=stock_name,
            signal_date=latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name),
            signal_type='涨停加一阳',
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength,
            risk_level=risk_level,
            reasons=reasons,
            confidence=signal_strength,
            technical_indicators={
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / df['volume_ma5'].iloc[-1],
                'macd_hist': latest['macdhist']
            }
        )

    def _determine_risk_level(self, signal_strength: float, stop_loss: float, entry_price: float) -> str:
        """确定风险等级"""
        risk_ratio = abs(entry_price - stop_loss) / entry_price

        if signal_strength >= 0.8 and risk_ratio <= 0.05:
            return '低'
        elif signal_strength >= 0.6 and risk_ratio <= 0.08:
            return '中'
        else:
            return '高'

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

        print(f"[扫描统计] 开始扫描 {len(stock_data)} 只股票...")

        for code, df in stock_data.items():
            if code in stock_info:
                try:
                    signal = self.analyze_midway_opportunity(df, code, stock_info[code])
                    if signal:
                        signals.append(signal)
                        print(f"[发现信号] {code} - 信号强度: {signal.signal_strength:.2f}")
                except Exception as e:
                    print(f"[错误] 分析股票 {code} 时出错: {e}")
                    continue

        # 按信号强度排序
        signals.sort(key=lambda x: x.signal_strength, reverse=True)

        print(f"[扫描统计] 共扫描 {len(stock_data)} 只股票，发现 {len(signals)} 个半路战法信号")

        return signals