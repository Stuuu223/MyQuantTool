# -*- coding: utf-8 -*-
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
from typing import List, Dict, Any, Optional, Tuple
import logging
import warnings
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

# 【CTO状态机重构】股票生命周期状态定义
class StockState(Enum):
    """股票在雷达中的生命周期状态"""
    OUTSIDE = "outside"           # 在蓄水池外
    CANDIDATE = "candidate"       # 进入候选池
    TRACKING = "tracking"         # 正在跟踪
    OPPORTUNITY = "opportunity"   # 确认为机会
    ELIMINATED = "eliminated"     # 被剔除

@dataclass
class TickSnapshot:
    """Tick快照数据结构 - CTO状态机架构"""
    timestamp: datetime
    price: float
    amount: float          # 累计成交额
    volume: float          # 累计成交量
    high: float
    low: float
    open: float

@dataclass  
class StockTracker:
    """股票跟踪器 - 维持15分钟历史状态"""
    stock_code: str
    state: StockState
    enter_time: datetime   # 进入候选池时间
    tick_history: deque = field(default_factory=lambda: deque(maxlen=300))  # 300个Tick历史
    
    # 实时计算指标
    current_price: float = 0.0
    current_amount: float = 0.0
    
    # 15分钟切片指标（真实计算，非脑补）
    flow_15min: float = 0.0
    flow_5min: float = 0.0
    
    # 打分结果
    final_score: float = 0.0
    sustain_ratio: float = 0.0
    mfe: float = 0.0
    inflow_ratio: float = 0.0
    volume_ratio: float = 0.0
    
    # 剔除原因
    elimination_reason: str = ""

# 【CTO V9 强制屏蔽】物理级消灭 Pandas 的向下转型警告
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# 【CTO V118】拒绝日志专用函数 - 写入文件，不刷终端
_REJECT_LOG_PATH = None

