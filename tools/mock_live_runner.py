#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全息战场模拟器 V2.0 — 工业级双引擎全榜追踪回演
================================================================

架构升级：
  - StockStateBuffer:     每只股票的历史缓冲区（TriggerValidator依赖）
  - TriggerValidator:     物理买点三维确认（弹弓/阶梯/点火），打分前注入
  - TradeDecisionBrain:   统一决策大脑（相对分位数动态入场），接收整个榜单
  - UniversalTracker:     全榜生命周期追踪（错过了什么）
  - PaperTradeEngine:     零摩擦理想对照组
  - MockExecutionManager: 真实摩擦撮合（滑点/流动性/微观防爆）
  - 工业级战报:            双引擎对比 + 全榜生命周期 + Alpha计算

使用方法：
    python tools/mock_live_runner.py --date 20260310
    python tools/mock_live_runner.py --start_date 20260310 --end_date 20260314
"""

import sys
import argparse
import logging
import json
import bisect
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.core.config_manager import get_config_manager
from logic.data_providers.true_dictionary import get_true_dictionary
from logic.strategies.kinetic_core_engine import KineticCoreEngine
from logic.execution.mock_execution_manager import MockExecutionManager, TriggerType
from logic.execution.trade_decision_brain import TradeDecisionBrain
from logic.execution.universal_tracker import UniversalTracker
from logic.execution.paper_trade_engine import PaperTradeEngine
from research_lab.trigger_validator import TriggerValidator
from logic.core.sandbox_manager import SandboxManager

logger = logging.getLogger(__name__)


# ============================================================
# 每只股票的历史缓冲区 — TriggerValidator 的数据基础
# ============================================================

class StockStateBuffer:
    """
    单只股票的滚动历史状态缓冲区。

    TriggerValidator.check_all_triggers() 需要：
      - price_history        最近N分钟价格序列
      - recent_mfe_list      最近N分钟MFE序列
      - recent_volume_ratios 最近N分钟量比序列
      - vwap                 当前成本均价（累计额/累计量）

    这些数据在原 mock_live_runner 里完全缺失，此类负责维护。
    """
    WINDOW = 30  # 保留30分钟历史

    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.price_history: List[float] = []
        self.mfe_history: List[float] = []
        self.volume_ratio_history: List[float] = []
        self.last_price: float = 0.0
        self.last_mfe: float = 0.0

    def update(self, price: float, mfe: float, sustain_ratio: float):
        """每分钟调用一次，推入最新数据"""
        self.price_history.append(price)
        self.mfe_history.append(mfe)
        self.volume_ratio_history.append(sustain_ratio)
        self.last_price = price
        self.last_mfe = mfe

        if len(self.price_history) > self.WINDOW:
            self.price_history.pop(0)
            self.mfe_history.pop(0)
            self.volume_ratio_history.pop(0)

    def get_vwap(self, tick_list: List[Dict], current_time: datetime, parse_fn,
                 time_index: List = None) -> float:
        """
        计算当日截止当前时刻的VWAP（成交额加权均价）。
        QMT amount 是累计值，取最新快照即可。
        使用 bisect 二分查找替代线性扫描（O(log n) vs O(n)）
        """
        if not tick_list:
            return self.last_price

        if time_index:
            # 使用预解析时间索引 + bisect
            idx = bisect.bisect_right(time_index, current_time) - 1
            if idx >= 0:
                total_amount = tick_list[idx]['amount']
                total_volume = tick_list[idx].get('volume', 0)
                if total_volume > 0:
                    return total_amount / total_volume
        else:
            # 回退到线性扫描（兼容旧调用）
            total_amount = 0.0
            total_volume = 0
            for tick in tick_list:
                try:
                    if parse_fn(tick['time']) <= current_time:
                        total_amount = tick['amount']
                        total_volume = tick.get('volume', 0)
                except Exception:
                    continue
            if total_volume > 0:
                return total_amount / total_volume
        return self.last_price

    def get_current_slope(self) -> float:
        """最近3分钟价格斜率"""
        if len(self.price_history) < 3:
            return 0.0
        base = self.price_history[-3]
        if base <= 0:
            return 0.0
        return (self.price_history[-1] - base) / base


# ============================================================
# MockLiveRunner V2.0
# ============================================================

class MockLiveRunner:
    """
    全息战场模拟器 V2.0

    职责：数据加载 + 时间轴驱动 + 缓冲区维护 + 帧分发
    决策：完全交给 TradeDecisionBrain（不在 Runner 里写任何 if 买/卖逻辑）
    """

    def __init__(
        self,
        target_date: str,
        stock_list: List[str] = None,
        initial_capital: float = 100_000.0,
        sandbox: SandboxManager = None
    ):
        self.target_date = target_date
        self.stock_list = stock_list or []
        self.config_manager = get_config_manager()

        # 沙盒
        self.sandbox = sandbox or SandboxManager(mode="backtest")

        # ── 打分引擎（单例，禁止循环内实例化）
        self.kinetic_engine = KineticCoreEngine()

        # ── TriggerValidator（独立实例，每只股票喂缓冲区数据）
        self.trigger_validator = TriggerValidator()

        # ── 决策大脑（接收整个榜单，返回 BUY/SELL/HOLD）
        self.decision_brain = TradeDecisionBrain()

        # ── 真实摩擦撮合引擎
        self.execution_manager = MockExecutionManager(
            initial_capital=initial_capital,
            max_position_ratio=1.0
        )

        # ── 零摩擦理想对照引擎
        self.paper_engine = PaperTradeEngine(initial_capital=initial_capital)

        # ── 全榜生命周期追踪器
        self.universal_tracker = UniversalTracker()

        # ── Tick数据 & 流通盘
        self.tick_queues: Dict[str, List[Dict]] = {}
        self.tick_time_index: Dict[str, List[datetime]] = {}  # 预解析时间戳列表（用于bisect）
        self.float_volumes: Dict[str, float] = {}

        # ── 每只股票的历史状态缓冲区（TriggerValidator依赖）
        self.stock_buffers: Dict[str, StockStateBuffer] = {}

        # ── 榜单快照
        self.leaderboard: Dict[str, Dict] = {}

        # ── 每分钟Top10审计台账
        self.daily_top10_ledger: List[Dict] = []

        # ── T+1锁 {stock_code: buy_date}
        self.t1_lock: Dict[str, str] = {}

        # ── 单吊锁（真实摩擦引擎）
        self.has_bought_today: bool = False

        # ── 单吊锁（零摩擦引擎）
        self.paper_bought_today: bool = False

        logger.info(
            f"[MockLiveRunner V2.0] date={target_date}  "
            f"capital=¥{initial_capital:,.0f}  sandbox={self.sandbox.get_run_id()}"
        )

    # ============================================================
    # 数据加载
    # ============================================================

    def load_tick_data(self, stock_code: str) -> bool:
        """加载单只股票Tick + 真实流通盘"""
        try:
            import xtquant.xtdata as xtdata

            tick_df = xtdata.get_local_data(
                field_list=[],
                stock_list=[stock_code],
                period='tick',
                start_time=f'{self.target_date}092500',
                end_time=f'{self.target_date}150000'
            )
            if tick_df is None or stock_code not in tick_df or tick_df[stock_code].empty:
                logger.warning(f"[load_tick] {stock_code} 无Tick数据")
                return False

            df = tick_df[stock_code]
            tick_list = []
            for _, row in df.iterrows():
                try:
                    raw_time = row.get('time', 0)
                    _ = self._parse_tick_time(raw_time)
                    tick = {
                        'time':          raw_time,
                        'price':         float(row.get('lastPrice', row.get('price', 0))),
                        'volume':        int(row.get('volume', 0)),
                        'amount':        float(row.get('amount', 0)),
                        'high':          float(row.get('high', 0)),
                        'low':           float(row.get('low', 0)),
                        'open':          float(row.get('open', 0)),
                        'lastClose':     float(row.get('lastClose', row.get('preClose', 0))),
                        'limitUpPrice':  float(row.get('limitUpPrice', 0)),
                        'limitDownPrice':float(row.get('limitDownPrice', 0)),
                        'askPrice1':     float(row.get('askPrice1', 0)),
                        'bidPrice1':     float(row.get('bidPrice1', 0)),
                    }
                    if tick['amount'] > 0 and tick['price'] > 0:
                        tick_list.append(tick)
                except Exception:
                    continue

            self.tick_queues[stock_code] = tick_list

            # 预解析时间戳列表（用于bisect二分查找，O(log n)替代O(n)线性扫描）
            time_list = [self._parse_tick_time(t['time']) for t in tick_list]
            self.tick_time_index[stock_code] = time_list

            # 真实流通盘（QMT FloatVolume 单位=股，无需转换）
            try:
                detail = xtdata.get_instrument_detail(stock_code)
                fv = detail.get('FloatVolume', 0) if detail else 0
                self.float_volumes[stock_code] = fv if fv and fv > 0 else 0
            except Exception as e:
                logger.warning(f"[load_tick] {stock_code} 流通盘失败: {e}")
                self.float_volumes[stock_code] = 0

            # 初始化该股票的历史缓冲区
            self.stock_buffers[stock_code] = StockStateBuffer(stock_code)

            logger.info(f"[load_tick] {stock_code} {len(tick_list)}个Tick  "
                        f"流通盘={self.float_volumes[stock_code]/1e8:.2f}亿股")
            return True

        except Exception as e:
            logger.error(f"[load_tick] {stock_code} 失败: {e}")
            return False

    # ============================================================
    # 主循环
    # ============================================================

    def run_mock_session(self):
        """运行完整交易时段"""
        print(f"\n{'='*72}")
        print(f"[全息战场 V2.0] {self.target_date}  双引擎 | TriggerValidator | 全榜追踪")
        print(f"{'='*72}")
        print(f"🔴 真实摩擦: 滑点千1~千2 | 流动性33%拒绝 | 微观防爆")
        print(f"🔵 零摩擦  : 零滑点 | 瞬时成交 | Alpha对照")
        print(f"🧭 买点验证: 引力弹弓 | 阶梯突破 | 真空点火")
        print(f"{'='*72}\n")

        loaded = sum(1 for s in self.stock_list if self.load_tick_data(s))
        if loaded == 0:
            print("[ERR] 无Tick数据，终止")
            return
        print(f"成功加载 {loaded}/{len(self.stock_list)} 只股票\n")

        # 竞价阶段榜单
        auction_t = datetime.strptime(f"{self.target_date}09:25:00", "%Y%m%d%H:%M:%S")
        self._calculate_leaderboard_at_time(auction_t)

        time_points = self._build_time_axis()
        key_events = {
            '09:30:00': '开盘', '11:30:00': '早盘结束',
            '13:00:00': '午盘开盘', '15:00:00': '收盘'
        }
        last_print_min = -99

        for current_time in time_points:
            ts = current_time.strftime('%H:%M:%S')
            if ts in key_events:
                print(f"\n⏰ [{ts}] {key_events[ts]}")
                print("-" * 50)

            # Step1: 计算榜单
            self._calculate_leaderboard_at_time(current_time)

            # Step2: 按分数排序
            sorted_board = sorted(
                self.leaderboard.items(),
                key=lambda x: x[1]['score'], reverse=True
            )

            # Step3: 更新每只股票的历史缓冲区（TriggerValidator的数据基础）
            self._update_stock_buffers(sorted_board)

            # Step4: 记录每分钟Top10到审计台账
            self._record_top10_to_ledger(current_time, sorted_board)

            # Step5: 构建带 trigger 信号的榜单 → 喂给 Brain → 双引擎执行
            self._run_decision_and_execute(current_time, sorted_board)

            # Step6: 持仓监控（双引擎）
            self._monitor_positions(current_time)

            cm = current_time.hour * 60 + current_time.minute
            if abs(cm - last_print_min) >= 15:
                self._print_status_brief(current_time, sorted_board)
                last_print_min = cm

        print(f"\n⏰ [15:00:00] 收盘")
        print("-" * 50)
        self._print_final_report()

    # ============================================================
    # 缓冲区维护
    # ============================================================

    def _update_stock_buffers(self, sorted_board: List[Tuple[str, Dict]]):
        """每帧推入最新数据到每只股票的历史缓冲区"""
        for code, data in sorted_board:
            buf = self.stock_buffers.get(code)
            if buf is None:
                buf = StockStateBuffer(code)
                self.stock_buffers[code] = buf
            buf.update(
                price=data['price'],
                mfe=data.get('mfe', 0.0),
                sustain_ratio=data.get('sustain_ratio', 1.0)
            )

    # ============================================================
    # 核心决策入口
    # ============================================================

    def _run_decision_and_execute(
        self,
        current_time: datetime,
        sorted_board: List[Tuple[str, Dict]]
    ):
        """
        统一决策入口 — 职责严格分离

        流程：
          1. 对榜单每只股票调用 TriggerValidator.check_all_triggers()
          2. 把 trigger_type / trigger_confidence 注入榜单条目
          3. 整个榜单喂给 TradeDecisionBrain.on_new_frame()
          4. Brain 返回决策事件 → 分发给双引擎
          5. 把 executed_trade + decision_context 喂给 UniversalTracker.on_frame()
        """
        if not sorted_board:
            return

        # ── Phase A: TriggerValidator 为每只股票计算物理买点信号
        enriched_targets: List[Dict] = []

        for rank, (code, data) in enumerate(sorted_board, 1):
            buf = self.stock_buffers.get(code)
            tick = data.get('tick', {})
            prev_close = tick.get('lastClose', data['price'])

            # 计算 VWAP（成本均价）
            vwap = 0.0
            if buf:
                vwap = buf.get_vwap(
                    self.tick_queues.get(code, []), current_time, self._parse_tick_time,
                    time_index=self.tick_time_index.get(code, [])
                )

            volume_ratio = data.get('sustain_ratio', 1.0)
            trigger_type = 'none'
            trigger_confidence = 0.0
            trigger_signal = None

            if buf and len(buf.price_history) >= 3:
                trigger_signal = self.trigger_validator.check_all_triggers(
                    stock_code=code,
                    current_price=data['price'],
                    prev_close=prev_close,
                    vwap=vwap if vwap > 0 else data['price'],
                    volume_ratio=volume_ratio,
                    current_mfe=data.get('mfe', 0.0),
                    recent_mfe_list=list(buf.mfe_history),
                    price_history=list(buf.price_history),
                    recent_volume_ratios=list(buf.volume_ratio_history),
                    current_slope=buf.get_current_slope(),
                    timestamp=current_time
                )

            if trigger_signal:
                trigger_type = trigger_signal.trigger_type
                trigger_confidence = trigger_signal.confidence

            dbg = data.get('debug_metrics', {})
            ignition_prob = dbg.get('ignition_prob', 0.0)

            enriched_targets.append({
                'code': code,
                'score': data['score'],
                'price': data['price'],
                'trigger_type': trigger_type,
                'trigger_confidence': trigger_confidence,
                'ignition_prob': ignition_prob,
                'mfe': data.get('mfe', 0.0),
                'sustain_ratio': data.get('sustain_ratio', 0.0),
            })

        # ── Phase B: 决策大脑
        held_price = 0.0
        if self.execution_manager.positions:
            held_code = next(iter(self.execution_manager.positions))
            held_pos = self.execution_manager.positions[held_code]
            held_price = held_pos.current_price if held_pos.current_price > 0 else held_pos.entry_price

        decision = self.decision_brain.on_new_frame(
            top_targets=enriched_targets,
            current_time=current_time,
            held_stock_current_price=held_price
        )

        # ── Phase C: 双引擎执行
        executed_trade: Optional[Dict] = None
        action = decision.get('action') if decision else None
        target_code = decision.get('stock_code') if decision else None
        reason = decision.get('reason', '') if decision else ''
        trigger_t = decision.get('trigger_type', 'none') if decision else 'none'

        if action == 'BUY' and target_code:
            executed_trade = self._execute_buy(
                current_time, target_code, enriched_targets, reason, trigger_t, decision
            )
        elif action == 'SELL' and target_code:
            executed_trade = self._execute_sell(
                current_time, target_code, enriched_targets, reason
            )

        # ── Phase D: 喂给 UniversalTracker
        # 传入整个榜单 + 本帧成交结果 + 大脑决策上下文（含 p90_threshold/median_score/relative_rank）
        self.universal_tracker.on_frame(
            top_targets=enriched_targets[:10],
            current_time=current_time,
            executed_trade=executed_trade,
            decision_context=decision
        )

    # ── 买入执行（双引擎）
    def _execute_buy(
        self,
        current_time: datetime,
        stock_code: str,
        enriched_targets: List[Dict],
        reason: str,
        trigger_type: str,
        decision: Dict
    ) -> Optional[Dict]:
        """
        Returns:
            executed_trade dict（供 UniversalTracker.on_frame 使用），失败返回 None
        """
        target = next((t for t in enriched_targets if t['code'] == stock_code), None)
        if target is None:
            return None
        price = target['price']
        score = target['score']
        tick_data = self.leaderboard.get(stock_code, {}).get('tick', {})
        minute_volume = self._get_minute_volume(stock_code, current_time)

        executed_trade = None

        # 真实摩擦引擎
        if not self.has_bought_today:
            success, order = self.execution_manager.place_mock_order(
                stock_code=stock_code,
                last_price=price,
                direction='BUY',
                trigger_type=TriggerType.STATIC_SCORE,
                tick_data=tick_data,
                minute_volume=minute_volume
            )
            if success:
                self.has_bought_today = True
                self.t1_lock[stock_code] = self.target_date
                executed_trade = {
                    'action': 'BUY',
                    'stock_code': stock_code,
                    'price': price,
                    'reason': reason,
                    'trigger_type': trigger_type,
                    'score': score,
                    'engine': 'real'
                }
                print(
                    f"\n🔴 [真实买入] {stock_code} @ {price:.2f}  "
                    f"分数:{score:.0f}  trigger:{trigger_type}  {reason}"
                )
            else:
                print(f"\n⚠️  [真实买入拒绝] {stock_code} @ {price:.2f}  {reason}")

        # 零摩擦引擎
        if not self.paper_bought_today:
            paper_order = self.paper_engine.place_order(
                stock_code=stock_code,
                price=price,
                direction='BUY',
                trigger_type=trigger_type,
                timestamp=current_time
            )
            if paper_order:
                self.paper_bought_today = True
                if executed_trade is None:
                    executed_trade = {
                        'action': 'BUY',
                        'stock_code': stock_code,
                        'price': price,
                        'reason': reason,
                        'trigger_type': 'paper_no_friction',
                        'score': score,
                        'engine': 'paper'
                    }
                print(f"🔵 [纸面买入] {stock_code} @ {price:.2f}  {reason}")

        return executed_trade

    # ── 卖出执行（双引擎）
    def _execute_sell(
        self,
        current_time: datetime,
        stock_code: str,
        enriched_targets: List[Dict],
        reason: str
    ) -> Optional[Dict]:
        target = next((t for t in enriched_targets if t['code'] == stock_code), None)
        price = target['price'] if target else 0.0

        executed_trade = None

        # 真实摩擦引擎
        if stock_code in self.execution_manager.positions:
            if not price:
                price = self.execution_manager.positions[stock_code].current_price
            if self.t1_lock.get(stock_code) == self.target_date:
                logger.debug(f"[SELL拒绝] {stock_code} T+1锁，今日买入不可卖出")
            else:
                success, order = self.execution_manager.place_mock_order(
                    stock_code=stock_code, last_price=price, direction='SELL'
                )
                if success:
                    executed_trade = {
                        'action': 'SELL',
                        'stock_code': stock_code,
                        'price': price,
                        'reason': reason,
                        'engine': 'real'
                    }
                    print(f"\n🟢 [真实卖出] {stock_code} @ {price:.2f}  {reason}")

        # 零摩擦引擎
        if stock_code in self.paper_engine.positions:
            p = price or self.paper_engine.positions[stock_code]['cost_price']
            self.paper_engine.place_order(
                stock_code=stock_code, price=p, direction='SELL', timestamp=current_time
            )
            if executed_trade is None:
                executed_trade = {
                    'action': 'SELL',
                    'stock_code': stock_code,
                    'price': p,
                    'reason': reason,
                    'engine': 'paper'
                }

        return executed_trade

    # ============================================================
    # 榜单计算（与原版逻辑完全一致，消除重复代码）
    # ============================================================

    def _calculate_leaderboard_at_time(self, target_time: datetime):
        self.leaderboard.clear()

        for stock_code, tick_list in self.tick_queues.items():
            # 使用预解析时间索引 + bisect_right 二分查找（O(log n) 替代 O(n)）
            time_list = self.tick_time_index.get(stock_code, [])
            if not time_list or not tick_list:
                continue

            # 二分查找：找到 <= target_time 的最后一个 tick 索引
            idx = bisect.bisect_right(time_list, target_time) - 1
            if idx < 0:
                continue
            current_tick = tick_list[idx]

            total_amount = current_tick['amount']
            cutoff_5 = target_time - timedelta(minutes=5)
            cutoff_15 = target_time - timedelta(minutes=15)

            # 二分查找 5 分钟前的 tick
            idx_5 = bisect.bisect_right(time_list, cutoff_5) - 1
            amt_5ago = tick_list[idx_5]['amount'] if idx_5 >= 0 else 0.0

            # 二分查找 15 分钟前的 tick
            idx_15 = bisect.bisect_right(time_list, cutoff_15) - 1
            amt_15ago = tick_list[idx_15]['amount'] if idx_15 >= 0 else 0.0

            true_flow_5min = max(0.0, total_amount - amt_5ago)
            true_flow_15min = max(0.0, total_amount - amt_15ago)

            real_float_vol = self.float_volumes.get(stock_code, 0)
            if real_float_vol <= 0:
                logger.debug(f"[leaderboard] {stock_code} 流通盘缺失，跳过")
                continue

            try:
                result = self.kinetic_engine.calculate_true_dragon_score(
                    net_inflow=true_flow_5min * 0.5,
                    price=current_tick['price'],
                    prev_close=current_tick['lastClose'],
                    high=current_tick['high'],
                    low=current_tick['low'],
                    open_price=current_tick['open'],
                    flow_5min=true_flow_5min,
                    flow_15min=true_flow_15min,
                    flow_5min_median_stock=5_000_000,
                    space_gap_pct=10.0,
                    float_volume_shares=real_float_vol,
                    current_time=target_time,
                    total_amount=total_amount,
                    total_volume=int(total_amount / current_tick['price']) if current_tick['price'] > 0 else 0,
                    limit_up_queue_amount=0,
                    mode='scan',
                    stock_code=stock_code
                )
                if isinstance(result, tuple) and len(result) >= 6:
                    score, sustain, inflow, ratio_stock, mfe, dbg = result[:6]
                elif isinstance(result, tuple) and len(result) >= 5:
                    score, sustain, inflow, ratio_stock, mfe = result[:5]
                    dbg = {}
                else:
                    continue

                self.leaderboard[stock_code] = {
                    'score': score, 'price': current_tick['price'],
                    'amount': total_amount, 'mfe': mfe,
                    'sustain_ratio': sustain, 'inflow_ratio': inflow,
                    'tick': current_tick, 'debug_metrics': dbg,
                    'true_flow_5min': true_flow_5min,
                    'true_flow_15min': true_flow_15min,
                }
            except Exception as e:
                logger.warning(f"[leaderboard] {stock_code} 打分失败: {e}")

    # ============================================================
    # 持仓监控（双引擎）
    # ============================================================

    def _monitor_positions(self, current_time: datetime):
        """监控真实引擎持仓 + 同步零摩擦引擎价格"""

        # ── 真实摩擦引擎
        for stock_code, pos in list(self.execution_manager.positions.items()):
            tick_list = self.tick_queues.get(stock_code, [])
            time_list = self.tick_time_index.get(stock_code, [])
            if not tick_list or not time_list:
                continue

            # bisect 二分查找（O(log n) 替代 O(n) reversed 扫描）
            idx = bisect.bisect_right(time_list, current_time) - 1
            if idx < 0:
                continue
            current_tick = tick_list[idx]

            pos.current_price = current_tick['price']
            pos.max_price = max(getattr(pos, 'max_price', pos.current_price), pos.current_price)

            # T+1锁：今日买入不止损
            if self.t1_lock.get(stock_code) == self.target_date:
                continue

            real_float_vol = self.float_volumes.get(stock_code, 0)
            if real_float_vol <= 0:
                logger.warning(f"[monitor] {stock_code} 流通盘缺失，跳过动能更新")
                continue

            cutoff_5 = current_time - timedelta(minutes=5)
            idx_5 = bisect.bisect_right(time_list, cutoff_5) - 1
            amt_5ago = tick_list[idx_5]['amount'] if idx_5 >= 0 else 0.0
            true_flow_5 = max(0.0, current_tick['amount'] - amt_5ago)
            inflow_ratio = (true_flow_5 * 0.5) / (real_float_vol * current_tick['price']) * 100 \
                if real_float_vol > 0 and current_tick['price'] > 0 else 0
            prev_close = current_tick.get('lastClose', current_tick['price'])
            amplitude = (current_tick['high'] - current_tick['low']) / prev_close if prev_close > 0 else 0
            mfe = amplitude / max(inflow_ratio, 0.01)

            entry_time = datetime.strptime(pos.entry_time, '%Y-%m-%d %H:%M:%S')
            minutes_elapsed = int((current_time - entry_time).total_seconds() / 60)

            stopped, reason = self.execution_manager.check_micro_guard(
                stock_code, current_tick['price'], mfe, minutes_elapsed
            )
            if stopped:
                success, _ = self.execution_manager.place_mock_order(
                    stock_code=stock_code,
                    last_price=current_tick['price'],
                    direction='SELL'
                )
                if success:
                    # 通知 UniversalTracker 止损卖出
                    stop_trade = {
                        'action': 'SELL',
                        'stock_code': stock_code,
                        'price': current_tick['price'],
                        'reason': f'微观防爆: {reason}',
                        'engine': 'real'
                    }
                    self.universal_tracker.on_frame(
                        top_targets=[],
                        current_time=current_time,
                        executed_trade=stop_trade,
                        decision_context=None
                    )
                    logger.warning(f"⚠️ [微观防爆] {stock_code} @ {current_tick['price']:.2f} {reason}")

        # ── 零摩擦引擎：只更新价格
        for stock_code in list(self.paper_engine.positions.keys()):
            tick_list = self.tick_queues.get(stock_code, [])
            time_list = self.tick_time_index.get(stock_code, [])
            if tick_list and time_list:
                idx = bisect.bisect_right(time_list, current_time) - 1
                if idx >= 0:
                    self.paper_engine.update_position_price(stock_code, tick_list[idx]['price'])

    # ============================================================
    # 工具方法
    # ============================================================

    def _build_time_axis(self) -> List[datetime]:
        start = datetime.strptime(f"{self.target_date}09:30:00", "%Y%m%d%H:%M:%S")
        end   = datetime.strptime(f"{self.target_date}14:57:00", "%Y%m%d%H:%M:%S")
        lunch_s = datetime.strptime(f"{self.target_date}11:31:00", "%Y%m%d%H:%M:%S")
        lunch_e = datetime.strptime(f"{self.target_date}13:00:00", "%Y%m%d%H:%M:%S")
        points, cur = [], start
        while cur <= end:
            if not (lunch_s <= cur < lunch_e):
                points.append(cur)
            cur += timedelta(minutes=1)
        return points

    def _get_minute_volume(self, stock_code: str, current_time: datetime) -> float:
        tick_list = self.tick_queues.get(stock_code, [])
        time_list = self.tick_time_index.get(stock_code, [])
        if not tick_list or not time_list:
            return 0.0
        ms = current_time.replace(second=0, microsecond=0)
        me = ms + timedelta(minutes=1)
        idx_ms = bisect.bisect_right(time_list, ms) - 1
        idx_me = bisect.bisect_right(time_list, me) - 1
        prev_amt = tick_list[idx_ms]['amount'] if idx_ms >= 0 else 0.0
        curr_amt = tick_list[idx_me]['amount'] if idx_me >= 0 else 0.0
        return max(0.0, curr_amt - prev_amt)

    def _parse_tick_time(self, time_val) -> datetime:
        """物理级时间戳解析（与原版完全一致）"""
        try:
            if isinstance(time_val, (int, float)):
                if time_val > 1_000_000_000_000:
                    dt = pd.to_datetime(time_val, unit='ms')
                    return dt.tz_localize('UTC').tz_convert('Asia/Shanghai').replace(tzinfo=None).to_pydatetime()
                elif time_val > 20_000_000_000_000:
                    return datetime.strptime(str(int(time_val)), "%Y%m%d%H%M%S")
                else:
                    return pd.to_datetime(time_val, unit='s').to_pydatetime()
            ts = str(time_val).strip()
            if ts.isdigit() and len(ts) >= 13:
                return pd.to_datetime(int(ts), unit='ms').to_pydatetime()
            if len(ts) == 6:
                return datetime.strptime(f"{self.target_date}{ts}", "%Y%m%d%H%M%S")
            elif len(ts) == 14:
                return datetime.strptime(ts, "%Y%m%d%H%M%S")
            return pd.to_datetime(ts).to_pydatetime()
        except Exception as e:
            raise ValueError(f"无法解析时间戳: {time_val} → {e}")

    def _record_top10_to_ledger(
        self, current_time: datetime, sorted_board: List[Tuple[str, Dict]]
    ):
        for rank, (code, data) in enumerate(sorted_board[:10], 1):
            dbg = data.get('debug_metrics', {})
            self.daily_top10_ledger.append({
                'date': self.target_date, 'time': current_time.strftime('%H:%M:%S'),
                'rank': rank, 'code': code,
                'score': data['score'], 'price': data['price'],
                'mfe': data.get('mfe', 0), 'sustain': data.get('sustain_ratio', 0),
                'inflow_pct': data.get('inflow_ratio', 0),
                'mass_potential': dbg.get('mass_potential', 0),
                'velocity': dbg.get('velocity', 0),
                'kinetic_energy': dbg.get('base_kinetic_energy', 0),
                'friction': dbg.get('friction_multiplier', 0),
                'purity': dbg.get('purity_norm', 0),
                'change_pct': dbg.get('change_pct', 0),
            })

    def _print_status_brief(
        self, current_time: datetime, sorted_board: List[Tuple[str, Dict]]
    ):
        ts = current_time.strftime('%H:%M')
        if sorted_board:
            top1_code, top1_data = sorted_board[0]
            buf = self.stock_buffers.get(top1_code)
            trigger_hint = ''
            if buf and len(buf.price_history) >= 3:
                sig = self.trigger_validator.check_all_triggers(
                    stock_code=top1_code,
                    current_price=top1_data['price'],
                    prev_close=top1_data['tick'].get('lastClose', top1_data['price']),
                    vwap=buf.get_vwap(
                        self.tick_queues.get(top1_code, []), current_time, self._parse_tick_time,
                        time_index=self.tick_time_index.get(top1_code, [])
                    ),
                    volume_ratio=top1_data.get('sustain_ratio', 1.0),
                    current_mfe=top1_data.get('mfe', 0.0),
                    recent_mfe_list=list(buf.mfe_history),
                    price_history=list(buf.price_history),
                    recent_volume_ratios=list(buf.volume_ratio_history),
                    current_slope=buf.get_current_slope(),
                    timestamp=current_time
                )
                if sig:
                    trigger_hint = f" 🎯{sig.trigger_type}({sig.confidence:.2f})"
            print(f"  [{ts}] Top1: {top1_code} 分={top1_data['score']:.0f} "
                  f"价={top1_data['price']:.2f}{trigger_hint}")
        real_pos = self.execution_manager.positions
        if real_pos:
            for code, pos in real_pos.items():
                lock = "T+1锁" if self.t1_lock.get(code) == self.target_date else "可卖"
                pnl = (pos.current_price - pos.entry_price) / pos.entry_price * 100 \
                    if pos.entry_price > 0 else 0
                print(f"  [{ts}] 🔴 {code} {lock}  成本={pos.entry_price:.2f} "
                      f"现={pos.current_price:.2f}  PnL={pnl:+.2f}%")
        paper_pos = self.paper_engine.positions
        if paper_pos:
            for code in paper_pos:
                pnl = self.paper_engine.get_unrealized_pnl_pct(code)
                print(f"  [{ts}] 🔵 纸面持仓 {code}  PnL={pnl:+.2f}%")

    # ============================================================
    # 工业级战报（三层）
    # ============================================================

    def _print_final_report(self):
        """
        Layer 1: 双引擎账户对比 + Alpha
        Layer 2: 全榜生命周期（错过了什么）
        Layer 3: TriggerValidator 触发信号统计
        Layer 4: 沙盒持久化
        """
        print("\n" + "="*72)
        print(f"【工业级战报 V2.0 — {self.target_date}】  沙盒:{self.sandbox.get_run_id()}")
        print("="*72)

        # ── Layer 1A: 真实摩擦引擎
        real_report = self.execution_manager.get_performance_report()
        real_pos_value = sum(
            p.current_price * p.volume for p in self.execution_manager.positions.values()
        )
        real_total    = real_report.get('final_cash', 0) + real_pos_value
        real_init     = real_report.get('initial_capital', 100_000)
        real_pnl      = real_total - real_init
        real_pnl_pct  = real_pnl / real_init * 100 if real_init > 0 else 0

        print("\n🔴 [真实摩擦引擎]")
        print(f"   总资产: ¥{real_total:>12,.2f}  |  盈亏: {real_pnl_pct:>+7.2f}%  (¥{real_pnl:+,.2f})")
        print(f"   现金:   ¥{real_report.get('final_cash',0):>12,.2f}  |  持仓: ¥{real_pos_value:>10,.2f}")
        print(f"   胜率:   {real_report.get('win_rate',0):.1f}%  "
              f"({real_report.get('win_count',0)}胜/{real_report.get('loss_count',0)}负)")
        if self.execution_manager.positions:
            print("   持仓明细:")
            for code, pos in self.execution_manager.positions.items():
                pnl_p = (pos.current_price - pos.entry_price) / pos.entry_price * 100 \
                    if pos.entry_price > 0 else 0
                lock = "T+1锁" if self.t1_lock.get(code) == self.target_date else "可卖"
                print(f"     [{lock}] {code}  买¥{pos.entry_price:.2f} → 现¥{pos.current_price:.2f}  {pnl_p:+.2f}%")

        # ── Layer 1B: 零摩擦引擎（使用实际方法名）
        paper_report  = self.paper_engine.get_performance_report()
        paper_total   = self.paper_engine.get_total_asset()
        paper_pnl     = paper_total - real_init
        paper_pnl_pct = paper_pnl / real_init * 100 if real_init > 0 else 0

        print(f"\n🔵 [零摩擦理想对照]")
        print(f"   总资产: ¥{paper_total:>12,.2f}  |  盈亏: {paper_pnl_pct:>+7.2f}%  (¥{paper_pnl:+,.2f})")
        if self.paper_engine.positions:
            print("   持仓明细:")
            for code in self.paper_engine.positions:
                pnl = self.paper_engine.get_unrealized_pnl_pct(code)
                print(f"     {code}  PnL={pnl:+.2f}%")

        # ── Alpha
        alpha = real_pnl_pct - paper_pnl_pct
        tag = "✅ 真实引擎跑赢理想" if alpha >= 0 else "⚠️  摩擦成本侵蚀α"
        print(f"\n📊 Alpha = {alpha:+.2f}%  {tag}")

        # ── Bug#4修复：注入双引擎对比数据到UniversalTracker
        for code in list(self.execution_manager.positions.keys()) | set(self.paper_engine.positions.keys()):
            # 真实引擎数据
            real_pos = self.execution_manager.positions.get(code)
            friction_buy = real_pos.entry_price if real_pos else 0
            friction_sell = real_pos.current_price if real_pos else 0
            
            # 零摩擦引擎数据
            paper_pos = self.paper_engine.positions.get(code)
            paper_buy = paper_pos.get('entry_price', 0) if paper_pos else 0
            paper_sell = paper_pos.get('current_price', 0) if paper_pos else 0
            
            if friction_buy > 0 or paper_buy > 0:
                self.universal_tracker.inject_paper_trade_result(
                    stock_code=code,
                    paper_buy=paper_buy,
                    paper_sell=paper_sell,
                    friction_buy=friction_buy,
                    friction_sell=friction_sell
                )

        # ── Layer 2: 全榜生命周期
        print("\n" + "-"*72)
        print("📋 [全榜生命周期] — 所有上榜票的命运（错过了什么）")
        print("-"*72)
        universe_report = self.universal_tracker.get_full_report()
        all_stocks_raw = universe_report.get('all_stocks', [])
        # all_stocks 是 list[dict]，每个 dict 有 'code' 和 'max_gain_pct' 字段
        sorted_universe = sorted(
            all_stocks_raw,
            key=lambda x: x.get('max_gain_pct', 0), reverse=True
        )[:20]
        if sorted_universe:
            print(f"\n  {'代码':<10} {'首次上榜':<9} {'上榜价':>8} "
                  f"{'峰值涨幅':>10} {'末价涨幅':>10} {'买入方式':<14} {'备注'}")
            print("  " + "-"*74)
            for info in sorted_universe:
                code = info.get('code', 'N/A')
                bought_by = info.get('bought_by_engines', [])
                eng_str   = '+'.join(bought_by) if bought_by else '❌ 未买入'
                peak  = info.get('max_gain_pct', 0)
                final = info.get('final_gain_pct', 0)
                note  = f'⭐ 错过 +{peak:.1f}%' if peak >= 3 and not bought_by else ('✅ 持有' if bought_by else '')
                print(f"  {code:<10} {info.get('first_appear_time','N/A'):<9} "
                      f"{info.get('first_appear_price',0):>8.2f} "
                      f"{peak:>+9.1f}% {final:>+9.1f}%  {eng_str:<14} {note}")
        tracked = universe_report.get('total_tracked', 0)
        bought  = universe_report.get('bought_count', 0)
        missed  = universe_report.get('total_missed_gain_pct', 0)
        print(f"\n  追踪:{tracked}只  买入:{bought}只  最大可能错过收益:{missed:+.1f}%")

        # ── Layer 3: TriggerValidator 触发信号统计
        print("\n" + "-"*72)
        print("🧭 [TriggerValidator] 物理买点触发信号统计")
        print("-"*72)
        tv_report = self.trigger_validator.generate_report()
        if 'error' not in tv_report:
            print(f"  总触发信号: {tv_report.get('total_signals', 0)}")
            for ttype, stats in tv_report.get('by_type', {}).items():
                print(f"  [{ttype}]  次数:{stats['count']}  "
                      f"5min胜率:{stats['win_rate_5min']:.0f}%  "
                      f"15min均收益:{stats['avg_return_15min']:+.2f}%")
        else:
            print("  本日无已验证触发信号（需第二天才能回填后续价格）")

        print("\n" + "="*72)

        # ── Layer 4: 沙盒持久化
        if self.daily_top10_ledger:
            self.sandbox.save_daily_ledger(self.target_date, self.daily_top10_ledger)

        battle_data = {
            'date': self.target_date,
            'sandbox_id': self.sandbox.get_run_id(),
            'real_engine': {
                'total_value': real_total, 'cash': real_report.get('final_cash', 0),
                'position_value': real_pos_value, 'pnl': real_pnl, 'pnl_pct': real_pnl_pct,
                'win_rate': real_report.get('win_rate', 0),
            },
            'paper_engine': {
                'total_value': paper_total, 'pnl': paper_pnl, 'pnl_pct': paper_pnl_pct
            },
            'alpha': alpha,
            'universe_report': universe_report,
            'trigger_report': tv_report,
        }
        self.sandbox.save_battle_report_json(self.target_date, battle_data)

        md = self._generate_markdown_report(
            real_total, real_pos_value, real_report, real_pnl, real_pnl_pct,
            paper_total, paper_pnl, paper_pnl_pct, alpha, sorted_universe, tv_report
        )
        self.sandbox.save_battle_report_md(self.target_date, md)
        print(f"\n📁 档案已存入沙盒: {self.sandbox.get_sandbox_root()}")

    def _generate_markdown_report(
        self,
        real_total, real_pos_value, real_report, real_pnl, real_pnl_pct,
        paper_total, paper_pnl, paper_pnl_pct, alpha, sorted_universe, tv_report
    ) -> str:
        lines = [
            f"# 全息战报 V2.0 — {self.target_date}\n",
            f"> 沙盒: `{self.sandbox.get_run_id()}`  "
            f"生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            "## 双引擎对比\n",
            "| 引擎 | 总资产 | 盈亏% | 备注 |",
            "|------|--------|-------|------|",
            f"| 🔴真实摩擦 | ¥{real_total:,.2f} | {real_pnl_pct:+.2f}% | "
            f"胜率{real_report.get('win_rate',0):.1f}% |",
            f"| 🔵零摩擦对照 | ¥{paper_total:,.2f} | {paper_pnl_pct:+.2f}% | — |",
            f"| **Alpha** | — | **{alpha:+.2f}%** | "
            f"{'✅跑赢' if alpha>=0 else '⚠️被摩擦侵蚀'} |\n",
            "## 全榜生命周期 Top20\n",
            "| 代码 | 首次上榜 | 上榜价 | 峰值 | 末涨幅 | 买入情况 |",
            "|------|---------|--------|------|--------|---------|",
        ]
        for info in sorted_universe:
            code = info.get('code', 'N/A')
            bought = '+'.join(info.get('bought_by_engines', [])) or '❌未买入'
            lines.append(
                f"| {code} | {info.get('first_appear_time','N/A')} | "
                f"¥{info.get('first_appear_price',0):.2f} | "
                f"{info.get('max_gain_pct',0):+.1f}% | "
                f"{info.get('final_gain_pct',0):+.1f}% | {bought} |"
            )
        lines.append("\n## TriggerValidator 触发统计\n")
        if 'by_type' in tv_report:
            lines += ["| 类型 | 次数 | 5min胜率 | 15min均收益 |",
                      "|------|------|---------|------------|"]
            for tt, st in tv_report['by_type'].items():
                lines.append(
                    f"| {tt} | {st['count']} | "
                    f"{st['win_rate_5min']:.0f}% | {st['avg_return_15min']:+.2f}% |"
                )
        return "\n".join(lines)


# ============================================================
# CLI 入口
# ============================================================

def _resolve_stock_list(date_str: str, stocks_param: str) -> List[str]:
    if stocks_param:
        return [s.strip() for s in stocks_param.split(',') if s.strip()]
    try:
        from logic.data_providers.universe_builder import UniverseBuilder
        pool, _ = UniverseBuilder(target_date=date_str).build()
        print(f"[UniverseBuilder] {date_str} 装载 {len(pool)} 只标的")
        return pool
    except Exception as e:
        print(f"[ERR] UniverseBuilder失败: {e}")
        return []


def run_single_day(args):
    stock_list = _resolve_stock_list(args.date, args.stocks)
    if not stock_list:
        print("[ERR] 股票池为空，终止")
        return
    sandbox = SandboxManager(mode="backtest")
    sandbox.save_config_snapshot({'date': args.date, 'capital': args.capital,
                                  'stock_count': len(stock_list)})
    runner = MockLiveRunner(args.date, stock_list, args.capital, sandbox)
    runner.run_mock_session()
    sandbox.print_sandbox_summary()


def run_continuous_backtest(args):
    try:
        from logic.utils.calendar_utils import get_trading_days_between
        trading_days = get_trading_days_between(args.start_date, args.end_date)
    except Exception:
        start = datetime.strptime(args.start_date, "%Y%m%d")
        end   = datetime.strptime(args.end_date,   "%Y%m%d")
        trading_days, cur = [], start
        while cur <= end:
            if cur.weekday() < 5:
                trading_days.append(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)

    sandbox = SandboxManager(mode="continuous_backtest")
    sandbox.save_config_snapshot({
        'start': args.start_date, 'end': args.end_date,
        'capital': args.capital, 'days': trading_days
    })
    print(f"\n🚀 多日连续回测 {args.start_date}→{args.end_date}  "
          f"{len(trading_days)}个交易日  沙盒:{sandbox.get_run_id()}")

    shared_manager = None
    daily_snapshots = []

    for i, date_str in enumerate(trading_days):
        print(f"\n{'='*72}\n📆 [{i+1}/{len(trading_days)}] {date_str}")
        stock_list = _resolve_stock_list(date_str, args.stocks)
        if not stock_list:
            print(f"[WARN] {date_str} 股票池为空，跳过")
            continue

        runner = MockLiveRunner(date_str, stock_list, args.capital, sandbox)
        if shared_manager is not None:
            runner.execution_manager = shared_manager
            shared_manager.carry_positions_to_next_day(
                f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            )
            # 跨日：继承持仓视为"已买入"，触发单吊锁
            runner.has_bought_today = len(shared_manager.positions) > 0
            # 跨日补充 float_volumes 缓存（持仓监控需要）
            for code in shared_manager.positions:
                if code not in runner.float_volumes:
                    runner.load_tick_data(code)

        runner.run_mock_session()
        shared_manager = runner.execution_manager

        snap = shared_manager.get_daily_snapshot(date_str)
        daily_snapshots.append(snap)
        print(f"📊 [{date_str}] 净值:¥{snap['total_value']:,.2f}  累计:{snap['pnl_pct']:+.2f}%")

    if daily_snapshots:
        print("\n" + "="*72)
        print("📈 资金曲线")
        print(f"{'日期':<12} {'现金':>12} {'持仓':>12} {'总资产':>12} {'累计收益':>10}")
        print("-"*62)
        for s in daily_snapshots:
            print(f"{s['date']:<12} ¥{s['cash']:>10,.2f} "
                  f"¥{s['position_value']:>10,.2f} "
                  f"¥{s['total_value']:>10,.2f} "
                  f"{s['pnl_pct']:>+9.2f}%")
        sandbox.save_equity_curve(daily_snapshots)
    sandbox.print_sandbox_summary()


def main():
    parser = argparse.ArgumentParser(description='全息战场模拟器 V2.0')
    parser.add_argument('--date',       type=str,   default='')
    parser.add_argument('--start_date', type=str,   default='')
    parser.add_argument('--end_date',   type=str,   default='')
    parser.add_argument('--stocks',     type=str,   default='')
    parser.add_argument('--capital',    type=float, default=100_000.0)
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    if args.start_date and args.end_date:
        run_continuous_backtest(args)
    elif args.date:
        run_single_day(args)
    else:
        print("[ERR] 必须指定 --date 或 --start_date + --end_date")


if __name__ == '__main__':
    main()
