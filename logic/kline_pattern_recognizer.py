"""
K线形态识别器 - 5种经典形态识别
功能：
- 头肩顶/底 (Head-Shoulder)
- 双重顶/底 (Double Top/Bottom)
- 三角形整理 (Triangle)
- 旗形整理 (Flag)
- 楔形整理 (Wedge)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class PatternType(Enum):
    """形态类型枚举"""
    HEAD_SHOULDER_TOP = "头肩顶"
    HEAD_SHOULDER_BOTTOM = "头肩底"
    DOUBLE_TOP = "双重顶"
    DOUBLE_BOTTOM = "双重底"
    ASCENDING_TRIANGLE = "上升三角形"
    DESCENDING_TRIANGLE = "下降三角形"
    SYMMETRICAL_TRIANGLE = "对称三角形"
    BULL_FLAG = "看涨旗形"
    BEAR_FLAG = "看跌旗形"
    RISING_WEDGE = "上升楔形"
    FALLING_WEDGE = "下降楔形"


class SignalType(Enum):
    """信号类型"""
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"


@dataclass
class PatternResult:
    """形态识别结果"""
    pattern_type: PatternType
    signal: SignalType
    confidence: float  # 置信度 0-1
    start_date: str
    end_date: str
    target_price: Optional[float]  # 目标价位
    stop_loss: Optional[float]  # 止损价位
    description: str


class KlinePatternRecognizer:
    """K线形态识别器"""
    
    def __init__(self, min_confidence: float = 0.6):
        """
        Args:
            min_confidence: 最小置信度阈值
        """
        self.min_confidence = min_confidence
    
    def recognize_patterns(
        self,
        df: pd.DataFrame,
        lookback: int = 60
    ) -> List[PatternResult]:
        """
        识别所有K线形态
        
        Args:
            df: K线数据，需要包含 open, high, low, close, volume 列
            lookback: 回溯天数
        
        Returns:
            识别到的形态列表
        """
        patterns = []
        
        # 确保数据格式正确
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        df = df.reset_index(drop=True)
        
        if len(df) < lookback:
            return patterns
        
        # 识别各种形态
        patterns.extend(self._detect_head_shoulder(df, lookback))
        patterns.extend(self._detect_double_top_bottom(df, lookback))
        patterns.extend(self._detect_triangle(df, lookback))
        patterns.extend(self._detect_flag(df, lookback))
        patterns.extend(self._detect_wedge(df, lookback))
        
        # 按置信度排序
        patterns.sort(key=lambda x: x.confidence, reverse=True)
        
        # 过滤低置信度结果
        patterns = [p for p in patterns if p.confidence >= self.min_confidence]
        
        return patterns
    
    def _detect_head_shoulder(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> List[PatternResult]:
        """检测头肩顶/底形态"""
        patterns = []
        
        # 使用局部极值点检测
        peaks, valleys = self._find_extremes(df, window=5)
        
        # 检测头肩顶 (M型)
        if len(peaks) >= 3:
            for i in range(len(peaks) - 2):
                left_shoulder = peaks[i]
                head = peaks[i + 1]
                right_shoulder = peaks[i + 2]
                
                # 验证头肩顶特征
                if (head['price'] > left_shoulder['price'] and 
                    head['price'] > right_shoulder['price'] and
                    abs(left_shoulder['price'] - right_shoulder['price']) / head['price'] < 0.05):
                    
                    confidence = self._calculate_head_shoulder_confidence(
                        df, left_shoulder, head, right_shoulder, 'top'
                    )
                    
                    if confidence >= self.min_confidence:
                        patterns.append(PatternResult(
                            pattern_type=PatternType.HEAD_SHOULDER_TOP,
                            signal=SignalType.SELL,
                            confidence=confidence,
                            start_date=df.iloc[left_shoulder['index']]['close'].name if hasattr(df.iloc[left_shoulder['index']]['close'], 'name') else str(left_shoulder['index']),
                            end_date=df.iloc[right_shoulder['index']]['close'].name if hasattr(df.iloc[right_shoulder['index']]['close'], 'name') else str(right_shoulder['index']),
                            target_price=head['price'] * 0.95,  # 目标价位
                            stop_loss=head['price'] * 1.02,  # 止损价位
                            description=f"头肩顶形态，头部价格 {head['price']:.2f}"
                        ))
        
        # 检测头肩底 (W型)
        if len(valleys) >= 3:
            for i in range(len(valleys) - 2):
                left_shoulder = valleys[i]
                head = valleys[i + 1]
                right_shoulder = valleys[i + 2]
                
                # 验证头肩底特征
                if (head['price'] < left_shoulder['price'] and 
                    head['price'] < right_shoulder['price'] and
                    abs(left_shoulder['price'] - right_shoulder['price']) / head['price'] < 0.05):
                    
                    confidence = self._calculate_head_shoulder_confidence(
                        df, left_shoulder, head, right_shoulder, 'bottom'
                    )
                    
                    if confidence >= self.min_confidence:
                        patterns.append(PatternResult(
                            pattern_type=PatternType.HEAD_SHOULDER_BOTTOM,
                            signal=SignalType.BUY,
                            confidence=confidence,
                            start_date=df.iloc[left_shoulder['index']]['close'].name if hasattr(df.iloc[left_shoulder['index']]['close'], 'name') else str(left_shoulder['index']),
                            end_date=df.iloc[right_shoulder['index']]['close'].name if hasattr(df.iloc[right_shoulder['index']]['close'], 'name') else str(right_shoulder['index']),
                            target_price=head['price'] * 1.05,
                            stop_loss=head['price'] * 0.98,
                            description=f"头肩底形态，头部价格 {head['price']:.2f}"
                        ))
        
        return patterns
    
    def _detect_double_top_bottom(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> List[PatternResult]:
        """检测双重顶/底形态"""
        patterns = []
        
        peaks, valleys = self._find_extremes(df, window=5)
        
        # 检测双重顶
        if len(peaks) >= 2:
            for i in range(len(peaks) - 1):
                left_peak = peaks[i]
                right_peak = peaks[i + 1]
                
                # 两峰高度接近
                if abs(left_peak['price'] - right_peak['price']) / left_peak['price'] < 0.03:
                    # 中间有明显的回调
                    mid_price = df.iloc[left_peak['index']:right_peak['index']]['low'].min()
                    if mid_price < left_peak['price'] * 0.97:
                        confidence = 0.7 + (1 - abs(left_peak['price'] - right_peak['price']) / left_peak['price']) * 0.3
                        
                        patterns.append(PatternResult(
                            pattern_type=PatternType.DOUBLE_TOP,
                            signal=SignalType.SELL,
                            confidence=confidence,
                            start_date=df.iloc[left_peak['index']]['close'].name if hasattr(df.iloc[left_peak['index']]['close'], 'name') else str(left_peak['index']),
                            end_date=df.iloc[right_peak['index']]['close'].name if hasattr(df.iloc[right_peak['index']]['close'], 'name') else str(right_peak['index']),
                            target_price=mid_price,
                            stop_loss=left_peak['price'] * 1.02,
                            description=f"双重顶形态，两峰价格 {left_peak['price']:.2f}, {right_peak['price']:.2f}"
                        ))
        
        # 检测双重底
        if len(valleys) >= 2:
            for i in range(len(valleys) - 1):
                left_valley = valleys[i]
                right_valley = valleys[i + 1]
                
                # 两谷深度接近
                if abs(left_valley['price'] - right_valley['price']) / left_valley['price'] < 0.03:
                    # 中间有明显的反弹
                    mid_price = df.iloc[left_valley['index']:right_valley['index']]['high'].max()
                    if mid_price > left_valley['price'] * 1.03:
                        confidence = 0.7 + (1 - abs(left_valley['price'] - right_valley['price']) / left_valley['price']) * 0.3
                        
                        patterns.append(PatternResult(
                            pattern_type=PatternType.DOUBLE_BOTTOM,
                            signal=SignalType.BUY,
                            confidence=confidence,
                            start_date=df.iloc[left_valley['index']]['close'].name if hasattr(df.iloc[left_valley['index']]['close'], 'name') else str(left_valley['index']),
                            end_date=df.iloc[right_valley['index']]['close'].name if hasattr(df.iloc[right_valley['index']]['close'], 'name') else str(right_valley['index']),
                            target_price=mid_price,
                            stop_loss=left_valley['price'] * 0.98,
                            description=f"双重底形态，两谷价格 {left_valley['price']:.2f}, {right_valley['price']:.2f}"
                        ))
        
        return patterns
    
    def _detect_triangle(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> List[PatternResult]:
        """检测三角形整理形态"""
        patterns = []
        
        # 使用线性回归检测趋势线
        recent_data = df.tail(lookback)
        
        # 检测上升三角形
        upper_slope, upper_intercept = self._linear_fit(
            np.arange(len(recent_data)),
            recent_data['high'].values
        )
        lower_slope, lower_intercept = self._linear_fit(
            np.arange(len(recent_data)),
            recent_data['low'].values
        )
        
        # 上升三角形：上轨水平，下轨上升
        if abs(upper_slope) < 0.01 and lower_slope > 0.02:
            confidence = min(0.9, 0.6 + lower_slope * 10)
            patterns.append(PatternResult(
                pattern_type=PatternType.ASCENDING_TRIANGLE,
                signal=SignalType.BUY,
                confidence=confidence,
                start_date=str(recent_data.index[0]),
                end_date=str(recent_data.index[-1]),
                target_price=recent_data['high'].max() * 1.03,
                stop_loss=recent_data['low'].min() * 0.98,
                description=f"上升三角形，上轨斜率 {upper_slope:.4f}，下轨斜率 {lower_slope:.4f}"
            ))
        
        # 下降三角形：下轨水平，上轨下降
        elif abs(lower_slope) < 0.01 and upper_slope < -0.02:
            confidence = min(0.9, 0.6 + abs(upper_slope) * 10)
            patterns.append(PatternResult(
                pattern_type=PatternType.DESCENDING_TRIANGLE,
                signal=SignalType.SELL,
                confidence=confidence,
                start_date=str(recent_data.index[0]),
                end_date=str(recent_data.index[-1]),
                target_price=recent_data['low'].min() * 0.97,
                stop_loss=recent_data['high'].max() * 1.02,
                description=f"下降三角形，上轨斜率 {upper_slope:.4f}，下轨斜率 {lower_slope:.4f}"
            ))
        
        # 对称三角形：上下轨收敛
        elif upper_slope < -0.01 and lower_slope > 0.01:
            convergence_rate = abs(upper_slope - lower_slope)
            confidence = min(0.85, 0.5 + convergence_rate * 5)
            patterns.append(PatternResult(
                pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                signal=SignalType.HOLD,
                confidence=confidence,
                start_date=str(recent_data.index[0]),
                end_date=str(recent_data.index[-1]),
                target_price=None,
                stop_loss=None,
                description=f"对称三角形，收敛率 {convergence_rate:.4f}"
            ))
        
        return patterns
    
    def _detect_flag(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> List[PatternResult]:
        """检测旗形整理形态"""
        patterns = []
        
        recent_data = df.tail(lookback)
        
        # 检测看涨旗形：前期上涨，然后小幅回调
        if len(recent_data) >= 20:
            # 分为两部分：旗杆（前10天）和旗面（后10天）
            pole = recent_data.iloc[:10]
            flag = recent_data.iloc[10:]
            
            # 旗杆上涨
            pole_trend = (pole['close'].iloc[-1] - pole['close'].iloc[0]) / pole['close'].iloc[0]
            
            # 旗面小幅回调
            flag_trend = (flag['close'].iloc[-1] - flag['close'].iloc[0]) / flag['close'].iloc[0]
            
            if pole_trend > 0.05 and -0.03 < flag_trend < 0:
                confidence = min(0.85, 0.6 + pole_trend * 5)
                patterns.append(PatternResult(
                    pattern_type=PatternType.BULL_FLAG,
                    signal=SignalType.BUY,
                    confidence=confidence,
                    start_date=str(flag.index[0]),
                    end_date=str(flag.index[-1]),
                    target_price=pole['close'].iloc[-1] * 1.05,
                    stop_loss=flag['low'].min() * 0.98,
                    description=f"看涨旗形，旗杆上涨 {pole_trend:.2%}，旗面回调 {flag_trend:.2%}"
                ))
            
            # 检测看跌旗形
            elif pole_trend < -0.05 and 0 < flag_trend < 0.03:
                confidence = min(0.85, 0.6 + abs(pole_trend) * 5)
                patterns.append(PatternResult(
                    pattern_type=PatternType.BEAR_FLAG,
                    signal=SignalType.SELL,
                    confidence=confidence,
                    start_date=str(flag.index[0]),
                    end_date=str(flag.index[-1]),
                    target_price=pole['close'].iloc[-1] * 0.95,
                    stop_loss=flag['high'].max() * 1.02,
                    description=f"看跌旗形，旗杆下跌 {pole_trend:.2%}，旗面反弹 {flag_trend:.2%}"
                ))
        
        return patterns
    
    def _detect_wedge(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> List[PatternResult]:
        """检测楔形整理形态"""
        patterns = []
        
        recent_data = df.tail(lookback)
        
        # 使用线性回归检测趋势线
        upper_slope, _ = self._linear_fit(
            np.arange(len(recent_data)),
            recent_data['high'].values
        )
        lower_slope, _ = self._linear_fit(
            np.arange(len(recent_data)),
            recent_data['low'].values
        )
        
        # 上升楔形：上下轨都上升，但上轨斜率大于下轨
        if upper_slope > 0.02 and lower_slope > 0.01 and upper_slope > lower_slope:
            convergence_rate = upper_slope - lower_slope
            confidence = min(0.8, 0.5 + convergence_rate * 8)
            patterns.append(PatternResult(
                pattern_type=PatternType.RISING_WEDGE,
                signal=SignalType.SELL,
                confidence=confidence,
                start_date=str(recent_data.index[0]),
                end_date=str(recent_data.index[-1]),
                target_price=recent_data['low'].min() * 0.95,
                stop_loss=recent_data['high'].max() * 1.02,
                description=f"上升楔形，上轨斜率 {upper_slope:.4f}，下轨斜率 {lower_slope:.4f}"
            ))
        
        # 下降楔形：上下轨都下降，但下轨斜率绝对值大于上轨
        elif upper_slope < -0.01 and lower_slope < -0.02 and abs(lower_slope) > abs(upper_slope):
            convergence_rate = abs(lower_slope) - abs(upper_slope)
            confidence = min(0.8, 0.5 + convergence_rate * 8)
            patterns.append(PatternResult(
                pattern_type=PatternType.FALLING_WEDGE,
                signal=SignalType.BUY,
                confidence=confidence,
                start_date=str(recent_data.index[0]),
                end_date=str(recent_data.index[-1]),
                target_price=recent_data['high'].max() * 1.05,
                stop_loss=recent_data['low'].min() * 0.98,
                description=f"下降楔形，上轨斜率 {upper_slope:.4f}，下轨斜率 {lower_slope:.4f}"
            ))
        
        return patterns
    
    def _find_extremes(
        self,
        df: pd.DataFrame,
        window: int = 5
    ) -> Tuple[List[Dict], List[Dict]]:
        """查找局部极值点"""
        peaks = []
        valleys = []
        
        for i in range(window, len(df) - window):
            current_high = df.iloc[i]['high']
            current_low = df.iloc[i]['low']
            
            # 检测峰值
            is_peak = True
            for j in range(i - window, i + window + 1):
                if j != i and df.iloc[j]['high'] >= current_high:
                    is_peak = False
                    break
            
            if is_peak:
                peaks.append({
                    'index': i,
                    'price': current_high,
                    'date': df.index[i]
                })
            
            # 检测谷值
            is_valley = True
            for j in range(i - window, i + window + 1):
                if j != i and df.iloc[j]['low'] <= current_low:
                    is_valley = False
                    break
            
            if is_valley:
                valleys.append({
                    'index': i,
                    'price': current_low,
                    'date': df.index[i]
                })
        
        return peaks, valleys
    
    def _calculate_head_shoulder_confidence(
        self,
        df: pd.DataFrame,
        left_shoulder: Dict,
        head: Dict,
        right_shoulder: Dict,
        pattern_type: str
    ) -> float:
        """计算头肩形态的置信度"""
        confidence = 0.6
        
        # 检查成交量
        left_volume = df.iloc[left_shoulder['index']]['volume']
        head_volume = df.iloc[head['index']]['volume']
        right_volume = df.iloc[right_shoulder['index']]['volume']
        
        # 头肩顶：头部成交量应该小于左肩
        if pattern_type == 'top':
            if head_volume < left_volume:
                confidence += 0.1
            if right_volume < left_volume:
                confidence += 0.1
        
        # 头肩底：头部成交量应该大于左肩
        else:
            if head_volume > left_volume:
                confidence += 0.1
            if right_volume > left_volume:
                confidence += 0.1
        
        # 检查对称性
        left_head_distance = head['index'] - left_shoulder['index']
        right_head_distance = right_shoulder['index'] - head['index']
        if abs(left_head_distance - right_head_distance) / max(left_head_distance, right_head_distance) < 0.3:
            confidence += 0.1
        
        # 检查高度一致性
        if pattern_type == 'top':
            height_ratio = abs(left_shoulder['price'] - right_shoulder['price']) / head['price']
        else:
            height_ratio = abs(left_shoulder['price'] - right_shoulder['price']) / head['price']
        
        if height_ratio < 0.05:
            confidence += 0.1
        
        return min(confidence, 0.95)
    
    def _linear_fit(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> Tuple[float, float]:
        """线性回归拟合"""
        if len(x) < 2:
            return 0.0, 0.0
        
        # 使用最小二乘法
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x ** 2)
        
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0, 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        return slope, intercept


def get_kline_pattern_recognizer(min_confidence: float = 0.6) -> KlinePatternRecognizer:
    """
    获取K线形态识别器实例
    
    Args:
        min_confidence: 最小置信度阈值
    
    Returns:
        KlinePatternRecognizer实例
    """
    return KlinePatternRecognizer(min_confidence=min_confidence)