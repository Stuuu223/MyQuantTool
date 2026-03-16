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

        logger.info(
            f"[OK] TradeDecisionBrain V2.0(路线A)初始化完成 | "
            f"里氏震级门槛: p{self.entry_percentile_threshold*100:.0f} × {self.entry_relative_multiplier}x | "
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

        # ── 1. 有持仓：优先判断出场 ──────────────────────────────────────────
        if self.current_position is not None:
            exit_decision = self._should_exit(held_stock_current_price, current_time)
            if exit_decision[0]:
                decision.action = 'SELL'
                decision.stock_code = self.held_stock_code
                decision.price = held_stock_current_price
                decision.reason = exit_decision[1]
                decision.score = self.entry_score

                self._log_decision(current_time, decision)

                logger.info(
                    f"🔔 [卖出信号] {decision.stock_code} | "
                    f"原因:{decision.reason} | "
                    f"价格:{decision.price:.2f} | "
                    f"盈亏:{(held_stock_current_price - self.entry_price) / self.entry_price * 100:+.2f}%"
                )

                # 【Fix#2】SELL分支必须清仓，防止下帧继续输出SELL死循环
                self.clear_position()

                return self._decision_to_dict(decision)

            # 持仓未触发出场，继续持有
            decision.action = 'HOLD'
            decision.stock_code = self.held_stock_code
            decision.price = held_stock_current_price
            decision.reason = "持仓中，等待出场信号"
            decision.score = self.entry_score

            self._log_decision(current_time, decision)
            return self._decision_to_dict(decision)

        # ── 2. 无持仓：判断入场 ──────────────────────────────────────────────
        entry_decision = self._should_enter(top_targets)
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
                f"💰 [买入信号] {decision.stock_code} | "
                f"score:{decision.score:.0f} | "
                f"p90门槛:{decision.p90_threshold:.0f} | "
                f"中位数:{decision.median_score:.0f} | "
                f"价格:{decision.price:.2f} | "
                f"通道:{entry_decision.get('entry_channel', '?')}"
            )

            return self._decision_to_dict(decision)

        # ── 3. 无入场信号：观望，打印分位数上下文 ──────────────────────────
        if top_targets:
            scores = [t.get('score', 0) for t in top_targets]
            p90 = self._percentile(scores, self.entry_percentile_threshold)
            median = statistics.median(scores) if scores else 0
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

    def _should_enter(self, top_targets: List[Dict]) -> Optional[Dict]:
        """
        【路线A 核心改造】里氏震级相对分位数入场判断

        旧版逻辑（已废弃）：
            top1.score >= entry_score_threshold（固定值65，量纲爆炸后完全失效）

        新版逻辑：
            Step1: 榜单至少 entry_min_board_size 票（防止单票孤榜误判）
            Step2: 计算当帧榜单的 p90 和 median
            Step3: 双通道判断
                通道A（有 trigger_type）: score >= p90 AND score >= median × multiplier
                通道B（无 trigger_type）: score >= p95 AND score >= median × multiplier AND ignition_prob >= 20%
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

        # 缓存供 WATCH 分支打印
        self._last_frame_p90 = p90
        self._last_frame_median = median

        # 计算榜首相对百分位（用于战报）
        n = len(scores)
        rank_below = sum(1 for s in scores if s < top1_score)
        relative_rank = rank_below / n if n > 0 else 0.0

        # ── 通道A：有明确触发信号 ───────────────────────────────────────────
        if trigger_type != '':
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

        # ── 通道B：无 trigger_type，依赖高分位+高点火概率 ─────────────────
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

    def clear_position(self):
        """
        清除持仓状态（卖出后调用）

        【Fix#3】必须写入 decision_log，保证复盘时 POSITION_CLEARED 可追踪。
        V1.0 此方法无日志，导致复盘时无法确定哪一帧清仓。
        """
        cleared_code = self.held_stock_code
        cleared_price = self.entry_price

        # 写入 decision_log（Fix#3）
        self.decision_log.append({
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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
