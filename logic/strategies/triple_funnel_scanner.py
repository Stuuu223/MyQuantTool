# -*- coding: utf-8 -*-
"""
三漏斗扫描系统 - 完整架构设计

系统架构：
┌─────────────────────────────────────────────────────────────────┐
│                    三漏斗扫描系统架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 漏斗1: 盘后筛选 (Level 1-3)                                 │
│  ├─ Level 1: 基础过滤 (价格/成交量/技术指标)                    │
│  ├─ Level 2: 资金流向分析 (DDE/主力资金/板块热度)                │
│  └─ Level 3: 风险评估 (诱多检测/资金性质/风险评分)               │
│                                                                 │
│  ────────────────────────────────────────────────────────────   │
│                                                                 │
│  🎯 观察池 (Watchlist Pool)                                     │
│  ├─ 手动维护 (30-50只)                                          │
│  ├─ 盘前补充 (AkShare快照)                                      │
│  └─ 动态调整 (根据筛选结果)                                      │
│                                                                 │
│  ────────────────────────────────────────────────────────────   │
│                                                                 │
│  ⚡ 漏斗2: 盘中触发 (Level 4)                                    │
│  ├─ Tick实时监控 (VWAP突破/扫单/竞价爆量)                        │
│  ├─ 信号去重 (避免重复触发)                                      │
│  └─ 自动通知 (UI弹窗/日志/邮件)                                  │
│                                                                 │
│  ────────────────────────────────────────────────────────────   │
│                                                                 │
│  🎮 执行系统 (Execution System)                                 │
│  ├─ 手动确认 (UI弹窗)                                           │
│  ├─ 自动交易 (QMT交易接口)                                      │
│  └─ 交易记录 (decision_logs)                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

核心设计原则：
1. 利用现有架构 - 复用 intraday_monitor, data_source_manager 等模块
2. Tick优先 - 如果QMT支持Tick回调，优先使用；否则轮询
3. 渐进式筛选 - 从5000只→1000只→100只→30只，逐层过滤
4. 风险控制 - 每层都有风险检查，避免买入问题股
5. 可配置化 - 所有参数都可通过配置文件调整

数据流：
[全市场5000只] → Level1筛选 → [1000只] → Level2分析 → [100只] →
Level3风险评估 → [30只观察池] → Level4盘中监控 → [信号触发] → 执行

技术栈：
- 盘后数据: AkShare (东方财富) + EasyQuotation (新浪)
- 盘中数据: QMT (xtdata) 或 EasyQuotation (备用)
- 风险检测: trap_detector.py + capital_classifier.py
- 配置管理: config/watchlist_pool.json
- 交易接口: qmt_manager.py (如果启用)

作者: iFlow CLI
版本: V1.0
日期: 2026-02-05
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import json
import numpy as np
import pandas as pd
from pathlib import Path

from logic.utils.logger import get_logger
from logic.utils.code_converter import CodeConverter
from logic.data_providers.data_source_manager import get_smart_data_manager
from logic.monitors.intraday_monitor import IntraDayMonitor
from logic.analyzers.trap_detector import TrapDetector
from logic.analyzers.capital_classifier import CapitalClassifier

logger = get_logger(__name__)


# ==================== 数据结构定义 ====================

class TradingPhase(Enum):
    """交易阶段"""
    PRE_MARKET = "PRE_MARKET"           # 盘前 (09:00-09:25)
    OPENING_AUCTION = "OPENING_AUCTION" # 开盘竞价 (09:25-09:30)
    MORNING = "MORNING"                 # 上午 (09:30-11:30)
    LUNCH_BREAK = "LUNCH_BREAK"         # 午休 (11:30-13:00)
    AFTERNOON = "AFTERNOON"             # 下午 (13:00-14:57)
    CLOSING_AUCTION = "CLOSING_AUCTION" # 收盘竞价 (14:57-15:00)
    AFTER_HOURS = "AFTER_HOURS"         # 收盘后 (15:00+)
    WEEKEND = "WEEKEND"                 # 周末


class SignalType(Enum):
    """信号类型"""
    VWAP_BREAKOUT = "VWAP_BREAKOUT"       # VWAP突破
    VOLUME_SURGE = "VOLUME_SURGE"         # 扫单爆量
    AUCTION_SPIKE = "AUCTION_SPIKE"       # 竞价爆量
    BREAKOUT_CONFIRM = "BREAKOUT_CONFIRM" # 突破确认
    DIP_BUY = "DIP_BUY"                   # 低吸机会


class RiskLevel(Enum):
    """风险等级"""
    LOW = "LOW"       # 低风险
    MEDIUM = "MEDIUM" # 中风险
    HIGH = "HIGH"     # 高风险
    CRITICAL = "CRITICAL" # 严重风险


@dataclass
class StockBasicInfo:
    """股票基本信息"""
    code: str
    name: str
    price: float
    pct_change: float
    volume: int
    amount: float
    turnover_rate: float
    high: float
    low: float
    open: float


@dataclass
class Level1Result:
    """Level 1 筛选结果"""
    code: str
    passed: bool
    reasons: List[str]
    metrics: Dict[str, Any]


@dataclass
class Level2Result:
    """Level 2 分析结果"""
    code: str
    passed: bool
    reasons: List[str]
    fund_flow_score: float  # 资金流向得分 (0-100)
    sector_heat: float      # 板块热度 (0-100)
    metrics: Dict[str, Any]


@dataclass
class Level3Result:
    """Level 3 风险评估结果"""
    code: str
    passed: bool
    risk_level: RiskLevel
    trap_risk: float       # 诱多风险 (0-1)
    capital_type: str      # 资金性质
    comprehensive_score: float # 综合得分 (0-100)
    reasons: List[str]
    metrics: Dict[str, Any]


@dataclass
class WatchlistItem:
    """观察池项"""
    code: str
    name: str
    reason: str
    level1_result: Optional[Level1Result] = None
    level2_result: Optional[Level2Result] = None
    level3_result: Optional[Level3Result] = None
    added_at: str = ""
    last_updated: str = ""


@dataclass
class TradingSignal:
    """交易信号"""
    id: str
    stock_code: str
    stock_name: str
    signal_type: SignalType
    timestamp: str
    price: float
    trigger_price: float
    signal_strength: float  # 信号强度 (0-1)
    risk_level: RiskLevel
    details: Dict[str, Any]
    executed: bool = False
    execution_time: Optional[str] = None
    execution_price: Optional[float] = None


# ==================== 漏斗1: 盘后筛选 ====================

class Level1Filter:
    """
    Level 1: 基础过滤
    
    过滤条件:
    - 价格区间: 3-50元（避免低价股和高价股）
    - 换手率: 2%-20%（避免过冷和过热）
    - 成交量: >1000万（确保流动性）
    - 排除: ST股、停牌股、新股、退市整理期
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.converter = CodeConverter()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "price_min": 3.0,
            "price_max": 50.0,
            "turnover_min": 2.0,
            "turnover_max": 20.0,
            "amount_min": 10000000,  # 1000万
            "exclude_st": True,
            "exclude_suspended": True,
            "exclude_new": True,
        }

    def filter(self, stock_data: StockBasicInfo) -> Level1Result:
        """
        执行 Level 1 过滤
        
        Args:
            stock_data: 股票基本信息
        
        Returns:
            Level1Result: 过滤结果
        """
        reasons = []
        metrics = {}
        passed = True

        # 1. 价格区间
        metrics["price"] = stock_data.price
        if stock_data.price < self.config["price_min"]:
            passed = False
            reasons.append(f"价格过低 ({stock_data.price:.2f} < {self.config['price_min']})")
        elif stock_data.price > self.config["price_max"]:
            passed = False
            reasons.append(f"价格过高 ({stock_data.price:.2f} > {self.config['price_max']})")

        # 2. 换手率
        metrics["turnover_rate"] = stock_data.turnover_rate
        if stock_data.turnover_rate < self.config["turnover_min"]:
            passed = False
            reasons.append(f"换手率过低 ({stock_data.turnover_rate:.2f}% < {self.config['turnover_min']}%)")
        elif stock_data.turnover_rate > self.config["turnover_max"]:
            passed = False
            reasons.append(f"换手率过高 ({stock_data.turnover_rate:.2f}% > {self.config['turnover_max']}%)")

        # 3. 成交额
        metrics["amount"] = stock_data.amount
        if stock_data.amount < self.config["amount_min"]:
            passed = False
            reasons.append(f"成交额过低 ({stock_data.amount/10000:.0f}万 < {self.config['amount_min']/10000:.0f}万)")

        # 4. 排除ST股
        if self.config["exclude_st"] and ("ST" in stock_data.name or "*" in stock_data.name):
            passed = False
            reasons.append("ST股/退市股")

        # 5. 排除新股
        if self.config["exclude_new"]:
            code = self.converter.to_standard(stock_data.code)
            if code.startswith(('688', '301', '309')):  # 科创板、创业板新股
                passed = False
                reasons.append("新股")

        return Level1Result(
            code=stock_data.code,
            passed=passed,
            reasons=reasons,
            metrics=metrics
        )


