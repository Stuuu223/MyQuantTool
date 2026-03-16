# -*- coding: utf-8 -*-
"""
live_session_patch.py - 动态粗筛补充方法补丁说明

【CTO指令】此文件说明需要手动将以下方法插入
tasks/run_live_trading_engine.py 的 LiveTradingEngine 类中。

位置: 在 __init__ 末尾新增两个实例变量，然后在类体内新增方法。

═══════════════════════════════════════════
Step 1: 在 __init__ 末尾（logger.info('[OK]...')之前）新增：
═══════════════════════════════════════════

        # 【P0修复】动态粗筛补充：每15分钟重扫全市场
        self._last_universe_refresh_time: Optional[datetime] = None
        self._universe_refresh_interval_min: int = 15

═══════════════════════════════════════════
Step 2: 在 run_historical_stream 之前新增方法：
═══════════════════════════════════════════

    def _maybe_refresh_universe(self, current_time: datetime):
        """
        【P0修复】动态粗筛补充 - 每15分钟重扫全市场

        解决问题：09:30一次性建立粗筛池后，下午新出现动能的票
        无法进入candidate_pool，导致14:27仅剩72只的断崖现象。

        设计原则：
        - 只新增，不重置：已在candidate/opportunity/eliminated的票保持原状态
        - 宽进标准：只要有量有价格动能就进候选池
        - 每15分钟执行一次，不阻塞主循环（O(n)扫描，约100ms）
        """
        if self._last_universe_refresh_time is None:
            self._last_universe_refresh_time = current_time
            return

        elapsed = (current_time - self._last_universe_refresh_time).total_seconds() / 60
        if elapsed < self._universe_refresh_interval_min:
            return

        try:
            from logic.data_providers.universe_builder import UniverseBuilder
            new_pool, _ = UniverseBuilder(
                target_date=self.target_date,
                mode='live'
            ).build()

            new_count = 0
            for code in new_pool:
                if (code not in self.candidate_pool and
                        code not in self.opportunity_pool and
                        code not in self.eliminated_pool):
                    self.candidate_pool[code] = StockTracker(
                        stock_code=code,
                        state=StockState.CANDIDATE,
                        enter_time=current_time
                    )
                    new_count += 1

            if new_count > 0:
                logger.info(
                    f"🔄 [动态补充] 粗筛池新增 {new_count} 只票 "
                    f"(候选池: {len(self.candidate_pool)} | "
                    f"机会池: {len(self.opportunity_pool)} | "
                    f"剔除池: {len(self.eliminated_pool)})"
                )

            self._last_universe_refresh_time = current_time

        except Exception as e:
            logger.warning(f"[WARN] 动态补充粗筛池失败: {e}")
            self._last_universe_refresh_time = current_time  # 失败也更新时间，避免死循环

═══════════════════════════════════════════
Step 3: 在主循环每帧调用（_run_radar_main_loop内）:
═══════════════════════════════════════════

        # 在主循环帧处理开始处插入：
        current_time = self.get_current_time()
        self._maybe_refresh_universe(current_time)

"""
# 此文件仅作说明用途，实际逻辑见上方注释
# 由于run_live_trading_engine.py体积过大(>1000行)，
# 直接全量覆盖推送会超出API限制，请参照此说明手动接入
# 或通过git cherry-pick方式应用
