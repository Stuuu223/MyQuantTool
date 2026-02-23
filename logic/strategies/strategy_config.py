#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战法参数配置 (Strategy Config)

V16.0 - 拾荒网实战版
来源: 10huang.cn (半路/龙头/竞价/低吸/创业板弹性)

Author: MyQuantTool Team
Date: 2026-02-16
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class StrategyConfig:
    """
    MyQuantTool 战法参数配置 (V16.0 - 拾荒网实战版)

    核心原则：
    1. 所有参数基于拾荒网实战经验
    2. 参数动态可调，适应不同市场环境
    3. 与现有TradeGatekeeper兼容
    """

    # ========================================
    # 1. 半路战法 (Halfway Board)
    # ========================================
    # 核心逻辑: 昨日烂板 + 今日弱转强 + 10点前快速上板
    # 拾荒网原文: "板后半路，最佳买点不是随便的 5%，而是昨日烂板 + 今日弱转强"
    HALFWAY_ENABLED: bool = True
    HALFWAY_TIME_LIMIT: str = "10:00:00"   # 超过10点不打半路 (风险不可控)
    HALFWAY_MIN_PCT: float = 0.05          # 最低涨幅 5%
    HALFWAY_MAX_PCT: float = 0.085         # 最高涨幅 8.5% (9%以上直接扫板，不半路)
    HALFWAY_VOL_RATIO_MIN: float = 1.5     # 量比 > 1.5 (必须放量)
    HALFWAY_ABOVE_AVG_PRICE: bool = True   # 必须在分时均价线上方

    # ========================================
    # 2. 龙头战法 (Leader)
    # ========================================
    # 核心逻辑: 连板高度 + 板块地位 + 情绪周期
    # 拾荒网原文: "情绪风向标，不只是看连板数，更要看溢价"
    LEADER_ENABLED: bool = True
    LEADER_MIN_DAYS: int = 3               # 3板定龙头 (拾荒网定义)
    LEADER_EMOTION_CYCLE: bool = True      # 开启情绪周期过滤器 (高标晋级才开仓)
    LEADER_SECTOR_RANK: int = 1            # 只要板块第一名 (杂毛不要)
    LEADER_PREMIUM_OPEN: float = 0.02      # 必须高开 > 2% (弱转强确认)

    # ========================================
    # 3. 集合竞价战法 (Call Auction)
    # ========================================
    # 核心逻辑: 1进2接力 + 爆量抢筹
    # 拾荒网原文: "竞价涨幅：0% ~ 7% (太高容易被砸，太低说明弱)"
    AUCTION_ENABLED: bool = True
    AUCTION_GAP_MIN: float = 0.00          # 允许平开
    AUCTION_GAP_MAX: float = 0.07          # 不要超过 7% (太高容易兑现)
    AUCTION_TURNOVER_MIN: float = 0.04     # 换手率 > 4% (低位)
    AUCTION_TURNOVER_MAX: float = 0.15     # 换手率 < 15% (高位需谨慎)
    AUCTION_VOLUME_RATIO: float = 2.0      # 竞价爆量 (相对于昨日同时段)

    # ========================================
    # 4. 低吸战法 (Low Suck)
    # ========================================
    # 核心逻辑: 核心资产 + 急跌承接 + 大单护盘
    # 拾荒网原文: "承接力，不是跌了就买，而是看谁在买"
    LOW_SUCK_ENABLED: bool = True
    LOW_SUCK_THRESHOLD: float = -0.03      # 触发观察点
    LOW_SUCK_RESISTANCE: bool = True       # 开启承接力检测 (必须有大单护盘)
    LOW_SUCK_VOL_SHRINK: bool = True       # 下跌必须缩量 (恐慌盘杀出，但主力未逃)

    # ========================================
    # 5. 创业板弹性战法 (GEM Elasticity)
    # ========================================
    # 核心逻辑: 20cm 溢价 + 首板挖掘
    # 拾荒网原文: "弹性，指 20cm 涨停板的溢价能力。创业板首板的赚钱效应远超主板连板"
    GEM_ELASTICITY_ENABLED: bool = True
    GEM_MIN_PCT_TRIGGER: float = 0.15      # 涨幅 > 15% 触发"扫板监控"
    GEM_VOL_RATIO_MIN: float = 1.8         # 量比 > 1.8 (更苛刻，要求主动攻击)
    GEM_1TO2_OPEN_PCT_MIN: float = 0.02    # 1进2 竞价最低高开 2%
    GEM_1TO2_OPEN_PCT_MAX: float = 0.06    # 1进2 竞价最高高开 6% (太高容易兑现)

    # ========================================
    # 6. 情绪引擎 (Sentiment Engine)
    # ========================================
    # 核心逻辑: 情绪风向标 + 周期判断
    # 拾荒网原文: "情绪周期四阶段：启动 -> 发酵 -> 高潮 -> 退潮"
    SENTIMENT_ENABLED: bool = True
    SENTIMENT_MIN_SCORE: float = 40.0      # 情绪分 < 40 (退潮期) 管住手
    SENTIMENT_MAX_SCORE: float = 70.0      # 情绪分 > 70 (高潮期) 全仓出击
    SENTIMENT_CYCLE_STAGE: str = "UNKNOWN"  # 当前周期阶段 (启动/发酵/高潮/退潮)

    # ========================================
    # 7. 市值分层 (Market Cap Tier)
    # ========================================
    # 与现有equity_data_accessor兼容
    MARKET_CAP_TIER_SMALL: float = 50.0    # 小市值 < 50亿
    MARKET_CAP_TIER_MID: float = 100.0     # 中市值 < 100亿
    MARKET_CAP_TIER_LARGE: float = 1000.0  # 大市值 < 1000亿

    # ========================================
    # 8. 资金流阈值 (Capital Flow Thresholds)
    # ========================================
    # 核心原则：资金流应该是相对于成交额的比例，而不是绝对值
    # 拾荒网观点：主力资金流入应该占总成交额的30%以上
    # 现有TradeGatekeeper：5000万作为资金流预警阈值
    #
    # 动态阈值（基于成交额比例）：
    # - 小市值（<50亿）：主力流入 > 成交额的30%
    # - 中市值（50-100亿）：主力流入 > 成交额的25%
    # - 大市值（>100亿）：主力流入 > 成交额的20%
    #
    # 兼容性：提供绝对值阈值作为降级方案
    CAPITAL_FLOW_RATIO_BULLISH: float = 0.30     # 主力净流入占比 > 30% (看多)
    CAPITAL_FLOW_RATIO_BEARISH: float = -0.20    # 主力净流入占比 < -20% (看空)
    CAPITAL_FLOW_RATIO_STRONG_BULLISH: float = 0.40  # 主力净流入占比 > 40% (强看多)
    CAPITAL_FLOW_ABSOLUTE_BULLISH: float = 50000000  # 降级方案：主力净流入 > 5000万 (看多)
    CAPITAL_FLOW_ABSOLUTE_BEARISH: float = -50000000 # 降级方案：主力净流出 < -5000万 (看空)

    # ========================================
    # 9. 风控阈值 (Risk Control)
    # ========================================
    # 与现有TradeGatekeeper兼容
    RISK_MAX_LOSS_PCT: float = -0.03       # 单只股票最大亏损 -3%
    RISK_MAX_POSITION_PCT: float = 0.3     # 单只股票最大仓位 30%
    RISK_MAX_TOTAL_POSITION: float = 0.8   # 总仓位上限 80%

    # ========================================
    # 10. 技术指标阈值 (Technical Indicators)
    # ========================================
    # ATR (Average True Range) 动态波动率
    ATR_ENABLED: bool = True
    ATR_PERIOD: int = 14                   # ATR周期 14天
    ATR_MULTIPLIER: float = 1.5            # ATR倍数 (用于动态止损)
    ATR_STOP_LOSS_PCT: float = 0.05       # 基于ATR的动态止损

    # ========================================
    # 兼容性配置 (Compatibility)
    # ========================================
    # 确保与现有系统兼容
    COMPATIBLE_WITH_TRADE_GATEKEEPER: bool = True
    COMPATIBLE_WITH_FULL_MARKET_SCANNER: bool = True
    COMPATIBLE_WITH_SCENARIO_CLASSIFIER: bool = True

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