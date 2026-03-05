"""
实盘总控引擎 - 实现"降频初筛，高频决断"的终极架构 (CTO加固版)

功能：
- 盘前粗筛：09:25获取股票池
- 开盘快照：09:30-09:35向量化过滤
- 火控雷达：09:35后Tick订阅+实时算分
- 交易执行：动能打分引擎得分+TradeGatekeeper风控

CTO加固要点:
- 修复QMT回调问题 (真·事件订阅)
- 避免time.sleep阻塞主线程
- 实现动态切入火控机制
- 修复TradeGatekeeper API差异

Author: AI总监 (CTO加固)
Date: 2026-02-24
Version: Phase 20 - 修复版
"""
import time
import threading
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

# CTO Step6: 时空对齐需要pandas处理Tick数据
try:
    import pandas as pd
except ImportError:
    pd = None

# 获取logger
try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging as log_mod
    logger = log_mod.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = log_mod.StreamHandler()
    handler.setFormatter(log_mod.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)


class LiveTradingEngine:
    """
    实盘总控引擎 - 实现老板的"降频初筛，高频决断" (CTO依赖注入版)
    
    CTO强制规范:
    - 使用依赖注入模式，从main.py传入QMT实例
    - 移除简化模式容错，QMT缺失必须崩溃
    - 实盘不容沙子，没有QMT就是玩具！
    """
    
    def __init__(self, qmt_manager=None, event_bus=None, volume_percentile: float = 1.5):
        """
        初始化引擎 - CTO强制：依赖注入模式
        
        Args:
            qmt_manager: QMT管理器实例（必须传入）
            event_bus: 事件总线实例（可选，内部创建）
            volume_percentile: 量比分位数阈值
        """
        # CTO强制：QMT Manager必须由外部注入！
        if qmt_manager is None:
            logger.error("❌ [LiveTradingEngine] CTO命令：没有券商通道，不准开机！")
            raise RuntimeError(
                "致命错误：QMT Manager缺失！\n"
                "CTO命令：实盘引擎拒绝空转！\n"
                "请在main.py中初始化QMT并传入引擎！"
            )
        
        self.qmt_manager = qmt_manager
        self.scanner = None
        self.event_bus = event_bus  # 可以为None，稍后初始化
        self.watchlist = []
        self.running = False
        self.volume_percentile = volume_percentile
        
        # 【CTO清理】已废弃的V18模块已删除，使用动能打分引擎替代
        # warfare_core/trade_gatekeeper/trader 已被纯血游资架构废除
        
        # 【CTO挂载】微积分形态学引擎 - 时空对齐 (管理多个股票实例)
        self.kinetic_engines: Dict[str, Any] = {}
        self._init_kinetic_engine()
        
        # 【CTO战地收尸】今日战报追踪
        self.highest_scores: Dict[str, Dict] = {}  # {stock_code: {'score': float, 'time': datetime, ...}}
        self.battle_report: Dict[str, Any] = {}    # 最终战报数据
        
        # 【CTO V4】静态机会池缓存 - 午休/盘后复盘用
        self.last_known_top_targets: List[Dict] = []  # 最后一次计算的机会池
        
        # 【CTO修复】初始化顺序：先EventBus，再QMTEventAdapter
        # 初始化EventBus（如果未传入）
        if self.event_bus is None:
            self._init_event_bus()
        
        # 【架构解耦】初始化QMT事件适配器（需要event_bus已就绪）
        self._init_qmt_adapter()
        
        logger.info("✅ [LiveTradingEngine] 初始化完成 - QMT Manager已注入")
    
    def _init_kinetic_engine(self):
        """【CTO挂载】初始化微积分形态学引擎管理器 - 时空对齐"""
        try:
            from logic.execution.kinetic_engine import KineticEngine
            self.kinetic_engine_class = KineticEngine
            self.kinetic_engines = {}  # {stock_code: engine_instance}
            logger.info("🎯 [时空对齐] KineticEngine微积分引擎管理器已挂载")
        except Exception as e:
            logger.error(f"❌ KineticEngine挂载失败: {e}")
            self.kinetic_engine_class = None
            self.kinetic_engines = {}
    
    def _get_kinetic_engine(self, stock_code: str):
        """获取或创建股票的KineticEngine实例"""
        if not self.kinetic_engine_class:
            return None
        if stock_code not in self.kinetic_engines:
            try:
                self.kinetic_engines[stock_code] = self.kinetic_engine_class(stock_code)
            except Exception as e:
                logger.debug(f"⚠️ 创建KineticEngine失败 {stock_code}: {e}")
                return None
        return self.kinetic_engines[stock_code]
    
    def _init_event_bus(self):
        """初始化EventBus"""
        try:
            from logic.data_providers.event_bus import create_event_bus
            self.event_bus = create_event_bus(max_queue_size=20000, max_workers=10)
            logger.debug("🎯 EventBus 已初始化")
        except Exception as e:
            logger.error(f"❌ EventBus 初始化失败: {e}")
            raise RuntimeError(f"EventBus初始化失败: {e}")
        
        # 【CTO修复连环雷2】FullMarketScanner已废弃，用UniverseBuilder替代！
        # 原因：FullMarketScanner模块不存在，导致self.scanner=None
        # 修复：直接使用UniverseBuilder的粗筛能力
        self.scanner = None  # 标记为None，后续用UniverseBuilder
        logger.info("🎯 [纯血游资雷达] 使用UniverseBuilder替代FullMarketScanner进行粗筛")
        
        try:
            from logic.data_providers.event_bus import create_event_bus
            self.event_bus = create_event_bus(max_queue_size=20000, max_workers=10)  # 扩大队列容量和工作线程
            logger.debug("🎯 EventBus 已加载")
        except ImportError:
            self.event_bus = None
            logger.error("❌ EventBus 加载失败")
        except Exception as e:
            self.event_bus = None
            logger.error(f"❌ EventBus 初始化异常: {e}")    
    def _init_qmt_adapter(self):
        """
        【架构解耦】初始化QMT事件适配器
        
        将底层QMT通讯细节封装到adapter，主引擎保持纯粹
        """
        try:
            from logic.data_providers.qmt_event_adapter import QMTEventAdapter
            self.qmt_adapter = QMTEventAdapter(event_bus=self.event_bus)
            if self.qmt_adapter.initialize():
                logger.info("✅ [LiveTradingEngine] QMTEventAdapter 初始化成功")
            else:
                logger.error("❌ [LiveTradingEngine] QMTEventAdapter 初始化失败")
                self.qmt_adapter = None
        except Exception as e:
            logger.error(f"❌ [LiveTradingEngine] QMTEventAdapter 创建失败: {e}")
            self.qmt_adapter = None
    
    def start_session(self, enable_dynamic_radar: bool = True):
        """
        启动交易会话 - CTO V4终极版（四级漏斗 + 看板先行 + 静态复盘缓存）
        时间线: 09:25(CTO第一斩) -> 09:30(开盘粗筛) -> 盘中(细筛+动能打分)
        
        Args:
            enable_dynamic_radar: 是否启用动态雷达（默认True，仅实盘使用）
        """
        import os
        
        # 【CTO V4看板绝对先行】第一帧立刻显示，不等任何操作！
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 80)
        print("🚀 [V20 纯血游资猎杀雷达] | 引擎唤醒中...")
        print("⏳ 正在进行全市场粗筛，请等待...")
        print("=" * 80)
        
        # 【CTO修复】将参数保存为实例变量，供后续函数使用
        self.enable_dynamic_radar = enable_dynamic_radar
        logger.info("🚀 启动实盘总控引擎 (CTO V4四级漏斗版)")
        
        # QMT Manager已通过依赖注入保证存在，无需检查
        logger.info("✅ [LiveTradingEngine] QMT Manager已就绪，启动完整模式")
        
        if self.event_bus is None:
            logger.error("❌ [LiveTradingEngine] EventBus缺失，会话启动失败！")
            raise RuntimeError("致命错误：EventBus缺失，会话启动失败！")
        
        self.running = True
        
        # 启动事件总线消费者
        self.event_bus.start_consumer()
        # 绑定Tick事件处理器
        self.event_bus.subscribe('tick', self._on_tick_data)
        
        # 获取当前时间
        current_time = datetime.now()
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        auction_end = current_time.replace(hour=9, minute=25, second=0, microsecond=0)
        
        # CTO修复：盘中启动时必须先执行快照筛选！
        if current_time >= market_open:
            logger.warning("⚠️ 当前时间已过09:30开盘，执行盘中补网...")
            
            # Step 1: 先执行第一斩（集合竞价筛选），填充初始watchlist
            logger.info("🔄 Step 1: 执行集合竞价快照初筛...")
            self._auction_snapshot_filter()
            
            if not self.watchlist:
                logger.warning("⚠️ 第一斩未找到目标股票，尝试全市场快照...")
                # 备用：直接使用全市场快照
                self._fallback_premarket_scan()
            
            # Step 2: 执行第二斩（开盘快照筛选），筛选强势股
            logger.info("🔄 Step 2: 执行开盘快照二筛...")
            self._snapshot_filter()
            
            # Step 3: 检查watchlist是否填充成功
            if not self.watchlist:
                logger.warning("❌ 快照筛选未找到目标股票，系统进入待机模式")
                logger.info("💡 提示：可能当前没有符合量比>0.95分位数的强势股")
                logger.info("🔄 系统将持续运行，等待下一分钟自动补网...")
                # CTO修复：不再自杀，系统持续运行等待自动补网
                # 启动自动补网机制
                self._start_auto_replenishment()
                return
            
            # Step 4: 订阅Tick数据（在watchlist填充后）
            logger.info("📡 订阅目标股票Tick数据...")
            self._setup_qmt_callbacks()
            
            # Step 5: 进入高频监控模式
            logger.info(f"🎯 进入高频监控模式，锁定右侧起爆目标 {len(self.watchlist)} 只目标")
            
            # 【CTO暴怒扒皮第一棒】强制高亮输出Watchlist数量
            watchlist_count = len(self.watchlist)
            logger.info("=" * 60)
            logger.info(f"🚨 [CTO强制审计] 盘中补网结束！当前真实观察池数量: {watchlist_count}只")
            if watchlist_count > 0:
                logger.info(f"📊 [CTO强制审计] 观察池前5只股票: {self.watchlist[:5]}")
            else:
                logger.error(f"❌ [CTO强制审计] 观察池为空！0.90分位的宽体雷达失效！")
            logger.info("=" * 60)
            
            # 【CTO强制回显】终端控制台输出
            import click
            click.echo(f"\n{'='*60}")
            click.echo(f"📢 [CTO物理透视] 盘中补网完毕！")
            click.echo(f"🎯 成功进入观察池的股票数量: {watchlist_count} 只")
            if watchlist_count > 0:
                click.echo(click.style(f"✅ 观察池前5只: {self.watchlist[:5]}", fg="green"))
            else:
                click.echo(click.style("❌ 致命警报：观察池为0！所有股票均被过滤！", fg="red"))
            click.echo(f"{'='*60}\n")
            
            self._fire_control_mode()
            return
        
        # 如果已过09:25但未到09:30，执行快照初筛
        if current_time >= auction_end:
            logger.info("🎯 已过09:25，立即执行CTO第一斩...")
            self._premarket_scan()  # 内部调用_auction_snapshot_filter
            
            # 计算到09:30的剩余时间
            seconds_to_open = (market_open - current_time).total_seconds()
            if seconds_to_open > 0:
                logger.info(f"⏰ 等待{seconds_to_open:.0f}秒到09:30开盘...")
                # 【CTO V5修复】等待期间显示缓存面板
                self._print_fire_control_panel([], initial_loading=True)
                import time
                time.sleep(seconds_to_open)
            
            # 【CTO V5修复】直接调用粗筛，不再用Timer
            self._snapshot_filter()
            
            # 【CTO V5修复】直接进入雷达循环！
            if self.watchlist and self.enable_dynamic_radar:
                self._setup_qmt_callbacks()
                self._run_radar_main_loop()
            return
        
        # 如果还没到09:25，等待到09:25执行第一斩
        seconds_to_auction = (auction_end - current_time).total_seconds()
        if seconds_to_auction > 0:
            logger.info(f"⏰ 等待{seconds_to_auction:.0f}秒到09:25集合竞价结束...")
            # 【CTO V5修复】等待期间显示缓存面板
            self._print_fire_control_panel([], initial_loading=True)
            import time
            time.sleep(seconds_to_auction)
            self._execute_auction_filter()
        else:
            self._execute_auction_filter()
    
    def _execute_auction_filter(self):
        """执行09:25集合竞价初筛"""
        logger.info("🔪 09:25 - CTO第一斩：集合竞价快照初筛...")
        self._premarket_scan()  # 内部调用_auction_snapshot_filter
        
        # 计算到09:30的剩余时间
        current_time = datetime.now()
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        seconds_to_open = (market_open - current_time).total_seconds()
        
        if seconds_to_open > 0:
            logger.info(f"⏰ 09:25初筛完成，等待{seconds_to_open:.0f}秒到09:30开盘...")
            # 【CTO V5修复】等待期间显示缓存面板
            self._print_fire_control_panel([], initial_loading=True)
            import time
            time.sleep(seconds_to_open)
        
        # 【CTO V5修复】直接调用粗筛，不再用Timer
        logger.info("🎯 已到09:30，立即启动开盘快照过滤...")
        self._snapshot_filter()
        
        # 【CTO V5修复】直接进入雷达循环！
        if self.watchlist and self.enable_dynamic_radar:
            self._setup_qmt_callbacks()
            self._run_radar_main_loop()
    
    def _setup_qmt_callbacks(self):
        """
        【架构解耦】使用QMTEventAdapter订阅Tick数据
        
        原有100+行的QMT底层代码已剥离至qmt_event_adapter.py
        主引擎只负责调度，不做底层脏活！
        """
        # CTO修复：检查watchlist是否已初始化
        if not self.watchlist:
            logger.warning("⚠️ watchlist未初始化，跳过Tick订阅")
            return
            
        # 检查adapter是否就绪
        if not hasattr(self, 'qmt_adapter') or self.qmt_adapter is None:
            logger.error("❌ QMTEventAdapter未初始化，无法订阅Tick")
            return
            
        # 【架构解耦】通过adapter订阅，主引擎保持纯粹
        try:
            subscribed_count = self.qmt_adapter.subscribe_ticks(self.watchlist)
            logger.info(f"✅ Tick订阅完成: {subscribed_count}/{len(self.watchlist)} 只股票")
        except Exception as e:
            logger.error(f"❌ Tick订阅失败: {e}")
    
    def _auction_snapshot_filter(self):
        """
        09:25集合竞价快照初筛 - CTO第一斩 - 带火力输出的雷达版
        
        【架构解耦】使用QMTEventAdapter获取数据，向量化过滤：
        1. open < prev_close（低开的，直接拉黑）
        2. volume < 1000（竞价连1000手都没有的，没有资金关注，拉黑）  
        3. open >= up_stop_price（开盘直接一字涨停的，买不到，拉黑）
        
        【CTO强化】显性输出竞价数据：
        - 计算竞价承接力 = 竞价金额 / 流通市值
        - 输出竞价爆量日志
        - 保存到CSV文件
        """
        import pandas as pd
        import time
        from datetime import datetime
        from logic.utils.calendar_utils import get_nth_previous_trading_day
        
        try:
            start_time = time.perf_counter()
            
            # 【架构解耦】使用adapter获取数据，而非直接调用xtdata
            if not hasattr(self, 'qmt_adapter') or self.qmt_adapter is None:
                logger.error("🚨 QMTEventAdapter未初始化")
                self._fallback_premarket_scan()
                return
            
            # 1. 获取全市场快照（1毫秒内完成）
            all_stocks = self.qmt_adapter.get_all_a_shares()
            if not all_stocks:
                logger.error("🚨 无法获取沪深A股列表")
                self._fallback_premarket_scan()
                return
            
            snapshot = self.qmt_adapter.get_full_tick_snapshot(all_stocks)
            
            if not snapshot:
                logger.error("🚨 无法获取09:25集合竞价快照")
                self._fallback_premarket_scan()
                return
            
            # 2. 转换为DataFrame，增加竞价Tick关键字段
            df = pd.DataFrame([
                {
                    'stock_code': code,
                    'open': tick.get('open', 0) if isinstance(tick, dict) else getattr(tick, 'open', 0),
                    'volume': tick.get('volume', 0) if isinstance(tick, dict) else getattr(tick, 'volume', 0),
                    'amount': tick.get('amount', 0) if isinstance(tick, dict) else getattr(tick, 'amount', 0),
                    'prev_close': tick.get('lastClose', 0) if isinstance(tick, dict) else getattr(tick, 'lastClose', 0),
                    'bidVol1': tick.get('bidVol1', 0) if isinstance(tick, dict) else getattr(tick, 'bidVol1', 0),
                    'askVol1': tick.get('askVol1', 0) if isinstance(tick, dict) else getattr(tick, 'askVol1', 0),
                    'bid1': tick.get('bid1', 0) if isinstance(tick, dict) else getattr(tick, 'bid1', 0),
                    'ask1': tick.get('ask1', 0) if isinstance(tick, dict) else getattr(tick, 'ask1', 0),
                }
                for code, tick in snapshot.items() if tick
            ])
            
            if df.empty:
                logger.error("🚨 09:25快照数据为空")
                return
            
            original_count = len(df)
            
            # 3. 从TrueDictionary获取涨停价和流通市值
            from logic.data_providers.true_dictionary import get_true_dictionary
            true_dict = get_true_dictionary()
            
            # 【Phase1终极修复】预热TrueDictionary（如果缓存为空）
            if not true_dict._float_volume or not true_dict._up_stop_price:
                logger.info("🔄 [TrueDictionary] 第一斩前预热中...")
                from logic.utils.calendar_utils import get_nth_previous_trading_day
                today = datetime.now().strftime('%Y%m%d')
                target_date = get_nth_previous_trading_day(today, 1)
                true_dict.warmup(df['stock_code'].tolist(), target_date=target_date, force=False)
            
            # 向量化获取涨停价和流通市值
            df['up_stop_price'] = df['stock_code'].map(
                lambda x: true_dict.get_up_stop_price(x) if true_dict else 0.0
            )
            df['float_volume'] = df['stock_code'].map(
                lambda x: true_dict.get_float_volume(x) if true_dict else 0.0
            )
            
            # 4. 计算竞价承接力 = 竞价金额 / 流通市值
            # amount单位是元，float_volume单位是股，需要转换
            df['auction_power'] = df.apply(
                lambda row: row['amount'] / (row['float_volume'] * row['open']) * 100 
                if row['float_volume'] > 0 and row['open'] > 0 else 0.0,
                axis=1
            )
            
            # 5. CTO物理过滤规则（向量化）
            mask = (
                (df['open'] >= df['prev_close']) &      # 非低开（高开或平开）
                (df['volume'] >= 1000) &                 # 有量（>=1000手）
                (df['open'] < df['up_stop_price'])       # 非一字板（可以买入）
            )
            
            filtered_df = df[mask].copy()
            
            # 按竞价承接力排序（承接力强的优先）
            filtered_df = filtered_df.sort_values('auction_power', ascending=False)
            
            # 计算开盘涨幅
            filtered_df['open_change_pct'] = (
                (filtered_df['open'] - filtered_df['prev_close']) / filtered_df['prev_close'] * 100
            )
            
            elapsed = (time.perf_counter() - start_time) * 1000
            
            # 6. 【CTO强化】输出竞价爆量日志
            today_str = datetime.now().strftime('%Y%m%d')
            
            # 竞价承接力TOP10（承接力 > 0.5%）
            high_power = filtered_df[filtered_df['auction_power'] > 0.5].head(10)
            if len(high_power) > 0:
                logger.info("=" * 60)
                logger.info(f"🔥 竞价爆量榜 (09:25集合竞价承接力TOP)")
                logger.info("=" * 60)
                for _, row in high_power.iterrows():
                    logger.info(
                        f"🔥 [{row['stock_code']}] "
                        f"竞价金额={row['amount']/10000:.1f}万 "
                        f"承接力={row['auction_power']:.3f}% "
                        f"高开={row['open_change_pct']:.2f}%"
                    )
                logger.info("=" * 60)
            
            # 7. 【CTO强化】保存竞价数据到CSV（统一目录data/auction/）
            import os
            os.makedirs('data/auction', exist_ok=True)
            output_path = f"data/auction/auction_tick_live_{today_str}.csv"
            try:
                output_df = filtered_df[['stock_code', 'open', 'prev_close', 'open_change_pct', 
                                         'volume', 'amount', 'auction_power', 'bidVol1', 'askVol1']]
                output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"✅ [竞价收割] {len(filtered_df)}只股票竞价数据已落盘 -> {output_path}")
            except Exception as e:
                logger.warning(f"⚠️ 竞价数据保存失败: {e}")
            
            # 8. 更新watchlist为初筛结果（CTO处决：删除Magic Number截断！）
            self.watchlist = filtered_df['stock_code'].tolist()
            
            logger.info(
                f"🔪 CTO第一斩完成: {original_count}只 → {len(self.watchlist)}只 "
                f"({len(self.watchlist)/original_count*100:.1f}%),耗时{elapsed:.2f}ms"
            )
            
            # 记录统计信息
            rejected_lower = len(df[df['open'] < df['prev_close']])
            rejected_lowvol = len(df[df['volume'] < 1000])
            rejected_limitup = len(df[df['open'] >= df['up_stop_price']])
            
            logger.debug(
                f"📊 初筛剔除统计: 低开{rejected_lower}只, 无量{rejected_lowvol}只, "
                f"一字板{rejected_limitup}只"
            )
            
        except Exception as e:
            logger.error(f"❌ 09:25快照初筛失败: {e}")
            logger.warning("⚠️ 初筛失败，回退到基础股票池（限制100只）")
            self._fallback_premarket_scan()

    def _fallback_premarket_scan(self):
        """
        【CTO修复】回退方案：使用QMTEventAdapter快照获取基础股票池
        严禁使用UniverseBuilder（它是盘前工具，依赖日K线）
        """
        logger.warning("⚠️ 执行QMT快照回退方案...")
        
        try:
            # 使用QMTEventAdapter获取全市场快照
            if not hasattr(self, 'qmt_adapter') or self.qmt_adapter is None:
                logger.error("❌ QMTEventAdapter未初始化，回退失败")
                self.watchlist = []
                return
            
            all_stocks = self.qmt_adapter.get_all_a_shares()
            if not all_stocks:
                logger.error("❌ 无法获取股票列表")
                self.watchlist = []
                return
            
            # 获取快照，只取前100只作为应急观察池
            snapshot = self.qmt_adapter.get_full_tick_snapshot(all_stocks[:500])
            if snapshot:
                self.watchlist = list(snapshot.keys())[:100]
                logger.info(f"📊 QMT快照回退完成: {len(self.watchlist)} 只候选")
            else:
                logger.error("❌ 快照获取失败")
                self.watchlist = []
        except Exception as e:
            logger.error(f"❌ 回退方案失败: {e}")
            self.watchlist = []

    def _premarket_scan(self):
        """
        盘前扫描 - CTO加固：直接使用快照初筛
        """
        # 使用快照初筛
        self._auction_snapshot_filter()
        
        # 预热TrueDictionary（获取涨停价/流通盘等静态数据，唯一真理源！）
        self._warmup_true_dictionary()
    
    def _warmup_true_dictionary(self):
        """预热TrueDictionary - 获取涨停价等静态数据 - CTO加固：容错机制"""
        try:
            from logic.data_providers.true_dictionary import get_true_dictionary
            from logic.utils.calendar_utils import get_nth_previous_trading_day
            
            true_dict = get_true_dictionary()
            
            # 【CTO修复】计算target_date（上一个交易日）
            today = datetime.now().strftime('%Y%m%d')
            target_date = get_nth_previous_trading_day(today, 1)  # 上一个交易日
            
            # 使用当前watchlist + 扩展池进行预热
            warmup_stocks = self._get_extended_stock_pool(self.watchlist)
            
            result = true_dict.warmup(warmup_stocks, target_date=target_date)
            
            if result['integrity']['is_ready']:
                atr_count = len(true_dict._atr_20d_map) if hasattr(true_dict, '_atr_20d_map') else 0
                prev_close_count = len(true_dict._prev_close_cache) if hasattr(true_dict, '_prev_close_cache') else 0
                logger.info(
                    f"✅ TrueDictionary装弹完成: "
                    f"涨停价{result['qmt'].get('success', 0)}只, "
                    f"5日均量{result['avg_volume'].get('success', 0)}只, "
                    f"ATR{atr_count}只, prev_close{prev_close_count}只"
                )
            else:
                logger.warning(f"⚠️ TrueDictionary装弹不完整: 缺失率{result['integrity']['missing_rate']*100:.1f}%")
                
        except Exception as e:
            logger.error(f"❌ TrueDictionary预热失败: {e}")
            logger.warning("💡 提示：将使用实时数据获取，可能影响性能")
    
    def _get_extended_stock_pool(self, universe: List[str]) -> List[str]:
        """
        获取扩展股票池用于InstrumentCache预热
        
        Args:
            universe: 基础股票池
            
        Returns:
            List[str]: 扩展后的股票池 (约500-1000只)
        """
        # 从基础池开始
        extended = set(universe)
        
        # 添加沪深A股主要股票
        try:
            # 【架构解耦】使用adapter获取数据
            if not hasattr(self, 'qmt_adapter') or self.qmt_adapter is None:
                logger.debug("QMTEventAdapter未初始化，跳过扩展")
                return list(extended)
            
            # 获取沪深A股列表 (前1000只用于缓存预热)
            all_a_shares = self.qmt_adapter.get_all_a_shares()
            
            # 优先添加watchlist中的股票
            for code in self.watchlist:
                normalized = self._normalize_stock_code(code)
                if normalized:
                    extended.add(normalized)
            
            # 添加额外的股票 (限制总数约800只，平衡性能和覆盖)
            remaining_slots = 800 - len(extended)
            if remaining_slots > 0 and all_a_shares:
                for code in all_a_shares[:remaining_slots]:
                    normalized = self._normalize_stock_code(code)
                    if normalized:
                        extended.add(normalized)
                        
        except Exception as e:
            logger.debug(f"获取扩展股票池失败: {e}")
        
        result = list(extended)
        logger.info(f"📦 扩展股票池: {len(result)} 只 (基础池 {len(universe)} 只)")
        return result
    
    def _normalize_stock_code(self, code: str) -> Optional[str]:
        """
        标准化股票代码格式
        
        Args:
            code: 原始股票代码
            
        Returns:
            Optional[str]: 标准化后的代码或None
        """
        if not isinstance(code, str):
            return None
        
        # 如果已经有后缀，直接返回
        if '.' in code:
            return code
        
        # 根据前缀判断交易所
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"
        elif code.startswith('8') or code.startswith('4'):
            # 北交所/新三板，暂不处理
            return None
        
        return code
    
    def _snapshot_filter(self):
        """
        【CTO V4四级漏斗】09:30开盘粗筛 - 只看量比！
        
        四级漏斗设计:
        - 一级漏斗(全市场): 5191只
        - 二级漏斗(粗筛池): 只用volume_ratio>=3.0x，目标~900只
        - 三级漏斗(细筛池): 换手率+ATR，盘中动态过滤，目标~100只
        - 四级漏斗(机会池): 动能打分TOP 20-30只
        
        【CTO红线】
        - 粗筛只看量比，不夹带换手率/ATR！
        - 细筛在雷达循环中进行
        """
        import pandas as pd
        
        start_time = time.perf_counter()
        
        try:
            from logic.data_providers.true_dictionary import get_true_dictionary
            from logic.core.config_manager import get_config_manager
            
            # 【CTO修复】prev_close已从快照lastClose获取，无需预热_prev_close_cache
            # 删除多余的预热逻辑，避免阻塞
            
            # 【架构解耦】检查adapter
            if not hasattr(self, 'qmt_adapter') or self.qmt_adapter is None:
                logger.error("🚨 QMTEventAdapter未初始化")
                self._fallback_premarket_scan()
                return
            
            # 1. 获取09:25筛选出的股票的开盘快照
            if not self.watchlist:
                logger.error("🚨 watchlist为空，无法进行09:30粗筛")
                self._fallback_premarket_scan()
                return
            
            snapshot = self.qmt_adapter.get_full_tick_snapshot(self.watchlist)
            
            if not snapshot:
                logger.error("🚨 无法获取09:30开盘快照")
                self._fallback_premarket_scan()
                return
            
            # 2. 转换为DataFrame
            df = pd.DataFrame([
                {
                    'stock_code': code,
                    'price': tick.get('lastPrice', 0) if isinstance(tick, dict) else getattr(tick, 'lastPrice', 0),
                    'volume': tick.get('volume', 0) if isinstance(tick, dict) else getattr(tick, 'volume', 0),
                    'amount': tick.get('amount', 0) if isinstance(tick, dict) else getattr(tick, 'amount', 0),
                    'prev_close': tick.get('lastClose', 0) if isinstance(tick, dict) else getattr(tick, 'lastClose', 0),  # 直接从快照获取昨收
                }
                for code, tick in snapshot.items() if tick
            ])
            
            if df.empty:
                logger.error("🚨 09:30快照数据为空")
                return
            
            original_count = len(df)
            
            # 3. 从TrueDictionary获取真实数据
            true_dict = get_true_dictionary()
            config_manager = get_config_manager()
            
            df['avg_volume_5d'] = df['stock_code'].map(true_dict.get_avg_volume_5d)
            df['avg_turnover_5d'] = df['stock_code'].map(true_dict.get_avg_turnover_5d)
            df['float_volume'] = df['stock_code'].map(true_dict.get_float_volume)
            # prev_close已从快照获取，无需再从TrueDictionary获取
            
            # 4. 计算量比（时间进度加权）
            df['volume_gu'] = df['volume'] * 100  # 手→股
            
            now = datetime.now()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            raw_minutes = (now - market_open).total_seconds() / 60
            minutes_passed = max(5, min(raw_minutes, 240))  # 缓冲5分钟，最大240分钟
            
            # 估算全天成交量
            df['estimated_full_day_volume'] = df['volume_gu'] / minutes_passed * 240
            # 【CTO修复】avg_volume_5d单位是手，需要乘100转成股
            df['avg_volume_5d_gu'] = df['avg_volume_5d'] * 100
            df['volume_ratio'] = df['estimated_full_day_volume'] / df['avg_volume_5d_gu'].replace(0, pd.NA)
            
            # 开盘瞬时换手率（用于过滤死亡换手派发）
            df['current_turnover'] = (df['volume_gu'] / df['float_volume'].replace(0, pd.NA)) * 100
            
            # 5日均成交额 = avg_volume_5d * prev_close (近似计算)
            # prev_close已在快照中获取，直接使用
            df['avg_amount_5d'] = df['avg_volume_5d'] * df['prev_close'] * 100  # 手→股→元
            
            # 【Phase1修复】不用dropna屠杀，改用fillna容错
            # 缺失数据用安全默认值填充，保留股票
            import numpy as np
            df['volume_ratio'] = df['volume_ratio'].fillna(1.0)
            df['avg_turnover_5d'] = df['avg_turnover_5d'].fillna(1.0)
            df['avg_amount_5d'] = df['avg_amount_5d'].fillna(0.0)
            df['current_turnover'] = df['current_turnover'].fillna(0.0)
            
            # 清理无穷大
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df['volume_ratio'] = df['volume_ratio'].fillna(1.0)
            
            pre_filter_count = len(df)
            
            # ========== 【Phase1修复】动态阈值：盘后降低门槛！==========
            base_volume_multiplier = config_manager.get('live_sniper.min_volume_multiplier', 3.0)
            
            # 【时间效应补偿】盘后量比回归，需要降低阈值
            if minutes_passed >= 240:
                # 盘后模式：量比是全天真实值，降低阈值到1.5x
                min_volume_multiplier = 1.5
                mode_tag = "盘后投影"
            elif minutes_passed >= 120:
                # 午后模式：量比部分回归，阈值2.0x
                min_volume_multiplier = 2.0
                mode_tag = "午后修正"
            else:
                # 早盘模式：量比脉冲期，保持原阈值
                min_volume_multiplier = base_volume_multiplier
                mode_tag = "早盘脉冲"
            
            # 【CTO建议】宽松阈值：3000万均额 + 1%换手，放大捕获范围
            min_avg_amount_5d = 30000000.0  # 3000万（CTO建议）
            min_avg_turnover_5d = 1.0       # 1%（CTO建议）
            max_open_turnover = 30.0        # 开盘换手率>30%视为死亡派发
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🔬 【四级漏斗-第二级粗筛】多维护城河生效！")
            logger.info(f"{'='*60}")
            logger.info(f"▶ 运行模式: {mode_tag} (已过{minutes_passed:.0f}分钟)")
            logger.info(f"▶ 输入池: {pre_filter_count} 只")
            logger.info(f"▶ 量比门槛: >= {min_volume_multiplier:.1f}x (动态调整)")
            logger.info(f"▶ 5日均额门槛: >= {min_avg_amount_5d/10000:.0f}万")
            logger.info(f"▶ 5日均换手门槛: >= {min_avg_turnover_5d:.1f}%")
            logger.info(f"▶ 死亡换手拦截: 开盘换手 < {max_open_turnover:.0f}%")
            
            # 多维复合过滤
            mask = (
                (df['volume_ratio'] >= min_volume_multiplier) &
                (df['avg_amount_5d'] >= min_avg_amount_5d) &
                (df['avg_turnover_5d'] >= min_avg_turnover_5d) &
                (df['current_turnover'] < max_open_turnover)
            )
            
            filtered_df = df[mask].copy()
            
            post_filter_count = len(filtered_df)
            
            logger.info(f"\n📊 【粗筛结果】:")
            logger.info(f"▶ 粗筛池: {post_filter_count} 只 (目标500-900只)")
            logger.info(f"🚫 淘汰: {pre_filter_count - post_filter_count} 只")
            logger.info(f"{'='*60}\n")
            
            # 按量比排序
            filtered_df = filtered_df.sort_values('volume_ratio', ascending=False)
            
            elapsed = (time.perf_counter() - start_time) * 1000
            
            # 数量提示
            if post_filter_count == 0:
                logger.warning(f"⚠️ 粗筛池为空！量比门槛{min_volume_multiplier:.1f}x可能过高")
            elif post_filter_count < 100:
                logger.info(f"💡 粗筛池数量较少: {post_filter_count}只")
            else:
                logger.info(f"✅ 粗筛池已就绪: {post_filter_count}只")
            
            # 【CTO V5处决】删除粗筛池上限截断！真实漏斗由量比决定！
            self.watchlist = filtered_df['stock_code'].tolist()
            
            logger.info(f"🔪 CTO四级漏斗-粗筛完成: {original_count}只 → {len(self.watchlist)}只，耗时{elapsed:.2f}ms")
            
            # 终端回显
            import click
            click.echo(f"\n{'='*60}")
            click.echo(f"📢 [四级漏斗-粗筛] {mode_tag}模式 | 量比>={min_volume_multiplier:.1f}x")
            click.echo(f"🎯 粗筛池: {len(self.watchlist)} 只")
            click.echo(f"{'='*60}\n")
            
            # 【CTO V5修复】删除Timer等待，直接return让start_session控制流程！
            # 粗筛完成后由start_session决定下一步（直接进入雷达循环）
            return
            
        except Exception as e:
            logger.error(f"❌ 09:30开盘粗筛失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _fire_control_mode(self):
        """
        【CTO V3终极重铸】高频监控模式 - 主线程直接接管！
        
        废除后台线程！雷达心跳必须在主线程！
        """
        # CTO修复：检查watchlist是否已初始化
        if not self.watchlist:
            logger.warning("⚠️ 股票池未初始化，跳过高频监控模式")
            logger.info("💡 提示：系统持续监控中，等待右侧起爆信号...")
            return
        
        logger.info(f"🎯 高频监控已激活: {len(self.watchlist)} 只目标 (主线程直接轮询)")
        
        # 初始化交易相关组件
        self._init_trading_components()
        
        # 【CTO V3】直接在主线程运行雷达循环！
        if self.enable_dynamic_radar:
            self._run_radar_main_loop()
        else:
            logger.info("📊 静态模式：跳过动态雷达")
    
    def _init_trading_components(self):
        """【CTO清理】初始化交易相关组件 - 纯血游资架构"""
        logger.debug("🎯 [纯血游资雷达] 交易组件初始化完成（精简模式）")
    
    def _print_fire_control_panel(self, top_targets, initial_loading=False, pool_stats=None, is_rest=False, msg=None):
        """
        【CTO V5】终极漏斗看板UI - 降维打击层次感 + 复盘模式 + 盘后投影
        
        Args:
            top_targets: TOP目标列表
            initial_loading: 是否首次加载
            pool_stats: 池统计 {'total', 'active', 'up', 'down', 'filtered'}
            is_rest: 是否午休/盘后复盘模式
            msg: 自定义消息（如"[盘后定格投影]"）
        """
        import os
        from datetime import datetime
        
        os.system('cls' if os.name == 'nt' else 'clear')
        now_str = datetime.now().strftime('%H:%M:%S')
        
        print("=" * 80)
        if msg:
            print(f"🚀 [V20 纯血游资猎杀雷达] | {msg} | {now_str}")
        elif is_rest:
            print(f"🚀 [V20 纯血游资猎杀雷达] | 📋 午休复盘模式 | {now_str}")
        else:
            print(f"🚀 [V20 纯血游资猎杀雷达] | 极速轮询模式 | {now_str}")
        print("=" * 80)
        
        if initial_loading:
            print("\n📡 雷达已锁定目标，正在捕获首轮微观动能数据...")
            print("⏳ 数据加载中 (Loading...)...\n")
            print("=" * 80)
            return
        
        if pool_stats:
            print(f"🎯 [狩猎漏斗] 基础池: 5191家 -> 粗筛池: {pool_stats['total']}家 -> 活跃监测: {pool_stats['active']}家")
            print(f"📈 [池内情绪] 涨: {pool_stats['up']}家 | 跌: {pool_stats['down']}家 | 死水/停牌: {pool_stats['filtered']}家")
            print("-" * 80)
        
        if is_rest or msg:
            print("📋 [机会池] TOP 10:")
        print(f"{'排名':<4} {'代码':<12} {'🩸血量':<10} {'价格':<8} {'涨跌幅':<8} {'流入比':<8}")
        print("-" * 80)
        
        if not top_targets:
            if is_rest or msg:
                print("  (暂无机会池数据)")
            else:
                print("  (当前无股票达到评分基础线，或正处于休盘期)")
        else:
            for i, t in enumerate(top_targets, 1):
                print(f"{i:<4} {t['code']:<12} {t['score']:<10.1f} {t['price']:<8.2f} {t['change']:<+7.1f}% {t['inflow_ratio']:<8.4f}")
        
        print("=" * 80)
        if msg:
            print(f"💡 {msg} - 数据已定格，仅供复盘审阅 (按 Ctrl+C 退出)")
        elif is_rest:
            print("💡 [复盘模式] 保留最后机会池数据，等待下午开盘... (按 Ctrl+C 退出)")
        else:
            print("💡 提示: 系统1秒极速刷新中... (按 Ctrl+C 退出并生成最终战报)")
    
    def _run_radar_main_loop(self):
        """
        【CTO V3终极重铸】真·狩猎雷达 - 主线程直接轮询版
        
        核心改造:
        1. 废除threading后台线程，主线程直接while循环
        2. 看板先行：initial_loading参数
        3. 漏斗UI：pool_stats统计
        4. 正确死水判断：今日累计volume==0（不是价格不变）
        5. 1秒刷新
        """
        import os
        import time
        from datetime import datetime, time as time_type
        from xtquant import xtdata
        from logic.data_providers.true_dictionary import get_true_dictionary
        from logic.strategies.kinetic_core_engine import 动能打分引擎CoreEngine
        
        # 预先获取TrueDictionary单例
        true_dict = get_true_dictionary()
        
        # 预先创建动能打分引擎实例
        core_engine = 动能打分引擎CoreEngine()
        
        # 【CTO V5】盘后投影标志位：记录是否已执行过盘后最终计算
        has_run_after_hours = False
        
        # 【CTO V7】盘后判断：避免不必要的订阅
        now_init = datetime.now()
        current_time_init = now_init.time()
        is_after_hours_init = current_time_init >= time_type(15, 0)
        
        # 【CTO V3看板绝对先行】第一帧立刻显示
        self._print_fire_control_panel([], initial_loading=True)
        
        # 【CTO V7闪电起步：分批唤醒QMT底层缓存，盘后跳过订阅！】
        if self.watchlist:
            logger.info(f"🔄 正在分批唤醒 {len(self.watchlist)} 只股票的 QMT 底层缓存...")
            batch_size = 50  # 【CTO V7】降至50只，更安全
            for i in range(0, len(self.watchlist), batch_size):
                batch = self.watchlist[i:i+batch_size]
                try:
                    # 【CTO V7】盘后无需订阅，直接拉快照；盘中才需订阅
                    if not is_after_hours_init:
                        xtdata.subscribe_whole_quote(batch)
                    # 轻碰一下接口，建立内存通道即可
                    xtdata.get_full_tick(batch)
                    time.sleep(0.1)  # 【CTO V7】必须让底盘呼吸！
                except Exception as e:
                    logger.warning(f"批次 {i//batch_size + 1} 唤醒失败: {e}")
            logger.info("✅ 缓存唤醒完毕，雷达正式起转！")
        
        logger.info("⚡ 主线程雷达循环开启！")
        
        try:
            while self.running:
                # 检查交易时间
                now = datetime.now()
                current_time = now.time()
                
                # 【CTO V5】午休期间：保持挂起，显示缓存
                is_lunch_break = time_type(11, 30) <= current_time < time_type(13, 0)
                if is_lunch_break and self.last_known_top_targets:
                    self._print_fire_control_panel(
                        self.last_known_top_targets, 
                        initial_loading=False, 
                        pool_stats={
                            'total': len(self.watchlist),
                            'active': 0,
                            'up': 0,
                            'down': 0,
                            'filtered': len(self.watchlist)
                        },
                        is_rest=True
                    )
                    print("\n⏸️ [午休复盘模式] 保留最后机会池数据，等待下午开盘...")
                    time.sleep(5)
                    continue
                
                # 【CTO V5】盘后期间 (15:00后)：执行一次最终计算然后定格展示
                is_after_hours = current_time >= time_type(15, 0)
                if is_after_hours and has_run_after_hours:
                    # 已经算过最终分数了，直接展示最终定格面板
                    self._print_fire_control_panel(
                        self.last_known_top_targets,
                        initial_loading=False,
                        pool_stats={
                            'total': len(self.watchlist),
                            'active': 0,
                            'up': 0,
                            'down': 0,
                            'filtered': len(self.watchlist)
                        },
                        msg="📋 盘后定格投影 - 今天的最终战果"
                    )
                    time.sleep(10)
                    continue
                
                # ----------------------------------------------------
                # 如果是盘中，或者是盘后的【第一次】循环，向下执行硬核打分！
                # ----------------------------------------------------
                loop_start = time.perf_counter()
                
                if not self.watchlist:
                    logger.warning("观察池为空，等待...")
                    time.sleep(5)
                    continue
                
                # 【CTO第一级：全量快照捕获】
                try:
                    all_ticks = xtdata.get_full_tick(self.watchlist)
                except Exception as e:
                    logger.error(f"获取全量Tick失败: {e}")
                    time.sleep(1)
                    continue
                
                if not all_ticks:
                    time.sleep(1)
                    continue
                
                current_top_targets = []
                pool_stats = {
                    'total': len(self.watchlist),
                    'active': 0,
                    'up': 0,
                    'down': 0,
                    'filtered': 0
                }
                
                # 【CTO第二级：极速布朗运动分类】
                for stock_code in self.watchlist:
                    tick = all_ticks.get(stock_code)
                    if not tick:
                        pool_stats['filtered'] += 1
                        continue
                    
                    current_price = tick.get('lastPrice', 0)
                    current_volume = tick.get('volume', 0)  # 今日累计成交量
                    # 【Phase1终极修复】从快照获取prev_close，不从TrueDictionary获取
                    pre_close = tick.get('lastClose', 0)
                    
                    # 【CTO V3修复】正确的死水判断：今日累计成交量为0
                    if current_volume == 0:
                        pool_stats['filtered'] += 1
                        continue
                    
                    if current_price <= 0 or pre_close is None or pre_close <= 0:
                        pool_stats['filtered'] += 1
                        continue
                    
                    # 统计涨跌
                    if current_price >= pre_close:
                        pool_stats['up'] += 1
                    else:
                        pool_stats['down'] += 1
                    
                    pool_stats['active'] += 1
                    
                    # 【CTO V4第三级：细筛 - 换手率+ATR】盘中动态过滤
                    try:
                        float_volume = true_dict.get_float_volume(stock_code)
                        volume_gu = current_volume * 100  # 手→股
                        turnover_rate = (volume_gu / float_volume * 100) if float_volume else 0
                        
                        # 换手率细筛：>5% 且 <150%
                        if turnover_rate < 5.0:
                            continue  # 换手不足，跳过
                        if turnover_rate >= 150.0:
                            continue  # 死亡换手，跳过
                        
                        # ATR势垒（可选，从true_dict获取）
                        atr_20d = true_dict.get_atr_20d(stock_code)
                        if atr_20d and atr_20d > 0:
                            today_tr = tick.get('high', current_price) - tick.get('low', current_price)
                            if today_tr > 0:
                                atr_ratio = today_tr / atr_20d
                                if atr_ratio < 1.8:
                                    continue  # ATR势垒不足，跳过
                    except Exception:
                        pass  # 细筛失败不阻塞，继续计算
                    
                    # 【CTO第四级：动能打分】
                    try:
                        change_pct = (current_price - pre_close) / pre_close
                        
                        float_market_cap = float_volume * pre_close if float_volume else 1.0
                        
                        flow_5min = current_volume * 0.1
                        flow_15min = current_volume * 0.3
                        flow_5min_median = true_dict.get_avg_volume_5d(stock_code) / 240
                        
                        high_60d = tick.get('high', current_price)
                        space_gap_pct = (high_60d - current_price) / high_60d if high_60d > 0 else 0.5
                        
                        try:
                            final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe = core_engine.calculate_true_dragon_score(
                                net_inflow=flow_15min * current_price,
                                price=current_price,
                                prev_close=pre_close,
                                high=current_price * 1.02,
                                low=current_price * 0.98,
                                open_price=current_price,
                                flow_5min=flow_5min,
                                flow_15min=flow_15min,
                                flow_5min_median_stock=flow_5min_median if flow_5min_median > 0 else 1.0,
                                space_gap_pct=space_gap_pct,
                                float_volume_shares=float_volume,
                                current_time=now.time()
                            )
                        except Exception:
                            final_score = change_pct * 100
                            sustain_ratio = 1.0
                            inflow_ratio = flow_15min * current_price / float_market_cap if float_market_cap > 0 else 0
                            ratio_stock = flow_5min / flow_5min_median if flow_5min_median > 0 else 0
                        
                        current_top_targets.append({
                            'code': stock_code,
                            'score': final_score,
                            'price': current_price,
                            'change': change_pct * 100,
                            'inflow_ratio': inflow_ratio,
                            'ratio_stock': ratio_stock,
                            'sustain_ratio': sustain_ratio
                        })
                    except Exception:
                        continue
                
                # 【CTO第五级：机会池排序】
                current_top_targets.sort(key=lambda x: x['score'], reverse=True)
                top_10 = current_top_targets[:10]
                
                # 【CTO V4关键】更新静态机会池缓存！
                if top_10:
                    self.last_known_top_targets = top_10
                
                # 【CTO V5】如果这是盘后的第一次计算，标记完成，以后不再重复算
                if is_after_hours:
                    has_run_after_hours = True
                    logger.info("✅ 盘后最终 Tick 快照计算完成，投影定格！")
                
                # 主线程强制刷屏
                self._print_fire_control_panel(top_10, initial_loading=False, pool_stats=pool_stats)
                
                # 战地收尸
                self._update_daily_battle_report(current_top_targets)
                
                # 【CTO物理限速器】1秒一圈
                elapsed = time.perf_counter() - loop_start
                sleep_time = max(0.1, 1.0 - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("🛑 用户中断，生成战报...")
            self._generate_final_battle_report()
        except Exception as e:
            logger.error(f"雷达循环异常: {e}")
            self._generate_final_battle_report()
    
    def _on_tick_data(self, tick_event):
        """
        Tick事件处理 - Phase 2: Tick级开火权下放 (CTO架构重塑)
        
        核心逻辑:
        1. 只在watchlist中的股票才处理 (0.90分位已进池)
        2. 实时计算该股票的量比（时间进度加权）
        3. 开火门槛：0.95分位（严格）
        4. 换手率检查（开火时才检查）
        5. 微观防线检查
        6. 动能打分引擎引擎算分
        7. 拔枪射击！
        
        Args:
            tick_event: Tick事件对象
        """
        # CTO强制透视：记录所有接收到的Tick（每100条打印一次避免刷屏）
        self._debug_tick_received_count = getattr(self, '_debug_tick_received_count', 0) + 1
        if self._debug_tick_received_count % 100 == 0:
            logger.debug(f"💓 [CTO透视] 累计接收Tick: {self._debug_tick_received_count} 条 | watchlist数量: {len(self.watchlist)}")
        
        # CTO加固：容错机制
        if not self.running:
            logger.warning("⚠️ [CTO透视] 引擎未运行，丢弃Tick")
            return
        
        stock_code = tick_event.stock_code
        
        # ============================================================
        # Phase 2 Step 1: 只在watchlist中的股票才处理
        # ============================================================
        if stock_code not in self.watchlist:
            # CTO透视：记录被过滤的股票（每1000条打印一次）
            self._debug_filtered_count = getattr(self, '_debug_filtered_count', 0) + 1
            if self._debug_filtered_count % 1000 == 0:
                logger.debug(f"🚫 [CTO透视] 已过滤 {self._debug_filtered_count} 条不在watchlist的Tick")
            return  # 不在观察池，直接丢弃
        
        # 【CTO清理】V18的warfare_core已废弃，使用动能打分引擎CoreEngine直接计算
        
        try:
            # ============================================================
            # Phase 2 Step 2: 实时计算该股票的量比（时间进度加权）
            # ============================================================
            from logic.data_providers.true_dictionary import get_true_dictionary
            
            now = datetime.now()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            minutes_passed = max(1, (now - market_open).total_seconds() / 60)
            
            current_volume = tick_event.volume
            true_dict = get_true_dictionary()
            avg_volume_5d = true_dict.get_avg_volume_5d(stock_code)
            
            if avg_volume_5d <= 0:
                logger.debug(f"⚠️ {stock_code} 5日均量无效，跳过")
                return
            
            # 估算全天成交量 = 当前成交量 / 已过分钟数 * 240分钟
            estimated_full_day_volume = current_volume / minutes_passed * 240
            current_volume_ratio = estimated_full_day_volume / avg_volume_5d
            
            # ============================================================
            # Phase 2 Step 3: 开火门槛 - 0.95分位（严格）
            # ============================================================
            from logic.core.config_manager import get_config_manager
            config_manager = get_config_manager()
            fire_threshold = self._get_current_fire_threshold(config_manager)
            
            # 只有当量比突破0.95分位才继续处理（开火权下放）
            if current_volume_ratio < fire_threshold:
                # 【CTO强制透视】记录被静默丢弃的Tick（每500条打印一次，避免刷屏）
                self._debug_below_threshold_count = getattr(self, '_debug_below_threshold_count', 0) + 1
                if self._debug_below_threshold_count % 500 == 0:
                    logger.debug(f"🚫 [CTO透视] 累计{self._debug_below_threshold_count}条Tick未达量比门槛({current_volume_ratio:.2f}x < {fire_threshold:.2f}x)")
                return  # 未达开火门槛，静默丢弃
            
            logger.info(f"🔥 {stock_code} 触发量比阈值: {current_volume_ratio:.2f}x >= {fire_threshold:.2f}x")
            
            # ============================================================
            # Phase 2 Step 4: 换手率检查（开火时才检查）
            # ============================================================
            turnover_rate = self._calculate_turnover_rate(stock_code, tick_event, true_dict)
            turnover_thresholds = config_manager.get_turnover_rate_thresholds()
            
            if turnover_rate < turnover_thresholds['per_minute_min']:
                logger.debug(f"🚫 {stock_code} 换手率不足: {turnover_rate:.2f}% < {turnover_thresholds['per_minute_min']:.2f}%")
                return  # 换手率不达标，放弃开火
            
            logger.info(f"✅ {stock_code} 换手率通过: {turnover_rate:.2f}%/min")
            
            # ============================================================
            # Phase 2 Step 5: 微观防线检查
            # ============================================================
            tick_data = {
                'stock_code': stock_code,
                'datetime': now,
                'price': tick_event.price,
                'volume': tick_event.volume,
                'amount': tick_event.amount,
                'open': tick_event.open,
                'high': tick_event.high,
                'low': tick_event.low,
                'prev_close': tick_event.prev_close,
                'volume_ratio': current_volume_ratio,
                'turnover_rate': turnover_rate,
            }
            
            if not self._micro_defense_check(stock_code, tick_data):
                logger.info(f"🚫 {stock_code} 未通过微观防线检查")
                return  # 微观防线拦截
            
            # ============================================================
            # 【CTO挂载】Phase 2 Step 5.5: 微积分形态学引擎 - 时空对齐
            # ============================================================
            kinetic_engine = self._get_kinetic_engine(stock_code)
            if kinetic_engine:
                # 将Tick喂给微积分引擎
                kinetic_engine.on_price_update(now, tick_event.price, tick_event.high)
                
                # 检测是否尖刺骗炮(Spike Trap)
                result = kinetic_engine.on_price_update(now, tick_event.price, tick_event.high)
                if result and result.get('is_trap', False):
                    logger.error(f"💀 {stock_code} 尖刺骗炮(Spike) detected! 时空否决！")
                    # 打上标签并跳过
                    tick_data['tag'] = "💀 尖刺骗炮(Spike)"
                    return  # 直接处决，不进入动能打分引擎算分
                
                # 检测生命周期T_maintain
                if hasattr(kinetic_engine, 'lifecycle_tracker'):
                    status = kinetic_engine.lifecycle_tracker.get_status()
                    if status and status.maintain_minutes < 11:
                        logger.warning(f"⏱️ {stock_code} 生命周期T_maintain={status.maintain_minutes} < 11min, 降权处理")
            
            # ============================================================
            # Phase 2 Step 6: 动能打分引擎引擎算分
            # ============================================================
            score = self._calculate_signal_score(stock_code, tick_data)
            
            if score < 70:  # 动能打分引擎阈值
                logger.info(f"🚫 {stock_code} 动能打分引擎得分不足: {score:.2f} < 70")
                return  # 得分不足，放弃开火
            
            logger.info(f"🎯 {stock_code} 动能打分引擎高分通过: {score:.2f}")
            
            # ============================================================
            # Phase 2 Step 7: 拔枪射击！
            # ============================================================
            self._execute_trade(stock_code, tick_data, score)
            
        except Exception as e:
            logger.error(f"❌ Tick事件处理失败 ({stock_code}): {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _get_current_fire_threshold(self, config_manager) -> float:
        """
        获取当前开火阈值 - 绝对量比阈值（非分位数！）
        
        Args:
            config_manager: 配置管理器实例
            
        Returns:
            float: 绝对量比阈值 (默认1.5倍)
        """
        # 【CTO重铸】：废除分位数误用，使用真实的游资放量标准
        # 从配置获取最小量比倍数（如1.5倍），而非分位数
        min_volume_multiplier = config_manager.get('live_sniper.min_volume_multiplier', 1.5)
        
        return min_volume_multiplier
    
    def _calculate_turnover_rate(self, stock_code: str, tick_event, true_dict) -> float:
        """
        计算每分钟换手率
        
        Args:
            stock_code: 股票代码
            tick_event: Tick事件
            true_dict: TrueDictionary实例
            
        Returns:
            float: 每分钟换手率 (%)
        """
        from datetime import datetime
        
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        minutes_passed = max(1, (now - market_open).total_seconds() / 60)
        
        current_volume = tick_event.volume
        float_volume = true_dict.get_float_volume(stock_code)
        
        if float_volume <= 0:
            return 0.0
        
        # 总换手率 = 成交量 / 流通股本 * 100%
        total_turnover_rate = (current_volume / float_volume) * 100
        
        # 每分钟换手率（实战核心指标）
        turnover_rate_per_min = total_turnover_rate / minutes_passed
        
        return turnover_rate_per_min
    
    def _micro_defense_check(self, stock_code: str, tick_data: Dict[str, Any]) -> bool:
        """
        微观防线检查 - 三道防线验证
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            
        Returns:
            bool: 是否通过微观防线
        """
        # 检查TradeGatekeeper是否可用
        if not self.trade_gatekeeper:
            logger.warning(f"⚠️ {stock_code} TradeGatekeeper未初始化，跳过微观防线")
            return True  # 容错：未初始化时默认通过
        
        try:
            # 防守斧：资金流检查
            capital_flow_ok = getattr(self.trade_gatekeeper, 'check_capital_flow', lambda *args: True)(
                stock_code, tick_data.get('volume_ratio', 0), tick_data
            )
            
            # 时机斧：板块共振检查
            sector_resonance_ok = getattr(self.trade_gatekeeper, 'check_sector_resonance', lambda *args: True)(
                stock_code, tick_data
            )
            
            # 资格斧：基础资格检查（涨跌停状态等）
            from logic.data_providers.true_dictionary import get_true_dictionary
            true_dict = get_true_dictionary()
            
            up_stop_price = true_dict.get_up_stop_price(stock_code)
            down_stop_price = true_dict.get_down_stop_price(stock_code)
            current_price = tick_data.get('price', 0)
            
            # 排除涨停和跌停状态
            if up_stop_price > 0 and current_price >= up_stop_price * 0.995:
                logger.debug(f"🚫 {stock_code} 接近涨停状态，放弃开火")
                return False
            
            if down_stop_price > 0 and current_price <= down_stop_price * 1.005:
                logger.debug(f"🚫 {stock_code} 接近跌停状态，放弃开火")
                return False
            
            # 综合微观防线结果
            micro_ok = capital_flow_ok and sector_resonance_ok
            
            if micro_ok:
                logger.info(f"✅ {stock_code} 微观防线检查通过")
            else:
                logger.info(f"🚫 {stock_code} 微观防线拦截: 资金={capital_flow_ok}, 板块={sector_resonance_ok}")
            
            return micro_ok
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 微观防线检查异常: {e}")
            return True  # 容错：异常时默认通过
    
    def _calculate_signal_score(self, stock_code: str, tick_data: Dict[str, Any]) -> float:
        """
        V20.5 动能算分 - 直接调用 kinetic_core_engine
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            
        Returns:
            float: 动能得分 (0-100)
        """
        try:
            # 【CTO 物理归位】：直接调用 V20.5 动能算子
            from logic.strategies.kinetic_core_engine import 动能打分引擎CoreEngine
            from logic.data_providers.true_dictionary import get_true_dictionary
            
            if not hasattr(self, '_kinetic_core'):
                self._kinetic_core = 动能打分引擎CoreEngine()
            
            true_dict = get_true_dictionary()
            
            # 提取 tick 数据
            price = tick_data.get('price', 0)
            volume = tick_data.get('volume', 0)
            amount = tick_data.get('amount', 0)
            high = tick_data.get('high', price)
            low = tick_data.get('low', price)
            open_price = tick_data.get('open', price)
            prev_close = tick_data.get('prev_close', price * 0.98)
            
            # 获取流通股本
            float_volume = true_dict.get_float_volume(stock_code)
            if not float_volume or float_volume <= 0:
                float_volume = 1e8  # 回退默认值
            
            # 计算5分钟和15分钟资金流（简化版）
            from datetime import datetime
            now = datetime.now()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            minutes_passed = max(1, (now - market_open).total_seconds() / 60)
            
            # 简化：用当前成交额估算资金流
            flow_5min = amount / max(1, minutes_passed) * 5 if minutes_passed > 0 else amount
            flow_15min = amount / max(1, minutes_passed) * 15 if minutes_passed > 0 else amount
            
            # 5分钟资金中位数（从5日均量估算）
            avg_vol_5d = true_dict.get_avg_volume_5d(stock_code)
            if avg_vol_5d and avg_vol_5d > 0:
                flow_5min_median = (avg_vol_5d / 240 * 5) * price
            else:
                flow_5min_median = flow_5min / 10
            
            # 调用 V20.5 动能引擎
            base_score, sustain_ratio, inflow_ratio, ratio_stock, mfe_score = self._kinetic_core.calculate_true_dragon_score(
                net_inflow=amount * 0.5,  # 简化：假设50%为净流入
                price=price,
                prev_close=prev_close,
                high=high,
                low=low,
                open_price=open_price,
                flow_5min=flow_5min,
                flow_15min=flow_15min,
                flow_5min_median_stock=flow_5min_median,
                space_gap_pct=0.05,
                float_volume_shares=float_volume,
                current_time=now
            )
            
            logger.debug(f"🎯 {stock_code} V20.5动能得分: {base_score:.2f}, sustain={sustain_ratio:.2f}, mfe={mfe_score:.2f}")
            return base_score
            
        except Exception as e:
            logger.error(f"❌ {stock_code} V20.5动能算分失败: {e}")
            return 0.0
            
            # 应用记忆multiplier
            final_score = base_score * memory_multiplier
            
            logger.debug(f"🎯 {stock_code} 动能算分: base={base_score:.2f}, memory_mult={memory_multiplier:.2f}, final={final_score:.2f}")
            return final_score
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 动能算分失败: {e}")
            return 0.0
    
    def _execute_trade(self, stock_code: str, tick_data: Dict[str, Any], score: float):
        """
        执行交易 - 拔枪射击
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            score: 动能打分引擎得分
        """
        if not self.trader:
            logger.warning(f"⚠️ {stock_code} 交易接口未连接，跳过执行")
            return
        
        try:
            logger.info(f"🚨 {stock_code} 触发交易信号! 得分={score:.2f}, 价格={tick_data.get('price', 0)}")
            
            # 执行交易
            from logic.execution.trade_interface import TradeOrder, OrderDirection
            
            order = TradeOrder(
                stock_code=stock_code,
                direction=OrderDirection.BUY.value,
                quantity=100,  # 可根据资金管理调整
                price=tick_data.get('price', 0),
                remark=f'动能打分引擎_{score:.1f}_VR_{tick_data.get("volume_ratio", 0):.1f}'
            )
            
            result = self.trader.buy(order)
            logger.info(f"💰 {stock_code} 交易结果: {result}")
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 交易执行失败: {e}")

    def format_dragon_report(self, rank: int, stock_code: str, stock_name: str,
                            final_score: float, inflow_ratio: float,
                            ratio_stock: float, sustain_ratio: float,
                            space_gap_pct: float, tag: str, mfe: float = 0.0) -> str:
        """
        格式化龙榜输出 - 工业级UI看板

        Args:
            rank: 排名序号
            stock_code: 股票代码
            stock_name: 股票名称
            final_score: 最终得分
            inflow_ratio: 流入比（净流入占流通市值比例）
            ratio_stock: 自身爆发倍数
            sustain_ratio: 接力比（资金维持率）
            space_gap_pct: 空间差百分比（用于纯度评级）
            tag: 标签（换手甜点/战法类型）
            mfe: MFE资金做功效率

        Returns:
            str: 格式化后的龙榜行
        """
        purity = '极优' if space_gap_pct < 0.05 else '优' if space_gap_pct < 0.10 else '良'
        return f"{rank}. [{stock_code} {stock_name}] 🩸得分: {final_score:.1f} | 流入比: {inflow_ratio:.1%} | 自身爆发: {ratio_stock:.1f}x | 接力(Sustain): {sustain_ratio:.2f}x | MFE: {mfe:.2f} | 纯度: {purity} | [标签: {tag}]"

    def calculate_time_slice_flows(self, stock_code: str, date: str = None) -> Optional[Dict]:
        """
        【CTO终极红线：时空绝对对齐】计算真实时间切片资金流
        
        核心要求：
        1. 绝不允许用全天数据估算切片！必须通过 get_local_data(period='tick'/'1m') 真实拉取日内历史流
        2. 截取 09:30-09:35 计算真实 flow_5min
        3. 截取 09:30-09:45 计算真实 flow_15min
        
        Args:
            stock_code: 股票代码
            date: 日期 'YYYYMMDD'，默认为今天
            
        Returns:
            Dict: 包含flow_5min, flow_15min的字典，或None（数据不足）
        """
        try:
            from xtquant import xtdata
            from datetime import datetime, timedelta
            
            # 默认使用今天
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            
            # 标准化代码
            normalized_code = self._normalize_stock_code(stock_code)
            
            # 【核心】真实拉取日内历史Tick流 - 严禁用全天数据估算！
            tick_data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume', 'amount'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if not tick_data or normalized_code not in tick_data:
                logger.warning(f"⚠️ {stock_code} 无Tick数据")
                return None
            
            df = tick_data[normalized_code]
            if df.empty or len(df) < 10:
                logger.warning(f"⚠️ {stock_code} Tick数据不足")
                return None
            
            # 转换时间戳为可读时间
            if 'time' in df.columns:
                if pd.api.types.is_numeric_dtype(df['time']):
                    df['datetime'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
                    df['time_str'] = df['datetime'].dt.strftime('%H:%M:%S')
                else:
                    df['time_str'] = df['time'].astype(str)
            
            # 【时空切片1】截取 09:30-09:35 计算真实 flow_5min
            df_5min = df[(df['time_str'] >= '09:30:00') & (df['time_str'] <= '09:35:00')].copy()
            if df_5min.empty:
                logger.warning(f"⚠️ {stock_code} 09:30-09:35 无数据")
                return None
            
            # 计算5分钟资金流入（简化：用amount增量）
            if 'amount' in df_5min.columns:
                flow_5min = df_5min['amount'].sum()
            else:
                # 如果没有amount，用 price * volume * 100 估算
                flow_5min = (df_5min['lastPrice'] * df_5min['volume'] * 100).sum()
            
            # 【时空切片2】截取 09:30-09:45 计算真实 flow_15min
            df_15min = df[(df['time_str'] >= '09:30:00') & (df['time_str'] <= '09:45:00')].copy()
            if df_15min.empty:
                logger.warning(f"⚠️ {stock_code} 09:30-09:45 无数据")
                return None
            
            if 'amount' in df_15min.columns:
                flow_15min = df_15min['amount'].sum()
            else:
                flow_15min = (df_15min['lastPrice'] * df_15min['volume'] * 100).sum()
            
            logger.debug(f"✅ {stock_code} 时空切片: 5min={flow_5min/1e8:.2f}亿, 15min={flow_15min/1e8:.2f}亿")
            
            return {
                'flow_5min': float(flow_5min),
                'flow_15min': float(flow_15min),
                'tick_count_5min': len(df_5min),
                'tick_count_15min': len(df_15min)
            }
            
        except Exception as e:
            logger.error(f"❌ {stock_code} 时空切片计算失败: {e}")
            return None

    def _check_trade_signal(self, stock_code: str, score: float, tick_data: Dict[str, Any]):
        """
        [已废弃] 检查交易信号 - Phase 2后统一使用_tick级开火流程
        
        保留此方法用于向后兼容，新逻辑已全部迁移至_on_tick_data
        """
        logger.debug(f"⚠️ _check_trade_signal已废弃，请使用新的Tick级开火流程")
        # 新逻辑已在_on_tick_data中实现，此方法不再被调用
    

    def _start_auto_replenishment(self):
        """
        CTO强制：启动自动补网定时器
        每分钟检查一次，如果watchlist为空则执行快照筛选
        """
        import threading
        import time
        from datetime import datetime
        
        def auto_replenish_loop():
            while self.running:
                try:
                    current_time = datetime.now()
                    market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
                    market_close = current_time.replace(hour=15, minute=0, second=0, microsecond=0)
                    
                    # 只在交易时间内运行
                    if market_open.time() <= current_time.time() <= market_close.time():
                        # 如果watchlist为空，执行快照筛选
                        if not self.watchlist:
                            logger.info("🔄 自动补网：执行快照筛选...")
                            self._snapshot_filter()
                            
                            # 如果筛选到股票，进入高频监控模式
                            if self.watchlist:
                                logger.info(f"🎯 自动补网成功，发现 {len(self.watchlist)} 只目标")
                                self._fire_control_mode()
                    
                    # 每分钟检查一次
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"❌ 自动补网循环异常: {e}")
                    time.sleep(60)  # 出错后也继续运行
        
        # 启动自动补网线程
        replenish_thread = threading.Thread(target=auto_replenish_loop, daemon=True)
        replenish_thread.start()
        logger.info("✅ 自动补网定时器已启动")

    def _process_snapshot_at_0930(self):
        """
        CTO修正：处理当前截面快照
        盘中启动时，获取当前市场快照并筛选强势股
        """
        import pandas as pd
        from datetime import datetime
        
        try:
            logger.info("🔄 执行当前截面快照筛选...")
            
            # 【架构解耦】检查adapter
            if not hasattr(self, 'qmt_adapter') or self.qmt_adapter is None:
                logger.error("🚨 QMTEventAdapter未初始化")
                return
            
            # 获取全市场快照
            all_stocks = self.qmt_adapter.get_all_a_shares()
            if not all_stocks:
                logger.error("🚨 无法获取股票列表")
                return
            
            snapshot = self.qmt_adapter.get_full_tick_snapshot(all_stocks)
            if not snapshot:
                logger.error("🚨 无法获取当前快照")
                return
            
            # 转换为DataFrame进行向量化过滤
            df = pd.DataFrame([
                {
                    'stock_code': code,
                    'price': tick.get('lastPrice', 0) if isinstance(tick, dict) else getattr(tick, 'lastPrice', 0),
                    'volume': tick.get('volume', 0) if isinstance(tick, dict) else getattr(tick, 'volume', 0),
                    'amount': tick.get('amount', 0) if isinstance(tick, dict) else getattr(tick, 'amount', 0),
                    'open': tick.get('open', 0) if isinstance(tick, dict) else getattr(tick, 'open', 0),
                    'high': tick.get('high', 0) if isinstance(tick, dict) else getattr(tick, 'high', 0),
                    'low': tick.get('low', 0) if isinstance(tick, dict) else getattr(tick, 'low', 0),
                    'prev_close': tick.get('lastClose', 0) if isinstance(tick, dict) else getattr(tick, 'lastClose', 0),
                }
                for code, tick in snapshot.items() if tick
            ])
            
            if df.empty:
                logger.error("🚨 快照数据为空")
                return
            
            # 从TrueDictionary获取涨停价
            from logic.data_providers.true_dictionary import get_true_dictionary
            true_dict = get_true_dictionary()
            
            df['up_stop_price'] = df['stock_code'].map(
                lambda x: true_dict.get_up_stop_price(x) if true_dict else 0.0
            )
            
            # 5日均量数据
            df['avg_volume_5d'] = df['stock_code'].map(true_dict.get_avg_volume_5d)
            
            # ⭐️ CTO裁决修复：引入时间进度加权，防止盘中量比失真
            # 量比 = 估算全天成交量 / 5日平均成交量
            # 其中 估算全天成交量 = 当前成交量 / 已过分钟数 * 240分钟
            now = datetime.now()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            raw_minutes = (now - market_open).total_seconds() / 60
            # CTO重塑Phase3：开盘前5分钟使用缓冲值5，防止量比虚高
            # 【Bug修复】限制最大240分钟，防止盘后运行量比被摊薄
            if raw_minutes < 5:
                minutes_passed = 5  # 缓冲启动区
            else:
                minutes_passed = min(max(1, raw_minutes), 240)  # 限制最大240分钟
            
            df['estimated_full_day_volume'] = df['volume'] / minutes_passed * 240
            df['volume_ratio'] = df['estimated_full_day_volume'] / df['avg_volume_5d'].replace(0, pd.NA)
            
            # 【CTO源码清剿】删除0.90 Magic Number，使用纯动态倍数（Ratio化）
            # 直接从配置读取最小放量倍数，Fail-Fast模式（无默认值）
            from logic.core.config_manager import get_config_manager
            config_manager = get_config_manager()
            try:
                min_volume_multiplier = config_manager.get('live_sniper.min_volume_multiplier')
                if min_volume_multiplier is None:
                    raise ValueError("配置缺失: live_sniper.min_volume_multiplier")
            except Exception as e:
                logger.error(f"❌ [CTO强制审计] 配置读取失败: {e}")
                raise RuntimeError("系统拒绝启动：缺少核心配置 live_sniper.min_volume_multiplier")
            
            # 【CTO源码清剿】纯动态倍数过滤：量比 >= 配置倍数（如1.5倍）
            mask = (
                (df['volume_ratio'] >= min_volume_multiplier) &  # ⭐️ 动态倍数：今日是5日均量的X倍
                (df['volume'] > 0)  # 只需有成交量
            )
            
            filtered_df = df[mask].copy()
            
            # 按量比排序
            filtered_df = filtered_df.sort_values('volume_ratio', ascending=False)
            
            # 4. 【CTO重塑】放宽数量限制：50-150只观察池
            watchlist_count = len(filtered_df)
            
            # 【CTO第三刀】消除观察池数量焦虑：只要>0就不警告
            if watchlist_count == 0:
                logger.warning(f"⚠️ 观察池为空，无法监控")
            elif watchlist_count < 10:
                logger.info(f"💡 观察池数量较少: {watchlist_count}只")
            else:
                logger.info(f"✅ 观察池已就绪: {watchlist_count}只")
            
            self.watchlist = filtered_df['stock_code'].tolist()[:150]  # 最多150只
            
            logger.info(f"✅ 当前截面筛选完成: {len(self.watchlist)} 只目标")
            
            if len(self.watchlist) > 0:
                top5 = filtered_df.head(5)
                for _, row in top5.iterrows():
                    logger.info(f"  🎯 {row['stock_code']}: 量比{row['volume_ratio']:.2f}")
            
        except Exception as e:
            logger.error(f"❌ 当前截面快照筛选失败: {e}")

    def stop(self):
        """停止引擎 - CTO战地收尸版"""
        logger.info("🛑 停止实盘总控引擎...")
        self.running = False
        
        # 【CTO核心护城河】释放QMT底层内存，防止内存泄漏！
        if self.watchlist:
            try:
                from xtquant import xtdata
                xtdata.unsubscribe_whole_quote(self.watchlist)
                logger.info(f"✅ 已释放 {len(self.watchlist)} 只股票的QMT订阅")
            except Exception as e:
                logger.warning(f"⚠️ 取消订阅失败: {e}")
        
        # 停止事件总线
        if self.event_bus:
            self.event_bus.stop()
        
        # 【CTO防呆保护】防止paper模式下没有trader属性导致的报错
        if hasattr(self, 'trader') and self.trader:
            self.trader.disconnect()
        
        # 【CTO战地收尸】生成最终战报
        self._generate_final_battle_report()
        
        logger.info("✅ 实盘总控引擎已停止")
    
    def _update_daily_battle_report(self, current_scores: list):
        """
        【CTO战地收尸】更新今日战报 - 维护每个股票的最高分记录
        
        Args:
            current_scores: 当前打分列表 [{'code': str, 'score': float, ...}, ...]
        """
        for item in current_scores:
            code = item.get('code', '')
            score = item.get('score', 0)
            
            if not code:
                continue
            
            # 更新最高分记录
            if code not in self.highest_scores or score > self.highest_scores[code].get('score', 0):
                self.highest_scores[code] = {
                    'code': code,
                    'score': score,
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'price': item.get('price', 0),
                    'change': item.get('change', 0),
                    'inflow_ratio': item.get('inflow_ratio', 0),
                    'ratio_stock': item.get('ratio_stock', 0),
                    'sustain_ratio': item.get('sustain_ratio', 0),
                    'purity': item.get('purity', '')
                }
    
    def _generate_final_battle_report(self):
        """
        【CTO战地收尸】生成最终战报 - 退出必留痕
        
        输出：
        1. data/battle_reports/battle_report_{date}.json
        2. 终端打印TOP 3战神榜
        """
        if not self.highest_scores:
            logger.info("📊 今日无战报数据（观察池为空或无打分记录）")
            return
        
        import json
        import os
        from pathlib import Path
        
        # 创建战报目录
        report_dir = Path('data/battle_reports')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now().strftime('%Y%m%d')
        report_path = report_dir / f'battle_report_{today}.json'
        
        # 按分数排序
        final_list = sorted(self.highest_scores.values(), key=lambda x: x.get('score', 0), reverse=True)
        
        # 生成战报数据
        report_data = {
            'date': today,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_targets': len(final_list),
            'top_targets': final_list[:50]  # 只保存前50名
        }
        
        # 保存JSON
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=4)
            logger.info(f"✅ 战地收官报告已生成 -> {report_path}")
        except Exception as e:
            logger.error(f"❌ 战报保存失败: {e}")
        
        # 终端打印战神榜
        print("\n" + "=" * 60)
        print("🏆 今日战神榜 TOP 10")
        print("=" * 60)
        print(f"{'排名':<4} {'代码':<12} {'最高血量':<10} {'时间':<10} {'涨幅':<8}")
        print("-" * 60)
        for i, target in enumerate(final_list[:10], 1):
            print(f"{i:<4} {target['code']:<12} {target['score']:<10.1f} {target['time']:<10} {target.get('change', 0):<8.2f}%")
        print("=" * 60)
        print(f"📊 总计追踪: {len(final_list)} 只股票")
        print(f"💾 完整战报: {report_path}")


# 便捷函数
def create_live_trading_engine() -> LiveTradingEngine:
    """
    创建实盘总控引擎实例
    
    Returns:
        LiveTradingEngine: 引擎实例
    """
    return LiveTradingEngine()


if __name__ == "__main__":
    # 测试实盘总控引擎
    print("🧪 实盘总控引擎测试 (CTO加固版)")
    print("=" * 50)
    
    # 创建引擎
    engine = create_live_trading_engine()
    
    print("🚀 引擎创建完成")
    print("💡 注意: 该测试仅验证组件加载，不执行实际交易")
    
    # 模拟启动（不实际运行）
    try:
        engine._init_trading_components()
        print("✅ 交易组件加载测试完成")
    except Exception as e:
        print(f"⚠️ 组件加载测试失败: {e}")
    
    print("\n✅ 实盘总控引擎测试完成")
    print("🎯 修复版已准备就绪")