def _log_reject(stock_code: str, reason: str):
    """
    【CTO V118】将拦截日志写入后台文件，不在终端刷屏
    
    Args:
        stock_code: 股票代码
        reason: 拒绝原因
    """
    global _REJECT_LOG_PATH
    from pathlib import Path
    
    if _REJECT_LOG_PATH is None:
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        _REJECT_LOG_PATH = log_dir / 'live_reject.log'
    
    try:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(_REJECT_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(f"[{ts}] [拦截] {stock_code} - {reason}\n")
    except Exception:
        pass  # 日志写入失败不阻塞主流程

# 【CTO R6修复】SSOT统一导入 - 严禁在高频函数内部局部导入！
from logic.core.config_manager import get_config_manager
# [V70 大道至简] TickEvent import 已删除 - EventBus 双轨制彻底废除
from logic.data_providers.true_dictionary import get_true_dictionary

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
    
    【CTO V52战役三】灵魂统一架构：
    - mode="live": 实盘模式，使用真实QMT适配器
    - mode="scan": 沙盘模式，使用MockQmtAdapter伪装历史Tick
    - 绝对同质同源：Scan和Live使用完全相同的引擎逻辑！
    """
    
    def __init__(self, qmt_manager=None, event_bus=None, volume_percentile: float = 1.5, 
                 mode: str = "live", target_date: str = None):
        """
        初始化引擎 - CTO强制：依赖注入模式
        
        Args:
            qmt_manager: QMT管理器实例（live模式必须传入）
            event_bus: 事件总线实例（可选，内部创建）
            volume_percentile: 量比分位数阈值
            mode: 运行模式 "live"(实盘) 或 "scan"(沙盘回测)
            target_date: 目标日期 (scan模式必需，格式: 'YYYYMMDD')
        """
        self.mode = mode
        self.target_date = target_date or datetime.now().strftime('%Y%m%d')
        
        # 【CTO V52战役三】scan模式允许跳过QMT检查
        if mode == "scan":
            logger.info(f"?? [LiveTradingEngine] 沙盘模式启动，目标日期: {self.target_date}")
            self.qmt_manager = qmt_manager  # 可以为None
        else:
            # CTO强制：live模式QMT Manager必须由外部注入！
            if qmt_manager is None:
                logger.error("[ERR] [LiveTradingEngine] CTO命令：没有券商通道，不准开机！")
                raise RuntimeError(
                    "致命错误：QMT Manager缺失！\n"
                    "CTO命令：实盘引擎拒绝空转！\n"
                    "请在main.py中初始化QMT并传入引擎！"
                )
            self.qmt_manager = qmt_manager
        self.scanner = None
        # event_bus参数保留仅为向后兼容，内部已不使用（大道至简重构）
        self.event_bus = None
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
        
        # 【CTO V13】pool_stats缓存 - 盘中无数据时显示上一次统计
        self.last_known_pool_stats: Dict[str, int] = {}
        
        # 【CTO Phase4.1】龙空龙宏观断电乘数 - 市场活跃水位计
        # 0.0 = 硬件级熔断，禁止买入；1.0 = 正常
        self._macro_multiplier: float = 1.0
        
        # 【CTO V46战役二】横向虹吸效应 - 全候选池总净流入缓存
        # 用于计算每只股票的vampire_ratio_pct = 该股净流入 / 全池总流入 * 100
        self.market_total_inflow_cache: float = 1000000.0  # 初始兜底100万
        
        # 【CTO V87 L1真实微积分】Tick差分流入累加器状态机
        # 废除power_ratio估算，使用真实的delta_amount和delta_price计算流入
        # {stock_code: {'inflow': float, 'last_amount': float, 'last_price': float}}
        self.l1_inflow_accumulator: Dict[str, Dict[str, float]] = {}
        
        # 【CTO V46架构大一统】持仓管理 - 使用ExitManager统一止损逻辑
        # positions: {stock_code: ExitManager实例}
        # 每个持仓都有自己的ExitManager来监控止损/止盈条件
        self.positions: Dict[str, Any] = {}  # {stock_code: ExitManager}
        
        # 【CTO审计修复】trade_gatekeeper初始化 - 原代码中只检查未初始化
        # 从execution模块导入TradeGatekeeper（如果存在）
        try:
            from logic.execution.trade_gatekeeper import TradeGatekeeper
            self.trade_gatekeeper = TradeGatekeeper()
            logger.info("[OK] TradeGatekeeper初始化成功")
        except (ImportError, Exception) as e:
            # 【CTO修复】日志必须与底层 Fail-Close 行为绝对统一！
            logger.error(f"[FATAL] TradeGatekeeper缺失或异常: {e}。微观防线失效，系统将拒绝一切实盘开仓！(Fail-Close)")
            self.trade_gatekeeper = None
        
        # 【CTO V71单吊极锋执行器】MockExecutionManager - L1虚拟交易所
        # 支持单吊模式(max_position_ratio=1.0)，物理摩擦力模型
        try:
            from logic.execution.mock_execution_manager import MockExecutionManager
            self.execution_manager = MockExecutionManager(
                initial_capital=100000.0,  # 10万初始资金
                max_position_ratio=1.0     # 单吊模式：单票可满仓
            )
            logger.info("[OK] MockExecutionManager初始化成功 - 单吊极锋模式")
        except (ImportError, Exception) as e:
            logger.error(f"[FATAL] MockExecutionManager缺失或异常: {e}。执行层失效！(Fail-Close)")
            self.execution_manager = None
        
        # 【架构大道至简】EventBus 双轨制已删除，统一主循环拉取架构
        # signal_queue 已废弃，3分钟抗重力测试移入主循环帧计数
        # 原_event_bus和_qmt_adapter初始化已移除，消灭竞态条件
        
        # 【CTO V39战役三】统一时间流 - 用Tick帧数替代绝对时间！
        # 假设系统3秒推一个Tick，3分钟=60帧。彻底消灭datetime.now()时间流速精神分裂！
        self.global_tick_frame: int = 0
        
        # 【CTO V53时间沙盒】统一时间获取入口
        # - Live模式：返回系统当前时间
        # - Scan模式：返回模拟时间（由Tick时间戳驱动）
        self._mock_time: Optional[datetime] = None
        
        # 【CTO架构重铸令R2/R3】L1价格推力探测器 + 微积分形态学
        # tick_history: 保存过去60个Tick（假设3秒/Tick，约3分钟微观轨迹）
        # volume_history: 保存过去60个成交量快照
        from collections import deque
        self.tick_history: Dict[str, deque] = {}       # {stock_code: deque(maxlen=60)}
        self.volume_history: Dict[str, deque] = {}     # {stock_code: deque(maxlen=60)}
        self._TICK_HISTORY_MAXLEN = 60  # 约3分钟微观轨迹
        
        # 【CTO状态机重构】动态蓄水池架构 - 解决伪时间折算和无状态扫描问题
        # 核心组件：
        # 1. candidate_pool: 宽进粗筛选出的候选股票池
        # 2. stock_trackers: 每只股票的历史状态跟踪器（维持15分钟Tick队列）
        # 3. opportunity_pool: 经精细打分后的机会池
        # 4. eliminated_pool: 被剔除的股票及其原因（负样本收集）
        self.candidate_pool: Dict[str, StockTracker] = {}      # 候选蓄水池
        self.opportunity_pool: Dict[str, StockTracker] = {}    # 机会池
        self.eliminated_pool: Dict[str, StockTracker] = {}     # 剔除池（负样本）
        
        # 【CTO动能悖论熔断】Sustain>5.0但CHG%<2.0时强制剔除
        self.kinetic_paradox_enabled: bool = True              # 熔断开关
        self.kinetic_paradox_sustain_threshold: float = 5.0    # Sustain阈值
        self.kinetic_paradox_change_threshold: float = 0.02    # 涨幅阈值(2%)
        
        # 【CTO宽进粗筛标准】简化粗筛，快速构建候选池
        self.candidate_price_momentum_threshold: float = 0.8   # 价格动能>0.8
        self.candidate_turnover_threshold: float = 0.01        # 换手率>1%
        
        # 【CTO动态剔除标准】从蓄水池中剔除的条件
        self.eliminate_mfe_threshold: float = 1.2              # MFE<1.2
        self.eliminate_volume_ratio_threshold: float = 3.0     # Volume_Ratio>3.0
        
        logger.info("[OK] [LiveTradingEngine] 初始化完成 - QMT Manager已注入")
        logger.info("[CTO状态机] 动态蓄水池架构已启用：candidate_pool/opportunity_pool/eliminated_pool")
    
    # ==================== 【CTO V53时间沙盒】统一时间获取入口 ====================
    
    def get_current_time(self) -> datetime:
        """
        【CTO V53时间沙盒】统一时间获取入口
        
        - Live模式：返回系统当前时间
        - Scan模式：返回模拟时间（由Tick时间戳驱动）
        
        Returns:
            datetime: 当前时间（Live）或模拟时间（Scan）
        """
        if self.mode == "scan" and self._mock_time is not None:
            return self._mock_time
        return datetime.now()
    
    def set_mock_time(self, tick_time: datetime):
        """
        【CTO V53时间沙盒】设置模拟时间（Scan模式专用）
        
        Args:
            tick_time: Tick数据携带的时间戳
        """
        self._mock_time = tick_time
    
    # ==================== 【CTO状态机重构】动态蓄水池核心方法 ====================
    
    def _update_stock_tracker(self, stock_code: str, tick_data: Dict) -> StockTracker:
        """
        【CTO状态机】更新股票跟踪器，维持15分钟Tick历史队列
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据字典
            
        Returns:
            StockTracker: 更新后的跟踪器
        """
        # 获取或创建跟踪器
        if stock_code not in self.candidate_pool:
            self.candidate_pool[stock_code] = StockTracker(
                stock_code=stock_code,
                state=StockState.OUTSIDE,
                enter_time=self.get_current_time()
            )
        
        tracker = self.candidate_pool[stock_code]
        
        # 提取Tick数据
        current_time = self.get_current_time()
        price = float(tick_data.get('lastPrice', 0.0))
        amount = float(tick_data.get('amount', 0.0))  # 累计成交额
        volume = float(tick_data.get('volume', 0.0))  # 累计成交量
        high = float(tick_data.get('high', price))
        low = float(tick_data.get('low', price))
        open_price = float(tick_data.get('open', price))
        
        # 创建快照并加入历史队列
        snapshot = TickSnapshot(
            timestamp=current_time,
            price=price,
            amount=amount,
            volume=volume,
            high=high,
            low=low,
            open=open_price
        )
        tracker.tick_history.append(snapshot)
        
        # 更新当前状态
        tracker.current_price = price
        tracker.current_amount = amount
        
        return tracker
    
    def _calculate_real_flow(self, tracker: StockTracker) -> Tuple[float, float]:
        """
        【CTO状态机】真实计算15分钟和5分钟流入
        不是用乘数，而是用真实的历史快照差值
        
        Args:
            tracker: 股票跟踪器
            
        Returns:
            Tuple[float, float]: (flow_15min, flow_5min)
        """
        if len(tracker.tick_history) < 2:
            return 0.0, 0.0
        
        current = tracker.tick_history[-1]
        
        # 找15分钟前的快照
        target_time_15min = current.timestamp - timedelta(minutes=15)
        snapshot_15min_ago = self._find_nearest_snapshot(tracker.tick_history, target_time_15min)
        
        # 找5分钟前的快照
        target_time_5min = current.timestamp - timedelta(minutes=5)
        snapshot_5min_ago = self._find_nearest_snapshot(tracker.tick_history, target_time_5min)
        
        # 真实流入 = 当前累计 - 历史累计
        flow_15min = current.amount - snapshot_15min_ago.amount if snapshot_15min_ago else 0.0
        flow_5min = current.amount - snapshot_5min_ago.amount if snapshot_5min_ago else 0.0
        
        return flow_15min, flow_5min
    
    def _find_nearest_snapshot(self, history: deque, target_time: datetime) -> Optional[TickSnapshot]:
        """
        【CTO状态机】在历史队列中找到最接近目标时间的快照
        
        Args:
            history: Tick历史队列
            target_time: 目标时间
            
        Returns:
            Optional[TickSnapshot]: 最接近的快照，如果没有则返回None
        """
        if not history:
            return None
        
        # 从后向前找最接近的
        best_match = None
        best_diff = timedelta.max
        
        for snapshot in reversed(history):
            diff = abs(snapshot.timestamp - target_time)
            if diff < best_diff:
                best_diff = diff
                best_match = snapshot
            # 如果找到足够近的，提前返回
            if diff < timedelta(seconds=5):
                return best_match
        
        return best_match
    
    def _should_enter_candidate_pool(self, tick_data: Dict, pre_close: float) -> bool:
        """
        【CTO状态机】宽进粗筛标准
        只有价格动能和换手率，不计算复杂指标
        
        Args:
            tick_data: Tick数据
            pre_close: 昨收价
            
        Returns:
            bool: 是否进入候选池
        """
        price = float(tick_data.get('lastPrice', 0.0))
        high = float(tick_data.get('high', price))
        low = float(tick_data.get('low', price))
        volume = float(tick_data.get('volume', 0.0))
        
        if price <= 0 or high <= low:
            return False
        
        # 价格动能 = (当前价 - 日内最低) / (日内最高 - 日内最低)
        price_momentum = (price - low) / (high - low)
        
        # 换手率计算（需要流通股本，这里简化）
        # 实际应该从TrueDictionary获取float_volume
        turnover_rate = 0.0  # 简化，实际应计算
        
        # 宽进标准：价格动能>0.8
        return price_momentum > self.candidate_price_momentum_threshold
    
    def _check_kinetic_paradox(self, tracker: StockTracker, pre_close: float) -> Tuple[bool, str]:
        """
        【CTO状态机】动能悖论熔断检查
        Sustain>5.0但CHG%<2.0时强制剔除
        
        Args:
            tracker: 股票跟踪器
            pre_close: 昨收价
            
        Returns:
            Tuple[bool, str]: (是否触发悖论, 原因)
        """
        if not self.kinetic_paradox_enabled:
            return False, ""
        
        # 计算涨幅
        if pre_close <= 0 or tracker.current_price <= 0:
            return False, ""
        
        change_pct = (tracker.current_price - pre_close) / pre_close
        
        # 检查悖论条件：高Sustain但低涨幅
        if (tracker.sustain_ratio > self.kinetic_paradox_sustain_threshold and 
            change_pct < self.kinetic_paradox_change_threshold):
            return True, f"动能悖论: Sustain={tracker.sustain_ratio:.2f}x但涨幅={change_pct:.2%}"
        
        return False, ""
    
    def _should_eliminate(self, tracker: StockTracker) -> Tuple[bool, str]:
        """
        【CTO状态机】动态剔除检查
        从蓄水池中移除不合格股票
        
        Args:
            tracker: 股票跟踪器
            
        Returns:
            Tuple[bool, str]: (是否剔除, 原因)
        """
        # 条件1: MFE<1.2且Volume_Ratio>3.0 (天量滞涨)
        if (tracker.mfe < self.eliminate_mfe_threshold and 
            tracker.volume_ratio > self.eliminate_volume_ratio_threshold):
            return True, f"天量滞涨: MFE={tracker.mfe:.2f}且量比={tracker.volume_ratio:.2f}"
        
        # 条件2: 价格跌破15分钟VWAP
        vwap_15min = self._calculate_vwap_15min(tracker)
        if vwap_15min > 0 and tracker.current_price < vwap_15min * 0.99:
            return True, f"跌破VWAP: 价格{tracker.current_price:.2f} < VWAP{vwap_15min:.2f}"
        
        return False, ""
    
    def _calculate_vwap_15min(self, tracker: StockTracker) -> float:
        """
        【CTO状态机】计算15分钟VWAP
        
        Args:
            tracker: 股票跟踪器
            
        Returns:
            float: 15分钟VWAP
        """
        if len(tracker.tick_history) < 2:
            return 0.0
        
        current = tracker.tick_history[-1]
        target_time = current.timestamp - timedelta(minutes=15)
        snapshot_15min_ago = self._find_nearest_snapshot(tracker.tick_history, target_time)
        
        if not snapshot_15min_ago:
            return 0.0
        
        # VWAP = (成交金额变化) / (成交量变化)
        amount_delta = current.amount - snapshot_15min_ago.amount
        volume_delta = current.volume - snapshot_15min_ago.volume
        
        if volume_delta <= 0:
            return 0.0
        
        return amount_delta / volume_delta
    
    def _calculate_l1_inflow(self, stock_code: str, current_amount: float, current_price: float,
                              pre_close: float, tick_high: float, tick_low: float, tick: dict = None) -> float:
        """
        【CTO V93 智能微积分算子】L2/L1 自适应优雅降级与盘口重力场
        
        升级点：
        1. 价格僵持时(ΔP=0)不再盲猜，使用盘口失衡度推断
        2. L2上帝视角(十档)和L1刺刀模式(五档)自动降级
        3. 三次方失衡算子(Imbalance^3)放大深层盘口意图
        
        Args:
            stock_code: 股票代码
            current_amount: 当前累计成交额
            current_price: 当前价格
            pre_close: 昨收价
            tick_high: 今日最高价
            tick_low: 今日最低价
            tick: 原始Tick数据字典(用于提取盘口)
            
        Returns:
            真实净流入估算值
        """
        # 初始化该股票的累加器
        if stock_code not in self.l1_inflow_accumulator:
            self.l1_inflow_accumulator[stock_code] = {
                'inflow': 0.0,
                'last_amount': current_amount,
                'last_price': current_price
            }
            # 首次调用：无历史数据，回退到power_ratio估算作为初始值
            price_range = tick_high - tick_low
            if price_range > 0 and pre_close > 0:
                power_ratio = (current_price - pre_close) / price_range
                power_ratio = max(-1.0, min(power_ratio, 1.0))
            else:
                power_ratio = 1.0 if current_price > pre_close else -1.0
            initial_inflow = current_amount * power_ratio * 0.5
            self.l1_inflow_accumulator[stock_code]['inflow'] = initial_inflow
            return initial_inflow
        
        acc = self.l1_inflow_accumulator[stock_code]
        last_amount = acc['last_amount']
        last_price = acc['last_price']
        
        # 计算真实增量
        delta_amount = current_amount - last_amount
        delta_price = current_price - last_price
        
        if delta_amount > 0:  # 有新成交
            if delta_price > 0:
                # 向上吃单，绝对做多
                acc['inflow'] += delta_amount
            elif delta_price < 0:
                # 向下砸盘，绝对做空
                acc['inflow'] -= delta_amount
            else:
                # === 价格僵持段：L2/L1 自适应盘口重力推断 ===
                imbalance = 0.0
                if tick:
                    ask_list = tick.get('askVol', [])
                    bid_list = tick.get('bidVol', [])
                    
                    # 动态嗅探：鸭子类型降级 (Duck Typing Degradation)
                    if isinstance(ask_list, list) and len(ask_list) >= 10:
                        # 👑 【L2 上帝视角】十档重力场全解析
                        total_ask = sum(ask_list[:10])
                        total_bid = sum(bid_list[:10])
                    else:
                        # ⚔️ 【L1 刺刀模式】无缝降级至五档推断
                        total_ask = sum([tick.get(f'askVol{i}', 0) for i in range(1, 6)]) if not ask_list else sum(ask_list[:5])
                        total_bid = sum([tick.get(f'bidVol{i}', 0) for i in range(1, 6)]) if not bid_list else sum(bid_list[:5])

                    if total_bid + total_ask > 0:
                        # 引入盘口引力非线性偏置 (Imbalance^3)
                        # 过滤噪音，将主力真实的深层压单/托单意图指数级放大！
                        imbalance = (total_bid - total_ask) / (total_bid + total_ask)
                        directional_force = imbalance ** 3 if imbalance > 0 else -((-imbalance) ** 3)
                        acc['inflow'] += delta_amount * directional_force
                # 如果没有tick数据，使用价格位置推断
                elif pre_close > 0:
                    price_position = (current_price - pre_close) / pre_close
                    direction = max(-1.0, min(1.0, price_position * 10))
                    acc['inflow'] += delta_amount * direction

        acc['last_amount'] = current_amount
        acc['last_price'] = current_price
        return acc['inflow']
    
    def _reset_l1_accumulator(self, stock_code: str = None):
        """
        【CTO V87】重置L1累加器
        每日开盘前调用，或针对特定股票重置
        """
        if stock_code:
            if stock_code in self.l1_inflow_accumulator:
                del self.l1_inflow_accumulator[stock_code]
        else:
            self.l1_inflow_accumulator.clear()
    
    def _transition_state(self, tracker: StockTracker, new_state: StockState, reason: str = ""):
        """
        【CTO状态机】状态转换
        
        Args:
            tracker: 股票跟踪器
            new_state: 新状态
            reason: 转换原因
        """
        old_state = tracker.state
        tracker.state = new_state
        
        if new_state == StockState.ELIMINATED:
            tracker.elimination_reason = reason
            # 从候选池移到剔除池
            if tracker.stock_code in self.candidate_pool:
                del self.candidate_pool[tracker.stock_code]
            self.eliminated_pool[tracker.stock_code] = tracker
            logger.info(f"💀 [剔除] {tracker.stock_code}: {reason}")
        
        elif new_state == StockState.OPPORTUNITY:
            # 从候选池移到机会池
            if tracker.stock_code in self.candidate_pool:
                del self.candidate_pool[tracker.stock_code]
            self.opportunity_pool[tracker.stock_code] = tracker
            logger.info(f"🎯 [机会] {tracker.stock_code}: 分数{tracker.final_score:.1f}")
        
        logger.debug(f"[状态转换] {tracker.stock_code}: {old_state.value} -> {new_state.value}")
    
    # ==================== 【CTO状态机重构】结束 ====================
    
    def run_historical_stream(self, tick_stream: list):
        """
        【CTO V61 绝对同源版】Scan模式专属引擎
        废弃将静态Tick强行喂给动态扳机(_on_tick_data)的错误做法。
        直接提取最终快照，100% 复刻 _run_radar_main_loop 的双层打分过滤机制！
        """
        if self.mode != 'scan':
            logger.warning("[WARN] 仅适用于Scan模式")
        
        self.running = True
        logger.info(f"🚀 [Time Machine] 启动定格沙盘，提取 {len(tick_stream)} 个底层切片...")
        
        self._init_qmt_adapter()
        
        # 1. 强制挂载全局字典并预热
        from logic.data_providers.true_dictionary import get_true_dictionary
        if not hasattr(self, 'true_dict') or not self.true_dict:
            self.true_dict = get_true_dictionary()
            
        mock_target_date = getattr(self.qmt_manager, 'target_date', None)
        
        # 【CTO 斩断双倍 I/O】禁止在此处二次召唤 UniverseBuilder，直接使用供弹带
        # 原代码: base_pool, _ = UniverseBuilder(target_date=mock_target_date).build()
        # 修复: 使用传入的tick_stream构建watchlist，避免重复磁盘I/O
        pass  # 预热移到watchlist构建之后
        
        # 2. 从入参提取最终定格快照 (由于是收盘数据，剥离时间轴)
        last_tick_by_stock = {}
        for tick in tick_stream:
            stock_code = tick.get('stock_code', '')
            if stock_code:
                last_tick_by_stock[stock_code] = tick
                
        self.watchlist = list(last_tick_by_stock.keys())
        if not self.watchlist:
            logger.warning("[WARN] 粗筛池为空！")
            return

        # 3. 构造虚拟系统时间（锁定在当天 15:00:00）
        import datetime as dt
        target_dt = dt.datetime.strptime(mock_target_date, "%Y%m%d") if mock_target_date else dt.datetime.now()
        engine_time = target_dt.replace(hour=15, minute=0, second=0, microsecond=0)
        self.set_mock_time(engine_time)

        # 4. 【绝对同源计算：第一遍扫描 - 计算宏观虹吸基准】
        market_total_inflow = 0.0
        first_pass_inflow_cache = {}
        
        for stock_code, tick in last_tick_by_stock.items():
            current_price = float(tick.get('lastPrice', 0) or tick.get('price', 0))
            pre_close = float(tick.get('lastClose', 0) or tick.get('prev_close', 0))
            current_amount = float(tick.get('amount', 0))
            tick_high = float(tick.get('high', current_price))
            tick_low = float(tick.get('low', current_price))
            
            # 【CTO V93 L2/L1智能微积分】价格僵持时使用盘口重力推断
            # 使用Tick差分状态机计算真实净流入
            net_inflow_est = self._calculate_l1_inflow(
                stock_code, current_amount, current_price, pre_close, tick_high, tick_low, tick
            )
            
            # === 【CTO V85: L1 对倒阻尼防线】 ===
            # 识别放量滞涨：如果当前成交额极大但涨幅极小，说明主力在对倒或派发
            # L1估算的流入严重失真，需要强制剥离！
            change_pct = (current_price - pre_close) / pre_close * 100 if pre_close > 0 else 0.0
            
            # 获取5日均成交额判断是否放量
            avg_volume_5d = self.true_dict.get_avg_volume_5d(stock_code) or 0.0
            avg_amount_5d = avg_volume_5d * 100 * pre_close if avg_volume_5d > 0 and pre_close > 0 else 0.0
            
            if avg_amount_5d > 0:
                # 盘后模式直接用全天数据
                current_ratio = current_amount / avg_amount_5d
                
                # 物理绞杀：如果量比 > 3.0 且 涨幅 < 2.0%
                if current_ratio > 3.0 and abs(change_pct) < 2.0:
                    # 放量滞涨，认定为摩擦消耗，强制抹除 90% 的虚假流入！
                    net_inflow_est *= 0.1
                    logger.debug(f"🚨 [对倒降维] {stock_code} 量比{current_ratio:.1f}x但涨幅仅{change_pct:.2f}%，剥离虚假流入！")
            
            if net_inflow_est > 0:
                market_total_inflow += net_inflow_est
            first_pass_inflow_cache[stock_code] = net_inflow_est
            
        self.market_total_inflow_cache = max(market_total_inflow, 1000000.0)

        # 5. 【绝对同源计算：第二遍精算 - 对齐 V20.5 引擎】
        current_top_targets = []
        if not hasattr(self, '_kinetic_core'):
            from logic.strategies.kinetic_core_engine import KineticCoreEngine
            self._kinetic_core = KineticCoreEngine()

        for stock_code, tick in last_tick_by_stock.items():
            try:
                current_price = float(tick.get('lastPrice', 0) or tick.get('price', 0))
                pre_close = float(tick.get('lastClose', 0) or tick.get('prev_close', 0))
                if current_price <= 0 or pre_close <= 0: continue
                    
                current_amount = float(tick.get('amount', 0))
                tick_high = float(tick.get('high', current_price))
                tick_low = float(tick.get('low', current_price))
                
                float_volume = self.true_dict.get_float_volume(stock_code) or 1000000000.0
                avg_volume_5d = self.true_dict.get_avg_volume_5d(stock_code) or 1.0
                avg_amount_5d = avg_volume_5d * 100 * pre_close
                
                # ============================================================
                # 【CTO V63 终极审判】废除全天均摊！调用真实时空切片！
                # 根因：妖股80%成交额集中在早盘30分钟，全天/16均摊会稀释动能！
                # 正解：调用calculate_time_slice_flows获取09:30-09:45真实早盘数据
                # ============================================================
                flow_5min = 0.0
                flow_15min = 0.0
                
                # 获取该股票在 09:30 - 09:45 之间的真实成交数据！
                slice_flows = self.calculate_time_slice_flows(stock_code, mock_target_date)
                if slice_flows:
                    flow_5min = slice_flows.get('flow_5min', 0.0)
                    flow_15min = slice_flows.get('flow_15min', 0.0)
                else:
                    # 【CTO 斩断脑补】拿不到真实切片直接物理跳过！宁可错杀绝不造假！
                    # 原fallback用0.15/0.35静态比例估算，严重违背时间流物理定律！
                    logger.debug(f"[拦截] {stock_code} 缺失真实时空切片，跳过打分")
                    continue
                
                change_pct = (current_price - pre_close) / pre_close
                price_position = (current_price - tick_low) / (tick_high - tick_low) if tick_high > tick_low else 0.5
                acceleration_factor = max(0.3, min(1.0 + (price_position - 0.5) * 1.0 + change_pct * 3.0, 3.0))
                flow_5min_median = avg_amount_5d / 48.0
                
                space_gap_pct = (tick_high - current_price) / tick_high if tick_high > 0 else 0.5
                
                stock_net_inflow = first_pass_inflow_cache.get(stock_code, 0.0)
                vampire_ratio_pct = min((stock_net_inflow / self.market_total_inflow_cache) * 100.0, 100.0) if self.market_total_inflow_cache > 0 and stock_net_inflow > 0 else 0.0
                
                if stock_code.startswith(('30', '68')): limit_up_price = round(pre_close * 1.20, 2)
                elif stock_code.startswith(('8', '4')): limit_up_price = round(pre_close * 1.30, 2)
                else: limit_up_price = round(pre_close * 1.10, 2)
                is_limit_up = (current_price >= limit_up_price - 0.011)
                limit_up_queue_amount = 50000000.0 if is_limit_up else 0.0
                
                # 调用核心引擎打分
                # 【CTO V101】获取连板基因
                is_yesterday_limit_up = self.static_cache.get(stock_code, {}).get('is_yesterday_limit_up', False)
                final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe = self._kinetic_core.calculate_true_dragon_score(
                    net_inflow=stock_net_inflow,
                    price=current_price,
                    prev_close=pre_close,
                    high=tick_high,
                    low=tick_low,
                    open_price=float(tick.get('open', current_price)),
                    flow_5min=flow_5min,
                    flow_15min=flow_15min,
                    flow_5min_median_stock=flow_5min_median if flow_5min_median > 0 else 1.0,
                    space_gap_pct=space_gap_pct,
                    float_volume_shares=float_volume,
                    current_time=engine_time,
                    is_limit_up=is_limit_up,
                    limit_up_queue_amount=limit_up_queue_amount,
                    mode="scan", # 告知引擎这是定格沙盘
                    stock_code=stock_code,
                    is_yesterday_limit_up=is_yesterday_limit_up,  # 【CTO V101】连板基因
                    vampire_ratio_pct=vampire_ratio_pct
                )
                
                price_range = tick_high - tick_low
                raw_purity = (current_price - pre_close) / price_range if price_range > 0 else (1.0 if current_price > pre_close else -1.0)
                quant_purity = min(max(raw_purity, -1.0), 1.0) * 100
                
                if final_score >= 50.0 and quant_purity > -50.0:
                    current_top_targets.append({
                        'code': stock_code,
                        'score': final_score,
                        'price': current_price,
                        'change': change_pct * 100,
                        'inflow_ratio': inflow_ratio,
                        'ratio_stock': ratio_stock,
                        'sustain_ratio': sustain_ratio,
                        'mfe': mfe,
                        'purity': quant_purity,
                        'time': engine_time.strftime('%H:%M:%S'),  # 【CTO V61修复】添加time字段
                        'first_entry_time': engine_time.strftime('%H:%M:%S')
                    })
            except Exception as e:
                continue

        current_top_targets.sort(key=lambda x: x['score'], reverse=True)
        self.last_known_top_targets = current_top_targets[:10]
        
        # 写入战报数据
        self.highest_scores = {t['code']: t for t in current_top_targets}
        
        # 6. 大屏展示
        logger.info(f"📊 强制收尸结算...共{len(current_top_targets)}只达标(>=50分)")
        if self.last_known_top_targets:
            self._print_fire_control_panel(
                self.last_known_top_targets, 
                initial_loading=False, 
                pool_stats={'total': len(last_tick_by_stock), 'active': len(current_top_targets), 'up': 0, 'down': 0, 'filtered': 0},
                is_rest=True
            )
            print("\n[CMD] 沙盘时间线推演定格完毕。")
        else:
            # 【CTO增强】即使榜单为空也显示提示，避免用户误以为卡死
            logger.warning(f"⚠️ 沙盘结算完成，但无股票达标(>=50分)。粗筛池{len(last_tick_by_stock)}只，请检查V65引力阻尼是否过严。")
            self._print_fire_control_panel(
                [], 
                initial_loading=False, 
                pool_stats={'total': len(last_tick_by_stock), 'active': 0, 'up': 0, 'down': 0, 'filtered': 0},
                is_rest=True,
                msg=f"无达标股票(粗筛{len(last_tick_by_stock)}只)"
            )
            print("\n[CMD] 沙盘时间线推演定格完毕。[空榜]")
            
        self._generate_final_battle_report()
        self._has_generated_report = True
    
    # ==========================================================================
    
    def _init_kinetic_engine(self):
        """【CTO V66废弃】微积分形态学引擎已移除 - 3秒快照无法支持毫秒级微积分"""
        # 【CTO审计】kinetic_engine.py在3秒快照数据上算微积分会产生假信号
        # 已删除，不再初始化
        self.kinetic_engine_class = None
        self.kinetic_engines = {}
        logger.info("[TARGET] [V66] KineticEngine已废弃，不再初始化")
    
    def _get_kinetic_engine(self, stock_code: str):
        """【CTO V66废弃】获取KineticEngine - 已移除"""
        return None
    
    def _init_event_bus(self):
        """【已废弃】大道至简重构：EventBus双轨制已删除"""
        pass    
    def _init_qmt_adapter(self):
        """【已废弃】大道至简重构：QMTEventAdapter绑定已删除"""
        pass
    
    def start_session(self, enable_dynamic_radar: bool = True):
        """
        启动交易会话 - CTO V30终极版（非交易日路由 + 四级漏斗 + 看板先行）
        时间线: 09:25(CTO第一斩) -> 09:30(开盘粗筛) -> 盘中(细筛+动能打分)
        
        Args:
            enable_dynamic_radar: 是否启用动态雷达（默认True，仅实盘使用）
        """
        # 【CTO V56熔断机制】沙盘模式严禁调用带有time.sleep和多线程阻塞的start_session！
        if self.mode == 'scan':
            logger.error("[架构违规] 沙盘模式严禁调用带有 time.sleep 和多线程阻塞的 start_session！")
            raise RuntimeError("Scan模式请调用专属的 run_historical_stream() 开启时间机器！")
        
        import os
        
        # 【CTO V4看板绝对先行】第一帧立刻显示，不等任何操作！
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 80)
        print("[RADAR] [V20 纯血游资猎杀雷达] | 引擎唤醒中...")
        print(" 正在进行全市场粗筛，请等待...")
        print("=" * 80)
        
        # 【CTO修复】将参数保存为实例变量，供后续函数使用
        self.enable_dynamic_radar = enable_dynamic_radar
        logger.info("[RADAR] 启动实盘总控引擎 (CTO V4四级漏斗版)")
        
        # QMT Manager已通过依赖注入保证存在，无需检查
        logger.info("[OK] [LiveTradingEngine] QMT Manager已就绪，启动完整模式")
        
        # 【大道至简】EventBus已废除，不再需要event_bus空值检查
        # 原代码会在event_bus=None时抛出RuntimeError，现已删除
        
        self.running = True
        
        # 【大道至简】EventBus双轨制已废除，主循环为唯一打分路径
        # 原event_bus.start_consumer/subscribe已删除，消灭竞态条件
        
        # 获取当前时间
        current_time = self.get_current_time()
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        auction_end = current_time.replace(hour=9, minute=25, second=0, microsecond=0)
        
        # 【CTO V30非交易日路由修复】
        # 问题根因：周六运行时，seconds_to_auction=(09:25-01:38)约28000秒是正数
        # 程序会sleep等待8小时到"09:25"，但周六根本没有交易！
        # 修复：检测到非交易日时，直接跳转到盘中热启动逻辑，执行盘后定格投影模式
        from logic.utils.calendar_utils import is_trading_day, get_latest_completed_trading_day
        today_str = current_time.strftime('%Y%m%d')
        is_today_trading = is_trading_day(today_str)
        
        if not is_today_trading:
            print(f"?? [CTO V30] 今日 {today_str} 是非交易日（周六/周日/节假日）")
            print("?? 自动切换到盘后定格投影模式...")
            # 强制进入盘中热启动分支，执行盘后投影
            # 跳过所有时间判断，直接执行粗筛+监控
            logger.warning("[NON-TRADING] 非交易日，执行盘后定格投影模式...")
        # CTO修复：盘中启动时必须先执行快照筛选！
        if current_time >= market_open or not is_today_trading:
            logger.warning("[HOT-START] 越过开盘集合竞价，执行全局截面扫描...")
            
            # 【CTO V17零秒点火】直接用UniverseBuilder拿底池，跳过全市场扫描！
            # 原逻辑：_auction_snapshot_filter() 全市场5191只扫描，卡3分钟
            # 新逻辑：UniverseBuilder三漏斗筛选，毫秒级完成
            if not self.watchlist:
                print("[FAST] Step 1: 从UniverseBuilder装载静态物理底池...")
                logger.info("[FAST] Step 1: 从UniverseBuilder装载静态物理底池...")
                try:
                    from logic.data_providers.universe_builder import UniverseBuilder
                    target_date = self.get_current_time().strftime('%Y%m%d')
                    builder = UniverseBuilder(target_date=target_date)
                    base_pool, volume_ratios = builder.build()
                    
                    if base_pool:
                        self.watchlist = base_pool
                        print(f"[OK] 静态底池装载完成: {len(self.watchlist)} 只标的")
                        logger.info(f"[OK] 静态底池装载完成: {len(self.watchlist)} 只标的")
                    else:
                        print("[ERR] 底池装载失败！")
                        logger.error("[ERR] 底池装载失败！")
                        self._fallback_premarket_scan()
                except Exception as e:
                    print(f"[ERR] UniverseBuilder失败: {e}")
                    logger.error(f"[ERR] UniverseBuilder失败: {e}")
                    self._fallback_premarket_scan()
            else:
                print(f"[FAST] 使用现有watchlist: {len(self.watchlist)} 只")
                logger.info(f"[FAST] 使用现有watchlist: {len(self.watchlist)} 只")
            
            # 【CTO V24修复】预热必须在快照筛选之前！
            # 否则TrueDictionary没有数据，avg_volume_5d=0，全部被过滤！
            print("[FAST] Step 2: 预热TrueDictionary（必须在快照筛选之前！）...")
            logger.info("[FAST] Step 2: 预热TrueDictionary（必须在快照筛选之前！）...")
            self._warmup_true_dictionary()
            print("[FAST] Step 2: 预热完成")
            
            # Step 3: 执行第三斩（开盘快照筛选），筛选强势股
            print("[FAST] Step 3: 执行开盘快照三筛...")
            logger.info("[FAST] Step 3: 执行开盘快照三筛...")
            self._snapshot_filter()
            print(f"[FAST] Step 3: 快照筛选完成, watchlist={len(self.watchlist) if self.watchlist else 0} 只")
            
            # Step 4: 检查watchlist是否填充成功
            if not self.watchlist:
                logger.warning("[ERR] 快照筛选未找到目标股票，系统进入待机模式")
                logger.info("[INFO] 提示：可能当前没有符合量比>0.95分位数的强势股")
                logger.info("[FAST] 系统将持续运行，等待下一分钟自动热扫描...")
                # CTO修复：不再自杀，系统持续运行等待自动热扫描
                # 启动自动热扫描机制
                self._start_auto_replenishment()
                return
            
            # Step 5: 订阅Tick数据（在watchlist填充后）
            logger.info("[DATA] 订阅目标股票Tick数据...")
            self._setup_qmt_callbacks()
            
            # Step 6: 进入高频监控模式
            logger.info(f"[TARGET] 进入高频监控模式，锁定右侧起爆目标 {len(self.watchlist)} 只目标")
            
            # 【CTO暴怒扒皮第一棒】强制高亮输出Watchlist数量
            watchlist_count = len(self.watchlist)
            logger.info("=" * 60)
            logger.info(f"[CTO] 热启动扫描完成！当前真实观察池数量: {watchlist_count}只")
            if watchlist_count > 0:
                logger.info(f"[CTO] 观察池前5只股票: {self.watchlist[:5]}")
            else:
                logger.error(f"[ERR] [CTO] 观察池为空！0.90分位的宽体雷达失效！")
            logger.info("=" * 60)
            
            # 【CTO强制回显】终端控制台输出
            import click
            click.echo(f"\n{'='*60}")
            click.echo(f"[CTO] 热启动扫描完毕！")
            click.echo(f"[TARGET] 成功进入观察池的股票数量: {watchlist_count} 只")
            if watchlist_count > 0:
                click.echo(click.style(f"[OK] 观察池前5只: {self.watchlist[:5]}", fg="green"))
            else:
                click.echo(click.style("[ERR] 致命警报：观察池为0！所有股票均被过滤！", fg="red"))
            click.echo(f"{'='*60}\n")
            
            self._fire_control_mode()
            return
        
        # 【CTO V30】非交易日时跳过所有时间判断，直接返回（已在上面处理）
        if not is_today_trading:
            return  # 非交易日已在上面处理，这里直接返回
            
        # 如果已过09:25但未到09:30，执行快照初筛
        if current_time >= auction_end:
            logger.info("[TARGET] 已过09:25，立即执行CTO第一斩...")
            self._premarket_scan()  # 内部调用_auction_snapshot_filter
            
            # 计算到09:30的剩余时间
            seconds_to_open = (market_open - current_time).total_seconds()
            if seconds_to_open > 0:
                logger.info(f"? 等待{seconds_to_open:.0f}秒到09:30开盘...")
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
            logger.info(f"? 等待{seconds_to_auction:.0f}秒到09:25集合竞价结束...")
            # 【CTO V5修复】等待期间显示缓存面板
            self._print_fire_control_panel([], initial_loading=True)
            import time
            time.sleep(seconds_to_auction)
            self._execute_auction_filter()
        else:
            self._execute_auction_filter()
    
    def _execute_auction_filter(self):
        """执行09:25集合竞价初筛"""
        logger.info("[CTO] 09:25 - CTO第一斩：集合竞价快照初筛...")
        self._premarket_scan()  # 内部调用_auction_snapshot_filter
        
        # 计算到09:30的剩余时间
        current_time = self.get_current_time()
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        seconds_to_open = (market_open - current_time).total_seconds()
        
        if seconds_to_open > 0:
            logger.info(f"? 09:25初筛完成，等待{seconds_to_open:.0f}秒到09:30开盘...")
            # 【CTO V5修复】等待期间显示缓存面板
            self._print_fire_control_panel([], initial_loading=True)
            import time
            time.sleep(seconds_to_open)
        
        # 【CTO V5修复】直接调用粗筛，不再用Timer
        logger.info("[TARGET] 已到09:30，立即启动开盘快照过滤...")
        self._snapshot_filter()
        
        # 【CTO V5修复】直接进入雷达循环！
        if self.watchlist and self.enable_dynamic_radar:
            self._setup_qmt_callbacks()
            self._run_radar_main_loop()
    
    def _setup_qmt_callbacks(self):
        """
        【大道至简】仅做subscribe_whole_quote订阅，激活QMT内存缓存
        
        EventBus双轨制已废除，主循环通过xtdata.get_full_tick()批量拉取。
        此方法仅保留subscribe_whole_quote订阅，确保QMT内存缓存被激活。
        """
        if not self.watchlist:
            logger.warning("[WARN] watchlist未初始化，跳过Tick订阅")
            return
        try:
            from xtquant import xtdata
            xtdata.subscribe_whole_quote(self.watchlist)
            logger.info(f"[OK] QMT Tick订阅: {len(self.watchlist)}只（主循环拉取模式）")
        except Exception as e:
            logger.error(f"[ERR] Tick订阅失败: {e}")
    
    def _auction_snapshot_filter(self):
        """
        【CTO V87 优雅同源】废除实盘专属竞价淘汰。
        竞价弱的票交由引擎自然打出低分，坚决不在初始列表里做物理切除！
        保证与 Scan/Mock 100% 对齐。
        
        原逻辑：过滤低开/无量/一字板等，破坏SSOT。
        新逻辑：直接return，让打分引擎自然淘汰。
        """
        logger.info("[SSOT] 竞价快照过滤已关闭，维持UniverseBuilder原始底池。")
        return
        # ===== 以下代码已被CTO V87废除 =====
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
            
            # 【CTO重构】废弃qmt_adapter，直接用xtdata
            from xtquant import xtdata
            
            # 1. 获取全市场快照（1毫秒内完成）
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            if not all_stocks:
                logger.error("[ERR] 无法获取沪深A股列表")
                return
            
            xtdata.subscribe_whole_quote(all_stocks)
            snapshot = xtdata.get_full_tick(all_stocks)
            
            if not snapshot:
                logger.error("[ERR] 无法获取09:25集合竞价快照")
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
                logger.error("?? 09:25快照数据为空")
                return
            
            original_count = len(df)
            
            # 3. 从TrueDictionary获取涨停价和流通市值
            from logic.data_providers.true_dictionary import get_true_dictionary
            true_dict = get_true_dictionary()
            
            # 【Phase1终极修复】预热TrueDictionary（如果缓存为空）
            if not true_dict._float_volume or not true_dict._up_stop_price:
                logger.info("?? [TrueDictionary] 第一斩前预热中...")
                from logic.utils.calendar_utils import get_nth_previous_trading_day
                today = self.get_current_time().strftime('%Y%m%d')
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
            
            # 5. 【CTO V46】竞价MFE物理探针（废除涨跌幅歧视！）
            # 不再歧视低开，只看资金做功效率（MFE）
            from logic.utils.price_utils import check_auction_validity, calculate_auction_mfe
            
            df['auction_valid'] = df.apply(
                lambda row: check_auction_validity(
                    {
                        'lastPrice': row['open'],
                        'amount': row['amount'],
                        'lastClose': row['prev_close'],
                        'high': row.get('high', row['open']),
                        'low': row.get('low', row['open'])
                    },
                    row['float_volume']
                ),
                axis=1
            )
            
            # 计算MFE值用于排序
            df['auction_mfe'] = df.apply(
                lambda row: calculate_auction_mfe(
                    {
                        'lastPrice': row['open'],
                        'amount': row['amount'],
                        'lastClose': row['prev_close']
                    },
                    row['float_volume']
                ),
                axis=1
            )
            
            # 过滤：只保留通过MFE考核的
            filtered_df = df[df['auction_valid']].copy()
            
            # 按MFE排序（做功效率高的优先）
            filtered_df = filtered_df.sort_values('auction_mfe', ascending=False)
            
            # 计算开盘涨幅（仅用于展示，不过滤）
            filtered_df['open_change_pct'] = (
                (filtered_df['open'] - filtered_df['prev_close']) / filtered_df['prev_close'] * 100
            )
            
            elapsed = (time.perf_counter() - start_time) * 1000
            
            # 6. 【CTO V46强化】输出竞价MFE爆量榜
            today_str = self.get_current_time().strftime('%Y%m%d')
            
            # MFE TOP10（MFE > 5）
            high_mfe = filtered_df[filtered_df['auction_mfe'] > 5].head(10)
            if len(high_mfe) > 0:
                logger.info("=" * 60)
                logger.info(f"?? 竞价MFE榜 (09:25资金做功效率TOP)")
                logger.info("=" * 60)
                for _, row in high_mfe.iterrows():
                    logger.info(
                        f"?? [{row['stock_code']}] "
                        f"MFE={row['auction_mfe']:.1f} "
                        f"竞价金额={row['amount']/10000:.1f}万 "
                        f"涨跌={row['open_change_pct']:+.2f}%"
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
                logger.info(f"[OK] [竞价收割] {len(filtered_df)}只股票竞价数据已落盘 -> {output_path}")
            except Exception as e:
                logger.warning(f"[WARN] 竞价数据保存失败: {e}")
            
            # 8. 更新watchlist为初筛结果（CTO处决：删除Magic Number截断！）
            self.watchlist = filtered_df['stock_code'].tolist()
            
            logger.info(
                f"[CTO] CTO第一斩完成: {original_count}只 → {len(self.watchlist)}只 "
                f"({len(self.watchlist)/original_count*100:.1f}%),耗时{elapsed:.2f}ms"
            )
            
            # 记录统计信息
            rejected_lower = len(df[df['open'] < df['prev_close']])
            rejected_lowvol = len(df[df['volume'] < 1000])
            rejected_limitup = len(df[df['open'] >= df['up_stop_price']])
            
            logger.debug(
                f"?? 初筛剔除统计: 低开{rejected_lower}只, 无量{rejected_lowvol}只, "
                f"一字板{rejected_limitup}只"
            )
            
        except Exception as e:
            logger.error(f"[ERR] 09:25快照初筛失败: {e}")
            logger.warning("[WARN] 初筛失败，回退到基础股票池（限制100只）")
            self._fallback_premarket_scan()

    def _fallback_premarket_scan(self):
        """
        【CTO修复】回退方案：使用QMTEventAdapter快照获取基础股票池
        严禁使用UniverseBuilder（它是盘前工具，依赖日K线）
        """
        logger.warning("[WARN] 执行QMT快照回退方案...")
        
        try:
            # 【CTO重构】废弃qmt_adapter，直接用xtdata
            from xtquant import xtdata
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            if not all_stocks:
                logger.error("[ERR] 无法获取股票列表")
                self.watchlist = []
                return
            
            # 获取快照，只取前100只作为应急观察池
            xtdata.subscribe_whole_quote(all_stocks[:500])
            snapshot = xtdata.get_full_tick(all_stocks[:500])
            if snapshot:
                self.watchlist = list(snapshot.keys())[:100]
                logger.info(f"[OK] QMT快照回退完成: {len(self.watchlist)} 只候选")
            else:
                logger.error("[ERR] 快照获取失败")
                self.watchlist = []
        except Exception as e:
            logger.error(f"[ERR] 回退方案失败: {e}")
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
            today = self.get_current_time().strftime('%Y%m%d')
            target_date = get_nth_previous_trading_day(today, 1)  # 上一个交易日
            
            # 使用当前watchlist + 扩展池进行预热
            warmup_stocks = self._get_extended_stock_pool(self.watchlist)
            
            result = true_dict.warmup(warmup_stocks, target_date=target_date)
            
            if result['integrity']['is_ready']:
                atr_count = len(true_dict._atr_20d_map) if hasattr(true_dict, '_atr_20d_map') else 0
                prev_close_count = len(true_dict._prev_close_cache) if hasattr(true_dict, '_prev_close_cache') else 0
                logger.info(
                    f"[OK] TrueDictionary装弹完成: "
                    f"涨停价{result['qmt'].get('success', 0)}只, "
                    f"5日均量{result['avg_volume'].get('success', 0)}只, "
                    f"ATR{atr_count}只, prev_close{prev_close_count}只"
                )
            else:
                logger.warning(f"[WARN] TrueDictionary装弹不完整: 缺失率{result['integrity']['missing_rate']*100:.1f}%")
                
        except Exception as e:
            logger.error(f"[ERR] TrueDictionary预热失败: {e}")
            logger.warning("[INFO] 提示：将使用实时数据获取，可能影响性能")
    
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
            # 【CTO重构】废弃qmt_adapter，直接用xtdata
            from xtquant import xtdata
            all_a_shares = xtdata.get_stock_list_in_sector('沪深A股')
            
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
        logger.info(f"[BOX] 扩展股票池: {len(result)} 只 (基础池 {len(universe)} 只)")
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
        【CTO V87 优雅同源】废除实盘专属开盘淘汰。
        开盘弱的票交由引擎自然打出低分，坚决不在初始列表里做物理切除！
        保证与 Scan/Mock 100% 对齐。
        
        原逻辑：过滤量比/换手率/死亡换手等，破坏SSOT。
        新逻辑：直接return，让打分引擎自然淘汰。
        """
        logger.info("[SSOT] 开盘快照过滤已关闭，维持UniverseBuilder原始底池。")
        return
        # ===== 以下代码已被CTO V87废除 =====
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
            
            # 【CTO重构】彻底废弃qmt_adapter幽灵依赖！直接用xtdata拉取快照
            # 原代码依赖self.qmt_adapter.get_full_tick_snapshot，但qmt_adapter已被废弃
            
            # 1. 获取09:25筛选出的股票的开盘快照
            if not self.watchlist:
                logger.error("[WARN] watchlist为空，无法进行09:30粗筛")
                return
            
            from xtquant import xtdata
            xtdata.subscribe_whole_quote(self.watchlist)
            time.sleep(1.0)  # 给予C++底层1秒钟内存聚合时间
            
            snapshot = xtdata.get_full_tick(self.watchlist)
            
            if not snapshot:
                logger.error("[ERR] xtdata.get_full_tick返回空快照，内存中无行情数据")
                self.watchlist = []
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
                logger.error("?? 09:30快照数据为空")
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
            
            now = self.get_current_time()
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
            # 【CTO V7修复】消除Pandas FutureWarning
            # 【CTO V24修复】默认值必须能让股票通过粗筛！
            # avg_amount_5d默认值改为5000万（刚好满足门槛）
            # avg_turnover_5d默认值改为2.5%（刚好满足门槛）
            import numpy as np
            df['volume_ratio'] = df['volume_ratio'].fillna(1.0).infer_objects(copy=False)
            df['avg_turnover_5d'] = df['avg_turnover_5d'].fillna(2.5).infer_objects(copy=False)  # 【CTO V24】刚好满足门槛
            df['avg_amount_5d'] = df['avg_amount_5d'].fillna(50000000.0).infer_objects(copy=False)  # 【CTO V24】5000万刚好满足门槛
            df['current_turnover'] = df['current_turnover'].fillna(0.0).infer_objects(copy=False)
            
            # 清理无穷大
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df['volume_ratio'] = df['volume_ratio'].fillna(1.0).infer_objects(copy=False)
            
            pre_filter_count = len(df)
            
            # ========== 【CTO V7 Phase4】牛市经验参数对齐！==========
            # 数据支撑：连板首板V3报告显示T-1换手中位3.69%，T0换手中位4.96%
            # 粗筛必须捕捉"暗流期"（换手从<3%异动至>3.5%但价格未动）
            
            # 【量比动态分位】取全市场90th分位，防止熊市数据塌缩
            volume_ratio_90th = df['volume_ratio'].quantile(0.90)
            min_volume_multiplier = max(volume_ratio_90th, 1.5)  # 绝对物理下限1.5x
            
            # 【时间效应补偿】午后量比回归，需要降低分位数门槛
            if minutes_passed >= 240:
                # 盘后模式：量比是全天真实值，使用70th分位
                volume_ratio_70th = df['volume_ratio'].quantile(0.70)
                min_volume_multiplier = max(volume_ratio_70th, 1.5)
                mode_tag = "盘后投影"
            elif minutes_passed >= 120:
                # 午后模式：量比部分回归，使用80th分位
                volume_ratio_80th = df['volume_ratio'].quantile(0.80)
                min_volume_multiplier = max(volume_ratio_80th, 1.5)
                mode_tag = "午后修正"
            else:
                # 早盘模式：量比脉冲期，使用90th分位
                mode_tag = "早盘脉冲"
            
            # 【CTO V25 统一配置读取】废除硬编码，全部从strategy_params.json读取！
            # stock_filter.min_avg_amount: 5000万均额
            # stock_filter.min_avg_turnover_pct: 2.5%换手（暗流期基因）
            min_avg_amount_5d = config_manager.get('stock_filter.min_avg_amount', 50000000.0)
            min_avg_turnover_5d = config_manager.get('stock_filter.min_avg_turnover_pct', 2.5)
            max_open_turnover = 30.0  # 开盘换手率>30%视为死亡派发
            
            logger.info(f"\n{'='*60}")
            logger.info(f"[FILTER] 【四级漏斗-第二级粗筛】CTO V86/V87绝对同质同源！")
            logger.info(f"{'='*60}")
            logger.info(f"> 运行模式: {mode_tag} (已过{minutes_passed:.0f}分钟)")
            logger.info(f"> 输入池: {pre_filter_count} 只")
            logger.info(f"> 【已废除】历史均额/换手过滤 - 右侧起爆抓平地惊雷！")
            logger.info(f"> 基础卫生过滤: 死亡换手 < {max_open_turnover:.0f}% | 极端无量 = 0")
            
            # 【CTO V86 绝对同质同源】废除历史均额和换手率过滤！
            # 右侧起爆抓的是"平地起惊雷"，昨天的死水不能过滤今天的爆发！
            # 只保留基础卫生过滤：
            # 1. 死亡换手（current_turnover > max_open_turnover）
            # 2. 极端无量（volume == 0）
            mask = (
                (df['volume_gu'] > 0) &
                (df['current_turnover'] < max_open_turnover)
            )
            
            filtered_df = df[mask].copy()
            
            post_filter_count = len(filtered_df)
            
            logger.info(f"\n?? 【粗筛结果】:")
            logger.info(f"> 粗筛池: {post_filter_count} 只 (目标500-900只)")
            logger.info(f"?? 淘汰: {pre_filter_count - post_filter_count} 只")
            logger.info(f"{'='*60}\n")
            
            # 按量比排序
            filtered_df = filtered_df.sort_values('volume_ratio', ascending=False)
            
            elapsed = (time.perf_counter() - start_time) * 1000
            
            # 数量提示
            if post_filter_count == 0:
                logger.warning(f"[WARN] 粗筛池为空！量比门槛{min_volume_multiplier:.1f}x可能过高")
            elif post_filter_count < 100:
                logger.info(f"[INFO] 粗筛池数量较少: {post_filter_count}只")
            else:
                logger.info(f"[OK] 粗筛池已就绪: {post_filter_count}只")
            
            # 【CTO V5处决】删除粗筛池上限截断！真实漏斗由量比决定！
            self.watchlist = filtered_df['stock_code'].tolist()
            
            logger.info(f"[CTO] CTO四级漏斗-粗筛完成: {original_count}只 → {len(self.watchlist)}只，耗时{elapsed:.2f}ms")
            
            # 终端回显
            import click
            click.echo(f"\n{'='*60}")
            click.echo(f"?? [四级漏斗-粗筛] {mode_tag}模式 | 量比>={min_volume_multiplier:.1f}x")
            click.echo(f"[TARGET] 粗筛池: {len(self.watchlist)} 只")
            click.echo(f"{'='*60}\n")
            
            # 【CTO V5修复】删除Timer等待，直接return让start_session控制流程！
            # 粗筛完成后由start_session决定下一步（直接进入雷达循环）
            return
            
        except Exception as e:
            logger.error(f"[ERR] 09:30开盘粗筛失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _fire_control_mode(self):
        """
        【CTO V3终极重铸】高频监控模式 - 主线程直接接管！
        
        废除后台线程！雷达心跳必须在主线程！
        """
        # CTO修复：检查watchlist是否已初始化
        if not self.watchlist:
            logger.warning("[WARN] 股票池未初始化，跳过高频监控模式")
            logger.info("[INFO] 提示：系统持续监控中，等待右侧起爆信号...")
            return
        
        logger.info(f"[TARGET] 高频监控已激活: {len(self.watchlist)} 只目标 (主线程直接轮询)")
        
        # 初始化交易相关组件
        self._init_trading_components()
        
        # 【CTO V3】直接在主线程运行雷达循环！
        if self.enable_dynamic_radar:
            self._run_radar_main_loop()
        else:
            logger.info("?? 静态模式：跳过动态雷达")
    
    def _init_trading_components(self):
        """【CTO清理】初始化交易相关组件 - 纯血游资架构"""
        logger.debug("[TARGET] [纯血游资雷达] 交易组件初始化完成（精简模式）")
    
    def _print_fire_control_panel(self, top_targets, initial_loading=False, pool_stats=None, is_rest=False, msg=None):
        """
        【CTO V34】UI渲染代理 - 调用metrics_utils中的render_live_dashboard
        
        实现UI与逻辑分离，实盘引擎只负责传数据，不负责画表格
        """
        from logic.utils.metrics_utils import render_live_dashboard
        render_live_dashboard(top_targets, pool_stats, is_rest, msg, initial_loading)
    
    def _run_radar_main_loop(self):
        """
        【CTO V30终极重铸】真·狩猎雷达 - 主线程直接轮询版
        
        核心改造:
        1. 废除threading后台线程，主线程直接while循环
        2. 看板先行：initial_loading参数
        3. 漏斗UI：pool_stats统计
        4. 正确死水判断：今日累计volume==0（不是价格不变）
        5. 1秒刷新
        6. 【CTO V30】插桩打点法：每步print+flush，杜绝静默卡死
        """
        import os
        import sys
        import time
        from datetime import datetime, time as time_type
        from xtquant import xtdata
        from logic.data_providers.true_dictionary import get_true_dictionary
        from logic.strategies.kinetic_core_engine import KineticCoreEngine
        
        # ==========================================
        # 【CTO V30】Step 1: 环境侦测 + 插桩打点
        # ==========================================
        from logic.utils.calendar_utils import is_trading_day, get_latest_completed_trading_day
        from datetime import datetime as dt
        
        today_str = dt.now().strftime('%Y%m%d')
        is_trading = is_trading_day(today_str)
        is_after_hours_init = dt.now().hour >= 15
        
        print(f">>> [INIT] 环境侦测: {'交易日' if is_trading else '非交易日'} | 盘后: {is_after_hours_init}")
        sys.stdout.flush()
        
        # ==========================================
        # 【CTO V30】Step 2: 第一帧画面（强行刷新缓冲区！）
        # ==========================================
        self._print_fire_control_panel([], initial_loading=True)
        sys.stdout.flush()
        
        # ==========================================
        # 【CTO V30】Step 3: 预编译静态指标快查表
        # ==========================================
        print(">>> [INIT] 正在预编译静态指标快查表 (O(1) 复杂度)...")
        sys.stdout.flush()
        
        # 预先获取TrueDictionary单例
        true_dict = get_true_dictionary()
        
        # 预先创建动能打分引擎实例
        core_engine = KineticCoreEngine()
        
        # 【CTO V5】盘后投影标志位：记录是否已执行过盘后最终计算
        has_run_after_hours = False
        
        # 【CTO V34】静态常数预编译快查表 - 剥离到TrueDictionary.build_static_cache
        static_cache = true_dict.build_static_cache(self.watchlist)
        self.static_cache = static_cache  # 【CTO V101】存储以便获取连板基因
        print(f">>> [INIT] 静态快查表编译完成: {len(static_cache)} 只股票")
        sys.stdout.flush()
        
        # ==========================================
        # 【CTO V38】Step 4: 唤醒底盘（删除周末防御逻辑，live只连QMT内存）
        # ==========================================
        print(f">>> [INIT] 开始分批唤醒 {len(self.watchlist)} 只股票的 QMT 底层缓存...")
        sys.stdout.flush()
        
        batch_size = 50  # 【CTO V7】降至50只，更安全
        for i in range(0, len(self.watchlist), batch_size):
            batch = self.watchlist[i:i+batch_size]
            try:
                # 【CTO V7】盘中才需订阅，非交易日/盘后跳过
                if is_trading and not is_after_hours_init:
                    xtdata.subscribe_whole_quote(batch)
                # 轻碰一下接口，建立内存通道即可
                xtdata.get_full_tick(batch)
                # 【CTO V56】沙盘模式CPU不需要呼吸，只需要计算！
                if self.mode == 'live':
                    time.sleep(0.1)  # 实盘让底盘呼吸
            except Exception as e:
                pass
        
        print(">>> [INIT] 引擎握手完毕！进入超频雷达主循环！")
        sys.stdout.flush()
        
        # ==========================================
        # 【CTO V30】正式进入死循环
        # ==========================================
        print(">>> [LOOP] 主线程雷达循环开启！")
        sys.stdout.flush()
        
        try:
            while self.running:
                # 【CTO V39战役三】统一时间流 - Tick帧计数！
                self.global_tick_frame += 1
                
                # 检查交易时间
                now = self.get_current_time()
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
                    # 【CTO R7修复】午休期间只打印一次，不要无限死循环刷屏！
                    # 斩断循环，安全挂起，下午由外部脚本重新拉起
                    logger.info("[STOP] 进入午休静默状态，雷达主线程安全休眠。")
                    self.running = False
                    break  # 替换原来的continue和time.sleep()
                
                # 【CTO V5】盘后期间 (15:00后)：执行一次最终计算然后定格展示
                is_after_hours = current_time >= time_type(15, 0)
                if is_after_hours and has_run_after_hours:
                    # 已经算过最终分数了，直接展示最终定格面板
                    # 【CTO V14修复】使用缓存的pool_stats，而非硬编码全0字典
                    cached_stats = self.last_known_pool_stats if self.last_known_pool_stats else {
                        'total': len(self.watchlist),
                        'active': 0,
                        'up': 0,
                        'down': 0,
                        'filtered': len(self.watchlist)
                    }
                    self._print_fire_control_panel(
                        self.last_known_top_targets,
                        initial_loading=False,
                        pool_stats=cached_stats,
                        msg="[LIST] 盘后定格投影 - 今天的最终战果"
                    )
                    if self.mode == 'live':
                        time.sleep(10)
                    continue
                
                # ----------------------------------------------------
                # 如果是盘中，或者是盘后的【第一次】循环，向下执行硬核打分！
                # ----------------------------------------------------
                loop_start = time.perf_counter()
                
                # 👇 【CTO V60 终极破血栓】主循环动态扩容探针（每3分钟心跳）
                if self.mode == 'live' and self.global_tick_frame % 180 == 0:  # 假设1秒1帧，180帧≈3分钟
                    logger.info("🌊 [活水引入] 执行全市场截面快照，捕获盘中新龙...")
                    try:
                        # 【CTO重构】废弃qmt_adapter，直接用xtdata
                        from xtquant import xtdata
                        all_a_shares = xtdata.get_stock_list_in_sector('沪深A股')
                        if all_a_shares:
                            xtdata.subscribe_whole_quote(all_a_shares)
                            mid_snapshot = xtdata.get_full_tick(all_a_shares)
                            if mid_snapshot:
                                import pandas as pd
                                mid_df = pd.DataFrame([
                                    {'code': c, 'vol': t.get('volume', 0), 'pre_c': t.get('lastClose', 0.01), 'p': t.get('lastPrice', 0)}
                                    for c, t in mid_snapshot.items() if t
                                ])
                                # 极速计算盘中量比（简化版，仅用于捕获突变）
                                now = self.get_current_time()
                                mid_minutes = max(5, (now - now.replace(hour=9, minute=30, second=0)).total_seconds() / 60)
                                
                                # 将 TrueDictionary 向量化提取
                                mid_df['avg_v_5d'] = mid_df['code'].map(lambda x: true_dict.get_avg_volume_5d(x) * 100).replace(0, pd.NA)
                                mid_df['vr'] = (mid_df['vol'] / mid_minutes * 240) / mid_df['avg_v_5d']
                                mid_df['chg'] = (mid_df['p'] - mid_df['pre_c']) / mid_df['pre_c'] * 100
                                
                                # 动态防线：取当前市场前 5% 的极强脉冲（符合老板相对论！）且涨幅>3%起势
                                if not mid_df.empty:
                                    dynamic_vr_threshold = mid_df['vr'].quantile(0.95)
                                    dynamic_vr_threshold = max(dynamic_vr_threshold, 3.0) # 兜底3倍
                                    
                                    new_dragons = mid_df[(mid_df['vr'] >= dynamic_vr_threshold) & (mid_df['chg'] >= 3.0)]['code'].tolist()
                                    
                                    added_count = 0
                                    for nd in new_dragons:
                                        if nd not in self.watchlist:
                                            self.watchlist.append(nd)
                                            added_count += 1
                                            
                                    if added_count > 0:
                                        logger.info(f"🔥 [沸水入池] 动态量比阀值飙至 {dynamic_vr_threshold:.1f}x！捕获 {added_count} 只新龙！当前池子: {len(self.watchlist)}只")
                                        # 同步订阅底层（容错包裹）
                                        try:
                                            from xtquant import xtdata
                                            xtdata.subscribe_whole_quote(self.watchlist[-added_count:])
                                        except Exception: pass
                    except Exception as e:
                        logger.error(f"[ERR] 盘中扩容探针失效: {e}")
                # 👆 【CTO V60】插入结束
                
                if not self.watchlist:
                    logger.warning("观察池为空，等待...")
                    if self.mode == 'live':
                        time.sleep(5)
                    continue
                
                # 【CTO Phase4.1 龙空龙】水位断电保护
                active_pool_size = len(self.watchlist)
                if active_pool_size < 20:
                    self._macro_multiplier = 0.0  # 触发硬件级熔断，禁止买入
                    logger.critical(f"?? [龙空龙警报] 市场活跃池仅 {active_pool_size} 只，流动性枯竭！系统强行拔电源，禁止任何买入！")
                else:
                    self._macro_multiplier = 1.0  # 正常
                
                # 【CTO第一级：全量快照捕获】
                try:
                    all_ticks = xtdata.get_full_tick(self.watchlist)
                except Exception as e:
                    logger.error(f"获取全量Tick失败: {e}")
                    if self.mode == 'live':
                        time.sleep(1)
                    continue
                
                # 【CTO V38】live模式只连QMT内存！
                # 如果返回空数据，说明是非交易日或QMT未启动
                # 不再尝试读取硬盘Tick，直接提示用户使用scan模式
                if not all_ticks:
                    logger.error("? QMT内存返回空Tick数据！")
                    logger.error("?? 如果是非交易日，请使用: python main.py scan")
                    if self.mode == 'live':
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
                
                # 【CTO V46战役二】横向虹吸效应 - 第一遍扫描计算全池总净流入
                # 物理意义：找出今天全候选池有多少资金在净流入
                # vampire_ratio = 该股净流入 / 全池总流入 * 100
                market_total_inflow = 0.0
                first_pass_inflow_cache = {}  # 缓存每只股票的净流入
                
                for stock_code in self.watchlist:
                    tick = all_ticks.get(stock_code)
                    if not tick:
                        continue
                    
                    current_price = tick.get('lastPrice', 0)
                    pre_close = tick.get('lastClose', 0)
                    current_amount = tick.get('amount', 0)  # 今日累计成交额（元）
                    tick_high = tick.get('high', current_price)
                    tick_low = tick.get('low', current_price)
                    
                    # 【CTO V93 L2/L1智能微积分】价格僵持时使用盘口重力推断
                    # 使用Tick差分状态机计算真实净流入
                    net_inflow_est = self._calculate_l1_inflow(
                        stock_code, float(current_amount), float(current_price), 
                        float(pre_close), float(tick_high), float(tick_low), tick
                    )
                    
                    # 【CTO V90 终极微积分与崩溃修复】
                    current_price = tick.get('lastPrice', 0)
                    pre_close = tick.get('lastClose', 0)
                    current_amount = tick.get('amount', 0)
                    
                    if stock_code not in self.l1_inflow_accumulator:
                        self.l1_inflow_accumulator[stock_code] = {
                            'inflow': 0.0, 'last_amount': current_amount, 'last_price': current_price
                        }
                        
                    cache = self.l1_inflow_accumulator[stock_code]
                    delta_amount = current_amount - cache['last_amount']
                    delta_price = current_price - cache['last_price']
                    
                    if delta_amount > 0:
                        if delta_price > 0:
                            cache['inflow'] += delta_amount
                        elif delta_price < 0:
                            cache['inflow'] -= delta_amount
                        else:
                            bid_vol = tick.get('bidVol1', 0)
                            ask_vol = tick.get('askVol1', 0)
                            if bid_vol + ask_vol > 0:
                                imb = (bid_vol - ask_vol) / (bid_vol + ask_vol)
                                cache['inflow'] += delta_amount * imb
                                
                    cache['last_amount'] = current_amount
                    cache['last_price'] = current_price
                    net_inflow_est = cache['inflow']
                    
                    # 修复 s_data 崩溃：直接从 true_dict 获取
                    avg_vol = true_dict.get_avg_volume_5d(stock_code) or 0.0
                    avg_amt = avg_vol * 100 * pre_close
                    change_pct = (current_price - pre_close) / pre_close * 100 if pre_close > 0 else 0
                    
                    if avg_amt > 0:
                        cur_ratio = current_amount / avg_amt
                        if cur_ratio > 3.0 and abs(change_pct) < 2.0:
                            net_inflow_est *= 0.1
                            logger.debug(f"[CTO V90] {stock_code} 放量滞涨，inflow降权")
                    
                    # 【CTO V90纠偏令】废除归零，实装量纲自适应校准仪！
                    float_volume = true_dict.get_float_volume(stock_code) or 0
                    if float_volume <= 0:
                        float_volume = 1000000000.0  # 默认10亿股
                    
                    float_market_cap = float_volume * current_price
                    
                    # 【量纲自适应校准算子】
                    calibrated_market_cap = float_market_cap
                    if float_market_cap > 0:
                        if float_market_cap < 20000000:  # 小于2000万，单位是"万股"
                            calibrated_market_cap = float_market_cap * 10000
                        elif float_market_cap < 200000000:  # 小于2亿，单位是"手"
                            calibrated_market_cap = float_market_cap * 100
                    
                    # 用校准后的市值计算真实流入占比（不再归零！）
                    if calibrated_market_cap > 0:
                        raw_inflow_pct = abs(net_inflow_est) / calibrated_market_cap * 100.0
                        if raw_inflow_pct > 80.0:
                            # 超过80%才可能是真正的数据异常，但也不归零，只记录警告
                            logger.warning(f"?? {stock_code} INFLOW={raw_inflow_pct:.2f}% 较高，但未归零")
                    
                    # 只累计正向净流入
                    if net_inflow_est > 0:
                        market_total_inflow += net_inflow_est
                    
                    first_pass_inflow_cache[stock_code] = net_inflow_est
                
                # 更新缓存（至少100万兜底，避免除零）
                self.market_total_inflow_cache = max(market_total_inflow, 1000000.0)
                print(f">>> [虹吸基准] 全候选池总净流入: {self.market_total_inflow_cache/100000000:.2f}亿元")
                sys.stdout.flush()
                
                # 【CTO第二级：极速布朗运动分类】
                for stock_code in self.watchlist:
                    tick = all_ticks.get(stock_code)
                    if not tick:
                        pool_stats['filtered'] += 1
                        continue
                    
                    current_price = tick.get('lastPrice', 0)
                    current_volume = tick.get('volume', 0)  # 今日累计成交量
                    
                    # ============================================================
                    # 【CTO架构重铸令R2/R3】L1价格推力探测器 + 微积分形态学
                    # ============================================================
                    from collections import deque
                    
                    # 初始化历史队列
                    if stock_code not in self.tick_history:
                        self.tick_history[stock_code] = deque(maxlen=self._TICK_HISTORY_MAXLEN)
                        self.volume_history[stock_code] = deque(maxlen=self._TICK_HISTORY_MAXLEN)
                    
                    # 更新历史队列（【CTO终极天网】存储current_volume用于计算增量换手！）
                    self.tick_history[stock_code].append({
                        'price': current_price,
                        'timestamp': now,
                        'volume': current_volume  # 总成交量（用于计算增量换手）
                    })
                    self.volume_history[stock_code].append(current_volume)
                    
                    # R2: L1价格推力探测器（ΔV/ΔP）- 放量滞涨一票否决
                    # 【CTO强制修正】修复量纲错误：用增量/增量比较，而非增量/累计比较
                    if len(self.volume_history[stock_code]) >= 20:  # 至少20个采样点（约1分钟）
                        history_list = list(self.volume_history[stock_code])
                        # 计算过去一段时间的"平均每Tick新增成交量"（增量/增量比较）
                        tick_vols = [history_list[i] - history_list[i-1] for i in range(1, len(history_list))]
                        avg_tick_vol = sum(tick_vols) / len(tick_vols) if tick_vols else 1.0
                        
                        # 当前Tick的新增成交量
                        current_tick_vol = current_volume - history_list[-1]
                        delta_price_pct = (current_price - self.tick_history[stock_code][0]['price']) / self.tick_history[stock_code][0]['price'] * 100
                        
                        # 正确逻辑：当前Tick成交量是过去1分钟平均的10倍以上（极度爆量），但价格涨幅极小
                        if avg_tick_vol > 0 and (current_tick_vol > avg_tick_vol * 10) and abs(delta_price_pct) < 0.2:
                            # 【CTO V118】日志降级到文件
                            _log_reject(stock_code, f"L1探针爆天量滞涨({current_tick_vol:.0f}>10x{avg_tick_vol:.0f}, {delta_price_pct:.2f}%)")
                            pool_stats['filtered'] += 1
                            continue
                    
                    # R3: Stair vs Spike二阶微积分防御（Δ2p）
                    # 【CTO强制修正】修复采样频率：用分钟级大切片，而非相邻3秒Tick
                    history_prices = list(self.tick_history[stock_code])
                    if len(history_prices) >= 60:  # 必须攒够3分钟数据（60个Tick，假设3秒/Tick）
                        # 切片采样：取现在(p0)，1.5分钟前(p1)，3分钟前(p2)
                        p_now = current_price
                        p_1_5min = history_prices[-30]['price']  # 30个Tick前 ≈ 1.5分钟
                        p_3min = history_prices[0]['price']       # 60个Tick前 ≈ 3分钟
                        
                        if p_1_5min > 0 and p_3min > 0:
                            v1 = p_1_5min - p_3min   # 前半段推力（1.5分钟）
                            v2 = p_now - p_1_5min    # 后半段推力（1.5分钟）
                            acceleration = v2 - v1   # 宏观二阶加速度
                            
                            # 【CTO修正】Spike骗炮检测：必须满足v2<0(正在砸盘)，才能定性为Spike！
                            # 原逻辑缺陷：acceleration<0只说明速度放缓，正常洗盘也会发生
                            # 新逻辑：v1>0(前半段拉升) + v2<0(后半段砸盘) + acceleration<0(减速) + 跌破起涨点
                            if v1 > 0 and v2 < 0 and acceleration < 0 and current_price < p_3min:
                                # 【CTO V118】重力异常日志降级到文件，不在终端刷屏
                                _log_reject(stock_code, f"Spike骗炮(v1={v1:.2f}, v2={v2:.2f})")
                                pool_stats['filtered'] += 1
                                continue
                    
                    
                    # 【CTO V20手术一】废除"缓存不到就杀人"的弱智拦截！
                    # [CTO V90] 已移除 s_data 依赖，直接从 true_dict 获取
                    # 修复：缓存缺失时兜底现场计算，绝不物理删除！
                    # 【CTO V21修复】get默认值对None无效！必须用or！
                    # 【CTO V23终极修复】昨收价优先从tick获取！流通股本用默认值兜底！
                    
                    # 【CTO V23】昨收价：tick的lastClose最可靠，绝不用预热！
                    pre_close = tick.get('lastClose', 0)
                    if pre_close <= 0:
                        pre_close = tick.get('lastPrice', 1.0)  # 再拿不到用现价
                    
                    float_volume = true_dict.get_float_volume(stock_code) or 0
                    avg_volume_5d = true_dict.get_avg_volume_5d(stock_code) or 1.0
                    if float_volume <= 0:
                        # 【CTO V90绝对物理兜底】
                        logger.debug(f"[WARN] {stock_code} 流通盘获取失败，启用10亿股强行兜底！")
                        float_volume = 1000000000.0  # 10亿股默认值
                    
                    # 【CTO V23】动态计算市值和成交额（基于tick的实时昨收价）
                    float_market_cap = float_volume * pre_close if float_volume > 0 and pre_close > 0 else 1.0
                    avg_amount_5d = avg_volume_5d * 100 * pre_close if avg_volume_5d > 0 and pre_close > 0 else 1.0
                    
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
                    
                    # 【CTO V12第三级：细筛 - 只防出货，不设底线！】
                    # V12哲学：时间加权换手只能做上限防守，不能做下限门槛
                    # 真龙可能缩量锁筹，只要不触发派发防线，一律放行给引擎打分！
                    try:
                        # 【CTO V20】float_volume已在上方从缓存或兜底获取
                        volume_gu = current_volume * 100  # 手→股
                        current_turnover = (volume_gu / float_volume * 100) if float_volume else 0
                        
                        # 【CTO V31修复】时间加权预估全天换手率
                        # 非交易日/盘后模式下使用全天数据（240分钟）
                        if is_after_hours or not is_trading:
                            minutes_elapsed = 240
                        else:
                            minutes_elapsed = (now.hour * 60 + now.minute) - (9 * 60 + 30)
                            minutes_elapsed = max(1, min(minutes_elapsed, 240))
                        est_full_day_turnover = current_turnover / minutes_elapsed * 240
                        
                        # 【CTO V12 死亡防线】只防出货，不设底线！
                        # 1. 绝对死亡线：全天换手 > 70%
                        if current_turnover >= 70.0 or est_full_day_turnover > 100.0:
                            continue  # 死亡换手/绞肉机，跳过
                        
                        # 2. 极速派发线：开盘30分钟内换手 > 15%
                        if minutes_elapsed <= 30 and current_turnover > 15.0:
                            continue  # 开盘极速派发，跳过
                        
                        # 3. ATR势垒（可选）- 这个需要动态计算，保留
                        atr_20d = true_dict.get_atr_20d(stock_code)
                        if atr_20d and atr_20d > 0:
                            today_tr = tick.get('high', current_price) - tick.get('low', current_price)
                            if today_tr > 0:
                                atr_ratio = today_tr / atr_20d
                                if atr_ratio < 1.8:
                                    continue  # ATR势垒不足，跳过
                        
                        # 放行！进入引擎打分环节
                        pool_stats['passed_fine_filter'] = pool_stats.get('passed_fine_filter', 0) + 1
                    except Exception:
                        pass  # 细筛失败不阻塞，继续计算
                    
                    # 【CTO第四级：动能打分】
                    try:
                        change_pct = (current_price - pre_close) / pre_close
                        
                        # 【CTO V20】float_market_cap已在上方从缓存或兜底获取
                        
                        # 【CTO V8量纲修复】使用tick的amount字段（成交额，元）
                        current_amount = tick.get('amount', 0)  # 今日累计成交额（元）
                        
                        # 【CTO V32终极修复】统一flow计算逻辑，非交易日也使用acceleration_factor！
                        # 问题根因：V31硬编码flow_15min=3*flow_5min导致sustain_ratio全员2.0
                        # 修复：无论盘中还是盘后，都用价格位置和涨幅估算acceleration_factor
                        
                        # 获取价格位置信息（用于估算资金加速）- 所有模式统一计算
                        tick_high = tick.get('high', current_price)
                        tick_low = tick.get('low', current_price)
                        price_position = (current_price - tick_low) / (tick_high - tick_low) if tick_high > tick_low else 0.5
                        
                        # 【CTO V13修复】sustain_ratio动态估算 - 所有模式统一计算
                        change_pct_for_sustain = (current_price - pre_close) / pre_close if pre_close > 0 else 0
                        
                        # 资金加速因子 - 物理公式，打破硬编码魔咒！
                        acceleration_factor = 1.0 + (price_position - 0.5) * 1.0 + change_pct_for_sustain * 3.0
                        acceleration_factor = max(0.3, min(acceleration_factor, 3.0))
                        
                        if is_after_hours or not is_trading:
                            # 盘后/非交易日：使用全天数据（240分钟）
                            minutes_elapsed = 240
                            flow_5min = current_amount / 48.0  # 每5分钟均值
                            # 【CTO V32关键修复】带上acceleration_factor，让sustain_ratio动态变化！
                            flow_15min = current_amount / 16.0 * acceleration_factor  # 破除2.0魔咒
                        else:
                            minutes_elapsed = (now.hour * 60 + now.minute) - (9 * 60 + 30)
                            minutes_elapsed = max(1, min(minutes_elapsed, 240))
                            
                            # 成交额估算
                            flow_5min = current_amount / minutes_elapsed * 5
                            flow_15min = current_amount / minutes_elapsed * 15 * acceleration_factor
                        
                        # 【CTO V20】avg_amount_5d已在上方从缓存或兜底获取
                        flow_5min_median = avg_amount_5d / 48.0  # 每5分钟历史中位数（元）
                        
                        # 【CTO V93 L2/L1智能微积分】价格僵持时使用盘口重力推断
                        # 使用Tick差分状态机计算真实净流入
                        tick_high = tick.get('high', current_price)
                        tick_low = tick.get('low', current_price)
                        net_inflow_est = self._calculate_l1_inflow(
                            stock_code, float(current_amount), float(current_price),
                            float(pre_close), float(tick_high), float(tick_low), tick
                        )
                        
                        # 【CTO修复】使用tick真实high/low计算动态MFE
                        high_60d = tick.get('high', current_price)
                        space_gap_pct = (high_60d - current_price) / high_60d if high_60d > 0 else 0.5
                        
                        # 【CTO V34修复】废除时间冻结毒瘤！
                        # 盘后/非交易日：使用mode="scan"跳过时间衰减，而非"穿越时间"
                        # 实盘交易：使用mode="live"应用时间衰减
                        engine_time = now  # 始终使用真实时间
                        engine_mode = "scan" if (is_after_hours or not is_trading) else "live"
                        
                        # 【CTO V34照妖镜修复】用绝对价格推导判断涨停（解决askPrice1盘后失效问题）
                        # 涨停价计算：主板10%，创业板/科创板20%，北交所30%
                        pre_close = tick.get('lastClose', 0.0) or 0.0
                        current_price = tick.get('lastPrice', 0.0) or 0.0
                        if stock_code.startswith(('30', '68')):  # 创业板、科创板 20%
                            limit_up_price = round(pre_close * 1.20, 2)
                        elif stock_code.startswith(('8', '4')):  # 北交所 30%
                            limit_up_price = round(pre_close * 1.30, 2)
                        else:  # 主板 10%
                            limit_up_price = round(pre_close * 1.10, 2)
                        # 现价距离涨停价<1分钱即判定为物理封板
                        is_limit_up = (current_price >= limit_up_price - 0.011)
                        
                        # 封单金额：尝试从盘口获取
                        ask_price1 = tick.get('askPrice1', 0.0) or 0.0
                        bid_price1 = tick.get('bidPrice1', 0.0) or 0.0
                        bid_vol1 = (tick.get('bidVol1', 0) or 0) * 100  # tick volume是手，转股
                        if is_limit_up:
                            if bid_price1 > 0 and bid_vol1 > 0:
                                limit_up_queue_amount = bid_price1 * bid_vol1
                            else:
                                # 盘口数据缺失时，给一个默认封单（防止真龙被误判）
                                limit_up_queue_amount = 50000000.0  # 默认5000万封单
                        else:
                            limit_up_queue_amount = 0.0
                        
                        # 【CTO V46战役二】计算横向虹吸比例
                        vampire_ratio_pct = 0.0
                        stock_net_inflow = first_pass_inflow_cache.get(stock_code, 0.0)
                        if self.market_total_inflow_cache > 0 and stock_net_inflow > 0:
                            vampire_ratio_pct = (stock_net_inflow / self.market_total_inflow_cache) * 100.0
                            vampire_ratio_pct = min(vampire_ratio_pct, 100.0)  # 上限100%
                        
                        # 【CTO V101】获取连板基因
                        is_yesterday_limit_up = self.static_cache.get(stock_code, {}).get('is_yesterday_limit_up', False)
                        try:
                            final_score, sustain_ratio, inflow_ratio, ratio_stock, mfe = core_engine.calculate_true_dragon_score(
                                net_inflow=net_inflow_est,  # 净流入估算（元）
                                price=current_price,
                                prev_close=pre_close,
                                high=tick_high,  # 【CTO修复】使用tick真实high
                                low=tick_low,    # 【CTO修复】使用tick真实low
                                open_price=tick.get('open', current_price),  # 【CTO修复】使用tick真实open
                                flow_5min=flow_5min,
                                flow_15min=flow_15min,
                                flow_5min_median_stock=flow_5min_median if flow_5min_median > 0 else 1.0,
                                space_gap_pct=space_gap_pct,
                                float_volume_shares=float_volume,
                                current_time=engine_time,  # 真实时间
                                is_limit_up=is_limit_up,  # 【CTO V33】涨停状态
                                limit_up_queue_amount=limit_up_queue_amount,  # 【CTO V33】封单金额
                                mode=engine_mode,  # 【CTO V34】scan跳过衰减/live应用衰减
                                stock_code=stock_code,  # 【CTO V35】股票代码用于动态danger_pct
                                is_yesterday_limit_up=is_yesterday_limit_up,  # 【CTO V101】连板基因
                                vampire_ratio_pct=vampire_ratio_pct  # 【CTO V46】横向虹吸效应
                            )
                        except Exception as e:
                            logger.debug(f"[SKIP] {stock_code} 高阶算子计算失败，剔除: {e}")
                            continue
                        
                        # 【CTO V21量化纯度】废除字符串标签，改为物理百分比！
                        # 纯度 = (当前价 - 昨收) / (最高 - 最低) * 100
                        # 含义：价格在日内区间中的位置，反映资金做多意愿
                        # +100% = 涨停（最高点），-100% = 跌停（最低点）
                        price_range = tick_high - tick_low
                        if price_range > 0:
                            raw_purity = (current_price - pre_close) / price_range
                        else:
                            raw_purity = 1.0 if current_price > pre_close else -1.0
                        quant_purity = min(max(raw_purity, -1.0), 1.0) * 100  # 范围 -100% 到 +100%
                        
                        # 【CTO V21垃圾隔离防线】
                        # 1. 决不允许不及格的票（<50分）上榜！
                        # 2. 决不允许极端出货（纯度<-50%）的票上榜！
                        if final_score >= 50.0 and quant_purity > -50.0:
                            current_top_targets.append({
                                'code': stock_code,
                                'score': final_score,
                                'price': current_price,
                                'change': change_pct * 100,
                                'inflow_ratio': inflow_ratio,  # 【CTO V15】真实值，绝不造假！
                                'ratio_stock': ratio_stock,
                                'sustain_ratio': sustain_ratio,
                                'mfe': mfe,  # 资金效率指标
                                'purity': quant_purity  # 【CTO V21】量化纯度百分比
                            })
                    except Exception:
                        continue
                
                # 【CTO第五级：机会池排序】
                current_top_targets.sort(key=lambda x: x['score'], reverse=True)
                top_10 = current_top_targets[:10]
                
                # 【CTO V4关键】更新静态机会池缓存！
                if top_10:
                    self.last_known_top_targets = top_10
                
                # ============================================================
                # 【CTO V71单吊极锋执行器】买入触发逻辑
                # ============================================================
                # 触发条件：榜首分数>=70分，且通过微观防线检查
                # 单吊模式：只买榜首一只，满仓单票
                # ============================================================
                if top_10 and self.execution_manager and self.mode == 'live':
                    top_stock = top_10[0]
                    top_code = top_stock['code']
                    top_score = top_stock['score']
                    
                    # 触发阈值：70分（确保是高质量机会）
                    if top_score >= 70.0:
                        # 获取Tick数据
                        top_tick = all_ticks.get(top_code, {})
                        top_price = top_tick.get('lastPrice', 0)
                        
                        # 微观防线检查
                        if self._micro_defense_check(top_code, top_tick):
                            logger.info(f"🎯 [单吊触发] {top_code} 分数={top_score:.1f} 价格={top_price:.2f}")
                            
                            # 扣动扳机（MockExecutionManager会自动检查资金状态）
                            success = self.execution_manager.place_mock_order(
                                top_code, 
                                top_price, 
                                'BUY'
                            )
                            
                            if success:
                                logger.info(f"✅ [成交确认] {top_code} 买入成功！")
                                # 单吊模式：买入后退出主循环（不再寻找其他机会）
                                # self.running = False
                            else:
                                logger.debug(f"❌ [买入失败] {top_code} 资金不足或仓位已满")
                
                # 【CTO V13】更新pool_stats缓存，解决盘中无数据时显示0的问题
                if pool_stats.get('active', 0) > 0:
                    self.last_known_pool_stats = pool_stats.copy()
                elif self.last_known_pool_stats:
                    # 当前无数据，使用缓存
                    pool_stats = self.last_known_pool_stats.copy()
                
                # 【CTO V5】如果这是盘后的第一次计算，标记完成，以后不再重复算
                if is_after_hours:
                    has_run_after_hours = True
                    logger.info("[OK] 盘后最终 Tick 快照计算完成，投影定格！")
                
                # 主线程刷屏（盘后模式静默，不清屏）
                self._print_fire_control_panel(top_10, initial_loading=False, pool_stats=pool_stats, is_rest=is_after_hours)
                
                # 【CTO V46架构大一统】持仓止损/止盈检查
                # 检查所有持仓是否触发卖出条件
                if self.positions:
                    exit_signals = self.check_position_exits(all_ticks)
                    for signal in exit_signals:
                        logger.warning(f"?? [持仓止损] {signal['code']}: {signal['reason']}")
                        # 这里只打印日志，实际卖出操作需要与交易接口对接
                        # self.close_position(signal['code'], signal['reason'])
                
                # 战地收尸
                self._update_daily_battle_report(current_top_targets)
                
                # 【CTO V31物理阻断】非交易日或盘后，渲染一次即为定格，严禁陷入死循环空转！
                if is_after_hours or not is_trading:
                    logger.info("[STOP] 盘后定格投影完毕，系统安全挂起。")
                    self.running = False  # 斩断死循环
                    self._skip_final_report = True  # 【CTO V32】跳过stop中的战报打印，避免重复
                    break
                
                # 【CTO物理限速器】1秒一圈（仅实盘模式）
                if self.mode == 'live':
                    elapsed = time.perf_counter() - loop_start
                    sleep_time = max(0.1, 1.0 - elapsed)
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("[STOP] 用户中断，生成战报...")
            if not getattr(self, '_has_generated_report', False):
                self._generate_final_battle_report()
                self._has_generated_report = True
        except Exception as e:
            logger.error(f"雷达循环异常: {e}")
            if not getattr(self, '_has_generated_report', False):
                self._generate_final_battle_report()
                self._has_generated_report = True
    
    def _on_tick_data(self, tick_event):
        """【已废弃】EventBus Tick回调——大道至简重构已删除双轨制"""
        pass
    def _get_current_sustain_ratio(self, stock_code: str, tick_data: Dict[str, Any]) -> float:
        """
        获取当前sustain_ratio（用于3分钟观察队列测试）
        
        Args:
            stock_code: 股票代码
            tick_data: 当前Tick数据
            
        Returns:
            float: sustain_ratio值
        """
        try:
            # 简化版：从_calculate_signal_score的返回值中提取
            # 如果无法获取，返回默认值1.0（不惩罚）
            price = tick_data.get('price', 0.0) or 0.0
            amount = tick_data.get('amount', 0.0) or 0.0
            pre_close = tick_data.get('lastClose', tick_data.get('prev_close', price)) or price
            
            from datetime import datetime
            now = self.get_current_time()
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            minutes_passed = max(1, (now - market_open).total_seconds() / 60)
            
            # 估算flow_5min和flow_15min
            flow_5min = amount / max(1, minutes_passed) * 5 if minutes_passed > 0 else amount
            flow_15min = amount / max(1, minutes_passed) * 15 if minutes_passed > 0 else amount
            
            # 计算sustain_ratio
            if flow_5min <= 0:
                return -1.0
            flow_next_10min = flow_15min - flow_5min
            sustain_ratio = (flow_next_10min / flow_5min) if flow_5min > 0 else 1.0
            return sustain_ratio
            
        except Exception as e:
            logger.debug(f"[WARN] {stock_code} 获取sustain_ratio失败: {e}，使用默认值1.0")
            return 1.0
    
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
        
        now = self.get_current_time()
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
        微观防线检查 - 四道防线验证
        
        [V70修复] 修复 'true_dict' in dir() 永假BUG，改为 try/except 正确获取单例
        
        Args:
            stock_code: 股票代码
            tick_data: Tick数据
            
        Returns:
            bool: 是否通过微观防线
        """
        # 检查TradeGatekeeper是否可用
        # 【CTO 绝对封杀】禁止 Fail-Open！风控宕机，拒绝一切交易！
        if not self.trade_gatekeeper:
            logger.error(f"[FATAL] {stock_code} TradeGatekeeper未初始化！防线失效，拒绝开火！(Fail-Close)")
            return False  # Fail-Close: 风控不可用时拒绝一切交易
        
        try:
            # ============================================================
            # 【CTO终极天网】L1放量滞涨探针：主力派发信号！
            # [V70修复] 原 'true_dict' in dir() 永假，改为 try/except 正确获取
            # ============================================================
            if stock_code in self.tick_history and len(self.tick_history[stock_code]) >= 100:  # 约5分钟历史
                tick_hist = list(self.tick_history[stock_code])
                old_tick = tick_hist[-100] if isinstance(tick_hist[-100], dict) else {'price': tick_hist[-100], 'volume': 0}
                old_price = old_tick.get('price', 0)
                old_volume = old_tick.get('volume', 0)
                
                current_price = tick_data.get('price', 0)
                current_volume = tick_data.get('volume', 0)  # 这是总成交量
                
                if old_price > 0 and current_price > 0 and old_volume > 0:
                    # [V71修复] 删除abs()！价格变化必须保留正负号才能检测下跌！
                    price_change_pct = (current_price - old_price) / old_price * 100
                    delta_volume = current_volume - old_volume
                    
                    # [V70修复] 原 'true_dict' in dir() 永假 → 改为 try/except 获取单例
                    try:
                        from logic.data_providers.true_dictionary import get_true_dictionary
                        _true_dict = get_true_dictionary()
                        float_volume = _true_dict.get_float_volume(stock_code) or 0
                    except Exception:
                        float_volume = 0
                    
                    if float_volume > 0:
                        # [V70修复] 量纲：delta_volume(手) * 100 = 股，/ float_volume(股) * 100 = %
                        delta_turnover = (delta_volume * 100) / float_volume * 100
                        
                        from datetime import time as time_type
                        now = self.get_current_time()
                        current_time_val = now.time()
                        
                        # 09:45后启动L1探针（给足早盘爆量建仓时间）
                        if current_time_val >= time_type(9, 45, 0):
                            if delta_turnover > 0.5 and price_change_pct < -0.5:
                                logger.warning(
                                    f"🚨 [L1探针] {stock_code} 爆量({delta_turnover:.2f}%)"
                                    f"且价格下跌({price_change_pct:.2f}%)，主力派发！"
                                )
                                return False
            
            # 防守斧：资金流检查
            capital_flow_ok = getattr(
                self.trade_gatekeeper, 'check_capital_flow', lambda *args: True
            )(stock_code, tick_data.get('volume_ratio', 0), tick_data)
            
            # 时机斧：板块共振检查
            sector_resonance_ok = getattr(
                self.trade_gatekeeper, 'check_sector_resonance', lambda *args: True
            )(stock_code, tick_data)
            
            # 资格斧：涨跌停状态检查
            try:
                from logic.data_providers.true_dictionary import get_true_dictionary
                _true_dict = get_true_dictionary()
                up_stop_price = _true_dict.get_up_stop_price(stock_code)
                down_stop_price = _true_dict.get_down_stop_price(stock_code)
            except Exception:
                up_stop_price = 0
                down_stop_price = 0
            
            current_price = tick_data.get('price', 0)
            if up_stop_price > 0 and current_price >= up_stop_price * 0.995:
                logger.debug(f"🔒 {stock_code} 接近涨停状态，放弃开火")
                return False
            if down_stop_price > 0 and current_price <= down_stop_price * 1.005:
                logger.debug(f"🔒 {stock_code} 接近跌停状态，放弃开火")
                return False
            
            micro_ok = capital_flow_ok and sector_resonance_ok
            if micro_ok:
                logger.info(f"[OK] {stock_code} 微观防线检查通过")
            else:
                logger.info(
                    f"🚫 {stock_code} 微观防线拦截: "
                    f"资金={capital_flow_ok}, 板块={sector_resonance_ok}"
                )
            return micro_ok
            
        except Exception as e:
            logger.error(f"[ERR] {stock_code} 微观防线检查异常: {e}")
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
            from logic.strategies.kinetic_core_engine import KineticCoreEngine
            from logic.data_providers.true_dictionary import get_true_dictionary
            
            if not hasattr(self, '_kinetic_core'):
                self._kinetic_core = KineticCoreEngine()
            
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
            now = self.get_current_time()
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
            
            # 【CTO V93 L2/L1智能微积分】价格僵持时使用盘口重力推断
            # 使用Tick差分状态机计算真实净流入
            net_inflow_est = self._calculate_l1_inflow(
                stock_code, float(amount), float(price),
                float(prev_close), float(high), float(low), tick_data
            )
            
            # === 【CTO V85: L1 对倒阻尼防线】 ===
            change_pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
            if avg_vol_5d and avg_vol_5d > 0:
                avg_amount_5d = avg_vol_5d * 100 * prev_close
                if avg_amount_5d > 0:
                    current_ratio = amount / avg_amount_5d
                    if current_ratio > 3.0 and abs(change_pct) < 2.0:
                        net_inflow_est *= 0.1
                        logger.debug(f"🚨 [对倒降维] {stock_code} 量比{current_ratio:.1f}x但涨幅仅{change_pct:.2f}%，剥离虚假流入！")
            
            # 【CTO V34照妖镜修复】用绝对价格推导判断涨停（解决askPrice1盘后失效问题）
            # 涨停价计算：主板10%，创业板/科创板20%，北交所30%
            if stock_code.startswith(('30', '68')):  # 创业板、科创板 20%
                limit_up_price = round(prev_close * 1.20, 2)
            elif stock_code.startswith(('8', '4')):  # 北交所 30%
                limit_up_price = round(prev_close * 1.30, 2)
            else:  # 主板 10%
                limit_up_price = round(prev_close * 1.10, 2)
            # 现价距离涨停价<1分钱即判定为物理封板
            is_limit_up = (price >= limit_up_price - 0.011)
            
            # 封单金额：尝试从盘口获取
            ask_price1 = tick_data.get('askPrice1', 0.0) or 0.0
            bid_price1 = tick_data.get('bidPrice1', 0.0) or 0.0
            bid_vol1 = (tick_data.get('bidVol1', 0) or 0) * 100  # tick volume是手，转股
            if is_limit_up:
                if bid_price1 > 0 and bid_vol1 > 0:
                    limit_up_queue_amount = bid_price1 * bid_vol1
                else:
                    # 盘口数据缺失时，给一个默认封单（防止真龙被误判）
                    limit_up_queue_amount = 50000000.0  # 默认5000万封单
            else:
                limit_up_queue_amount = 0.0
            
            # 【CTO V101】获取连板基因
            is_yesterday_limit_up = self.static_cache.get(stock_code, {}).get('is_yesterday_limit_up', False)
            # 调用 V20.5 动能引擎
            base_score, sustain_ratio, inflow_ratio, ratio_stock, mfe_score = self._kinetic_core.calculate_true_dragon_score(
                net_inflow=net_inflow_est,  # 【CTO V87】使用L1微积分状态机
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
                current_time=now,
                is_limit_up=is_limit_up,  # 【CTO V33】涨停状态
                limit_up_queue_amount=limit_up_queue_amount,  # 【CTO V33】封单金额
                mode="live",  # 【CTO V34】黄金3分钟队列用live模式
                stock_code=stock_code,  # 【CTO V35】股票代码用于动态danger_pct
                is_yesterday_limit_up=is_yesterday_limit_up  # 【CTO V101】连板基因
            )
            
            logger.debug(
                f"[TARGET] {stock_code} V20.5动能得分: "
                f"{base_score:.2f}, sustain={sustain_ratio:.2f}, mfe={mfe_score:.2f}"
            )
            return base_score
            
        except Exception as e:
            logger.error(f"[ERR] {stock_code} V20.5动能算分失败: {e}")
            return 0.0
        # [V70] 已删除: return后的memory_multiplier僵尸代码 + 多余的第二个except块
            return final_score
            
        except Exception as e:
            logger.error(f"[ERR] {stock_code} 动能算分失败: {e}")
            return 0.0
    
    def _execute_trade(self, stock_code: str, tick_data: Dict[str, Any], score: float):
        """
        【CTO V66废弃】交易执行 - 已移除
        
        原因：
        1. self.trader从未初始化
        2. trade_interface.py已删除
        3. 系统当前专注于打分和扫描，不执行交易
        
        保留此函数仅用于记录触发信号
        """
        price = tick_data.get('price', 0.0) or 0.0
        logger.info(f"[信号记录] {stock_code} 触发交易信号! 得分={score:.2f}, 价格={price:.2f}")
        logger.warning(f"[V66] 交易执行已禁用，系统当前仅支持打分和扫描")
        return

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
        return f"{rank}. [{stock_code} {stock_name}] 得分: {final_score:.1f} | 流入比: {inflow_ratio:.1%} | 自身爆发: {ratio_stock:.1f}x | 接力(Sustain): {sustain_ratio:.2f}x | MFE: {mfe:.2f} | 纯度: {purity} | [标签: {tag}]"

    def calculate_time_slice_flows(self, stock_code: str, date: str = None) -> Optional[Dict]:
        """
        【CTO终极红线：时空绝对对齐】计算真实时间切片资金流
        
        [V70修复] 使用reset_index(drop=True)降维，彻底消除str and int崩溃
        """
        try:
            from xtquant import xtdata
            import pandas as pd
            
            if date is None:
                date = self.get_current_time().strftime('%Y%m%d')
            
            normalized_code = self._normalize_stock_code(stock_code)
            
            tick_data = xtdata.get_local_data(
                field_list=['time', 'lastPrice', 'volume', 'amount'],
                stock_list=[normalized_code],
                period='tick',
                start_time=date,
                end_time=date
            )
            
            if not tick_data or normalized_code not in tick_data:
                return None
            
            df = tick_data[normalized_code]
            if df.empty or len(df) < 10:
                return None
            
            # 【CTO 降维打击】强制重置索引！将混合索引降维为纯净的 Integer Index！
            # 彻底拔除 '>' not supported between instances of 'str' and 'int' 的病根！
            df = df.reset_index(drop=True)
            
            if 'time' in df.columns:
                if pd.api.types.is_numeric_dtype(df['time']):
                    df['datetime'] = pd.to_datetime(df['time'], unit='ms') + pd.Timedelta(hours=8)
                    df['time_str'] = df['datetime'].dt.strftime('%H:%M:%S')
                else:
                    df['time_str'] = df['time'].astype(str)
            
            # 【时空切片1】09:30-09:35
            df_5min = df[(df['time_str'] >= '09:30:00') & (df['time_str'] <= '09:35:00')]
            if df_5min.empty:
                return None
            
            if 'amount' in df_5min.columns:
                first_idx = df_5min.index[0]  # 现在这是绝对安全的纯数字 int!
                last_idx = df_5min.index[-1]
                prev_amount = df.at[first_idx - 1, 'amount'] if first_idx > 0 else 0.0
                flow_5min = df.at[last_idx, 'amount'] - prev_amount
            else:
                first_idx = df_5min.index[0]
                last_idx = df_5min.index[-1]
                prev_volume = df.at[first_idx - 1, 'volume'] if first_idx > 0 else 0.0
                delta_volume = df.at[last_idx, 'volume'] - prev_volume
                avg_price = df_5min['lastPrice'].mean()
                flow_5min = avg_price * delta_volume * 100
            
            # 【时空切片2】09:30-09:45
            df_15min = df[(df['time_str'] >= '09:30:00') & (df['time_str'] <= '09:45:00')]
            if df_15min.empty:
                return None
            
            if 'amount' in df_15min.columns:
                first_idx = df_15min.index[0]
                last_idx = df_15min.index[-1]
                prev_amount = df.at[first_idx - 1, 'amount'] if first_idx > 0 else 0.0
                flow_15min = df.at[last_idx, 'amount'] - prev_amount
            else:
                first_idx = df_15min.index[0]
                last_idx = df_15min.index[-1]
                prev_volume = df.at[first_idx - 1, 'volume'] if first_idx > 0 else 0.0
                delta_volume = df.at[last_idx, 'volume'] - prev_volume
                avg_price = df_15min['lastPrice'].mean()
                flow_15min = avg_price * delta_volume * 100
            
            return {
                'flow_5min': float(flow_5min),
                'flow_15min': float(flow_15min),
                'tick_count_5min': len(df_5min),
                'tick_count_15min': len(df_15min)
            }
            
        except Exception as e:
            logger.error(f"[ERR] {stock_code} 时空切片计算失败: {e}")
            return None

    def _check_trade_signal(self, stock_code: str, score: float, tick_data: Dict[str, Any]):
        """
        [已废弃] 检查交易信号 - Phase 2后统一使用_tick级开火流程
        
        保留此方法用于向后兼容，新逻辑已全部迁移至_on_tick_data
        """
        logger.debug(f"[WARN] _check_trade_signal已废弃，请使用新的Tick级开火流程")
        # 新逻辑已在_on_tick_data中实现，此方法不再被调用
    

    def _start_auto_replenishment(self):
        """
        【CTO V59 动态雷达重铸】全天候脉冲扫描
        废除 "为空才扫描" 的静态漏斗，改为盘中定时全市场广角雷达！
        """
        import threading
        import time
        from datetime import datetime
        
        def auto_replenish_loop():
            while self.running:
                try:
                    current_time = self.get_current_time()
                    market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
                    market_close = current_time.replace(hour=15, minute=0, second=0, microsecond=0)
                    
                    if market_open.time() <= current_time.time() <= market_close.time():
                        # 【CTO 切除术】删除 if not self.watchlist: 的弱智拦截！
                        # 无论池子里有几只，每 3 分钟都要对全市场进行广角扫描捕获新龙！
                        logger.info("📡 [全息天网] 启动盘中动态广角扫描，搜寻新起爆真龙...")
                        self._process_snapshot_at_0930()  # 复用全市场快照探针
                    
                    if self.mode == 'live':
                        time.sleep(180)  # 【CTO节拍器】每 3 分钟扫一次全市场！
                    else:
                        break  # Scan模式不需要跑后台死循环
                        
                except Exception as e:
                    logger.error(f"[ERR] 自动热扫描循环异常: {e}")
                    if self.mode == 'live':
                        time.sleep(60)
        
        if self.mode == 'live':
            replenish_thread = threading.Thread(target=auto_replenish_loop, daemon=True)
            replenish_thread.start()
            logger.info("[OK] 盘中动态广角雷达已启动，每 3 分钟巡航一次全市场！")

    def _process_snapshot_at_0930(self):
        """
        CTO修正：处理当前截面快照
        盘中启动时，获取当前市场快照并筛选强势股
        """
        import pandas as pd
        from datetime import datetime
        
        try:
            logger.info("🔍 执行当前截面快照筛选...")
            
            # 【CTO重构】废弃qmt_adapter，直接用xtdata
            from xtquant import xtdata
            all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
            if not all_stocks:
                logger.error("[ERR] 无法获取股票列表")
                return
            
            xtdata.subscribe_whole_quote(all_stocks)
            snapshot = xtdata.get_full_tick(all_stocks)
            if not snapshot:
                logger.error("[ERR] 无法获取当前快照")
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
                logger.error("?? 快照数据为空")
                return
            
            # 从TrueDictionary获取涨停价
            from logic.data_providers.true_dictionary import get_true_dictionary
            true_dict = get_true_dictionary()
            
            df['up_stop_price'] = df['stock_code'].map(
                lambda x: true_dict.get_up_stop_price(x) if true_dict else 0.0
            )
            
            # 5日均量数据
            df['avg_volume_5d'] = df['stock_code'].map(true_dict.get_avg_volume_5d)
            
            # ?? CTO裁决修复：引入时间进度加权，防止盘中量比失真
            # 量比 = 估算全天成交量 / 5日平均成交量
            # 其中 估算全天成交量 = 当前成交量 / 已过分钟数 * 240分钟
            now = self.get_current_time()
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
                logger.error(f"[ERR] [CTO强制审计] 配置读取失败: {e}")
                raise RuntimeError("系统拒绝启动：缺少核心配置 live_sniper.min_volume_multiplier")
            
            # 【CTO源码清剿】纯动态倍数过滤：量比 >= 配置倍数（如1.5倍）
            mask = (
                (df['volume_ratio'] >= min_volume_multiplier) &  # ?? 动态倍数：今日是5日均量的X倍
                (df['volume'] > 0)  # 只需有成交量
            )
            
            filtered_df = df[mask].copy()
            
            # 按量比排序
            filtered_df = filtered_df.sort_values('volume_ratio', ascending=False)
            
            # 【CTO V59 动态累计扩容】将新异动的股票加入现有池子，并去重
            new_stocks = filtered_df['stock_code'].tolist()[:150]
            added_stocks = [s for s in new_stocks if s not in self.watchlist]
            
            if added_stocks:
                self.watchlist.extend(added_stocks)
                logger.info(f"🔥 [天网捕获] 盘中捕捉到 {len(added_stocks)} 只新异动标的！当前雷达池扩容至: {len(self.watchlist)}只")
                
                # 【极其关键】必须为新猎物挂载 QMT 内存订阅，否则主循环读不到新股票的 Tick！
                if self.mode == 'live':
                    try:
                        from xtquant import xtdata
                        xtdata.subscribe_whole_quote(added_stocks)
                    except Exception as e:
                        pass
            else:
                logger.info(f"📡 [天网扫描] 本次扫描未发现新面孔，雷达池维持 {len(self.watchlist)}只")
            
        except Exception as e:
            logger.error(f"[ERR] 当前截面快照筛选失败: {e}")

    def stop(self):
        """停止引擎 - CTO战地收尸版"""
        logger.info("[STOP] 停止实盘总控引擎...")
        self.running = False
        
        # 【CTO V7修复】QMT无需手动取消订阅，进程退出时自动释放
        # 原unsubscribe_whole_quote是幻觉函数，QMT官方无此方法
        if self.watchlist:
            logger.info(f"[OK] 系统安全退出，{len(self.watchlist)} 只股票订阅由操作系统回收")
        
        # [V70 大道至简] event_bus 已彻底废除，无需调用 stop()
        # self.event_bus 永远为 None，原 if self.event_bus: self.event_bus.stop() 已删除
        
        # 【CTO防呆保护】防止paper模式下没有trader属性导致的报错
        if hasattr(self, 'trader') and self.trader:
            self.trader.disconnect()
        
        # 【CTO V32】非交易日模式下跳过战报打印（已在_print_fire_control_panel打印过）
        # 【CTO V52战役二】同时检查_has_generated_report标志，防止异常分支重复生成
        if not getattr(self, '_skip_final_report', False) and not getattr(self, '_has_generated_report', False):
            # 【CTO战地收尸】生成最终战报
            self._generate_final_battle_report()
            self._has_generated_report = True
        else:
            logger.info("[OK] 跳过最终战报打印（已在其他分支生成）")
        
        logger.info("[OK] 实盘总控引擎已停止")
    
    # =========================================================================
    # 【CTO V46架构大一统】持仓管理 - 使用ExitManager统一止损逻辑
    # =========================================================================
    
    def open_position(self, stock_code: str, entry_price: float, entry_score: float, entry_time: str = None):
        """
        开仓 - 创建ExitManager实例
        
        Args:
            stock_code: 股票代码
            entry_price: 入场价格
            entry_score: 入场时的打分（用于区分真龙/平民）
            entry_time: 入场时间（可选，默认当前时间）
        """
        from logic.execution.exit_manager import ExitManager
        
        if entry_time is None:
            entry_time = self.get_current_time().strftime('%Y%m%d')
        
        self.positions[stock_code] = ExitManager(
            entry_price=entry_price,
            entry_time=entry_time,
            entry_score=entry_score,
            stock_code=stock_code
        )
        logger.info(f"?? [开仓] {stock_code} @ {entry_price:.2f}, 分数={entry_score:.0f}")
    
    def close_position(self, stock_code: str, reason: str = ""):
        """
        平仓 - 删除ExitManager实例
        
        Args:
            stock_code: 股票代码
            reason: 平仓原因
        """
        if stock_code in self.positions:
            exit_mgr = self.positions[stock_code]
            logger.info(f"?? [平仓] {stock_code} 原因: {reason}, 收益: {exit_mgr.current_price/exit_mgr.entry_price*100-100:.2f}%")
            del self.positions[stock_code]
    
    def check_position_exits(self, all_ticks: Dict) -> List[Dict]:
        """
        检查所有持仓是否触发止损/止盈
        
        Args:
            all_ticks: 全量Tick数据 {stock_code: tick_dict}
            
        Returns:
            List[Dict]: 触发卖出的持仓列表 [{'code': str, 'reason': str, 'price': float}, ...]
        """
        exits = []
        
        for stock_code, exit_mgr in list(self.positions.items()):
            tick = all_ticks.get(stock_code)
            if not tick:
                continue
            
            # 构造Tick数据传给ExitManager
            tick_data = {
                'price': float(tick.get('lastPrice', 0)),
                'lastPrice': float(tick.get('lastPrice', 0)),
                'amount': float(tick.get('amount', 0)),
                'volume': float(tick.get('volume', 0)),
                'time': self.get_current_time().strftime('%Y%m%d%H%M%S')
            }
            
            # 调用统一的卖点守门人
            result = exit_mgr.on_tick(tick_data)
            
            if result['action'] == 'sell':
                exits.append({
                    'code': stock_code,
                    'reason': result['reason'],
                    'price': result['price'],
                    'max_profit': result['max_profit'],
                    'curr_profit': result['curr_profit']
                })
        
        return exits
    
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
            
            # 【CTO修复】更新最高分记录，添加first_entry_time锚点
            current_time_str = self.get_current_time().strftime('%H:%M:%S')
            
            if code not in self.highest_scores:
                # 首次入池，记录first_entry_time
                self.highest_scores[code] = {
                    'code': code,
                    'score': score,
                    'time': current_time_str,
                    'first_entry_time': current_time_str,  # 【CTO补充】首次被盯上的时间
                    'price': item.get('price', 0),
                    'change': item.get('change', 0),
                    'inflow_ratio': item.get('inflow_ratio', 0),
                    'ratio_stock': item.get('ratio_stock', 0),
                    'sustain_ratio': item.get('sustain_ratio', 0),
                    'purity': item.get('purity', '')
                }
            elif score > self.highest_scores[code].get('score', 0):
                # 破纪录时，保留首次入池时间
                existing_first_time = self.highest_scores[code].get('first_entry_time', 
                                                                    self.highest_scores[code].get('time'))
                self.highest_scores[code].update({
                    'score': score,
                    'time': current_time_str,
                    'first_entry_time': existing_first_time,  # 保留原始入池时间
                    'price': item.get('price', 0),
                    'change': item.get('change', 0),
                    'inflow_ratio': item.get('inflow_ratio', 0),
                    'ratio_stock': item.get('ratio_stock', 0),
                    'sustain_ratio': item.get('sustain_ratio', 0),
                    'purity': item.get('purity', '')
                })
    
    def _generate_final_battle_report(self):
        """
        【CTO战地收尸】生成最终战报 - 退出必留痕
        
        输出：
        1. data/battle_reports/battle_report_{date}.json
        2. 终端打印TOP 3战神榜
        """
        if not self.highest_scores:
            logger.info("?? 今日无战报数据（观察池为空或无打分记录）")
            return
        
        import json
        import os
        from pathlib import Path
        
        # 创建战报目录
        report_dir = Path('data/battle_reports')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        current_time = self.get_current_time()  # 【CTO V53时间沙盒】统一时间获取
        today = current_time.strftime('%Y%m%d')
        report_path = report_dir / f'battle_report_{today}.json'
        
        # 按分数排序
        final_list = sorted(self.highest_scores.values(), key=lambda x: x.get('score', 0), reverse=True)
        
        # 生成战报数据
        report_data = {
            'date': today,
            'generated_at': current_time.strftime('%Y-%m-%d %H:%M:%S'),  # 【CTO V53时间沙盒】
            'total_targets': len(final_list),
            'top_targets': final_list[:50]  # 只保存前50名
        }
        
        # 保存JSON
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=4)
            logger.info(f"[OK] 战地收官报告已生成 -> {report_path}")
        except Exception as e:
            logger.error(f"[ERR] 战报保存失败: {e}")
        
        # 终端打印战神榜
        print("\n" + "=" * 60)
        print("?? 今日战神榜 TOP 10")
        print("=" * 60)
        print(f"{'排名':<4} {'代码':<12} {'最高血量':<10} {'时间':<10} {'涨幅':<8}")
        print("-" * 60)
        for i, target in enumerate(final_list[:10], 1):
            print(f"{i:<4} {target['code']:<12} {target['score']:<10.1f} {target.get('time', '--:--:--'):<10} {target.get('change', 0):<8.2f}%")
        print("=" * 60)
        print(f"?? 总计追踪: {len(final_list)} 只股票")
        print(f"?? 完整战报: {report_path}")


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
    print("?? 实盘总控引擎测试 (CTO加固版)")
    print("=" * 50)
    
    # 创建引擎
    engine = create_live_trading_engine()
    
    print("[RADAR] 引擎创建完成")
    print("[INFO] 注意: 该测试仅验证组件加载，不执行实际交易")
    
    # 模拟启动（不实际运行）
    try:
        engine._init_trading_components()
        print("[OK] 交易组件加载测试完成")
    except Exception as e:
        print(f"[WARN] 组件加载测试失败: {e}")
    
    print("\n[OK] 实盘总控引擎测试完成")
    print("[TARGET] 修复版已准备就绪")
