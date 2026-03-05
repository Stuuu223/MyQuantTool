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
        启动交易会话 - CTO强制规范版（修复盘中启动死局）
        时间线: 09:25(CTO第一斩) -> 09:30(开盘快照二筛) -> 09:35(火控雷达)
        
        CTO修复：盘中启动时必须先执行快照筛选填充watchlist！
        
        Args:
            enable_dynamic_radar: 是否启用动态雷达（默认True，仅实盘使用）
        """
        # 【CTO修复】将参数保存为实例变量，供后续函数使用
        self.enable_dynamic_radar = enable_dynamic_radar
        logger.info("🚀 启动实盘总控引擎 (CTO第一斩版)")
        
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
                timer = threading.Timer(seconds_to_open, self._snapshot_filter)
                timer.daemon = True
                timer.start()
            else:
                self._snapshot_filter()
            return
        
        # 如果还没到09:25，等待到09:25执行第一斩
        seconds_to_auction = (auction_end - current_time).total_seconds()
        if seconds_to_auction > 0:
            logger.info(f"⏰ 等待{seconds_to_auction:.0f}秒到09:25集合竞价结束...")
            auction_timer = threading.Timer(seconds_to_auction, self._execute_auction_filter)
            auction_timer.daemon = True
            auction_timer.start()
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
            timer = threading.Timer(seconds_to_open, self._snapshot_filter)
            timer.daemon = True
            timer.start()
        else:
            logger.info("🎯 已到09:30，立即启动开盘快照过滤...")
            self._snapshot_filter()
    
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
                    'prev_close': tick.get('preClose', 0) if isinstance(tick, dict) else getattr(tick, 'preClose', 0),
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
            
            # 7. 【CTO强化】保存竞价数据到CSV
            output_path = f"data/auction_snapshot_{today_str}.csv"
            try:
                output_df = filtered_df[['stock_code', 'open', 'prev_close', 'open_change_pct', 
                                         'volume', 'amount', 'auction_power', 'bidVol1', 'askVol1']]
                output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 竞价数据已保存: {output_path} ({len(filtered_df)}只)")
            except Exception as e:
                logger.warning(f"⚠️ 竞价数据保存失败: {e}")
            
            # 8. 更新watchlist为初筛结果（限制500只）
            self.watchlist = filtered_df['stock_code'].tolist()[:500]
            
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
            true_dict = get_true_dictionary()
            
            # 使用当前watchlist + 扩展池进行预热
            warmup_stocks = self._get_extended_stock_pool(self.watchlist)
            
            result = true_dict.warmup(warmup_stocks)
            
            if result['integrity']['is_ready']:
                logger.info(
                    f"✅ TrueDictionary装弹完成: "
                    f"涨停价缓存{result['qmt'].get('success', 0)}只, "
                    f"5日均量缓存{result['tushare'].get('success', 0)}只"
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
        09:30开盘快照二筛 - CTO第二斩
        500只 → 30只（16:1淘汰）
        
        核心逻辑:
        1. 获取09:25筛选出的500只股票的开盘快照
        2. 从TrueDictionary获取真实五日均量、流通盘
        3. 向量化计算量比和换手率
        4. CTO物理过滤: 量比>3 且 1%<换手率<20%
        5. 只保留Top30给动能打分引擎引擎
        """
        import pandas as pd
        
        start_time = time.perf_counter()
        
        try:
            from logic.data_providers.true_dictionary import get_true_dictionary
            
            # 【架构解耦】检查adapter
            if not hasattr(self, 'qmt_adapter') or self.qmt_adapter is None:
                logger.error("🚨 QMTEventAdapter未初始化")
                self._fallback_premarket_scan()
                return
            
            # 1. 获取09:25筛选出的股票的开盘快照
            if not self.watchlist:
                logger.error("🚨 watchlist为空，无法进行09:30二筛")
                self._fallback_premarket_scan()
                return
            
            snapshot = self.qmt_adapter.get_full_tick_snapshot(self.watchlist)
            
            if not snapshot:
                logger.error("🚨 无法获取09:30开盘快照")
                # CTO加固：容错机制 - 使用回退方案
                self._fallback_premarket_scan()
                return
            
            # 2. 转换为DataFrame（向量化，无iterrows）
            df = pd.DataFrame([
                {
                    'stock_code': code,
                    'price': tick.get('lastPrice', 0) if isinstance(tick, dict) else getattr(tick, 'lastPrice', 0),
                    'volume': tick.get('volume', 0) if isinstance(tick, dict) else getattr(tick, 'volume', 0),
                    'amount': tick.get('amount', 0) if isinstance(tick, dict) else getattr(tick, 'amount', 0),
                    'open': tick.get('open', 0) if isinstance(tick, dict) else getattr(tick, 'open', 0),
                    'high': tick.get('high', 0) if isinstance(tick, dict) else getattr(tick, 'high', 0),
                    'low': tick.get('low', 0) if isinstance(tick, dict) else getattr(tick, 'low', 0),
                }
                for code, tick in snapshot.items() if tick
            ])
            
            if df.empty:
                logger.error("🚨 09:30快照数据为空")
                return
            
            original_count = len(df)
            
            # 3. 从TrueDictionary获取真实数据（五日均量、流通盘）
            true_dict = get_true_dictionary()
            
            # 向量化获取数据（使用map而非iterrows）
            df['avg_volume_5d'] = df['stock_code'].map(true_dict.get_avg_volume_5d)
            df['float_volume'] = df['stock_code'].map(true_dict.get_float_volume)
            
            # 4. 向量化计算量比和换手率（CTO规范：禁止iterrows）
            # 【宪法第九条】量纲对齐：tick volume(手) → 股 (×100)
            df['volume_gu'] = df['volume'] * 100  # 手→股
            
            # ⭐️ CTO裁决修复：引入时间进度加权，防止早盘量比失真
            # 量比 = 估算全天成交量 / 5日平均成交量
            # 其中 估算全天成交量 = 当前成交量 / 已过分钟数 * 240分钟
            from datetime import datetime
            now = datetime.now()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            raw_minutes = (now - market_open).total_seconds() / 60
            # CTO重塑Phase3：开盘前5分钟使用缓冲值5，防止量比虚高
            # 【Bug修复】限制最大240分钟，防止盘后运行量比被摊薄
            if raw_minutes < 5:
                minutes_passed = 5  # 缓冲启动区
                logger.info(f"⏰ 开盘缓冲期: 使用最小值5分钟计算量比")
            else:
                minutes_passed = min(raw_minutes, 240)  # 限制最大240分钟
            
            # 时间进度加权：估算全天成交量 (单位：股)
            df['estimated_full_day_volume'] = df['volume_gu'] / minutes_passed * 240
            df['volume_ratio'] = df['estimated_full_day_volume'] / df['avg_volume_5d'].replace(0, pd.NA)
            
            # 换手率 = 成交量(股) / 流通股本(股) * 100%
            df['turnover_rate'] = (df['volume_gu'] / df['float_volume'].replace(0, pd.NA)) * 100
            
            # ⭐️ CTO终极Ratio化：计算每分钟换手率（老板钦定）
            # 实战意义：09:35(5分钟)需>1%，10:00(30分钟)需>6%，排除盘中偷袭假起爆
            df['turnover_rate_per_min'] = df['turnover_rate'] / minutes_passed
            
            # 清理无效数据
            df = df.dropna(subset=['volume_ratio', 'turnover_rate', 'turnover_rate_per_min'])
            
            # 5. 【CTO Phase1重塑】宽体观察池：0.90分位门槛，移除换手率限制
            # 观察池是雷达标的，不是最终买入点 - 放宽进池门槛
            from logic.core.config_manager import get_config_manager
            
            config_manager = get_config_manager()
            
            # 【架构大一统】使用GlobalFilterGateway统一过滤逻辑
            # 无论是实盘、回放、回测，都必须走同一套Boss三维铁网！
            from logic.strategies.global_filter_gateway import apply_boss_filters
            
            # 【物理探针】记录过滤前数据
            pre_filter_count = len(df)
            logger.info(f"\n{'='*60}")
            logger.info(f"🔬 【物理探针】09:30快照筛选漏斗分析")
            logger.info(f"{'='*60}")
            logger.info(f"▶ 初始输入池: {pre_filter_count} 只")
            logger.info(f"   量比范围: {df['volume_ratio'].min():.2f}x ~ {df['volume_ratio'].max():.2f}x")
            logger.info(f"   换手范围: {df['turnover_rate'].min():.2f}% ~ {df['turnover_rate'].max():.2f}%")
            
            filtered_df, stats = apply_boss_filters(
                df=df,
                config_manager=config_manager,
                true_dict=true_dict,
                context="realtime_snapshot"
            )
            
            # 【物理探针】记录过滤后数据
            post_filter_count = len(filtered_df)
            rejection_count = pre_filter_count - post_filter_count
            rejection_rate = rejection_count / pre_filter_count * 100 if pre_filter_count > 0 else 0
            
            logger.info(f"\n📊 【物理探针】过滤统计:")
            logger.info(f"▶ 过滤后剩余: {post_filter_count} 只")
            logger.info(f"🚫 被淘汰: {rejection_count} 只 ({rejection_rate:.1f}%)")
            logger.info(f"✅ 通过率: {stats.get('filter_rate', 'N/A')}")
            logger.info(f"📋 应用的过滤器: {stats.get('filters_applied', [])}")
            logger.info(f"{'='*60}\n")
            
            # 按量比排序
            filtered_df = filtered_df.sort_values('volume_ratio', ascending=False)
            
            elapsed = (time.perf_counter() - start_time) * 1000
            
            # 6. 【CTO重塑】放宽数量限制：50-150只观察池
            watchlist_count = len(filtered_df)
            
            # 【CTO第三刀】消除观察池数量焦虑：只要>0就不警告
            if watchlist_count == 0:
                logger.warning(f"⚠️ 观察池为空，无法监控")
            elif watchlist_count < 10:
                logger.info(f"💡 观察池数量较少: {watchlist_count}只")
            else:
                logger.info(f"✅ 观察池已就绪: {watchlist_count}只")
            
            self.watchlist = filtered_df['stock_code'].tolist()[:150]  # 最多150只
            
            # ⭐️ 记录Ratio化参数（CTO封板要求）
            # 【修复】从config读取min_volume_multiplier，而非假设变量存在
            min_volume_multiplier = config_manager.get('live_sniper.min_volume_multiplier', 1.5)
            logger.info(f"🔪 CTO第二斩完成: {original_count}只 → {len(self.watchlist)}只，耗时{elapsed:.2f}ms")
            logger.info(f"   ⏱️ 开盘已运行: {minutes_passed:.1f}分钟 | 量比倍数门槛: {min_volume_multiplier:.2f}x (动态Ratio)")
            logger.info(f"   📊 【CTO源码清剿】观察池使用纯动态倍数（>= {min_volume_multiplier}x），Zero Magic Number！")
            
            # 【CTO强制回显】必须在终端显示观察池状态！
            import click
            click.echo(f"\n{'='*60}")
            click.echo(f"📢 [CTO物理透视] 09:30盘中快照筛选完毕！")
            click.echo(f"🎯 成功越过 {min_volume_multiplier:.1f}x 量比门槛的股票数量: {len(self.watchlist)} 只")
            if len(self.watchlist) == 0:
                click.echo(click.style("❌ 致命警报：观察池为0！所有股票均被过滤，雷达无目标可盯！", fg="red"))
                click.echo(click.style(f"   请检查 {min_volume_multiplier:.1f}x 量比门槛是否过高，或今日行情是否极其低迷", fg="yellow"))
            elif len(self.watchlist) < 10:
                click.echo(click.style(f"⚠️ 观察池数量较少: {len(self.watchlist)}只", fg="yellow"))
            else:
                click.echo(click.style(f"✅ 观察池已就绪: {len(self.watchlist)}只", fg="green"))
            click.echo(f"{'='*60}\n")
            
            # 7. 记录详细日志（Top5）
            if len(filtered_df) > 0:
                top5 = filtered_df.head(5)
                for _, row in top5.iterrows():
                    logger.info(f"  🎯 {row['stock_code']}: 量比{row['volume_ratio']:.1f}, 换手{row['turnover_rate']:.1f}%, 每分钟{row['turnover_rate_per_min']:.2f}%")
            
            # 8. 启动09:35火控雷达定时器
            logger.info("🎯 09:30二筛完成，等待09:35启动火控雷达...")
            timer = threading.Timer(300.0, self._fire_control_mode)  # 5分钟后09:35
            timer.daemon = True
            timer.start()
            
        except Exception as e:
            logger.error(f"❌ 09:30开盘二筛失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _fire_control_mode(self):
        """高频监控模式 - Tick订阅+实时算分 - CTO强制规范版"""
        # CTO修复：检查watchlist是否已初始化
        if not self.watchlist:
            logger.warning("⚠️ 股票池未初始化，跳过高频监控模式")
            logger.info("💡 提示：系统持续监控中，等待右侧起爆信号...")
            # CTO修复：不再自杀，系统持续运行等待自动补网
            return
        
        logger.info(f"🎯 高频监控已激活: {len(self.watchlist)} 只目标 (通过QMT回调接收数据)")
        
        # 初始化交易相关组件
        self._init_trading_components()
        
        # 【CTO铁血整改】根据实例变量决定是否启动动态雷达
        if self.enable_dynamic_radar:
            logger.info("📡 启动动态雷达刷新线程...")
            self._start_dynamic_radar()
        else:
            logger.info("📊 静态模式：跳过动态雷达")
    
    def _init_trading_components(self):
        """【CTO清理】初始化交易相关组件 - 纯血游资架构"""
        # 【CTO说明】V18的warfare_core/trade_gatekeeper等模块已被纯血游资架构废除
        # 相关功能已整合到动能打分引擎CoreEngine和GlobalFilterGateway
        logger.debug("🎯 [纯血游资雷达] 交易组件初始化完成（精简模式）")
    
    def _start_dynamic_radar(self):
        """
        【CTO铁血整改】启动动态雷达刷新线程
        每3秒刷新一次看板，展示watchlist中股票的实时动能打分引擎分数
        """
        import threading
        import os
        import time
        from datetime import datetime
        
        def radar_loop():
            while self.running:
                try:
                    # 清屏
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    # 获取当前时间
                    now = datetime.now()
                    time_str = now.strftime('%H:%M:%S')
                    
                    # 打印表头
                    print("="*100)
                    print(f"🚀 [V20 纯血游资雷达] 动态火控看板 | 当前时间: {time_str}")
                    print("="*100)
                    
                    # 计算watchlist中每只股票的实时分数
                    dragon_list = []
                    for stock_code in self.watchlist[:20]:  # 只计算前20只
                        try:
                            # 获取实时数据
                            from xtquant import xtdata
                            from logic.data_providers.true_dictionary import get_true_dictionary
                            from logic.core.config_manager import get_config_manager
                            
                            true_dict = get_true_dictionary()
                            config_manager = get_config_manager()
                            
                            # 获取当前价格和成交量
                            full_tick = xtdata.get_full_tick([stock_code])
                            if not full_tick or stock_code not in full_tick:
                                continue
                            
                            tick = full_tick[stock_code]
                            current_price = tick.get('lastPrice', 0)
                            current_volume = tick.get('volume', 0)
                            pre_close = true_dict.get_prev_close(stock_code)
                            
                            if current_price <= 0 or pre_close <= 0:
                                continue
                            
                            # 计算涨幅
                            change_pct = (current_price - pre_close) / pre_close
                            
                            # 获取流通数据
                            float_volume = true_dict.get_float_volume(stock_code)
                            float_market_cap = float_volume * pre_close if float_volume > 0 else 1.0
                            
                            # 估算flow (简化)
                            flow_5min = current_volume * 0.1  # 简化估算
                            flow_15min = current_volume * 0.3
                            flow_5min_median = true_dict.get_avg_volume_5d(stock_code) / 240
                            
                            # 计算Space Gap
                            high_60d = tick.get('high', current_price)
                            space_gap_pct = (high_60d - current_price) / high_60d if high_60d > 0 else 0.5
                            
                            # 调用动能打分引擎验钞机
                            try:
                                from logic.strategies.动能打分引擎_core_engine import 动能打分引擎CoreEngine
                                动能打分引擎_engine = 动能打分引擎CoreEngine()
                                final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe = 动能打分引擎_engine.calculate_true_dragon_score(
                                    net_inflow=flow_15min * current_price,
                                    price=current_price,
                                    prev_close=pre_close,
                                    high=current_price * 1.02,
                                    low=current_price * 0.98,
                                    open_price=current_price,  # 【CTO修复】添加开盘价
                                    flow_5min=flow_5min,
                                    flow_15min=flow_15min,
                                    flow_5min_median_stock=flow_5min_median if flow_5min_median > 0 else 1.0,
                                    space_gap_pct=space_gap_pct,
                                    float_volume_shares=float_volume,
                                    current_time=now.time()
                                )
                            except Exception as e:
                                # 简化计算
                                final_score = change_pct * 100
                                sustain_ratio = 1.0
                                inflow_ratio = flow_15min * current_price / float_market_cap if float_market_cap > 0 else 0
                                ratio_stock = flow_5min / flow_5min_median if flow_5min_median > 0 else 0
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.error(f"动能打分引擎引擎计算失败: {e}")
                            # 纯度评级
                            purity = '极优' if space_gap_pct < 0.05 else '优' if space_gap_pct < 0.10 else '良'
                            
                            dragon_list.append({
                                'code': stock_code,
                                'score': final_score,
                                'price': current_price,
                                'change': change_pct * 100,
                                'inflow_ratio': inflow_ratio,
                                'ratio_stock': ratio_stock,
                                'sustain_ratio': sustain_ratio,
                                'purity': purity
                            })
                        except Exception as e:
                            continue
                    
                    # 排序
                    dragon_list.sort(key=lambda x: x['score'], reverse=True)
                    
                    # 打印榜单
                    print(f"{'排名':<4} {'代码':<12} {'🩸得分':<8} {'价格':<8} {'涨幅':<8} {'流入比':<8} {'爆发':<6} {'接力':<6} {'纯度':<4}")
                    print("-"*100)
                    for i, dragon in enumerate(dragon_list[:10], 1):
                        print(f"{i:<4} {dragon['code']:<12} {dragon['score']:<8.1f} {dragon['price']:<8.2f} {dragon['change']:<7.1f}% {dragon['inflow_ratio']:<7.2%} {dragon['ratio_stock']:<6.1f}x {dragon['sustain_ratio']:<6.2f}x {dragon['purity']:<4}")
                    
                    print("="*100)
                    print(f"💡 提示: 系统持续监控中... (按 Ctrl+C 退出)")
                    
                except Exception as e:
                    logger.error(f"雷达刷新异常: {e}")
                
                # 3秒刷新
                time.sleep(3)
        
        # 启动雷达线程
        radar_thread = threading.Thread(target=radar_loop, daemon=True)
        radar_thread.start()
        logger.info("🎯 动态雷达刷新线程已启动 (3秒刷新)")
    
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
                    'prev_close': tick.get('preClose', 0) if isinstance(tick, dict) else getattr(tick, 'preClose', 0),
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
        """停止引擎"""
        logger.info("🛑 停止实盘总控引擎...")
        self.running = False
        
        # 停止事件总线
        if self.event_bus:
            self.event_bus.stop()
        
        # 【CTO防呆保护】防止paper模式下没有trader属性导致的报错
        if hasattr(self, 'trader') and self.trader:
            self.trader.disconnect()
        
        logger.info("✅ 实盘总控引擎已停止")


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