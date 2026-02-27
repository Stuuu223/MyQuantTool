#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kinetic Engine - 微积分形态学与生命周期追踪系统 (V1.0)
职责：通过微积分形态学识别Stair(阶梯) vs Spike(尖刺)模式，追踪股票生命周期
Author: quant_dev
Date: 2026-02-27

核心功能:
1. StairDetector: 阶梯形态检测（稳健上涨）
2. SpikeDetector: 尖刺形态检测（诱多陷阱识别）
3. LifecycleTracker: 生命周期T_maintain追踪 + 黄金3分钟倒计时
"""

import time
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Tuple
import logging

try:
    from logic.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class MorphologyType(Enum):
    """形态类型枚举"""
    UNKNOWN = auto()
    STAIR = auto()      # 阶梯形态：稳健上涨
    SPIKE = auto()      # 尖刺形态：突然拉升
    TRAP = auto()       # 诱多陷阱：加速后回落
    SUSTAINED = auto()  # 持续形态：高位维持


class LifecyclePhase(Enum):
    """生命周期阶段"""
    EARLY = "early"         # 早期：起爆后0-3分钟
    MAINTAIN = "maintain"   # 维持期：高位震荡
    DECLINE = "decline"     # 衰退期：无法维持


@dataclass
class KineticSnapshot:
    """动力学快照数据"""
    timestamp: datetime
    price: float
    high: float
    delta_p: float = 0.0           # 一阶速度 (price change)
    delta2_p: float = 0.0          # 二阶加速度 (change of change)
    morphology: MorphologyType = MorphologyType.UNKNOWN
    trap_detected: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.strftime('%H:%M:%S'),
            'price': round(self.price, 3),
            'high': round(self.high, 3),
            'delta_p': round(self.delta_p, 4),
            'delta2_p': round(self.delta2_p, 4),
            'morphology': self.morphology.name,
            'trap_detected': self.trap_detected
        }


@dataclass
class LifecycleStatus:
    """生命周期状态报告"""
    stock_code: str
    phase: LifecyclePhase
    maintain_minutes: int
    sustain_ratio: float
    is_golden_3min: bool
    remaining_seconds: int
    burst_timestamp: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'stock_code': self.stock_code,
            'phase': self.phase.value,
            'maintain_minutes': self.maintain_minutes,
            'sustain_ratio': round(self.sustain_ratio, 3),
            'is_golden_3min': self.is_golden_3min,
            'remaining_seconds': self.remaining_seconds,
            'burst_time': self.burst_timestamp.strftime('%H:%M:%S') if self.burst_timestamp else None
        }


class StairDetector:
    """
    阶梯形态检测器 (Stair Pattern Detector)
    
    特征：
    - 价格稳步上涨，delta_p保持正值且波动小
    - 加速度delta2_p接近0（匀速上涨）
    - 无明显的负加速度拐点
    
    识别逻辑：
    - 连续3分钟delta_p > 0
    - abs(delta2_p) < 阈值（匀速特征）
    """
    
    def __init__(self, 
                 window_size: int = 3,
                 velocity_threshold: float = 0.01,
                 acceleration_tolerance: float = 0.005):
        """
        Args:
            window_size: 滚动窗口大小（分钟）
            velocity_threshold: 最小速度阈值（价格变化比例）
            acceleration_tolerance: 加速度容忍度（判断匀速的标准）
        """
        self.window_size = window_size
        self.velocity_threshold = velocity_threshold
        self.acceleration_tolerance = acceleration_tolerance
        
        # 线程安全的双端队列存储价格切片
        self._price_queue: deque = deque(maxlen=window_size + 1)
        self._time_queue: deque = deque(maxlen=window_size + 1)
        self._lock = threading.Lock()
        
        # 计算缓存（O(1)性能）
        self._last_velocity = 0.0
        self._last_acceleration = 0.0
        
    def update(self, timestamp: datetime, price: float) -> KineticSnapshot:
        """
        更新价格数据并计算动力学指标
        
        Args:
            timestamp: 当前时间戳
            price: 当前价格
            
        Returns:
            KineticSnapshot: 动力学快照
        """
        with self._lock:
            # 添加新数据点
            self._price_queue.append(price)
            self._time_queue.append(timestamp)
            
            # 计算一阶速度和二阶加速度
            delta_p, delta2_p = self._calculate_derivatives()
            
            # 识别形态
            morphology = self._detect_morphology(delta_p, delta2_p)
            
            snapshot = KineticSnapshot(
                timestamp=timestamp,
                price=price,
                high=max(self._price_queue) if self._price_queue else price,
                delta_p=delta_p,
                delta2_p=delta2_p,
                morphology=morphology
            )
            
            # 更新缓存
            self._last_velocity = delta_p
            self._last_acceleration = delta2_p
            
            return snapshot
    
    def _calculate_derivatives(self) -> Tuple[float, float]:
        """
        计算一阶速度和二阶加速度（微积分核心）
        
        Returns:
            Tuple[float, float]: (一阶速度, 二阶加速度)
        """
        n = len(self._price_queue)
        if n < 2:
            return 0.0, 0.0
        
        # 一阶速度：当前价格变化
        prices = list(self._price_queue)
        delta_p = prices[-1] - prices[-2]
        
        # 二阶加速度：速度的变化
        if n < 3:
            delta2_p = 0.0
        else:
            prev_delta_p = prices[-2] - prices[-3]
            delta2_p = delta_p - prev_delta_p
        
        return delta_p, delta2_p
    
    def _detect_morphology(self, delta_p: float, delta2_p: float) -> MorphologyType:
        """
        基于速度和加速度识别形态
        
        Args:
            delta_p: 一阶速度
            delta2_p: 二阶加速度
            
        Returns:
            MorphologyType: 识别的形态类型
        """
        # 速度为正且加速度接近0 -> 阶梯形态（稳健上涨）
        if delta_p > self.velocity_threshold and abs(delta2_p) < self.acceleration_tolerance:
            return MorphologyType.STAIR
        
        # 速度为正但负加速度很大 -> 尖刺形态（可能诱多）
        if delta_p > 0 and delta2_p < -self.acceleration_tolerance * 2:
            return MorphologyType.TRAP
        
        return MorphologyType.UNKNOWN
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态（线程安全）"""
        with self._lock:
            return {
                'window_size': self.window_size,
                'queue_length': len(self._price_queue),
                'last_velocity': round(self._last_velocity, 4),
                'last_acceleration': round(self._last_acceleration, 4),
                'prices': list(self._price_queue)
            }


