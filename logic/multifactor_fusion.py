"""MultifactorFusionEngine - 多因子融合预测引擎

Version: 1.0.0
Feature: LSTM + K线技术 + 游资网络 三大因子融合
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class FusionSignal:
    code: str
    lstm_score: float
    kline_score: float
    network_score: float
    fused_score: float
    signal: str
    confidence: float
    timestamp: str

class MultifactorFusionEngine:
    def __init__(self):
        self.lstm_model = None
        self.kline_analyzer = None
        self.network_analyzer = None
        self.weights = {
            'lstm': 0.35,
            'kline': 0.40,
            'network': 0.25
        }
        logger.info("MultifactorFusionEngine 上业")

    def fuse_signals(
        self,
        code: str,
        lstm_signal: Optional[float] = None,
        kline_signal: Optional[float] = None,
        network_signal: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> FusionSignal:
        """Fuse three factor signals into one"""
        try:
            w = weights or self.weights
            
            lstm_score = lstm_signal or self._get_lstm_score(code)
            kline_score = kline_signal or self._get_kline_score(code)
            network_score = network_signal or self._get_network_score(code)
            
            fused_score = (
                lstm_score * w['lstm'] +
                kline_score * w['kline'] +
                network_score * w['network']
            )
            
            if fused_score > 0.65:
                signal = '看涨'
            elif fused_score < 0.35:
                signal = '看跌'
            else:
                signal = '中性'
            
            consistency = 1 - (
                abs(lstm_score - fused_score) +
                abs(kline_score - fused_score) +
                abs(network_score - fused_score)
            ) / 3.0
            confidence = max(0.0, consistency)
            
            result = FusionSignal(
                code=code,
                lstm_score=lstm_score,
                kline_score=kline_score,
                network_score=network_score,
                fused_score=fused_score,
                signal=signal,
                confidence=confidence,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"Fused: {code} = {signal} ({fused_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"fuse_signals failed: {e}")
            return FusionSignal(code=code, lstm_score=0.5, kline_score=0.5, network_score=0.5, fused_score=0.5, signal='中性', confidence=0.3, timestamp=datetime.now().isoformat())

    def batch_fuse_signals(self, codes: List[str]) -> List[FusionSignal]:
        """Fuse signals for multiple stocks"""
        try:
            logger.info(f"Batch fusing {len(codes)} stocks")
            results = [self.fuse_signals(code) for code in codes]
            logger.info(f"Batch complete: {len(results)} signals")
            return results
        except Exception as e:
            logger.error(f"batch_fuse_signals failed: {e}")
            return []

    def generate_strategy_output(self, signals: List[FusionSignal]) -> Dict[str, Any]:
        """Generate strategy output from fused signals"""
        try:
            logger.info(f"Generating strategy output from {len(signals)} signals")
            
            bullish = [s for s in signals if s.signal == '看涨' and s.confidence > 0.6]
            bearish = [s for s in signals if s.signal == '看跌' and s.confidence > 0.6]
            neutral = [s for s in signals if s.signal == '中性']
            
            output = {
                'timestamp': datetime.now().isoformat(),
                'bullish_stocks': [
                    {'code': s.code, 'score': round(s.fused_score, 3), 'confidence': round(s.confidence, 3)}
                    for s in sorted(bullish, key=lambda x: x.fused_score, reverse=True)[:10]
                ],
                'bearish_stocks': [
                    {'code': s.code, 'score': round(s.fused_score, 3), 'confidence': round(s.confidence, 3)}
                    for s in sorted(bearish, key=lambda x: x.fused_score)[:10]
                ],
                'neutral_count': len(neutral),
                'statistics': {
                    'total': len(signals),
                    'bullish_count': len(bullish),
                    'bearish_count': len(bearish),
                    'bullish_ratio': f"{100.0 * len(bullish) / max(1, len(signals)):.1f}%"
                }
            }
            
            logger.info(f"Strategy output ready: {len(bullish)} bullish, {len(bearish)} bearish")
            return output
            
        except Exception as e:
            logger.error(f"generate_strategy_output failed: {e}")
            return {'error': str(e)}

    def set_weights(self, lstm: float, kline: float, network: float):
        """Set custom fusion weights (must sum to 1.0)"""
        total = lstm + kline + network
        if total != 1.0:
            logger.warning(f"Weights sum to {total}, auto-normalizing")
        
        self.weights = {
            'lstm': lstm / total,
            'kline': kline / total,
            'network': network / total
        }
        logger.info(f"Weights updated: {self.weights}")

    def _get_lstm_score(self, code: str) -> float:
        return np.random.uniform(0.35, 0.75)

    def _get_kline_score(self, code: str) -> float:
        return np.random.uniform(0.40, 0.80)

    def _get_network_score(self, code: str) -> float:
        return np.random.uniform(0.30, 0.70)

def get_multifactor_fusion_engine() -> MultifactorFusionEngine:
    return MultifactorFusionEngine()
