#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战法参数配置 (Strategy Config) - 统一配置管理

V17.0 - 统一配置管理版
从strategy_params.json加载参数，确保所有组件使用同一套配置

Author: MyQuantTool Team
Date: 2026-02-24
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class StrategyConfig:
    """
    MyQuantTool 战法参数配置 (V17.0 - 统一配置管理版)

    核心原则：
    1. 所有参数从strategy_params.json统一加载
    2. 提供fallback机制，确保系统鲁棒性
    3. 与现有系统完全兼容
    """

    # 从strategy_params.json加载的参数
    # 半路战法参数
    HALFWAY_ENABLED: bool = True
    HALFWAY_VOL_RATIO_PERCENTILE: float = 0.88  # 量比分位数阈值
    HALFWAY_PRICE_MOMENTUM_PERCENTILE: float = 0.85  # 涨幅分位数阈值
    HALFWAY_TIME_LIMIT: str = "10:00:00"
    HALFWAY_MIN_PCT: float = 0.05
    HALFWAY_MAX_PCT: float = 0.085
    HALFWAY_ABOVE_AVG_PRICE: bool = True

    # 龙头战法参数
    LEADER_ENABLED: bool = True
    LEADER_CHANGE_PCT_PERCENTILE: float = 0.92
    LEADER_VOLUME_RATIO_PERCENTILE: float = 0.90
    LEADER_MIN_DAYS: int = 3
    LEADER_EMOTION_CYCLE: bool = True
    LEADER_SECTOR_RANK: int = 1
    LEADER_PREMIUM_OPEN: float = 0.02

    # 真资金攻击策略参数
    TRUE_ATTACK_ENABLED: bool = True
    TRUE_ATTACK_INFLOW_RATIO_PERCENTILE: float = 0.99
    TRUE_ATTACK_PRICE_STRENGTH_PERCENTILE: float = 0.95

    # 诱多检测参数
    TRAP_ENABLED: bool = True
    TRAP_VOLUME_SPIKE_PERCENTILE: float = 0.95

    # 竞价战法参数
    AUCTION_ENABLED: bool = True
    AUCTION_GAP_MIN: float = 0.00
    AUCTION_GAP_MAX: float = 0.07
    AUCTION_TURNOVER_MIN: float = 0.04
    AUCTION_TURNOVER_MAX: float = 0.15
    AUCTION_VOLUME_RATIO: float = 2.0

    # 低吸战法参数
    LOW_SUCK_ENABLED: bool = True
    LOW_SUCK_THRESHOLD: float = -0.03
    LOW_SUCK_RESISTANCE: bool = True
    LOW_SUCK_VOL_SHRINK: bool = True

    # 创业板弹性战法参数
    GEM_ELASTICITY_ENABLED: bool = True
    GEM_MIN_PCT_TRIGGER: float = 0.15
    GEM_VOL_RATIO_MIN: float = 1.8
    GEM_1TO2_OPEN_PCT_MIN: float = 0.02
    GEM_1TO2_OPEN_PCT_MAX: float = 0.06

    # 情绪引擎参数
    SENTIMENT_ENABLED: bool = True
    SENTIMENT_MIN_SCORE: float = 40.0
    SENTIMENT_MAX_SCORE: float = 70.0
    SENTIMENT_CYCLE_STAGE: str = "UNKNOWN"

    # 市值分层参数
    MARKET_CAP_TIER_SMALL: float = 50.0
    MARKET_CAP_TIER_MID: float = 100.0
    MARKET_CAP_TIER_LARGE: float = 1000.0

    # 资金流阈值参数
    CAPITAL_FLOW_RATIO_BULLISH: float = 0.30
    CAPITAL_FLOW_RATIO_BEARISH: float = -0.20
    CAPITAL_FLOW_RATIO_STRONG_BULLISH: float = 0.40
    CAPITAL_FLOW_ABSOLUTE_BULLISH: float = 50000000
    CAPITAL_FLOW_ABSOLUTE_BEARISH: float = -50000000

    # 风控参数
    RISK_MAX_LOSS_PCT: float = -0.03
    RISK_MAX_POSITION_PCT: float = 0.3
    RISK_MAX_TOTAL_POSITION: float = 0.8
    RISK_MAX_POSITIONS: int = 3
    RISK_DOMINANCE_RATIO_THRESHOLD: float = 1.5

    # 技术指标参数
    ATR_ENABLED: bool = True
    ATR_PERIOD: int = 14
    ATR_MULTIPLIER: float = 1.5
    ATR_STOP_LOSS_PCT: float = 0.05

    # Portfolio层参数
    PORTFOLIO_MAX_POSITIONS: int = 3
    PORTFOLIO_DOMINANCE_RATIO_THRESHOLD: float = 1.5
    PORTFOLIO_MAX_DRAWDOWN_PCT: float = 0.03
    PORTFOLIO_MIN_ADVANTAGE_SCORE: float = 0.70

    # 兼容性配置
    COMPATIBLE_WITH_TRADE_GATEKEEPER: bool = True
    COMPATIBLE_WITH_FULL_MARKET_SCANNER: bool = True
    COMPATIBLE_WITH_SCENARIO_CLASSIFIER: bool = True

    def __post_init__(self):
        """初始化后从strategy_params.json加载配置"""
        self.load_from_config_file()

    def load_from_config_file(self):
        """从strategy_params.json加载配置参数"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "strategy_params.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    params = json.load(f)

                # 加载halfway参数
                halfway = params.get('halfway', {})
                self.HALFWAY_VOL_RATIO_PERCENTILE = halfway.get('volume_surge_percentile', 0.88)
                self.HALFWAY_PRICE_MOMENTUM_PERCENTILE = halfway.get('price_momentum_percentile', 0.85)
                self.HALFWAY_ENABLED = halfway.get('use_percentile', True)

                # 加载leader参数
                leader = params.get('leader', {})
                self.LEADER_CHANGE_PCT_PERCENTILE = leader.get('change_pct_percentile', 0.92)
                self.LEADER_VOLUME_RATIO_PERCENTILE = leader.get('volume_ratio_percentile', 0.90)
                self.LEADER_ENABLED = leader.get('use_percentile', True)

                # 加载true_attack参数
                true_attack = params.get('true_attack', {})
                self.TRUE_ATTACK_INFLOW_RATIO_PERCENTILE = true_attack.get('inflow_ratio_percentile', 0.99)
                self.TRUE_ATTACK_PRICE_STRENGTH_PERCENTILE = true_attack.get('price_strength_percentile', 0.95)
                self.TRUE_ATTACK_ENABLED = true_attack.get('use_percentile', True)

                # 加载trap参数
                trap = params.get('trap', {})
                self.TRAP_VOLUME_SPIKE_PERCENTILE = trap.get('volume_spike_percentile', 0.95)
                self.TRAP_ENABLED = trap.get('use_percentile', True)

                # 加载portfolio参数
                portfolio = params.get('portfolio', {})
                self.PORTFOLIO_MAX_POSITIONS = portfolio.get('max_positions', 3)
                self.PORTFOLIO_DOMINANCE_RATIO_THRESHOLD = portfolio.get('dominance_ratio_threshold', 1.5)
                self.PORTFOLIO_MAX_DRAWDOWN_PCT = portfolio.get('max_drawdown_pct', 0.03)
                self.PORTFOLIO_MIN_ADVANTAGE_SCORE = portfolio.get('min_advantage_score', 0.70)

        except Exception as e:
            print(f"⚠️ 从strategy_params.json加载配置失败，使用默认值: {e}")
            # 使用默认值，系统仍可正常运行
            pass

    def get_config_dict(self) -> Dict:
        """
        获取配置字典（用于兼容现有系统）

        Returns:
            dict: 配置字典
        """
        return {
            'halfway': {
                'enabled': self.HALFWAY_ENABLED,
                'time_limit': self.HALFWAY_TIME_LIMIT,
                'min_pct': self.HALFWAY_MIN_PCT,
                'max_pct': self.HALFWAY_MAX_PCT,
                'vol_ratio_min': self.HALFWAY_VOL_RATIO_MIN,
                'above_avg_price': self.HALFWAY_ABOVE_AVG_PRICE,
            },
            'leader': {
                'enabled': self.LEADER_ENABLED,
                'min_days': self.LEADER_MIN_DAYS,
                'emotion_cycle': self.LEADER_EMOTION_CYCLE,
                'sector_rank': self.LEADER_SECTOR_RANK,
                'premium_open': self.LEADER_PREMIUM_OPEN,
            },
            'auction': {
                'enabled': self.AUCTION_ENABLED,
                'gap_min': self.AUCTION_GAP_MIN,
                'gap_max': self.AUCTION_GAP_MAX,
                'turnover_min': self.AUCTION_TURNOVER_MIN,
                'turnover_max': self.AUCTION_TURNOVER_MAX,
                'volume_ratio': self.AUCTION_VOLUME_RATIO,
            },
            'low_suck': {
                'enabled': self.LOW_SUCK_ENABLED,
                'threshold': self.LOW_SUCK_THRESHOLD,
                'resistance': self.LOW_SUCK_RESISTANCE,
                'vol_shrink': self.LOW_SUCK_VOL_SHRINK,
            },
            'gem_elasticity': {
                'enabled': self.GEM_ELASTICITY_ENABLED,
                'min_pct_trigger': self.GEM_MIN_PCT_TRIGGER,
                'vol_ratio_min': self.GEM_VOL_RATIO_MIN,
                '1to2_open_pct_min': self.GEM_1TO2_OPEN_PCT_MIN,
                '1to2_open_pct_max': self.GEM_1TO2_OPEN_PCT_MAX,
            },
            'sentiment': {
                'enabled': self.SENTIMENT_ENABLED,
                'min_score': self.SENTIMENT_MIN_SCORE,
                'max_score': self.SENTIMENT_MAX_SCORE,
                'cycle_stage': self.SENTIMENT_CYCLE_STAGE,
            },
            'market_cap': {
                'tier_small': self.MARKET_CAP_TIER_SMALL,
                'tier_mid': self.MARKET_CAP_TIER_MID,
                'tier_large': self.MARKET_CAP_TIER_LARGE,
            },
            'capital_flow': {
                'ratio_bullish': self.CAPITAL_FLOW_RATIO_BULLISH,
                'ratio_bearish': self.CAPITAL_FLOW_RATIO_BEARISH,
                'ratio_strong_bullish': self.CAPITAL_FLOW_RATIO_STRONG_BULLISH,
                'absolute_bullish': self.CAPITAL_FLOW_ABSOLUTE_BULLISH,
                'absolute_bearish': self.CAPITAL_FLOW_ABSOLUTE_BEARISH,
            },
            'risk': {
                'max_loss_pct': self.RISK_MAX_LOSS_PCT,
                'max_position_pct': self.RISK_MAX_POSITION_PCT,
                'max_total_position': self.RISK_MAX_TOTAL_POSITION,
            },
            'atr': {
                'enabled': self.ATR_ENABLED,
                'period': self.ATR_PERIOD,
                'multiplier': self.ATR_MULTIPLIER,
                'stop_loss_pct': self.ATR_STOP_LOSS_PCT,
            },
        }

    def validate(self) -> bool:
        """
        验证配置参数的合理性

        Returns:
            bool: 配置是否有效
        """
        # 验证半路战法
        if self.HALFWAY_MIN_PCT >= self.HALFWAY_MAX_PCT:
            raise ValueError("HALFWAY_MIN_PCT 必须 < HALFWAY_MAX_PCT")

        # 验证竞价战法
        if self.AUCTION_GAP_MIN >= self.AUCTION_GAP_MAX:
            raise ValueError("AUCTION_GAP_MIN 必须 < AUCTION_GAP_MAX")

        # 验证情绪引擎
        if self.SENTIMENT_MIN_SCORE >= self.SENTIMENT_MAX_SCORE:
            raise ValueError("SENTIMENT_MIN_SCORE 必须 < SENTIMENT_MAX_SCORE")

        # 验证市值分层
        if not (0 < self.MARKET_CAP_TIER_SMALL < self.MARKET_CAP_TIER_MID < self.MARKET_CAP_TIER_LARGE):
            raise ValueError("市值分层参数必须递增")

        return True


# 全局配置实例（单例模式）
_global_config: StrategyConfig = None


def get_strategy_config() -> StrategyConfig:
    """
    获取全局策略配置（单例模式）

    Returns:
        StrategyConfig: 全局配置实例
    """
    global _global_config
    if _global_config is None:
        _global_config = StrategyConfig()
        _global_config.validate()
    return _global_config


def set_strategy_config(config: StrategyConfig) -> None:
    """
    设置全局策略配置

    Args:
        config: 新的配置实例
    """
    global _global_config
    config.validate()
    _global_config = config