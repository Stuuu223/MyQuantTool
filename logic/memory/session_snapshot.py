# -*- coding: utf-8 -*-
"""
SessionSnapshot - 盘中 Session 快照引擎

解决问题：live 引擎重启后变成「没有记忆的瞎子」

设计原则：
- 每 30 秒后台自动快照一次（daemon线程，不阻塞主循环）
- 重启时自动检测同日快照并恢复 9 个关键状态
- 原子写入（写tmp → rename），防止崩溃损坏快照
- 仅序列化可JSON化的状态，Tick历史队列不序列化（太大且可从实时流重建）

接入方式（main.py live_cmd）：
    session_snap = SessionSnapshot(trade_date)
    snapshot = session_snap.load()
    if snapshot:
        session_snap.restore_to_engine(engine, snapshot)
    session_snap.start_auto_snapshot(engine)  # 30秒一次后台快照

Author: CTO
Date: 2026-03-16
Version: V1.0
"""
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import logging
logger = logging.getLogger(__name__)


class SessionSnapshot:
    """
    盘中 Session 快照引擎

    快照文件路径: data/session_snapshots/session_YYYYMMDD.json
    """
    SNAPSHOT_DIR = Path("data/session_snapshots")
    SNAPSHOT_INTERVAL = 30  # 秒

    def __init__(self, trade_date: str):
        """
        Args:
            trade_date: 交易日 YYYYMMDD
        """
        self.trade_date = trade_date
        self.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self._snapshot_file = self.SNAPSHOT_DIR / f"session_{trade_date}.json"
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._bg_thread: Optional[threading.Thread] = None

    # ─────────────────────────────────────────────────────────────────────────
    # 核心：从引擎提取可序列化状态
    # ─────────────────────────────────────────────────────────────────────────
    def build_snapshot(self, engine) -> Dict[str, Any]:
        """
        从 LiveTradingEngine 实例提取快照

        不序列化：
        - tick_history / volume_history（Tick队列，重启后从实时流重建）
        - candidate_pool 的 tick_history 子字段（同上）
        - qmt_manager 实例（不可序列化）
        """
        # ── decision_brain 持仓状态 ───────────────────────────────────────────
        brain_state = {}
        if getattr(engine, 'decision_brain', None):
            db = engine.decision_brain
            brain_state = {
                'current_position': db.current_position,
                'entry_price': db.entry_price,
                'entry_score': db.entry_score,
                'held_stock_code': db.held_stock_code,
                'entry_time': db.entry_time.isoformat() if db.entry_time else None,
            }

        # ── execution_manager 资金状态 ────────────────────────────────────────
        exec_state = {}
        if getattr(engine, 'execution_manager', None):
            em = engine.execution_manager
            exec_state = {
                'current_capital': getattr(em, 'current_capital', 0),
                'initial_capital': getattr(em, 'initial_capital', 100000.0),
                'total_pnl': getattr(em, 'total_pnl', 0),
                'positions': {
                    k: {
                        'stock_code': k,
                        'entry_price': getattr(v, 'entry_price', 0),
                        'shares': getattr(v, 'shares', 0),
                    }
                    for k, v in getattr(em, 'positions', {}).items()
                },
            }

        # ── opportunity_pool 摘要（不含 Tick 历史） ───────────────────────────
        oppo_summary = {}
        for code, t in getattr(engine, 'opportunity_pool', {}).items():
            try:
                oppo_summary[code] = {
                    'stock_code': code,
                    'final_score': float(getattr(t, 'final_score', 0)),
                    'current_price': float(getattr(t, 'current_price', 0)),
                    'state': t.state.value if hasattr(t, 'state') else 'unknown',
                }
            except Exception:
                pass

        # ── L1 资金流向累加器 ─────────────────────────────────────────────────
        l1_state = {}
        for k, v in getattr(engine, 'l1_inflow_accumulator', {}).items():
            try:
                l1_state[k] = {
                    'inflow': float(v.get('inflow', 0)),
                    'last_amount': float(v.get('last_amount', 0)),
                    'last_price': float(v.get('last_price', 0)),
                }
            except Exception:
                pass

        # ── 今日战报最高分记录 ────────────────────────────────────────────────
        highest_scores = {}
        for code, v in getattr(engine, 'highest_scores', {}).items():
            try:
                highest_scores[code] = {
                    'score': float(v.get('score', 0)),
                    'time': str(v.get('time', '')),
                    'price': float(v.get('price', 0)),
                }
            except Exception:
                pass

        return {
            'trade_date': self.trade_date,
            'snapshot_time': datetime.now().isoformat(),
            'engine_mode': getattr(engine, 'mode', 'live'),
            'brain_state': brain_state,
            'exec_state': exec_state,
            'opportunity_pool': oppo_summary,
            'l1_inflow_accumulator': l1_state,
            'highest_scores': highest_scores,
            'market_total_inflow_cache': float(getattr(engine, 'market_total_inflow_cache', 1000000.0)),
            'global_tick_frame': int(getattr(engine, 'global_tick_frame', 0)),
            'watchlist': list(getattr(engine, 'watchlist', [])),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 写入
    # ─────────────────────────────────────────────────────────────────────────
    def save(self, engine) -> bool:
        """快照写入磁盘（原子操作）"""
        with self._lock:
            try:
                data = self.build_snapshot(engine)
                tmp = self._snapshot_file.with_suffix('.tmp')
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tmp.replace(self._snapshot_file)
                logger.debug(f"[SessionSnapshot] 快照已保存: {self._snapshot_file.name}")
                return True
            except Exception as e:
                logger.warning(f"[SessionSnapshot] 快照写入失败: {e}")
                return False

    # ─────────────────────────────────────────────────────────────────────────
    # 读取恢复
    # ─────────────────────────────────────────────────────────────────────────
    def load(self) -> Optional[Dict[str, Any]]:
        """重启时调用，读取同日快照。无快照或日期不符返回 None"""
        if not self._snapshot_file.exists():
            return None
        try:
            with open(self._snapshot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('trade_date') != self.trade_date:
                logger.info(f"[SessionSnapshot] 快照日期 {data.get('trade_date')} != 今日 {self.trade_date}，忽略")
                return None
            snap_time = data.get('snapshot_time', '未知')
            logger.info(f"[SessionSnapshot] [OK] 发现同日快照 (保存于 {snap_time})，准备恢复...")
            return data
        except Exception as e:
            logger.warning(f"[SessionSnapshot] 快照读取失败: {e}")
            return None

    def restore_to_engine(self, engine, snapshot: Dict[str, Any]):
        """将快照数据注入 LiveTradingEngine 实例"""
        logger.info("[SessionSnapshot] 🔄 开始恢复 Session 状态...")

        # 1. 恢复 decision_brain 持仓
        brain_state = snapshot.get('brain_state', {})
        if brain_state and getattr(engine, 'decision_brain', None):
            db = engine.decision_brain
            db.current_position = brain_state.get('current_position')
            db.entry_price = float(brain_state.get('entry_price', 0.0))
            db.entry_score = float(brain_state.get('entry_score', 0.0))
            db.held_stock_code = brain_state.get('held_stock_code', '')
            et = brain_state.get('entry_time')
            db.entry_time = datetime.fromisoformat(et) if et else None
            if db.held_stock_code:
                logger.info(f"[SessionSnapshot]   [OK] 持仓恢复: {db.held_stock_code} @{db.entry_price:.2f}")

        # 2. 恢复 execution_manager 资金
        exec_state = snapshot.get('exec_state', {})
        if exec_state and getattr(engine, 'execution_manager', None):
            em = engine.execution_manager
            if 'current_capital' in exec_state:
                em.current_capital = float(exec_state['current_capital'])
            if 'total_pnl' in exec_state:
                em.total_pnl = float(exec_state['total_pnl'])
            logger.info(f"[SessionSnapshot]   [OK] 资金恢复: ¥{getattr(em, 'current_capital', 0):,.2f} "
                        f"| 今日盈亏: ¥{getattr(em, 'total_pnl', 0):+,.2f}")

        # 3. 恢复 L1 资金流向累加器
        l1_state = snapshot.get('l1_inflow_accumulator', {})
        if l1_state:
            engine.l1_inflow_accumulator = l1_state
            logger.info(f"[SessionSnapshot]   [OK] L1资金流向累加器恢复: {len(l1_state)} 只票")

        # 4. 恢复宏观资金虹吸缓存
        engine.market_total_inflow_cache = float(
            snapshot.get('market_total_inflow_cache', engine.market_total_inflow_cache)
        )

        # 5. 恢复帧计数
        engine.global_tick_frame = int(snapshot.get('global_tick_frame', 0))

        # 6. 恢复今日战报
        engine.highest_scores = snapshot.get('highest_scores', {})
        if engine.highest_scores:
            logger.info(f"[SessionSnapshot]   [OK] 今日战报恢复: {len(engine.highest_scores)} 只票历史最高分")

        # 7. 恢复 watchlist（若引擎 watchlist 为空）
        saved_watchlist = snapshot.get('watchlist', [])
        if saved_watchlist and not getattr(engine, 'watchlist', []):
            engine.watchlist = saved_watchlist
            logger.info(f"[SessionSnapshot]   [OK] watchlist恢复: {len(saved_watchlist)} 只票")

        # 8. 【Bug#4修复】恢复 opportunity_pool（仅恢复state=OPPORTUNITY的）
        oppo_pool = snapshot.get('opportunity_pool', {})
        if oppo_pool and hasattr(engine, 'opportunity_pool'):
            from tasks.run_live_trading_engine import StockTracker, StockState
            restored_count = 0
            for code, info in oppo_pool.items():
                if code not in engine.opportunity_pool:
                    engine.opportunity_pool[code] = StockTracker(
                        stock_code=code,
                        state=StockState.OPPORTUNITY,
                    )
                    # 恢复分数（用于后续决策）
                    engine.opportunity_pool[code].final_score = float(
                        info.get('final_score', 0)
                    )
                    restored_count += 1
            if restored_count > 0:
                logger.info(f"[SessionSnapshot]   [OK] 机会池恢复: {restored_count} 只票")

        logger.info(f"[SessionSnapshot] 🚀 Session 恢复完成 "
                    f"(快照时间: {snapshot.get('snapshot_time', '未知')})")

    # ─────────────────────────────────────────────────────────────────────────
    # 后台自动快照线程
    # ─────────────────────────────────────────────────────────────────────────
    def start_auto_snapshot(self, engine):
        """启动后台线程，每 SNAPSHOT_INTERVAL 秒自动快照一次"""
        if self._bg_thread and self._bg_thread.is_alive():
            return  # 防止重复启动

        def _worker():
            while not self._stop_event.wait(timeout=self.SNAPSHOT_INTERVAL):
                self.save(engine)

        self._bg_thread = threading.Thread(
            target=_worker,
            daemon=True,
            name="SessionSnapshotWorker"
        )
        self._bg_thread.start()
        logger.info(f"[SessionSnapshot] 后台自动快照已启动 (间隔 {self.SNAPSHOT_INTERVAL}s) → "
                    f"{self._snapshot_file.name}")

    def stop_auto_snapshot(self, engine=None):
        """停止后台线程，并强制写入最终快照"""
        self._stop_event.set()
        if engine is not None:
            self.save(engine)
            logger.info("[SessionSnapshot] 最终快照已写入")

    # ─────────────────────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────────────────────
    def snapshot_exists(self) -> bool:
        return self._snapshot_file.exists()

    def snapshot_info(self) -> Optional[Dict]:
        """返回快照摘要（不恢复），用于启动时显示状态"""
        data = self.load()
        if not data:
            return None
        return {
            'snapshot_time': data.get('snapshot_time'),
            'held_stock': data.get('brain_state', {}).get('held_stock_code', ''),
            'capital': data.get('exec_state', {}).get('current_capital', 0),
            'total_pnl': data.get('exec_state', {}).get('total_pnl', 0),
            'tick_frame': data.get('global_tick_frame', 0),
            'watchlist_count': len(data.get('watchlist', [])),
            'opportunity_count': len(data.get('opportunity_pool', {})),
            'highest_scores_count': len(data.get('highest_scores', {})),
        }
