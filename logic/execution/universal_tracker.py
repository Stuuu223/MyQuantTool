# -*- coding: utf-8 -*-
"""
全榜生命周期追踪器 V2.0

【V2.0 重大升级】
- 支持方案B严格入场模式（trigger_type 必须有物理信号才计入「系统机会」）
- 增加 DecisionEvent 数据结构，完整记录决策大脑每帧的判断依据
- 增加双引擎对比接口（paper_engine vs friction_engine）
- 增加「错过复盘」维度：记录未买入票的后续走势
- 增加 ScanValidator 同质性结果嵌入

核心价值:
  记录所有曾经上榜（进入top_targets）的票的完整轨迹
  无论是否被系统实际买入
  事后可复盘「那只我没买的后来涨了多少」

Author: CTO Research Lab
Date: 2026-03-16
Version: V2.0
"""
import json
import csv
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class DecisionEvent:
    """
    决策事件 - 记录决策大脑每次做出 BUY/SELL/WATCH 判断时的完整上下文
    """
    frame_time: str                 # 帧时间戳
    action: str                     # BUY / SELL / WATCH / HOLD
    stock_code: str                 # 目标股票代码（WATCH/HOLD 时为空）
    price: float                    # 决策时价格
    score: float                    # 决策时榜首分数
    trigger_type: str               # 物理触发类型（方案B必须非空才能 BUY）
    trigger_confidence: float       # 触发置信度
    ignition_prob: float            # 点火概率
    p90_threshold: float            # 本帧 p90 阈值
    median_score: float             # 本帧中位数分数
    reason: str                     # 决策理由文本
    held_stock: str                 # 决策时的持仓（单吊）
    held_price: float               # 持仓现价
    held_unrealized_pnl_pct: float  # 持仓未实现盈亏%

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StockLifecycle:
    """
    股票生命周期数据结构 V2.0

    记录一只股票从上榜到追踪结束的完整轨迹。
    新增字段：方案B相关的触发信号分析、双引擎视角的机会价值。
    """
    code: str
    first_appear_time: str = ""           # 第一次上榜时间
    last_appear_time: str = ""            # 最后一次上榜时间
    appear_count: int = 0                 # 上榜次数
    peak_score: float = 0.0               # 历史最高分
    first_appear_price: float = 0.0       # 首次上榜时价格
    peak_price: float = 0.0               # 上榜期间最高价
    final_price: float = 0.0              # 收盘/追踪结束时价格
    max_gain_pct: float = 0.0             # 从首次上榜到最高价的涨幅（%）
    final_gain_pct: float = 0.0           # 从首次上榜到结束的涨幅（%）
    was_bought: bool = False              # 是否被系统买入
    buy_price: float = 0.0                # 买入价（未买入为0）
    sell_price: float = 0.0               # 卖出价（未卖出为0）
    actual_pnl_pct: float = 0.0           # 实际盈亏%（未买入为0）
    missed_gain_pct: float = 0.0          # 错过的涨幅（was_bought=True时为0）
    peak_trigger_type: str = ""           # 最高分时的触发类型
    score_history: List[float] = field(default_factory=list)
    price_history: List[float] = field(default_factory=list)
    trigger_types_history: List[str] = field(default_factory=list)
    # === V2.0 新增 ===
    had_physical_trigger: bool = False    # 是否曾出现过物理触发信号（方案B资格）
    trigger_first_time: str = ""          # 首次物理触发时间
    trigger_first_price: float = 0.0      # 首次物理触发时价格
    trigger_peak_confidence: float = 0.0  # 历史最高触发置信度
    schema_b_eligible: bool = False       # 方案B入场资格（score >= p95 AND trigger存在）
    paper_buy_price: float = 0.0          # 零摩擦引擎「理想买入」价格
    paper_sell_price: float = 0.0         # 零摩擦引擎「理想卖出」价格
    paper_pnl_pct: float = 0.0            # 零摩擦理想收益%
    friction_pnl_pct: float = 0.0         # 真实摩擦收益%
    alpha_lost_to_friction: float = 0.0   # 摩擦损耗 pp（paper - friction）
    skip_reason: str = ""                 # 未被买入的原因（方案B拒绝/仓位满/分数不足）

    def to_dict(self) -> Dict:
        return asdict(self)