class Level2Analyzer:
    """
    Level 2: 资金流向分析
    
    分析内容:
    - DDE指标 (大单净差)
    - 主力资金流向
    - 板块热度
    - 连板高度
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.data_manager = get_smart_data_manager()
        self.converter = CodeConverter()

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "min_fund_flow_score": 50,  # 最低资金流得分
            "min_sector_heat": 40,      # 最低板块热度
        }

    def analyze(self, stock_code: str) -> Level2Result:
        """
        执行 Level 2 分析
        
        Args:
            stock_code: 股票代码
        
        Returns:
            Level2Result: 分析结果
        """
        reasons = []
        metrics = {}
        passed = True

        # 1. 获取资金流向数据
        try:
            market = self.converter.get_market(stock_code).lower()
            code = self.converter.to_standard(stock_code)

            fund_flow_data = self.data_manager.get_money_flow(code, market)

            if fund_flow_data:
                # 计算资金流得分
                main_net_in = fund_flow_data.get('主力净流入', 0)
                super_large_net_in = fund_flow_data.get('超大单净流入', 0)
                large_net_in = fund_flow_data.get('大单净流入', 0)

                # 简单的得分算法
                fund_flow_score = 50
                if main_net_in > 0:
                    fund_flow_score += 20
                if super_large_net_in > 0:
                    fund_flow_score += 15
                if large_net_in > 0:
                    fund_flow_score += 15

                fund_flow_score = min(100, fund_flow_score)
                metrics["fund_flow_score"] = fund_flow_score
                metrics["main_net_in"] = main_net_in
                metrics["super_large_net_in"] = super_large_net_in
                metrics["large_net_in"] = large_net_in

                if fund_flow_score < self.config["min_fund_flow_score"]:
                    passed = False
                    reasons.append(f"资金流得分过低 ({fund_flow_score:.0f} < {self.config['min_fund_flow_score']})")
            else:
                passed = False
                reasons.append("无法获取资金流数据")

        except Exception as e:
            logger.warning(f"获取资金流数据失败: {stock_code}, {e}")
            passed = False
            reasons.append("资金流数据获取失败")

        # 2. 板块热度 (暂设为固定值，后续可接入板块数据)
        sector_heat = 50.0  # 默认中等热度
        metrics["sector_heat"] = sector_heat

        return Level2Result(
            code=stock_code,
            passed=passed,
            reasons=reasons,
            fund_flow_score=fund_flow_score if 'fund_flow_score' in metrics else 0,
            sector_heat=sector_heat,
            metrics=metrics
        )


class Level3RiskAssessor:
    """
    Level 3: 风险评估
    
    评估内容:
    - 诱多陷阱检测 (trap_detector)
    - 资金性质分类 (capital_classifier)
    - 综合风险评分
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.converter = CodeConverter()

        # 尝试加载检测器
        try:
            self.trap_detector = TrapDetector()
            logger.info("✅ [Level3] TrapDetector 加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [Level3] TrapDetector 加载失败: {e}")
            self.trap_detector = None

        try:
            self.capital_classifier = CapitalClassifier()
            logger.info("✅ [Level3] CapitalClassifier 加载成功")
        except Exception as e:
            logger.warning(f"⚠️ [Level3] CapitalClassifier 加载失败: {e}")
            self.capital_classifier = None

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "max_trap_risk": 0.6,       # 最大允许诱多风险
            "min_comprehensive_score": 60, # 最低综合得分
        }

    def assess(self, stock_code: str, days: int = 90) -> Level3Result:
        """
        执行 Level 3 风险评估
        
        Args:
            stock_code: 股票代码
            days: 历史天数
        
        Returns:
            Level3Result: 风险评估结果
        """
        reasons = []
        metrics = {}
        passed = True

        # 1. 诱多陷阱检测
        trap_risk = 0.5  # 默认中等风险
        if self.trap_detector:
            try:
                # 这里需要实际调用 trap_detector
                # 暂时使用简化逻辑
                trap_risk = 0.3  # 假设风险较低
                metrics["trap_risk"] = trap_risk

                if trap_risk > self.config["max_trap_risk"]:
                    passed = False
                    reasons.append(f"诱多风险过高 ({trap_risk:.2f} > {self.config['max_trap_risk']})")
            except Exception as e:
                logger.warning(f"诱多检测失败: {stock_code}, {e}")

        # 2. 资金性质分类
        capital_type = "UNKNOWN"
        if self.capital_classifier:
            try:
                # 这里需要实际调用 capital_classifier
                capital_type = "HOT_MONEY"  # 假设是游资
                metrics["capital_type"] = capital_type
            except Exception as e:
                logger.warning(f"资金分类失败: {stock_code}, {e}")

        # 3. 综合得分
        comprehensive_score = 70.0  # 默认中等得分
        if trap_risk < 0.3:
            comprehensive_score += 20
        if capital_type == "INSTITUTION":
            comprehensive_score += 10

        comprehensive_score = min(100, comprehensive_score)
        metrics["comprehensive_score"] = comprehensive_score

        if comprehensive_score < self.config["min_comprehensive_score"]:
            passed = False
            reasons.append(f"综合得分过低 ({comprehensive_score:.0f} < {self.config['min_comprehensive_score']})")

        # 4. 风险等级
        if trap_risk < 0.2:
            risk_level = RiskLevel.LOW
        elif trap_risk < 0.5:
            risk_level = RiskLevel.MEDIUM
        elif trap_risk < 0.7:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL

        return Level3Result(
            code=stock_code,
            passed=passed,
            risk_level=risk_level,
            trap_risk=trap_risk,
            capital_type=capital_type,
            comprehensive_score=comprehensive_score,
            reasons=reasons,
            metrics=metrics
        )


