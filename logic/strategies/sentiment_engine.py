#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪引擎 (Sentiment Engine)

V16.0 - 市场情绪实时计算与分析
基于现有MarketSentimentAnalyzer进行扩展

核心功能：
1. 实时计算市场情绪分（0-100）
2. 情绪周期判断（启动/发酵/高潮/退潮）
3. 情绪开关功能（情绪差时禁止开仓）
4. 情绪趋势预警（情绪转向预警）

Author: MyQuantTool Team
Date: 2026-02-16
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
# 导入现有的情绪分析器（适配现有架构）
from logic.utils.algo_sentiment import MarketSentimentAnalyzer
from logic.data_providers.data_adapter import DataAdapter
from logic.strategies.strategy_config import StrategyConfig, get_strategy_config
import logging

logger = logging.getLogger(__name__)


class SentimentEngine:
    """
    市场情绪引擎（V16.0）

    核心指标（拾荒网实战经验）：
    1. 连板晋级率 - 昨日涨停股今日继续涨停的比例
    2. 炸板率 - 涨停打开的比例
    3. 大面率 - 昨日涨停今日跌停的比例（核按钮）
    4. 涨停封单强度 - 封单金额/成交额
    5. 情绪周期阶段 - 启动/发酵/高潮/退潮

    职责：
    - 实时计算市场情绪分（0-100）
    - 判断当前情绪周期阶段
    - 提供情绪开关功能（风控）
    - 预警情绪转向
    """

    def __init__(self, data_adapter: DataAdapter = None, config: StrategyConfig = None):
        """
        初始化情绪引擎

        Args:
            data_adapter: 数据适配器
            config: 策略配置
        """
        self.adapter = data_adapter or DataAdapter()
        self.cfg = config or get_strategy_config()

        # 当前情绪分（0-100）
        self.current_sentiment_score = 50.0  # 初始分 50 (中性)

        # 情绪历史（用于趋势分析）
        self.sentiment_history = []
        self.max_history_length = 20

        # 情绪周期阶段
        self.cycle_stage = "UNKNOWN"  # 启动/发酵/高潮/退潮

        # 情绪预警标志
        self.sentiment_warning = False

        # 初始化现有的情绪分析器（适配现有架构）
        self.legacy_analyzer = MarketSentimentAnalyzer()

        logger.info("✅ 情绪引擎初始化成功")

    def calculate_sentiment(self) -> float:
        """
        计算今日市场情绪分（0-100）

        拾荒网实战逻辑：
        - 基准分 50（中性）
        - 晋级率贡献：每 10% +5分
        - 核按钮惩罚：每 10% -10分（亏钱效应更敏感）
        - 封板强度贡献：每 10% +3分

        Returns:
            float: 情绪分 (0-100)
        """
        # 1. 获取昨日涨停池的表现
        limit_up_pool = self.adapter.get_yesterday_limit_up_pool()
        if not limit_up_pool:
            logger.warning("无法获取昨日涨停池，情绪分维持中性")
            return 50.0

        # 2. 获取实时数据
        df = self.adapter.get_realtime_snapshot(limit_up_pool)
        if df.empty:
            logger.warning("无法获取实时数据，情绪分维持中性")
            return 50.0

        # 3. 计算核心指标
        # 晋级率：涨幅 > 9.5% 视为晋级（涨停）
        promoted_count = len(df[df['pct_chg'] > 0.095])
        total_count = len(df)
        promotion_rate = promoted_count / total_count if total_count > 0 else 0

        # 大面率：跌幅 > 5% 视为大面（核按钮）
        nuclear_count = len(df[df['pct_chg'] < -0.05])
        nuclear_rate = nuclear_count / total_count if total_count > 0 else 0

        # 炸板率：涨幅在 5% - 9.5% 之间（涨停打开）
        broken_count = len(df[(df['pct_chg'] > 0.05) & (df['pct_chg'] <= 0.095)])
        broken_rate = broken_count / total_count if total_count > 0 else 0

        # 4. 综合评分算法（拾荒网逻辑）
        # 基准分 50
        # 晋级率贡献: 每 10% +5分
        # 核按钮惩罚: 每 10% -10分 (亏钱效应更敏感)
        # 炸板率惩罚: 每 10% -3分
        score = 50 + (promotion_rate * 50) - (nuclear_rate * 100) - (broken_rate * 30)

        # 5. 限制在 0-100 之间
        self.current_sentiment_score = max(0, min(100, score))

        # 6. 更新情绪历史
        self._update_sentiment_history()

        # 7. 判断情绪周期阶段
        self._determine_cycle_stage()

        logger.info(f"当前市场情绪分: {self.current_sentiment_score:.1f} "
                   f"(晋级率: {promotion_rate:.1%}, 核按钮率: {nuclear_rate:.1%}, "
                   f"炸板率: {broken_rate:.1%}, 周期: {self.cycle_stage})")

        return self.current_sentiment_score

    def _update_sentiment_history(self):
        """
        更新情绪历史记录
        """
        self.sentiment_history.append({
            'time': datetime.now(),
            'score': self.current_sentiment_score,
            'stage': self.cycle_stage
        })

        # 限制历史长度
        if len(self.sentiment_history) > self.max_history_length:
            self.sentiment_history.pop(0)

    def _determine_cycle_stage(self):
        """
        判断情绪周期阶段（拾荒网四阶段模型）

        阶段定义：
        - 启动期：情绪分 40-60，涨停数量增加
        - 发酵期：情绪分 60-80，连板高度提升
        - 高潮期：情绪分 > 80，赚钱效应最强
        - 退潮期：情绪分 < 40，核按钮增多
        """
        if self.current_sentiment_score < 40:
            self.cycle_stage = "退潮期"
        elif self.current_sentiment_score < 60:
            self.cycle_stage = "启动期"
        elif self.current_sentiment_score < 80:
            self.cycle_stage = "发酵期"
        else:
            self.cycle_stage = "高潮期"

        # 更新配置
        self.cfg.SENTIMENT_CYCLE_STAGE = self.cycle_stage

    def check_sentiment_warning(self) -> bool:
        """
        检查情绪预警（情绪转向预警）

        拾荒网逻辑：
        - 情绪连续下降 3 天 → 预警
        - 情绪从 >70 降到 <50 → 预警

        Returns:
            bool: 是否触发预警
        """
        if len(self.sentiment_history) < 3:
            return False

        # 检查情绪是否连续下降
        recent_scores = [h['score'] for h in self.sentiment_history[-3:]]
        is_declining = recent_scores[0] > recent_scores[1] > recent_scores[2]

        # 检查情绪是否从高潮期快速下降
        if len(self.sentiment_history) >= 5:
            recent_5 = [h['score'] for h in self.sentiment_history[-5:]]
            if max(recent_5) > 70 and min(recent_5) < 50:
                self.sentiment_warning = True
                logger.warning("⚠️ 情绪预警：情绪从高潮期快速下降")
                return True

        if is_declining:
            self.sentiment_warning = True
            logger.warning("⚠️ 情绪预警：情绪连续下降")
            return True

        self.sentiment_warning = False
        return False

    def can_open_position(self) -> Tuple[bool, str]:
        """
        风控开关：情绪太差禁止开仓（空仓模式）

        拾荒网心法：情绪分 < 40 (退潮期) 管住手

        Returns:
            Tuple[bool, str]: (是否允许开仓, 原因)
        """
        if not self.cfg.SENTIMENT_ENABLED:
            return True, "情绪引擎未启用"

        if self.current_sentiment_score < self.cfg.SENTIMENT_MIN_SCORE:
            reason = f"⛔ 市场情绪极差 ({self.current_sentiment_score:.1f})，{self.cycle_stage}，触发空仓防守模式！"
            logger.warning(reason)
            return False, reason

        if self.sentiment_warning:
            reason = f"⚠️ 情绪预警生效 ({self.current_sentiment_score:.1f})，建议减仓或空仓"
            logger.warning(reason)
            return False, reason

        return True, "情绪正常，允许开仓"

    def get_strategy_recommendation(self) -> Dict:
        """
        根据情绪提供策略建议（拾荒网实战经验）

        Returns:
            Dict: 策略建议
        """
        recommendation = {
            'sentiment_score': self.current_sentiment_score,
            'cycle_stage': self.cycle_stage,
            'warning': self.sentiment_warning,
            'can_open_position': False,
            'reason': '',
            'recommended_strategies': [],
        }

        # 判断是否允许开仓
        can_open, reason = self.can_open_position()
        recommendation['can_open_position'] = can_open
        recommendation['reason'] = reason

        # 根据情绪阶段推荐策略
        if self.cycle_stage == "启动期":
            recommendation['recommended_strategies'] = ['halfway', 'gem_elasticity']
            recommendation['detail'] = "启动期：试错首板（创业板首板），半路战法"
        elif self.cycle_stage == "发酵期":
            recommendation['recommended_strategies'] = ['leader', 'auction']
            recommendation['detail'] = "发酵期：接力龙头（连板战法），集合竞价1进2"
        elif self.cycle_stage == "高潮期":
            recommendation['recommended_strategies'] = ['leader', 'gem_elasticity']
            recommendation['detail'] = "高潮期：全仓出击，龙头和创业板弹性"
        else:  # 退潮期
            recommendation['recommended_strategies'] = ['low_suck']
            recommendation['detail'] = "退潮期：管住手！只做反核或空仓"

        return recommendation

    def get_sentiment_details(self) -> Dict:
        """
        获取情绪详细信息（用于展示）

        Returns:
            Dict: 情绪详细信息
        """
        return {
            'current_score': self.current_sentiment_score,
            'cycle_stage': self.cycle_stage,
            'warning': self.sentiment_warning,
            'history': self.sentiment_history,
            'recommendation': self.get_strategy_recommendation(),
        }

    def reset(self):
        """
        重置情绪引擎（用于测试或新交易日）
        """
        self.current_sentiment_score = 50.0
        self.sentiment_history = []
        self.cycle_stage = "UNKNOWN"
        self.sentiment_warning = False
        logger.info("✅ 情绪引擎已重置")


# 全局情绪引擎实例（单例模式）
_global_engine: SentimentEngine = None


def get_sentiment_engine(data_adapter: DataAdapter = None, config: StrategyConfig = None) -> SentimentEngine:
    """
    获取全局情绪引擎（单例模式）

    Args:
        data_adapter: 数据适配器
        config: 策略配置

    Returns:
        SentimentEngine: 全局情绪引擎实例
    """
    global _global_engine
    if _global_engine is None:
        _global_engine = SentimentEngine(data_adapter=data_adapter, config=config)
    return _global_engine