class UniversalTracker:
    """
    全榜生命周期追踪器 V2.0

    架构职责分离:
      - UniversalTracker: 只负责「记录」和「统计」
      - TradeDecisionBrain: 负责「决策」（何时买、买哪个、何时卖）
      - MockExecutionManager: 负责「撮合」（资金管理、滑点模拟）
      - PaperTradeEngine: 负责「理想对照」（零摩擦、假设每次成交）
    """

    MAX_PRICE_HISTORY = 300
    MAX_SCORE_HISTORY = 30

    def __init__(self, session_id: str = None, schema: str = 'B'):
        """
        Args:
            session_id: 会话ID（默认使用当前日期时间）
            schema: 入场方案 'A'（宽松） 或 'B'（严格，需要物理触发）
        """
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.schema = schema
        self.registry: Dict[str, StockLifecycle] = {}
        self._bought_codes: set = set()
        self._sold_codes: Dict[str, float] = {}
        self.decision_log: List[DecisionEvent] = []   # 决策事件流
        self._validation_result: Optional[Dict] = None  # ScanValidator 结果嵌入
        logger.info(
            f"[OK] UniversalTracker V2.0 初始化完成 | 会话: {self.session_id} | 入场方案: {schema}"
        )

    # ------------------------------------------------------------------
    # 核心帧更新接口（每个 Tick 帧调用一次）
    # ------------------------------------------------------------------

    def on_frame(
        self,
        top_targets: List[Dict],
        current_time: datetime,
        executed_trade: Dict = None,
        decision_context: Dict = None,
        global_prices: Dict[str, float] = None
    ):
        """
        每帧调用，传入当前榜单和当帧是否有实际成交。

        Args:
            top_targets: 当前榜单（current_top_targets）
            current_time: 当前时间
            executed_trade: 当帧成交信息 {'action', 'stock_code', 'price', 'reason'} 或 None
            decision_context: 决策大脑输出的完整上下文（来自 TradeDecisionBrain.on_new_frame 返回值）
            global_prices: 全量价格快照 {stock_code: current_price}
                           【CTO V192修复】解决视野盲区：即使股票跌出榜单，仍能更新peak_price
        """
        time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

        # 记录决策事件
        if decision_context:
            self._record_decision_event(decision_context, time_str, executed_trade)

        # 处理成交
        if executed_trade:
            self._process_trade(executed_trade, time_str)

        # 更新榜单中的股票状态
        for target in top_targets:
            code = target.get('code', '')
            if not code:
                continue
            self._update_stock_on_appear(
                code=code,
                score=target.get('score', 0.0),
                price=target.get('price', 0.0),
                trigger_type=target.get('trigger_type') or '',
                trigger_confidence=target.get('trigger_confidence', 0.0),
                ignition_prob=target.get('ignition_prob', 0.0),
                time_str=time_str
            )
        
        # 【CTO V192修复】视野盲区消除：用global_prices更新所有已上榜股票的价格
        # 即使某票跌出榜单，仍能追踪其peak_price，计算真实的missed_gain
        if global_prices:
            for code in list(self.registry.keys()):
                if code in global_prices:
                    self.on_price_update(code, global_prices[code], current_time)

    # ------------------------------------------------------------------
    # 价格持续追踪（离榜后仍需更新到收盘）
    # ------------------------------------------------------------------

    def on_price_update(self, stock_code: str, current_price: float, current_time: datetime):
        """
        持续更新已上榜票的价格（用于计算错过收益）。
        即使该票已离榜，仍需持续更新直到收盘。
        """
        lifecycle = self.registry.get(stock_code)
        if not lifecycle:
            return
        lifecycle.final_price = current_price
        if current_price > lifecycle.peak_price:
            lifecycle.peak_price = current_price
        if lifecycle.first_appear_price > 0:
            lifecycle.max_gain_pct = (
                (lifecycle.peak_price - lifecycle.first_appear_price)
                / lifecycle.first_appear_price * 100
            )
            lifecycle.final_gain_pct = (
                (current_price - lifecycle.first_appear_price)
                / lifecycle.first_appear_price * 100
            )
        if not lifecycle.was_bought:
            lifecycle.missed_gain_pct = lifecycle.max_gain_pct

    # ------------------------------------------------------------------
    # 双引擎对比注入
    # ------------------------------------------------------------------

    def inject_paper_trade_result(
        self,
        stock_code: str,
        paper_buy: float,
        paper_sell: float,
        friction_buy: float,
        friction_sell: float
    ):
        """
        注入双引擎对比结果。
        在 PaperTradeEngine 和 MockExecutionManager 均完成交易后调用。

        Args:
            stock_code: 股票代码
            paper_buy / paper_sell: 零摩擦引擎买卖价
            friction_buy / friction_sell: 真实摩擦引擎买卖价
        """
        lifecycle = self._get_or_create(stock_code)
        if paper_buy > 0 and paper_sell > 0:
            lifecycle.paper_buy_price = paper_buy
            lifecycle.paper_sell_price = paper_sell
            lifecycle.paper_pnl_pct = (paper_sell - paper_buy) / paper_buy * 100
        if friction_buy > 0 and friction_sell > 0:
            lifecycle.friction_pnl_pct = (friction_sell - friction_buy) / friction_buy * 100
        lifecycle.alpha_lost_to_friction = lifecycle.paper_pnl_pct - lifecycle.friction_pnl_pct
        logger.info(
            f"[双引擎] {stock_code}: 理想={lifecycle.paper_pnl_pct:+.2f}% | "
            f"真实={lifecycle.friction_pnl_pct:+.2f}% | "
            f"摩擦损耗={lifecycle.alpha_lost_to_friction:+.2f}pp"
        )

    def inject_scan_validation(self, validation_result: Dict):
        """
        嵌入 ScanValidator 的同质性验证结果到战报中。

        Args:
            validation_result: ScanVsLiveReport.to_dict() 的输出
        """
        self._validation_result = validation_result
        logger.info(
            f"[UniversalTracker] ScanValidator 结果已嵌入 | "
            f"同质性: {'PASS' if validation_result.get('overall_passed') else 'FAIL'}"
        )

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _record_decision_event(
        self,
        decision_context: Dict,
        time_str: str,
        executed_trade: Optional[Dict]
    ):
        """将决策大脑输出记录为 DecisionEvent"""
        held_code = decision_context.get('stock_code', '')
        event = DecisionEvent(
            frame_time=time_str,
            action=decision_context.get('action', 'WATCH'),
            stock_code=held_code,
            price=decision_context.get('price', 0.0),
            score=decision_context.get('score', 0.0),
            trigger_type=decision_context.get('trigger_type') or '',
            trigger_confidence=decision_context.get('trigger_confidence', 0.0),
            ignition_prob=decision_context.get('ignition_prob', 0.0),
            p90_threshold=decision_context.get('p90_threshold', 0.0),
            median_score=decision_context.get('median_score', 0.0),
            reason=decision_context.get('reason', ''),
            held_stock=decision_context.get('held_stock', ''),
            held_price=decision_context.get('held_price', 0.0),
            held_unrealized_pnl_pct=decision_context.get('held_unrealized_pnl_pct', 0.0)
        )
        self.decision_log.append(event)

    def _process_trade(self, trade: Dict, time_str: str):
        """处理成交信息"""
        action = trade.get('action', '')
        code = trade.get('stock_code', '')
        price = trade.get('price', 0.0)
        skip_reason = trade.get('skip_reason', '')
        if not code:
            return
        if action == 'BUY':
            self._bought_codes.add(code)
            lifecycle = self._get_or_create(code)
            lifecycle.was_bought = True
            lifecycle.buy_price = price
            logger.info(f"📊 [追踪] {code} 买入 @¥{price:.2f}")
        elif action == 'SELL':
            self._sold_codes[code] = price
            lifecycle = self.registry.get(code)
            if lifecycle:
                lifecycle.sell_price = price
                if lifecycle.buy_price > 0:
                    lifecycle.actual_pnl_pct = (
                        (price - lifecycle.buy_price) / lifecycle.buy_price * 100
                    )
                logger.info(
                    f"📊 [追踪] {code} 卖出 @¥{price:.2f} | 盈亏:{lifecycle.actual_pnl_pct:+.2f}%"
                )
        elif action == 'SKIP' and code:
            lifecycle = self._get_or_create(code)
            lifecycle.skip_reason = skip_reason

    def _get_or_create(self, code: str) -> StockLifecycle:
        if code not in self.registry:
            self.registry[code] = StockLifecycle(code=code)
        return self.registry[code]

    def _update_stock_on_appear(
        self,
        code: str,
        score: float,
        price: float,
        trigger_type: str,
        trigger_confidence: float,
        ignition_prob: float,
        time_str: str
    ):
        """更新股票上榜状态"""
        lifecycle = self._get_or_create(code)

        if lifecycle.appear_count == 0:
            lifecycle.first_appear_time = time_str
            lifecycle.first_appear_price = price
            lifecycle.peak_price = price
            lifecycle.peak_score = score

        lifecycle.appear_count += 1
        lifecycle.last_appear_time = time_str

        if score > lifecycle.peak_score:
            lifecycle.peak_score = score
            lifecycle.peak_trigger_type = trigger_type

        if price > lifecycle.peak_price:
            lifecycle.peak_price = price

        lifecycle.final_price = price

        if lifecycle.first_appear_price > 0:
            lifecycle.max_gain_pct = (
                (lifecycle.peak_price - lifecycle.first_appear_price)
                / lifecycle.first_appear_price * 100
            )
            lifecycle.final_gain_pct = (
                (price - lifecycle.first_appear_price)
                / lifecycle.first_appear_price * 100
            )

        # === V2.0: 物理触发信号记录 ===
        if trigger_type and not lifecycle.had_physical_trigger:
            lifecycle.had_physical_trigger = True
            lifecycle.trigger_first_time = time_str
            lifecycle.trigger_first_price = price
        if trigger_confidence > lifecycle.trigger_peak_confidence:
            lifecycle.trigger_peak_confidence = trigger_confidence

        # === V2.0: 方案B资格判定 ===
        # 方案B: 必须有物理触发信号（trigger_type 非空）才具备入场资格
        if trigger_type and score > 0:
            lifecycle.schema_b_eligible = True

        lifecycle.score_history.append(score)
        if len(lifecycle.score_history) > self.MAX_SCORE_HISTORY:
            lifecycle.score_history = lifecycle.score_history[-self.MAX_SCORE_HISTORY:]

        lifecycle.price_history.append(price)
        if len(lifecycle.price_history) > self.MAX_PRICE_HISTORY:
            lifecycle.price_history = lifecycle.price_history[-self.MAX_PRICE_HISTORY:]

        lifecycle.trigger_types_history.append(trigger_type)

    # ------------------------------------------------------------------
    # 报告生成
    # ------------------------------------------------------------------

    def get_full_report(self) -> Dict:
        """
        返回完整工业级战报。

        结构:
          summary: 摘要统计
          schema_b_analysis: 方案B专项分析
          dual_engine_comparison: 双引擎对比
          decision_log_summary: 决策事件流摘要
          all_stocks: 所有上榜票全生命周期
          scan_validation: ScanValidator 同质性结果（如有）
        """
        all_stocks = list(self.registry.values())
        bought_stocks = [s for s in all_stocks if s.was_bought]
        missed_stocks = [s for s in all_stocks if not s.was_bought]
        schema_b_eligible = [s for s in all_stocks if s.schema_b_eligible]
        schema_b_missed = [s for s in schema_b_eligible if not s.was_bought]

        best_missed = max(missed_stocks, key=lambda x: x.max_gain_pct) if missed_stocks else None
        worst_bought = min(bought_stocks, key=lambda x: x.actual_pnl_pct) if bought_stocks else None
        best_schema_b_missed = (
            max(schema_b_missed, key=lambda x: x.max_gain_pct) if schema_b_missed else None
        )

        # 双引擎统计
        dual_stocks = [s for s in bought_stocks if s.paper_pnl_pct != 0 or s.friction_pnl_pct != 0]
        avg_paper_pnl = (
            sum(s.paper_pnl_pct for s in dual_stocks) / len(dual_stocks) if dual_stocks else 0.0
        )
        avg_friction_pnl = (
            sum(s.friction_pnl_pct for s in dual_stocks) / len(dual_stocks) if dual_stocks else 0.0
        )
        avg_alpha_lost = avg_paper_pnl - avg_friction_pnl

        # 决策事件流统计
        buy_events = [e for e in self.decision_log if e.action == 'BUY']
        sell_events = [e for e in self.decision_log if e.action == 'SELL']
        watch_events = [e for e in self.decision_log if e.action == 'WATCH']

        return {
            'session_id': self.session_id,
            'schema': self.schema,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_appeared': len(all_stocks),
                'bought_count': len(bought_stocks),
                'missed_count': len(missed_stocks),
                'win_rate_pct': (
                    len([s for s in bought_stocks if s.actual_pnl_pct > 0])
                    / len(bought_stocks) * 100 if bought_stocks else 0.0
                ),
                'avg_bought_pnl_pct': (
                    sum(s.actual_pnl_pct for s in bought_stocks) / len(bought_stocks)
                    if bought_stocks else 0.0
                ),
                'avg_missed_gain_pct': (
                    sum(s.max_gain_pct for s in missed_stocks) / len(missed_stocks)
                    if missed_stocks else 0.0
                ),
                'best_missed': self._lifecycle_to_summary(best_missed) if best_missed else None,
                'worst_bought': self._lifecycle_to_summary(worst_bought) if worst_bought else None,
            },
            'schema_b_analysis': {
                'schema_b_eligible_count': len(schema_b_eligible),
                'schema_b_bought_count': len([s for s in schema_b_eligible if s.was_bought]),
                'schema_b_missed_count': len(schema_b_missed),
                'best_schema_b_missed': (
                    self._lifecycle_to_summary(best_schema_b_missed)
                    if best_schema_b_missed else None
                ),
                'schema_b_conversion_rate_pct': (
                    len([s for s in schema_b_eligible if s.was_bought])
                    / len(schema_b_eligible) * 100 if schema_b_eligible else 0.0
                ),
                'note': (
                    '方案B: 只有同时满足「物理触发信号 + 分位数入场条件」的票才具备买入资格。'
                    '此处列出所有具备资格的票，无论最终是否买入。'
                )
            },
            'dual_engine_comparison': {
                'tracked_count': len(dual_stocks),
                'avg_paper_pnl_pct': round(avg_paper_pnl, 3),
                'avg_friction_pnl_pct': round(avg_friction_pnl, 3),
                'avg_alpha_lost_to_friction_pp': round(avg_alpha_lost, 3),
                'verdict': (
                    '摩擦可控' if abs(avg_alpha_lost) < 1.0
                    else f'摩擦过大: 平均损耗 {avg_alpha_lost:.2f}pp，建议检查滑点模型'
                ),
                'per_stock': [
                    {
                        'code': s.code,
                        'paper_pnl_pct': round(s.paper_pnl_pct, 3),
                        'friction_pnl_pct': round(s.friction_pnl_pct, 3),
                        'alpha_lost_pp': round(s.alpha_lost_to_friction, 3)
                    }
                    for s in dual_stocks
                ]
            },
            'decision_log_summary': {
                'total_frames': len(self.decision_log),
                'buy_count': len(buy_events),
                'sell_count': len(sell_events),
                'watch_count': len(watch_events),
                'buy_events': [e.to_dict() for e in buy_events],
                'sell_events': [e.to_dict() for e in sell_events],
            },
            'all_stocks': [
                s.to_dict()
                for s in sorted(all_stocks, key=lambda x: x.peak_score, reverse=True)
            ],
            'scan_validation': self._validation_result,
        }

    def _lifecycle_to_summary(self, lifecycle: StockLifecycle) -> Dict:
        return {
            'code': lifecycle.code,
            'peak_score': lifecycle.peak_score,
            'first_appear_price': lifecycle.first_appear_price,
            'max_gain_pct': round(lifecycle.max_gain_pct, 3),
            'actual_pnl_pct': round(lifecycle.actual_pnl_pct, 3),
            'was_bought': lifecycle.was_bought,
            'schema_b_eligible': lifecycle.schema_b_eligible,
            'had_physical_trigger': lifecycle.had_physical_trigger,
            'trigger_first_time': lifecycle.trigger_first_time,
            'skip_reason': lifecycle.skip_reason,
            'alpha_lost_to_friction': round(lifecycle.alpha_lost_to_friction, 3),
        }

    def get_missed_opportunities(self) -> List[StockLifecycle]:
        """获取错过的机会（max_gain_pct > 3% 的未买入票）"""
        missed = [
            s for s in self.registry.values()
            if not s.was_bought and s.max_gain_pct > 3.0
        ]
        return sorted(missed, key=lambda x: x.max_gain_pct, reverse=True)

    def get_bought_stocks(self) -> List[StockLifecycle]:
        return [s for s in self.registry.values() if s.was_bought]

    def get_stats(self) -> Dict:
        all_stocks = list(self.registry.values())
        bought = [s for s in all_stocks if s.was_bought]
        return {
            'session_id': self.session_id,
            'total_tracked': len(all_stocks),
            'bought_count': len(bought),
            'missed_count': len(all_stocks) - len(bought),
            'win_rate': (
                len([s for s in bought if s.actual_pnl_pct > 0]) / len(bought) * 100
                if bought else 0.0
            ),
            'avg_score': (
                sum(s.peak_score for s in all_stocks) / len(all_stocks)
                if all_stocks else 0.0
            ),
            'decision_events': len(self.decision_log),
        }

    def export_to_json(self, filepath: str):
        report = self.get_full_report()
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"[OK] V2.0 全榜追踪战报已导出: {filepath}")

    def export_to_csv(self, filepath: str):
        all_stocks = list(self.registry.values())
        if not all_stocks:
            logger.warning("[WARN] 无追踪数据可导出")
            return
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        fieldnames = [
            'code', 'first_appear_time', 'last_appear_time', 'appear_count',
            'peak_score', 'first_appear_price', 'peak_price', 'final_price',
            'max_gain_pct', 'final_gain_pct', 'was_bought', 'buy_price',
            'sell_price', 'actual_pnl_pct', 'missed_gain_pct', 'peak_trigger_type',
            'had_physical_trigger', 'trigger_first_time', 'trigger_first_price',
            'trigger_peak_confidence', 'schema_b_eligible',
            'paper_buy_price', 'paper_sell_price', 'paper_pnl_pct',
            'friction_pnl_pct', 'alpha_lost_to_friction', 'skip_reason'
        ]
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for stock in all_stocks:
                writer.writerow(asdict(stock))
        logger.info(f"[OK] CSV 已导出: {filepath}")
