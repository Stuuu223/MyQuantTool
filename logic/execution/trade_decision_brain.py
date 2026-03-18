# -*- coding: utf-8 -*-
"""
交易决策大脑 - 单吊模式 (路线A: 里氏震级相对分位数决策版)

【设计哲学 - 里氏震级原则】
score 的绝对值无意义，因为量纲随市场状态浮动（可能是 200，也可能是 200,000）。
真正有意义的是：今天这只票是不是今天所有上榜票里的"地震异常点"？

解决方案：不用固定门槛，改用当前帧榜单的动态分位数。
  - 榜首 score >= p90(当前榜单) AND >= 1.5 × median(当前榜单)
  → 才认为是"真正的异动"，触发入场

【单吊约束（硬红线）】
- 任何时刻最多持有 1 只股票
- 持仓期间不允许换仓（必须先平仓才能开新仓）
- 资金 100% 集中

Author: CTO Research Lab
Date: 2026-03-16
Version: V2.0 (路线A - 里氏震级相对分位数决策)
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
import logging
import statistics

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    """决策结果数据结构"""
    action: str              # 'BUY' | 'SELL' | 'HOLD' | 'WATCH'
    stock_code: str = ""     # BUY时有效
    price: float = 0.0       # 建议价格
    reason: str = ""         # 决策原因（用于战报）
    score: float = 0.0       # 触发分数
    trigger_type: str = ""   # 触发类型
    # 【路线A新增】分位数上下文，用于战报审计
    p90_threshold: float = 0.0    # 当帧p90门槛
    median_score: float = 0.0     # 当帧中位分数
    relative_rank: float = 0.0    # 榜首在榜单中的百分位（0~1）


class TradeDecisionBrain:
    """
    交易决策大脑 - 单吊模式 (路线A: 里氏震级相对分位数决策版)

    【核心变更 vs V1.0】
    旧版：entry_score_threshold = 65.0（固定值，因量纲爆炸完全失效）
    新版：不依赖任何固定分数门槛，改用当前帧榜单的动态分位数
         → 无论 score 是 200 还是 200,000，决策逻辑永远有效
    """

    def __init__(self, config: dict = None):
        """
        初始化决策大脑

        Args:
            config: 可配置参数字典，支持覆盖默认值

        【V2.0 参数变更说明】
        entry_score_threshold 已废弃（默认 float('inf') 表示永远不用固定门槛）
        新增分位数相关参数：
          - entry_percentile_threshold: 榜首必须超过的分位点（默认 p90）
          - entry_relative_multiplier: 榜首必须超过 median × N 倍（默认 1.5）
          - entry_min_board_size: 榜单最少几票才做决策（默认 10，_percentile需要n>=10才让p90有统计意义）
          - entry_ignition_prob_min_b: 通道B最低点火概率门槛（默认 20.0%）
        """
        config = config or {}

        # 【已废弃，保留仅供向后兼容日志打印】
        self.entry_score_threshold: float = config.get('entry_score_threshold', float('inf'))

        # 止损止盈超时（不变）
        self.stop_loss_pct: float = config.get('stop_loss_pct', -0.03)
        self.take_profit_pct: float = config.get('take_profit_pct', 0.08)
        self.max_hold_minutes: int = config.get('max_hold_minutes', 120)

        # 【路线A 新增参数】里氏震级相对分位数门槛
        self.entry_percentile_threshold: float = config.get('entry_percentile_threshold', 0.90)
        self.entry_relative_multiplier: float = config.get('entry_relative_multiplier', 1.5)
        # 【Bug#1修复】默认值改为10，_percentile需要n>=10才让p90有统计意义(n=5时p90≈第4名)
        self.entry_min_board_size: int = config.get('entry_min_board_size', 10)
        self.entry_ignition_prob_min_b: float = config.get('entry_ignition_prob_min_b', 20.0)

        # 【CTO V193 宪法级物理门槛】无硬编码，可配置
        # 注意：这是买入决策门槛，不是KineticCoreEngine的底线门槛(0.57)
        # CTO宪法规定：Price_Momentum > 0.9 才是起爆临界点
        self.pm_threshold_buy: float = config.get('pm_threshold_buy', 0.90)
        
        # 【CTO V195 修复NoneType崩溃陷阱】
        # 原逻辑`if 'mfe_threshold_buy' not in config`只检查键是否存在
        # 但config.get()可能返回None值，导致后续比较`top1_mfe < None`抛TypeError
        # 必须检查值是否为None，而不是键是否存在
        mfe_val = config.get('mfe_threshold_buy')
        if mfe_val is None:
            raise ValueError(
                "缺乏 MFE 验证分布数据，禁止使用魔法数字。"
                "请在 strategy_params.json 的 decision_brain 配置节中显式设置 mfe_threshold_buy 参数。"
                "建议通过回测确定最优阈值。"
            )
        self.mfe_threshold_buy: float = float(mfe_val)

        # 内部状态
        self.current_position: Optional[Dict] = None
        self.entry_time: Optional[datetime] = None
        self.entry_price: float = 0.0
        self.entry_score: float = 0.0
        self.decision_log: List[Dict] = []
        self.held_stock_code: str = ""

        # 【路线A】每帧分位数快照（用于战报回溯）
        self._last_frame_p90: float = 0.0
        self._last_frame_median: float = 0.0
        
        # 【P2修复】卖出后冷静期：防止车轮战
        self._last_sell_time: Optional[datetime] = None
        self._sell_cooldown_minutes: int = config.get('sell_cooldown_minutes', 30)

        logger.info(
            f"[OK] TradeDecisionBrain V2.0(路线A)初始化完成 | "
            f"里氏震级门槛: p{self.entry_percentile_threshold*100:.0f} x {self.entry_relative_multiplier}x | "
            f"物理门槛: PM>={self.pm_threshold_buy:.2f} MFE>={self.mfe_threshold_buy:.1f} | "
            f"止损:{self.stop_loss_pct*100:.1f}% | "
            f"止盈:{self.take_profit_pct*100:.1f}% | "
            f"最大持仓:{self.max_hold_minutes}分钟 | "
            f"最小榜单:{self.entry_min_board_size}票"
        )

    # =========================================================================
    # 公开接口（签名与 V1.0 完全一致，外部注入点无需任何修改）
    # =========================================================================

    def on_new_frame(
        self,
        top_targets: List[Dict],
        current_time: datetime,
        held_stock_current_price: float = 0.0
    ) -> Dict:
        """
        每帧调用一次，返回决策字典

        Args:
            top_targets: 当前榜单（来自current_top_targets），字段包括：
                - code: str               # 股票代码
                - score: float            # 最终分数（里氏震级量纲，绝对值无意义）
                - price: float            # 当前价格
                - trigger_type: str|None  # 触发类型
                - trigger_confidence: float
                - ignition_prob: float    # 点火概率（%）
                - mfe: float
                - sustain_ratio: float
            current_time: 当前时间
            held_stock_current_price: 持仓股当前价格（无持仓传0）

        Returns:
            决策字典：
            {
                'action': 'BUY' | 'SELL' | 'HOLD' | 'WATCH',
                'stock_code': str,
                'price': float,
                'reason': str,
                'score': float,
                'trigger_type': str,
                # 路线A新增审计字段：
                'p90_threshold': float,   # 当帧p90门槛
                'median_score': float,    # 当帧中位分数
                'relative_rank': float    # 榜首百分位
            }
        """
        decision = DecisionResult(action='WATCH')

        # 【Bug C修复】无论有无持仓，都先计算并更新分位数缓存
        # 原问题：_last_frame_p90/median只在_should_enter()内更新，有持仓时不调用_should_enter()
        # 导致SELL/HOLD期间战报里的分位数是入场时的历史值，不是当前帧实时值
        if top_targets and len(top_targets) >= 1:
            scores = [t.get('score', 0.0) for t in top_targets]
            if scores:
                self._last_frame_p90 = self._percentile(scores, self.entry_percentile_threshold)
                self._last_frame_median = statistics.median(scores)

        # ── 1. 有持仓：优先判断出场 ──────────────────────────────────────────
        if self.current_position is not None:
            exit_decision = self._should_exit(held_stock_current_price, current_time)
            if exit_decision[0]:
                decision.action = 'SELL'
                decision.stock_code = self.held_stock_code
                decision.price = held_stock_current_price
                decision.reason = exit_decision[1]
                decision.score = self.entry_score
                # 【P0修复】SELL分支也填充p90和median（使用缓存值）
                decision.p90_threshold = self._last_frame_p90
                decision.median_score = self._last_frame_median

                self._log_decision(current_time, decision)

                logger.info(
                    f"[TRADE-SELL] [卖出信号] {decision.stock_code} | "
                    f"原因:{decision.reason} | "
                    f"价格:{decision.price:.2f} | "
                    f"盈亏:{(held_stock_current_price - self.entry_price) / self.entry_price * 100:+.2f}%"
                )

                # 【Fix#2】SELL分支必须清仓，防止下帧继续输出SELL死循环
                # 【Bug A修复】传入current_time确保回测场景冷静期正确生效
                self.clear_position(current_time=current_time)

                return self._decision_to_dict(decision)

            # 持仓未触发出场，继续持有
            decision.action = 'HOLD'
            decision.stock_code = self.held_stock_code
            decision.price = held_stock_current_price
            decision.reason = "持仓中，等待出场信号"
            decision.score = self.entry_score
            # 【P0修复】HOLD分支也填充p90和median（使用缓存值）
            decision.p90_threshold = self._last_frame_p90
            decision.median_score = self._last_frame_median

            self._log_decision(current_time, decision)
            return self._decision_to_dict(decision)

        # ── 2. 无持仓：判断入场 ──────────────────────────────────────────────
        entry_decision = self._should_enter(top_targets, current_time)
        if entry_decision is not None:
            decision.action = 'BUY'
            decision.stock_code = entry_decision['code']
            decision.price = entry_decision['price']
            decision.score = entry_decision['score']
            decision.trigger_type = entry_decision.get('trigger_type', '')
            decision.p90_threshold = entry_decision.get('p90_threshold', 0.0)
            decision.median_score = entry_decision.get('median_score', 0.0)
            decision.relative_rank = entry_decision.get('relative_rank', 0.0)
            decision.reason = (
                f"里氏震级触发入场 | "
                f"score={decision.score:.0f} >= p{self.entry_percentile_threshold*100:.0f}({decision.p90_threshold:.0f}) "
                f"且 >= {self.entry_relative_multiplier}x×median({decision.median_score:.0f}) | "
                f"通道:{entry_decision.get('entry_channel', '?')} | "
                f"trigger_type:{decision.trigger_type or 'None'}"
            )

            self.current_position = entry_decision
            self.entry_time = current_time
            self.entry_price = entry_decision['price']
            self.entry_score = entry_decision['score']
            self.held_stock_code = entry_decision['code']

            self._log_decision(current_time, decision)

            logger.info(
                f"[TRADE-BUY] [买入信号] {decision.stock_code} | "
                f"score:{decision.score:.0f} | "
                f"p90门槛:{decision.p90_threshold:.0f} | "
                f"中位数:{decision.median_score:.0f} | "
                f"价格:{decision.price:.2f} | "
                f"通道:{entry_decision.get('entry_channel', '?')}"
            )

            return self._decision_to_dict(decision)

        # ── 3. 无入场信号：观望，打印分位数上下文 ──────────────────────────
        if top_targets:
            # 【Bug-New-2修复】复用on_new_frame开头已缓存的分位数，避免第三次重复计算
            p90 = self._last_frame_p90
            median = self._last_frame_median
            top1 = top_targets[0]
            decision.reason = (
                f"观望 | 榜首score={top1.get('score', 0):.0f} "
                f"< p{self.entry_percentile_threshold*100:.0f}({p90:.0f}) "
                f"或 < {self.entry_relative_multiplier}x×median({median:.0f}={median*self.entry_relative_multiplier:.0f}需)"
            )
            decision.p90_threshold = p90
            decision.median_score = median
        else:
            decision.reason = "榜单为空，继续观望"

        self._log_decision(current_time, decision)
        return self._decision_to_dict(decision)

    # =========================================================================
    # 核心决策逻辑（私有）
    # =========================================================================

    # 有效触发信号类型（修复Bug#1：'none'字符串误判为有信号）
    VALID_TRIGGERS = {'vacuum_ignition', 'stair_breakout', 'gravity_slingshot'}

    def _should_enter(self, top_targets: List[Dict], current_time: datetime = None) -> Optional[Dict]:
        """
        【路线A 核心改造】里氏震级相对分位数入场判断

        旧版逻辑（已废弃）：
            top1.score >= entry_score_threshold（固定值65，量纲爆炸后完全失效）

        新版逻辑：
            Step0: 开盘冷却期（Bug#2修复）- 09:35前不入场，防止噪声
            Step1: 榜单至少 entry_min_board_size 票（防止单票孤榜误判）
            Step2: 计算当帧榜单的 p90 和 median
            Step3: 双通道判断
                通道A（有 VALID 触发信号）: score >= p90 AND score >= median × multiplier
                通道B（无触发信号）: score >= p95 AND score >= median × multiplier AND ignition_prob >= 20%
            Step4: 全部通过 → 返回入场目标

        物理意义：
            - p90 保证「榜首比90%的票都高」
            - median × 1.5x 保证「榜首至少是平均水平的1.5倍」
            - 两个条件都满足才能确认是"本帧真正的异动票"
        """
        # 单吊约束
        if self.current_position is not None:
            return None

        if not top_targets:
            return None

        # Bug#2修复：开盘冷却期（09:30-09:35不入场，防止噪声买入）
        if current_time is not None:
            cooldown_end = current_time.replace(hour=9, minute=35, second=0, microsecond=0)
            if current_time < cooldown_end:
                logger.debug(f"[冷却期] {current_time.strftime('%H:%M:%S')} 开盘前5分钟，不入场")
                return None
            
            # 【P2修复】卖出后冷静期（防止车轮战：卖出后立即买入另一只）
            if self._last_sell_time is not None:
                minutes_since_sell = (current_time - self._last_sell_time).total_seconds() / 60
                if minutes_since_sell < self._sell_cooldown_minutes:
                    remaining = self._sell_cooldown_minutes - minutes_since_sell
                    logger.debug(
                        f"[冷静期] 卖出后{minutes_since_sell:.0f}分钟 < {self._sell_cooldown_minutes}分钟，"
                        f"还需等待{remaining:.0f}分钟"
                    )
                    return None

        # 榜单规模保护（防止 1-2 票孤榜时 p90=p50=同一票，任何票都能通过）
        if len(top_targets) < self.entry_min_board_size:
            logger.debug(
                f"[路线A] 榜单仅{len(top_targets)}票 < 最小要求{self.entry_min_board_size}票，跳过决策"
            )
            return None

        scores = [t.get('score', 0.0) for t in top_targets]
        top1 = top_targets[0]
        top1_score = top1.get('score', 0.0)
        trigger_type = top1.get('trigger_type') or ''
        ignition_prob = top1.get('ignition_prob', 0.0)

        # 零分保护：榜单全是0分时跳过决策（防止 0>=0 通过入场）
        if top1_score <= 0:
            logger.debug(f"[路线A] 榜首score={top1_score:.0f}，跳过决策")
            return None

        # 计算分位数快照
        p90 = self._percentile(scores, self.entry_percentile_threshold)
        p95 = self._percentile(scores, 0.95)
        median = statistics.median(scores)
        relative_threshold = median * self.entry_relative_multiplier

        # 计算榜首相对百分位（用于战报）
        n = len(scores)
        rank_below = sum(1 for s in scores if s < top1_score)
        relative_rank = rank_below / n if n > 0 else 0.0

        # =========== 【CTO V193 宪法级物理门槛强制校验】 ===========
        # 关键：决策大脑选龙必须使用严格的物理门槛，不是底线淘汰
        # KineticCoreEngine的0.57和0.1是底线Veto，决策大脑必须寻找真正的起爆点
        top1_price_momentum = top1.get('price_momentum', 0.0)
        top1_mfe = top1.get('mfe', 0.0)

        # 物理门槛1: Price Momentum 必须超过起爆临界点(默认0.9)
        # 物理意义：(price - low) / (high - low) > 0.9 表示价格在日内高位，有起爆势能
        if top1_price_momentum < self.pm_threshold_buy:
            logger.debug(
                f"[VETO-PM] {top1.get('code')} momentum={top1_price_momentum:.2f} "
                f"< 阈值{self.pm_threshold_buy:.2f}，未达起爆临界点，跳过"
            )
            return None

        # 物理门槛2: MFE 必须满足最低效率要求(默认1.0)
        # 物理意义：MFE = 振幅% / 流入占比，低MFE表示资金效率极低（大钱只砸出小振幅）
        if top1_mfe < self.mfe_threshold_buy:
            logger.debug(
                f"[VETO-MFE] {top1.get('code')} MFE={top1_mfe:.2f} "
                f"< 阈值{self.mfe_threshold_buy:.2f}，资金效率过低，跳过"
            )
            return None
        # =============================================================
        
        # =========== 【CTO V199 断层碾压狙击逻辑】 ===========
        # 核心理念：只抓绝对龙头，必须有断层碾压优势
        # 条件A：榜首分数 > 5000（确保是高质量机会）
        # 条件B：物理门槛已通过（PM和MFE都在阈值之上）
        # 条件C：top1 > top2 * 1.2（断层碾压，若无top2则直接满足）
        
        MIN_SNIPER_SCORE = 5000.0  # 最低狙击分数
        FAULT_LINE_RATIO = 1.2     # 断层碾压比例
        
        # 提取top2分数
        top2_score = scores[1] if len(scores) > 1 else 0.0
        
        # 条件A：分数必须超过最低狙击线
        if top1_score < MIN_SNIPER_SCORE:
            logger.debug(
                f"[VETO-SCORE] {top1.get('code')} score={top1_score:.0f} < 狙击线{MIN_SNIPER_SCORE:.0f}"
            )
            return None
        
        # 条件C：断层碾压（榜首必须碾压第二名20%以上）
        if top2_score > 0 and top1_score < top2_score * FAULT_LINE_RATIO:
            fault_line_gap = (top1_score / top2_score - 1) * 100 if top2_score > 0 else 0
            logger.debug(
                f"[VETO-FAULT] {top1.get('code')} 未形成断层碾压 | "
                f"top1={top1_score:.0f} vs top2={top2_score:.0f} | "
                f"领先{fault_line_gap:.1f}% < 断层要求{FAULT_LINE_RATIO-1:.0%}"
            )
            return None
        
        # 断层碾压逻辑通过，记录日志
        fault_line_gap = (top1_score / top2_score - 1) * 100 if top2_score > 0 else 100
        logger.debug(
            f"[SNIPER-OK] {top1.get('code')} 断层碾压通过 | "
            f"score={top1_score:.0f} > 狙击线{MIN_SNIPER_SCORE:.0f} | "
            f"断层领先{fault_line_gap:.1f}%"
        )
        # =============================================================

        # Bug#1修复：使用VALID_TRIGGERS集合判断，而非 trigger_type != ''
        has_valid_trigger = trigger_type in self.VALID_TRIGGERS

        # ── 通道A：有明确触发信号 ───────────────────────────────────────────
        if has_valid_trigger:
            passes = (top1_score >= p90) and (top1_score >= relative_threshold)
            if passes:
                logger.debug(
                    f"[路线A 通道A] {top1.get('code')} 通过入场 | "
                    f"score={top1_score:.0f} >= p90({p90:.0f}) 且 >= {relative_threshold:.0f} | "
                    f"trigger={trigger_type}"
                )
                return {
                    **top1,
                    'p90_threshold': p90,
                    'median_score': median,
                    'relative_rank': relative_rank,
                    'entry_channel': 'A_trigger'
                }
            else:
                logger.debug(
                    f"[路线A 通道A] {top1.get('code')} 未通过 | "
                    f"score={top1_score:.0f} p90需>={p90:.0f}({top1_score>=p90}) "
                    f"relative需>={relative_threshold:.0f}({top1_score>=relative_threshold})"
                )
                return None

        # ── 通道B：无有效 trigger_type，依赖高分位+高点火概率 ─────────────────
        passes_b = (
            (top1_score >= p95) and
            (top1_score >= relative_threshold) and
            (ignition_prob >= self.entry_ignition_prob_min_b)
        )
        if passes_b:
            logger.debug(
                f"[路线A 通道B] {top1.get('code')} 通过入场 | "
                f"score={top1_score:.0f} >= p95({p95:.0f}) | "
                f"ignition_prob={ignition_prob:.1f}% >= {self.entry_ignition_prob_min_b}%"
            )
            return {
                **top1,
                'p90_threshold': p90,
                'median_score': median,
                'relative_rank': relative_rank,
                'entry_channel': 'B_ignition'
            }
        else:
            logger.debug(
                f"[路线A 通道B] {top1.get('code')} 未通过 | "
                f"score={top1_score:.0f} p95需>={p95:.0f}({top1_score>=p95}) | "
                f"ignition={ignition_prob:.1f}%需>={self.entry_ignition_prob_min_b}%({ignition_prob>=self.entry_ignition_prob_min_b})"
            )
            return None

    def _should_exit(self, current_price: float, current_time: datetime) -> Tuple[bool, str]:
        """
        出场判断逻辑（优先级顺序：止损 > 止盈 > 超时）

        Args:
            current_price: 当前价格
            current_time: 当前时间

        Returns:
            (是否出场, 原因)
        """
        if self.entry_price <= 0:
            return False, ""

        pnl_ratio = (current_price - self.entry_price) / self.entry_price

        # 1. 止损（最高优先级，硬红线）
        if pnl_ratio <= self.stop_loss_pct:
            return True, f"止损触发: {pnl_ratio*100:.2f}% <= {self.stop_loss_pct*100:.1f}%"

        # 2. 止盈
        if pnl_ratio >= self.take_profit_pct:
            return True, f"止盈触发: {pnl_ratio*100:.2f}% >= {self.take_profit_pct*100:.1f}%"

        # 3. 超时
        if self.entry_time is not None:
            hold_minutes = (current_time - self.entry_time).total_seconds() / 60
            if hold_minutes >= self.max_hold_minutes:
                return True, f"持仓超时: {hold_minutes:.0f}分钟 >= {self.max_hold_minutes}分钟"

        return False, ""

    # =========================================================================
    # 状态管理
    # =========================================================================

    def clear_position(self, current_time: Optional[datetime] = None):
        """
        清除持仓状态（卖出后调用）

        【Fix#3】必须写入 decision_log，保证复盘时 POSITION_CLEARED 可追踪。
        V1.0 此方法无日志，导致复盘时无法确定哪一帧清仓。
        
        【CTO审计Bug A修复】
        使用传入的 current_time 而非 datetime.now()，确保回测场景下冷静期正确生效。
        在回测中，current_time 是历史时间（如 2026-03-16），datetime.now() 是当前时间（如 2026-03-17），
        两者差值为负数导致冷静期检查 _should_enter() 中的 (current_time - _last_sell_time) 永远为负，
        冷静期在回测中完全失效。
        """
        cleared_code = self.held_stock_code
        cleared_price = self.entry_price
        
        # 【Bug A修复】使用传入的时间或回退到系统时间
        effective_time = current_time if current_time else datetime.now()

        # 写入 decision_log（Fix#3）
        self.decision_log.append({
            'time': effective_time.strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'POSITION_CLEARED',
            'stock_code': cleared_code,
            'reason': '持仓状态已清空',
            'score': self.entry_score,
            'price': cleared_price
        })

        self.current_position = None
        self.entry_time = None
        self.entry_price = 0.0
        self.entry_score = 0.0
        self.held_stock_code = ""
        
        # 【Bug A修复】记录卖出时间，启动冷静期（使用正确的时钟）
        self._last_sell_time = effective_time

        logger.debug(f"[DEBUG] TradeDecisionBrain 持仓已清空: {cleared_code} @{cleared_price:.2f}")

    # =========================================================================
    # 辅助方法
    # =========================================================================

    @staticmethod
    def _percentile(data: List[float], p: float) -> float:
        """
        计算数列的 p 分位数（线性插值，与 numpy.percentile 行为一致）

        Args:
            data: 数据列表（至少1个元素）
            p: 分位点（0.0~1.0）

        Returns:
            分位数值
        """
        if not data:
            return 0.0
        sorted_data = sorted(data)
        n = len(sorted_data)
        if n == 1:
            return sorted_data[0]
        # 线性插值
        idx = p * (n - 1)
        lower = int(idx)
        upper = min(lower + 1, n - 1)
        frac = idx - lower
        return sorted_data[lower] * (1 - frac) + sorted_data[upper] * frac

    def _log_decision(self, time: datetime, decision: DecisionResult):
        """记录决策日志（含路线A分位数上下文）"""
        self.decision_log.append({
            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'action': decision.action,
            'stock_code': decision.stock_code,
            'reason': decision.reason,
            'score': decision.score,
            'price': decision.price,
            # 路线A 审计字段
            'p90_threshold': decision.p90_threshold,
            'median_score': decision.median_score,
            'relative_rank': decision.relative_rank
        })

    def _decision_to_dict(self, decision: DecisionResult) -> Dict:
        """将 DecisionResult 转换为 dict（含路线A审计字段）"""
        return {
            'action': decision.action,
            'stock_code': decision.stock_code,
            'price': decision.price,
            'reason': decision.reason,
            'score': decision.score,
            'trigger_type': decision.trigger_type,
            # 路线A 审计字段（下游可选消费，不影响现有接口）
            'p90_threshold': decision.p90_threshold,
            'median_score': decision.median_score,
            'relative_rank': decision.relative_rank
        }

    # =========================================================================
    # 查询接口（与 V1.0 完全一致）
    # =========================================================================

    def get_decision_log(self) -> List[Dict]:
        """获取决策日志"""
        return self.decision_log.copy()

    def get_position_info(self) -> Optional[Dict]:
        """获取当前持仓信息"""
        if self.current_position is None:
            return None
        return {
            'stock_code': self.held_stock_code,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.strftime('%Y-%m-%d %H:%M:%S') if self.entry_time else '',
            'entry_score': self.entry_score
        }

    def get_config(self) -> Dict:
        """获取当前配置"""
        return {
            'entry_score_threshold': self.entry_score_threshold,  # 已废弃，保留兼容
            'entry_percentile_threshold': self.entry_percentile_threshold,
            'entry_relative_multiplier': self.entry_relative_multiplier,
            'entry_min_board_size': self.entry_min_board_size,
            'entry_ignition_prob_min_b': self.entry_ignition_prob_min_b,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'max_hold_minutes': self.max_hold_minutes
        }

    def update_config(self, config: Dict):
        """
        更新配置（支持运行时热更新）

        Args:
            config: 新配置字典
        """
        if 'entry_percentile_threshold' in config:
            self.entry_percentile_threshold = config['entry_percentile_threshold']
        if 'entry_relative_multiplier' in config:
            self.entry_relative_multiplier = config['entry_relative_multiplier']
        if 'entry_min_board_size' in config:
            self.entry_min_board_size = config['entry_min_board_size']
        if 'entry_ignition_prob_min_b' in config:
            self.entry_ignition_prob_min_b = config['entry_ignition_prob_min_b']
        if 'stop_loss_pct' in config:
            self.stop_loss_pct = config['stop_loss_pct']
        if 'take_profit_pct' in config:
            self.take_profit_pct = config['take_profit_pct']
        if 'max_hold_minutes' in config:
            self.max_hold_minutes = config['max_hold_minutes']

        logger.info(f"[OK] TradeDecisionBrain V2.0 配置已更新: {config}")