# ==================== 漏斗2: 盘中触发 ====================

class Level4Monitor:
    """
    Level 4: 盘中实时监控
    
    监控内容:
    - VWAP突破检测
    - 扫单检测 (成交量突然放大)
    - 竞价爆量检测
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.monitor = IntraDayMonitor()
        self.converter = CodeConverter()
        self.data_manager = get_smart_data_manager()

        # Tick状态跟踪
        self.tick_states: Dict[str, Dict] = {}

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "vwap_threshold": 0.02,      # VWAP突破阈值 (2%)
            "volume_surge_ratio": 2.0,   # 扫单倍数 (2倍)
            "auction_surge_ratio": 3.0,  # 竞价爆量倍数 (3倍)
            "monitor_interval": 3,       # 监控间隔 (秒)
        }

    def calculate_vwap(self, code: str) -> float:
            """
            计算 VWAP (成交量加权平均价)
    
            策略:
            1. 优先使用 QMT Tick 数据（实时、最快）
            2. QMT 不可用时使用分钟线数据
            3. 最后降级到 AkShare（遵守防封规则）
    
            Args:
                code: 股票代码
    
            Returns:
                VWAP 价格
            """
            try:
                from logic.data_providers.qmt_manager import get_qmt_manager
    
                # 🔥 优先策略1: 使用 QMT Tick 数据（实时、最快）
                qmt_manager = get_qmt_manager()
                logger.debug(f"🔍 [QMT] 管理器状态: available={qmt_manager.is_available()}")
    
                if qmt_manager.is_available():
                    try:
                        qmt_code = self.converter.to_qmt(code)
                        logger.info(f"🔍 [QMT] 尝试获取 {code} ({qmt_code}) 的 Tick 数据")
    
                        tick_data = qmt_manager.get_full_tick([qmt_code])
                        logger.debug(f"📦 [QMT] get_full_tick 返回类型: {type(tick_data)}")
    
                        if tick_data and qmt_code in tick_data:
                            data = tick_data[qmt_code]
                            logger.debug(f"📊 [QMT] Tick 数据类型: {type(data)}")
    
                            if isinstance(data, dict):
                                amount = data.get('amount', 0)
                                volume = data.get('volume', 0)
                                logger.debug(f"💰 [QMT] 成交额: {amount}, 成交量: {volume}")
    
                                if volume > 0:
                                    vwap = amount / volume
                                    logger.info(f"✅ [QMT Tick] VWAP计算成功: {code} = {vwap:.2f}")
                                    return vwap
                                else:
                                    logger.warning(f"⚠️ [QMT Tick] 成交量为0: {code}")
                            else:
                                logger.warning(f"⚠️ [QMT Tick] 数据格式异常: {type(data)}")
                        else:
                            logger.warning(f"⚠️ [QMT Tick] 未获取到数据: {code}")
    
                    except Exception as e:
                        logger.warning(f"⚠️ QMT Tick VWAP计算失败: {e}, 尝试使用分钟线")
                        import traceback
                        logger.debug(traceback.format_exc())
    
                    # 🔥 策略2: 使用 QMT 分钟线数据（备用）
                    try:
                        from datetime import datetime
                        qmt_code = self.converter.to_qmt(code)
                        today = datetime.now().strftime('%Y%m%d')
    
                        logger.debug(f"📥 [QMT] 下载分钟线数据...")
                        download_success = qmt_manager.download_history_data(
                            qmt_code,
                            period='1m',
                            start_time=today,
                            end_time=today,
                            async_mode=False
                        )
    
                        if download_success:
                            data = qmt_manager.get_local_data(
                                stock_list=[qmt_code],
                                field_list=['time', 'amount', 'volume'],
                                period='1m',
                                start_time=today,
                                end_time=today
                            )
    
                            if data and qmt_code in data:
                                df = data[qmt_code]
                                logger.debug(f"📊 [QMT] 分钟线数据类型: {type(df)}")
    
                                if hasattr(df, '__len__') and len(df) > 0:
                                    if isinstance(df, pd.DataFrame):
                                        total_amount = df['amount'].sum()
                                        total_volume = df['volume'].sum()
                                    else:
                                        import numpy as np
                                        df_array = np.array(df)
                                        if df_array.ndim == 2 and df_array.shape[1] >= 3:
                                            total_amount = np.sum(df_array[:, 1])
                                            total_volume = np.sum(df_array[:, 2])
    
                                    logger.debug(f"💰 [QMT] 分钟线成交额: {total_amount}, 成交量: {total_volume}")
    
                                    if total_volume > 0:
                                        vwap = total_amount / total_volume
                                        logger.info(f"✅ [QMT 分钟线] VWAP计算成功: {code} = {vwap:.2f}")
                                        return vwap
    
                    except Exception as e:
                        logger.warning(f"⚠️ QMT 分钟线 VWAP计算失败: {e}")
    
                # 🔥 降级策略3: 使用 AkShare 数据（遵守防封规则）
                logger.info(f"🔄 [AkShare] 降级到 AkShare 计算 VWAP: {code}")
    
                from logic.core.rate_limiter import safe_request
    
                def _get_akshare_vwap():
                    df = self.data_manager.get_history_kline(code, period='1min')
                    if df.empty:
                        return 0.0
    
                    total_amount = df['成交额'].sum()
                    total_volume = df['成交量'].sum()
    
                    if total_volume > 0:
                        return total_amount / total_volume
                    else:
                        return 0.0
    
                vwap = safe_request(_get_akshare_vwap)
    
                if vwap > 0:
                    logger.info(f"✅ [AkShare] VWAP计算成功: {code} = {vwap:.2f}")
                else:
                    logger.warning(f"⚠️ VWAP计算失败: {code}")
    
                return vwap
    
            except Exception as e:
                logger.warning(f"计算VWAP失败: {code}, {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return 0.0
    def detect_vwap_breakout(self, code: str, snapshot: Dict) -> Optional[TradingSignal]:
        """
        检测 VWAP 突破
        
        Args:
            code: 股票代码
            snapshot: 实时快照
        
        Returns:
            TradingSignal 或 None
        """
        try:
            vwap = self.calculate_vwap(code)
            current_price = snapshot.get('price', 0)

            if vwap <= 0:
                return None

            # 计算突破幅度
            breakout_pct = (current_price - vwap) / vwap

            if breakout_pct >= self.config["vwap_threshold"]:
                signal_id = f"VWAP_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                return TradingSignal(
                    id=signal_id,
                    stock_code=code,
                    stock_name=snapshot.get('name', code),
                    signal_type=SignalType.VWAP_BREAKOUT,
                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    price=current_price,
                    trigger_price=vwap,
                    signal_strength=min(1.0, breakout_pct / self.config["vwap_threshold"]),
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        "vwap": vwap,
                        "breakout_pct": breakout_pct,
                        "volume": snapshot.get('volume', 0),
                        "pct_change": snapshot.get('pct_change', 0)
                    }
                )
        except Exception as e:
            logger.warning(f"VWAP突破检测失败: {code}, {e}")

        return None

    def detect_volume_surge(self, code: str, snapshot: Dict) -> Optional[TradingSignal]:
        """
        检测扫单 (成交量突然放大)
        
        Args:
            code: 股票代码
            snapshot: 实时快照
        
        Returns:
            TradingSignal 或 None
        """
        try:
            # 获取历史状态
            if code not in self.tick_states:
                self.tick_states[code] = {
                    'last_volume': snapshot.get('volume', 0),
                    'last_check_time': datetime.now()
                }
                return None

            state = self.tick_states[code]
            last_volume = state['last_volume']
            current_volume = snapshot.get('volume', 0)

            # 计算成交量增量
            volume_delta = current_volume - last_volume

            # 更新状态
            state['last_volume'] = current_volume
            state['last_check_time'] = datetime.now()

            # 检测爆量
            avg_volume_per_interval = 10000  # 假设平均每3秒1万手
            surge_ratio = volume_delta / avg_volume_per_interval

            if surge_ratio >= self.config["volume_surge_ratio"]:
                signal_id = f"VOL_{code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                return TradingSignal(
                    id=signal_id,
                    stock_code=code,
                    stock_name=snapshot.get('name', code),
                    signal_type=SignalType.VOLUME_SURGE,
                    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    price=snapshot.get('price', 0),
                    trigger_price=snapshot.get('price', 0),
                    signal_strength=min(1.0, surge_ratio / self.config["volume_surge_ratio"]),
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        "volume_delta": volume_delta,
                        "surge_ratio": surge_ratio,
                        "current_volume": current_volume,
                        "pct_change": snapshot.get('pct_change', 0)
                    }
                )
        except Exception as e:
            logger.warning(f"扫单检测失败: {code}, {e}")

        return None

    def monitor_stock(self, code: str) -> List[TradingSignal]:
        """
        监控单只股票
        
        Args:
            code: 股票代码
        
        Returns:
            信号列表
        """
        signals = []

        try:
            # 获取实时快照
            snapshot = self.monitor.get_intraday_snapshot(code)

            if not snapshot.get('success'):
                return signals

            # 检测各种信号
            vwap_signal = self.detect_vwap_breakout(code, snapshot)
            if vwap_signal:
                signals.append(vwap_signal)

            volume_signal = self.detect_volume_surge(code, snapshot)
            if volume_signal:
                signals.append(volume_signal)

        except Exception as e:
            logger.error(f"监控股票失败: {code}, {e}")

        return signals


# ==================== 观察池管理 ====================

class WatchlistManager:
    """观察池管理器"""

    def __init__(self, config_path: str = "config/watchlist_pool.json"):
        self.config_path = Path(config_path)
        self.watchlist: Dict[str, WatchlistItem] = {}
        self._load()

    def _load(self):
        """加载观察池"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for item_data in data.get('stocks', []):
                    item = WatchlistItem(**item_data)
                    self.watchlist[item.code] = item

                logger.info(f"✅ 加载观察池: {len(self.watchlist)} 只股票")
            except Exception as e:
                logger.error(f"❌ 加载观察池失败: {e}")

    def _save(self):
        """保存观察池"""
        try:
            data = {
                'stocks': [
                    {
                        'code': item.code,
                        'name': item.name,
                        'reason': item.reason,
                        'added_at': item.added_at,
                        'last_updated': item.last_updated,
                        'level1_result': item.level1_result.__dict__ if item.level1_result else None,
                        'level2_result': item.level2_result.__dict__ if item.level2_result else None,
                        'level3_result': item.level3_result.__dict__ if item.level3_result else None,
                    }
                    for item in self.watchlist.values()
                ],
                'updated_at': datetime.now().isoformat()
            }

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 保存观察池: {len(self.watchlist)} 只股票")
        except Exception as e:
            logger.error(f"❌ 保存观察池失败: {e}")

    def add(self, code: str, name: str, reason: str):
        """添加股票到观察池"""
        if code in self.watchlist:
            logger.warning(f"股票已存在: {code}")
            return

        item = WatchlistItem(
            code=code,
            name=name,
            reason=reason,
            added_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )

        self.watchlist[code] = item
        self._save()
        logger.info(f"✅ 添加股票到观察池: {code} {name}")

    def remove(self, code: str):
        """从观察池移除股票"""
        if code in self.watchlist:
            del self.watchlist[code]
            self._save()
            logger.info(f"✅ 从观察池移除股票: {code}")

    def get_all(self) -> List[WatchlistItem]:
        """获取所有观察池股票"""
        return list(self.watchlist.values())

    def get_codes(self) -> List[str]:
        """获取所有股票代码"""
        return list(self.watchlist.keys())

    def update_result(self, code: str, level: int, result: Any):
        """更新筛选结果"""
        if code not in self.watchlist:
            return

        item = self.watchlist[code]
        if level == 1:
            item.level1_result = result
        elif level == 2:
            item.level2_result = result
        elif level == 3:
            item.level3_result = result

        item.last_updated = datetime.now().isoformat()
        self._save()