class SpikeDetector:
    """
    尖刺形态与诱多陷阱检测器 (Spike & Trap Detector)
    
    核心逻辑：
    - 如果 delta_p > 阈值（突然拉升）
    - 随后 delta2_p < 负阈值（快速回落）
    - 则打上 TRAP 标签（诱多陷阱）
    
    这是典型的"脉冲式上涨"特征，常见于量化对倒诱多。
    """
    
    def __init__(self,
                 window_size: int = 3,
                 spike_velocity_threshold: float = 0.02,
                 trap_acceleration_threshold: float = -0.015,
                 cooldown_seconds: int = 60):
        """
        Args:
            window_size: 滚动窗口大小
            spike_velocity_threshold: 尖刺触发速度阈值（2%涨幅）
            trap_acceleration_threshold: 陷阱识别加速度阈值（负值）
            cooldown_seconds: 冷却时间（避免重复触发）
        """
        self.window_size = window_size
        self.spike_velocity_threshold = spike_velocity_threshold
        self.trap_acceleration_threshold = trap_acceleration_threshold
        self.cooldown_seconds = cooldown_seconds
        
        # 数据结构
        self._price_queue: deque = deque(maxlen=window_size + 2)
        self._velocity_history: deque = deque(maxlen=window_size)
        self._lock = threading.Lock()
        
        # 状态追踪
        self._last_trap_time: Optional[datetime] = None
        self._trap_count = 0
        self._consecutive_spikes = 0
        
    def update(self, timestamp: datetime, price: float) -> KineticSnapshot:
        """
        更新价格并检测尖刺/陷阱
        
        Args:
            timestamp: 当前时间戳
            price: 当前价格
            
        Returns:
            KineticSnapshot: 包含陷阱检测结果
        """
        with self._lock:
            # 添加新价格
            self._price_queue.append(price)
            
            # 计算速度和加速度
            delta_p, delta2_p = self._calculate_kinetics()
            
            # 检测陷阱
            is_trap = self._detect_trap(timestamp, delta_p, delta2_p)
            
            # 检测尖刺
            is_spike = self._detect_spike(delta_p)
            
            # 确定形态
            morphology = self._classify_morphology(delta_p, delta2_p, is_trap, is_spike)
            
            snapshot = KineticSnapshot(
                timestamp=timestamp,
                price=price,
                high=max(self._price_queue) if self._price_queue else price,
                delta_p=delta_p,
                delta2_p=delta2_p,
                morphology=morphology,
                trap_detected=is_trap
            )
            
            return snapshot
    
    def _calculate_kinetics(self) -> Tuple[float, float]:
        """计算动力学指标"""
        prices = list(self._price_queue)
        n = len(prices)
        
        if n < 2:
            return 0.0, 0.0
        
        # 一阶速度
        delta_p = prices[-1] - prices[-2]
        self._velocity_history.append(delta_p)
        
        # 二阶加速度
        if n < 3:
            delta2_p = 0.0
        else:
            prev_delta_p = prices[-2] - prices[-3]
            delta2_p = delta_p - prev_delta_p
        
        return delta_p, delta2_p
    
    def _detect_trap(self, timestamp: datetime, delta_p: float, delta2_p: float) -> bool:
        """
        诱多陷阱检测逻辑
        
        条件：
        1. 速度 > 阈值（突然拉升）
        2. 加速度 < 负阈值（快速回落）
        3. 不在冷却期内
        """
        # 检查冷却期
        if self._last_trap_time:
            elapsed = (timestamp - self._last_trap_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False
        
        # 核心陷阱识别逻辑
        is_trap = (
            delta_p > self.spike_velocity_threshold and 
            delta2_p < self.trap_acceleration_threshold
        )
        
        if is_trap:
            self._last_trap_time = timestamp
            self._trap_count += 1
            logger.warning(f"🚨 TRAP DETECTED! delta_p={delta_p:.4f}, delta2_p={delta2_p:.4f}")
        
        return is_trap
    
    def _detect_spike(self, delta_p: float) -> bool:
        """检测尖刺形态（单纯的速度突变）"""
        is_spike = delta_p > self.spike_velocity_threshold
        if is_spike:
            self._consecutive_spikes += 1
        else:
            self._consecutive_spikes = 0
        return is_spike
    
    def _classify_morphology(self, delta_p: float, delta2_p: float, 
                             is_trap: bool, is_spike: bool) -> MorphologyType:
        """分类形态类型"""
        if is_trap:
            return MorphologyType.TRAP
        if is_spike:
            return MorphologyType.SPIKE
        if delta_p > 0 and abs(delta2_p) < 0.001:
            return MorphologyType.SUSTAINED
        return MorphologyType.UNKNOWN
    
    def get_trap_statistics(self) -> Dict[str, Any]:
        """获取陷阱检测统计"""
        with self._lock:
            return {
                'total_traps_detected': self._trap_count,
                'consecutive_spikes': self._consecutive_spikes,
                'last_trap_time': self._last_trap_time.strftime('%H:%M:%S') if self._last_trap_time else None,
                'cooldown_active': self._last_trap_time is not None and 
                    (datetime.now() - self._last_trap_time).total_seconds() < self.cooldown_seconds
            }


class LifecycleTracker:
    """
    生命周期追踪器 (Lifecycle Tracker)
    
    功能：
    1. T_maintain追踪：记录股票在高位维持的时间
    2. 黄金3分钟倒计时：起爆后前3分钟的关键观察期
    
    规则：
    - maintain_minutes: 如果 current_price >= high * 0.98, 计数+1
    - 黄金3分钟: (current_time - burst_time) <= 3分钟 且 sustain_ratio < 1.2 -> False
    """
    
    def __init__(self, 
                 stock_code: str,
                 maintain_threshold: float = 0.98,
                 golden_minutes: int = 3,
                 sustain_ratio_threshold: float = 1.2):
        """
        Args:
            stock_code: 股票代码
            maintain_threshold: 维持阈值（相对高点的比例，默认98%）
            golden_minutes: 黄金观察期（分钟）
            sustain_ratio_threshold: 维持率阈值
        """
        self.stock_code = stock_code
        self.maintain_threshold = maintain_threshold
        self.golden_minutes = golden_minutes
        self.sustain_ratio_threshold = sustain_ratio_threshold
        
        # 状态变量
        self._maintain_minutes = 0
        self._burst_timestamp: Optional[datetime] = None
        self._current_high = 0.0
        self._sustain_count = 0
        self._total_checks = 0
        
        # 线程锁
        self._lock = threading.Lock()
        
    def record_burst(self, timestamp: datetime, price: float, high: float):
        """
        记录起爆点
        
        Args:
            timestamp: 起爆时间戳
            price: 起爆价格
            high: 当日最高
        """
        with self._lock:
            self._burst_timestamp = timestamp
            self._current_high = high
            self._maintain_minutes = 0
            self._sustain_count = 0
            self._total_checks = 0
            logger.info(f"📍 [{self.stock_code}] Burst recorded at {timestamp.strftime('%H:%M:%S')}, price={price}")
    
    def update(self, timestamp: datetime, current_price: float, current_high: float) -> LifecycleStatus:
        """
        更新生命周期状态
        
        Args:
            timestamp: 当前时间戳
            current_price: 当前价格
            current_high: 当前最高点
            
        Returns:
            LifecycleStatus: 生命周期状态
        """
        with self._lock:
            self._total_checks += 1
            self._current_high = max(self._current_high, current_high)
            
            # T_maintain追踪：价格维持在高点98%以上
            if current_price >= self._current_high * self.maintain_threshold:
                self._maintain_minutes += 1
                self._sustain_count += 1
            
            # 计算维持率
            sustain_ratio = self._sustain_count / self._total_checks if self._total_checks > 0 else 0.0
            
            # 黄金3分钟倒计时检查
            is_golden_3min = self._check_golden_3min(timestamp, sustain_ratio)
            
            # 确定生命周期阶段
            phase = self._determine_phase(timestamp, is_golden_3min, sustain_ratio)
            
            # 计算剩余秒数
            remaining_seconds = self._calculate_remaining_seconds(timestamp)
            
            return LifecycleStatus(
                stock_code=self.stock_code,
                phase=phase,
                maintain_minutes=self._maintain_minutes,
                sustain_ratio=sustain_ratio,
                is_golden_3min=is_golden_3min,
                remaining_seconds=remaining_seconds,
                burst_timestamp=self._burst_timestamp
            )
    
    def _check_golden_3min(self, timestamp: datetime, sustain_ratio: float) -> bool:
        """
        黄金3分钟检查
        
        逻辑：
        - 如果在起爆后3分钟内且维持率 < 1.2，返回False（不合格）
        - 否则返回True（通过黄金期检验）
        
        Returns:
            bool: 是否通过黄金3分钟检验
        """
        if not self._burst_timestamp:
            return False
        
        elapsed = (timestamp - self._burst_timestamp).total_seconds()
        in_golden_window = elapsed <= self.golden_minutes * 60
        
        if in_golden_window and sustain_ratio < self.sustain_ratio_threshold:
            # 在黄金期内但维持率不足 -> 不合格
            return False
        
        return True
    
    def _determine_phase(self, timestamp: datetime, 
                         is_golden_3min: bool, 
                         sustain_ratio: float) -> LifecyclePhase:
        """确定生命周期阶段"""
        if not self._burst_timestamp:
            return LifecyclePhase.EARLY
        
        elapsed_minutes = (timestamp - self._burst_timestamp).total_seconds() / 60
        
        # 早期阶段：起爆后前3分钟
        if elapsed_minutes <= self.golden_minutes:
            return LifecyclePhase.EARLY
        
        # 维持期：成功通过黄金3分钟检验且维持率高
        if is_golden_3min and sustain_ratio >= self.sustain_ratio_threshold:
            return LifecyclePhase.MAINTAIN
        
        # 衰退期：无法维持高位
        return LifecyclePhase.DECLINE
    
    def _calculate_remaining_seconds(self, timestamp: datetime) -> int:
        """计算黄金3分钟剩余秒数"""
        if not self._burst_timestamp:
            return 0
        
        elapsed_seconds = (timestamp - self._burst_timestamp).total_seconds()
        remaining = max(0, self.golden_minutes * 60 - int(elapsed_seconds))
        return remaining
    
    def get_maintain_status(self) -> Dict[str, Any]:
        """
        获取维持状态接口（外部调用）
        
        Returns:
            Dict包含维持分钟数、维持率、当前阶段等
        """
        with self._lock:
            sustain_ratio = self._sustain_count / self._total_checks if self._total_checks > 0 else 0.0
            
            return {
                'stock_code': self.stock_code,
                'maintain_minutes': self._maintain_minutes,
                'sustain_ratio': round(sustain_ratio, 3),
                'sustain_count': self._sustain_count,
                'total_checks': self._total_checks,
                'current_high': round(self._current_high, 3),
                'burst_timestamp': self._burst_timestamp.strftime('%H:%M:%S') if self._burst_timestamp else None
            }
    
    def is_qualified(self, timestamp: datetime, current_price: float) -> bool:
        """
        综合判断股票是否合格（通过生命周期检验）
        
        Args:
            timestamp: 当前时间
            current_price: 当前价格
            
        Returns:
            bool: 是否合格
        """
        status = self.update(timestamp, current_price, self._current_high)
        
        # 条件1：通过黄金3分钟检验
        if not status.is_golden_3min:
            return False
        
        # 条件2：维持率达标
        if status.sustain_ratio < self.sustain_ratio_threshold:
            return False
        
        # 条件3：不在衰退期
        if status.phase == LifecyclePhase.DECLINE:
            return False
        
        return True


class KineticEngine:
    """
    动力学引擎（统一入口）
    
    整合StairDetector、SpikeDetector、LifecycleTracker
    提供统一的分析接口
    """
    
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.stair_detector = StairDetector()
        self.spike_detector = SpikeDetector()
        self.lifecycle_tracker = LifecycleTracker(stock_code)
        
        # 历史记录
        self._snapshots: List[KineticSnapshot] = []
        self._max_history = 100
        
    def on_price_update(self, timestamp: datetime, price: float, high: float) -> Dict[str, Any]:
        """
        统一价格更新入口
        
        Args:
            timestamp: 时间戳
            price: 当前价格
            high: 当日最高
            
        Returns:
            综合分析结果
        """
        # 更新各检测器
        stair_snapshot = self.stair_detector.update(timestamp, price)
        spike_snapshot = self.spike_detector.update(timestamp, price)
        lifecycle_status = self.lifecycle_tracker.update(timestamp, price, high)
        
        # 保存快照
        self._snapshots.append(spike_snapshot)
        if len(self._snapshots) > self._max_history:
            self._snapshots.pop(0)
        
        # 综合判断
        is_safe = (
            spike_snapshot.morphology != MorphologyType.TRAP and
            lifecycle_status.is_golden_3min and
            lifecycle_status.phase != LifecyclePhase.DECLINE
        )
        
        return {
            'stock_code': self.stock_code,
            'timestamp': timestamp.strftime('%H:%M:%S'),
            'price': price,
            'is_safe': is_safe,
            'stair': stair_snapshot.to_dict(),
            'spike': {
                **spike_snapshot.to_dict(),
                'trap_stats': self.spike_detector.get_trap_statistics()
            },
            'lifecycle': lifecycle_status.to_dict(),
            'recommendation': self._generate_recommendation(spike_snapshot, lifecycle_status)
        }
    
    def record_burst(self, timestamp: datetime, price: float, high: float):
        """记录起爆点"""
        self.lifecycle_tracker.record_burst(timestamp, price, high)
    
    def _generate_recommendation(self, spike: KineticSnapshot, 
                                  lifecycle: LifecycleStatus) -> str:
        """生成交易建议"""
        if spike.trap_detected:
            return "🚫 AVOID: Trap detected - likely fake breakout"
        
        if not lifecycle.is_golden_3min:
            return "⏳ WAIT: Within golden 3min window, sustain ratio insufficient"
        
        if lifecycle.phase == LifecyclePhase.DECLINE:
            return "📉 PASS: Lifecycle in decline phase"
        
        if spike.morphology == MorphologyType.STAIR:
            return "✅ BUY: Stair pattern confirmed, lifecycle healthy"
        
        if lifecycle.phase == LifecyclePhase.MAINTAIN:
            return "✅ HOLD: In maintain phase, price stable"
        
        return "👀 WATCH: Monitoring..."


# ==========================================
# 使用示例 (Usage Examples)
# ==========================================

def example_usage():
    """完整使用示例"""
    print("=" * 60)
    print("Kinetic Engine - 微积分形态学与生命周期追踪")
    print("=" * 60)
    
    # 1. 创建引擎
    engine = KineticEngine("000001.SZ")
    
    # 2. 模拟价格数据（正常阶梯上涨）
    print("\n【场景1：阶梯形态上涨】")
    base_time = datetime.now()
    prices = [10.0, 10.05, 10.12, 10.18, 10.25]  # 稳步上涨
    
    for i, price in enumerate(prices):
        ts = base_time + timedelta(minutes=i)
        result = engine.on_price_update(ts, price, max(prices[:i+1]))
        print(f"  {result['timestamp']}: Price={price:.2f} | "
              f"Morphology={result['spike']['morphology']} | "
              f"Δp={result['spike']['delta_p']:.4f} | "
              f"Δ²p={result['spike']['delta2_p']:.4f}")
    
    # 3. 模拟诱多陷阱
    print("\n【场景2：诱多陷阱识别】")
    trap_engine = KineticEngine("000002.SZ")
    trap_prices = [10.0, 10.20, 10.35, 10.15, 10.05]  # 突然拉升后快速回落
    
    for i, price in enumerate(trap_prices):
        ts = base_time + timedelta(minutes=i)
        result = trap_engine.on_price_update(ts, price, max(trap_prices[:i+1]))
        trap_flag = "🚨 TRAP!" if result['spike']['trap_detected'] else ""
        print(f"  {result['timestamp']}: Price={price:.2f} | "
              f"Δp={result['spike']['delta_p']:.4f} | "
              f"Δ²p={result['spike']['delta2_p']:.4f} {trap_flag}")
    
    # 4. 生命周期追踪演示
    print("\n【场景3：生命周期追踪 + 黄金3分钟】")
    lifecycle_engine = KineticEngine("000003.SZ")
    
    # 记录起爆点
    burst_time = base_time
    lifecycle_engine.record_burst(burst_time, 10.0, 10.0)
    
    # 模拟黄金3分钟内的价格变化
    golden_prices = [
        (0, 10.0),    # 起爆
        (1, 10.15),   # 第1分钟
        (2, 10.25),   # 第2分钟
        (3, 10.30),   # 第3分钟（临界点）
        (4, 10.28),   # 第4分钟（维持）
        (5, 10.15),   # 第5分钟（回落）
    ]
    
    for minute, price in golden_prices:
        ts = burst_time + timedelta(minutes=minute)
        result = lifecycle_engine.on_price_update(ts, price, 10.30)
        lifecycle = result['lifecycle']
        print(f"  T+{minute}min: Price={price:.2f} | Phase={lifecycle['phase']} | "
              f"Golden3min={lifecycle['is_golden_3min']} | "
              f"Maintain={lifecycle['maintain_minutes']}min | "
              f"Sustain={lifecycle['sustain_ratio']:.2f}")
    
    # 5. 综合建议
    print("\n【综合交易建议】")
    final_result = lifecycle_engine.on_price_update(
        burst_time + timedelta(minutes=5), 10.15, 10.30
    )
    print(f"  股票: {final_result['stock_code']}")
    print(f"  安全: {'✅' if final_result['is_safe'] else '❌'}")
    print(f"  建议: {final_result['recommendation']}")
    
    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)


if __name__ == "__main__":
    example_usage()
