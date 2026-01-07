"""KlinePatternRecognizer - K线序列网络形态识别

Version: 1.0.0
Feature: 经典K线形态识别 (Head-Shoulder, Double-Bottom, 三角形, 旁脞等)

核心职责:
- Head-Shoulder (头肩肇)
- Double-Bottom / Double-Top (双底 / 双顶)
- 三角形 (Ascending/Descending/Symmetric Triangle)
- 旁脞形 (Flag Pattern)
- 企嚴穀上需 (Pennant Pattern)
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class KlinePatternRecognizer:
    """K线形态识别器
    
    设计原则:
    - 基于 企财财霑流 的物理年鲁 算法
    - 经典形态 分析
    - 上涨 / 下跌 信号 推辺
    - 形态笔 分数凳传
    """

    def __init__(self):
        self.recognized_patterns = []
        logger.info("📈 KlinePatternRecognizer initialized")

    def recognize_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Recognize all patterns in K-line data
        
        Args:
            df: DataFrame with columns [high, low, close, volume]
            
        Returns:
            List of recognized patterns with scores
        """
        try:
            patterns = []
            
            # Check each pattern type
            if self._check_head_shoulder(df):
                patterns.append({
                    'pattern': 'Head-Shoulder',
                    'signal': '看跌',
                    'score': 0.85,
                    'position': 'Top',
                    'target_drop': '3-5%'
                })
            
            if self._check_double_bottom(df):
                patterns.append({
                    'pattern': 'Double-Bottom',
                    'signal': '看涨',
                    'score': 0.82,
                    'position': 'Bottom',
                    'target_rise': '5-8%'
                })
            
            if self._check_triangle(df):
                patterns.append({
                    'pattern': 'Triangle (Ascending)',
                    'signal': '看涨',
                    'score': 0.75,
                    'position': 'Consolidation',
                    'breakout_level': 'Upper Resistance'
                })
            
            if self._check_flag_pattern(df):
                patterns.append({
                    'pattern': 'Flag Pattern',
                    'signal': 'Continuation',
                    'score': 0.78,
                    'position': 'Continuation',
                    'breakout_direction': 'Previous Trend'
                })
            
            logger.info(f"✅ Recognized {len(patterns)} patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"❌ recognize_patterns failed: {e}")
            return []

    def _check_head_shoulder(self, df: pd.DataFrame) -> bool:
        """Check for Head-Shoulder pattern
        
        头肩肇特疵:
        - 左肩 (Left Shoulder)
        - 上涨 → 下跌
        - 头 (Head) 上涨 → 下跌
        - 右肩 (Right Shoulder) 上涨 → 下跌
        - 右肩高度 < 头高度
        """
        try:
            if len(df) < 15:
                return False
            
            high = df['high'].values
            low = df['low'].values
            
            # Find peaks and valleys
            peaks = []
            for i in range(1, len(high) - 1):
                if high[i] > high[i-1] and high[i] > high[i+1]:
                    peaks.append(i)
            
            # Look for 3 peaks pattern
            if len(peaks) >= 3:
                p1, p2, p3 = peaks[-3:]
                
                # Check pattern
                if high[p1] < high[p2] > high[p3] and high[p1] ≈ high[p3]:
                    logger.info("💀 Head-Shoulder pattern detected")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ _check_head_shoulder failed: {e}")
            return False

    def _check_double_bottom(self, df: pd.DataFrame) -> bool:
        """Check for Double-Bottom pattern
        
        双底特疵:
        - 下跌 → 上涨 → 下跌
        - 两个低点 接近 (差异 < 5%)
        - 中间高点是两个低点 高点
        """
        try:
            if len(df) < 15:
                return False
            
            low = df['low'].values
            high = df['high'].values
            
            # Find valleys
            valleys = []
            for i in range(1, len(low) - 1):
                if low[i] < low[i-1] and low[i] < low[i+1]:
                    valleys.append(i)
            
            # Look for 2 valleys pattern
            if len(valleys) >= 2:
                v1, v2 = valleys[-2:]
                
                # Check similarity
                diff_pct = abs(low[v1] - low[v2]) / max(low[v1], low[v2])
                
                if diff_pct < 0.05 and v2 - v1 > 5:
                    logger.info("💙 Double-Bottom pattern detected")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ _check_double_bottom failed: {e}")
            return False

    def _check_triangle(self, df: pd.DataFrame) -> bool:
        """Check for Triangle pattern (Ascending)
        
        上升三角形 特疵:
        - 高点逐次下降
        - 低点逐次上涨
        - 两条趋势线会聚
        """
        try:
            if len(df) < 10:
                return False
            
            high = df['high'].values[-20:]
            low = df['low'].values[-20:]
            
            # Calculate trend lines
            x = np.arange(len(high))
            
            # High trend (should be descending)
            high_trend = np.polyfit(x, high, 1)[0]
            
            # Low trend (should be ascending)
            low_trend = np.polyfit(x, low, 1)[0]
            
            # Ascending triangle: high descending, low ascending
            if high_trend < -0.01 and low_trend > 0.01:
                logger.info("📈 Triangle pattern detected")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ _check_triangle failed: {e}")
            return False

    def _check_flag_pattern(self, df: pd.DataFrame) -> bool:
        """Check for Flag pattern
        
        旁脞形 特疵:
        - 需要滑会騧騧的上涨
        - 旁脞：一段沇整维持
        - 维持 中低于之前上涨趋势
        """
        try:
            if len(df) < 15:
                return False
            
            close = df['close'].values[-15:]
            volume = df['volume'].values[-15:] if 'volume' in df.columns else np.ones(15)
            
            # Check for consolidation pattern
            recent_std = np.std(close[-5:])
            earlier_std = np.std(close[:5])
            
            # Volume should decrease during flag
            recent_vol = np.mean(volume[-5:])
            earlier_vol = np.mean(volume[:5])
            
            if recent_std < earlier_std * 0.5 and recent_vol < earlier_vol:
                logger.info("🏁 Flag pattern detected")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ _check_flag_pattern failed: {e}")
            return False

    def get_pattern_signal(self, pattern_type: str) -> Tuple[str, float]:
        """Get trading signal for specific pattern
        
        Args:
            pattern_type: Type of pattern
            
        Returns:
            (signal: '看涨'/'看跌', score: 0~1)
        """
        pattern_signals = {
            'Head-Shoulder': ('看跌', 0.85),
            'Double-Bottom': ('看涨', 0.82),
            'Triangle': ('看涨', 0.75),
            'Flag': ('Continuation', 0.78),
            'Pennant': ('Continuation', 0.72)
        }
        
        return pattern_signals.get(pattern_type, ('中性', 0.5))


def get_kline_pattern_recognizer() -> KlinePatternRecognizer:
    """Get or create KlinePatternRecognizer instance"""
    return KlinePatternRecognizer()