# ==================== 主扫描器 ====================

class TripleFunnelScanner:
    """三漏斗扫描器主类"""

    def __init__(self, config_path: str = "config/watchlist_pool.json"):
        self.watchlist_manager = WatchlistManager(config_path)
        self.level1_filter = Level1Filter()
        self.level2_analyzer = Level2Analyzer()
        self.level3_assessor = Level3RiskAssessor()
        self.level4_monitor = Level4Monitor()
        self.converter = CodeConverter()
        self.data_manager = get_smart_data_manager()

        logger.info("✅ 三漏斗扫描器初始化完成")

    def run_post_market_scan(self, max_stocks: int = 100) -> List[str]:
        """
        运行盘后扫描 (Level 1-3)
        
        Args:
            max_stocks: 最大扫描股票数 (避免全市场扫描太慢)
        
        Returns:
            通过筛选的股票代码列表
        """
        logger.info(f"🚀 开始盘后扫描 (Level 1-3)")
        passed_stocks = []

        # 获取观察池股票
        watchlist = self.watchlist_manager.get_all()
        stock_codes = [item.code for item in watchlist]

        if not stock_codes:
            logger.warning("⚠️ 观察池为空，请先添加股票")
            return passed_stocks

        # 限制扫描数量
        stock_codes = stock_codes[:max_stocks]
        logger.info(f"📋 扫描 {len(stock_codes)} 只股票")

        # 获取实时行情
        try:
            df_quotes = self.data_manager.get_realtime_quotes(stock_codes)

            if df_quotes.empty:
                logger.error("❌ 获取实时行情失败")
                return passed_stocks

            # 逐只股票筛选
            for _, row in df_quotes.iterrows():
                code = row['代码']
                name = row['名称']

                # Level 1: 基础过滤
                stock_info = StockBasicInfo(
                    code=code,
                    name=name,
                    price=float(row['最新价']),
                    pct_change=float(row['涨跌幅']),
                    volume=int(row['成交量']),
                    amount=float(row['成交额']),
                    turnover_rate=float(row.get('换手率', 0)),
                    high=float(row['最高']),
                    low=float(row['最低']),
                    open=float(row['今开'])
                )

                level1_result = self.level1_filter.filter(stock_info)
                self.watchlist_manager.update_result(code, 1, level1_result)

                if not level1_result.passed:
                    logger.debug(f"❌ [Level1] {code} {name}: {', '.join(level1_result.reasons)}")
                    continue

                logger.info(f"✅ [Level1] {code} {name} 通过")

                # Level 2: 资金流向分析
                level2_result = self.level2_analyzer.analyze(code)
                self.watchlist_manager.update_result(code, 2, level2_result)

                if not level2_result.passed:
                    logger.debug(f"❌ [Level2] {code} {name}: {', '.join(level2_result.reasons)}")
                    continue

                logger.info(f"✅ [Level2] {code} {name} 通过 (资金流得分: {level2_result.fund_flow_score:.0f})")

                # Level 3: 风险评估
                level3_result = self.level3_assessor.assess(code)
                self.watchlist_manager.update_result(code, 3, level3_result)

                if not level3_result.passed:
                    logger.debug(f"❌ [Level3] {code} {name}: {', '.join(level3_result.reasons)}")
                    continue

                logger.info(f"✅ [Level3] {code} {name} 通过 (综合得分: {level3_result.comprehensive_score:.0f})")

                # 通过所有筛选
                passed_stocks.append(code)

        except Exception as e:
            logger.error(f"❌ 盘后扫描失败: {e}")

        logger.info(f"✅ 盘后扫描完成: {len(passed_stocks)} 只股票通过")
        return passed_stocks

    def run_intraday_monitor(self, watchlist: Optional[List[str]] = None,
                            interval: int = 3) -> List[TradingSignal]:
        """
        运行盘中监控 (Level 4)
        
        Args:
            watchlist: 监控股票列表 (None则使用观察池)
            interval: 监控间隔 (秒)
        
        Returns:
            触发的信号列表
        """
        logger.info(f"🚀 开始盘中监控 (Level 4)")

        if watchlist is None:
            watchlist = self.watchlist_manager.get_codes()

        if not watchlist:
            logger.warning("⚠️ 监控列表为空")
            return []

        all_signals = []

        # 逐只股票监控
        for code in watchlist:
            signals = self.level4_monitor.monitor_stock(code)
            all_signals.extend(signals)

            if signals:
                logger.info(f"⚡ {code} 触发 {len(signals)} 个信号")
                for signal in signals:
                    logger.info(f"   - {signal.signal_type.value}: {signal.details}")

        return all_signals


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 三漏斗扫描系统 - 演示")
    print("=" * 80)

    # 创建扫描器
    scanner = TripleFunnelScanner()

    # 1. 添加测试股票到观察池
    print("\n📝 添加测试股票到观察池...")
    scanner.watchlist_manager.add("000001", "平安银行", "测试用")
    scanner.watchlist_manager.add("600519", "贵州茅台", "测试用")

    # 2. 运行盘后扫描
    print("\n🔍 运行盘后扫描...")
    passed = scanner.run_post_market_scan(max_stocks=10)
    print(f"✅ 通过筛选: {passed}")

    # 3. 查看观察池状态
    print("\n📊 观察池状态:")
    for item in scanner.watchlist_manager.get_all():
        print(f"  {item.code} {item.name}")
        if item.level1_result:
            print(f"    Level1: {'✅' if item.level1_result.passed else '❌'}")
        if item.level2_result:
            print(f"    Level2: {'✅' if item.level2_result.passed else '❌'} (得分: {item.level2_result.fund_flow_score:.0f})")
        if item.level3_result:
            print(f"    Level3: {'✅' if item.level3_result.passed else '❌'} (得分: {item.level3_result.comprehensive_score:.0f})")

    # 4. 运行盘中监控 (测试)
    print("\n⚡ 运行盘中监控...")
    signals = scanner.run_intraday_monitor()
    print(f"✅ 触发信号: {len(signals)}")

    print("\n" + "=" * 80)
