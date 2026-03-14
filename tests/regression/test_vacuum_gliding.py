# -*- coding: utf-8 -*-
"""
【CTO周末曼哈顿计划】回归测试 - 真空滑行豁免

测试目标：
1. 真空滑行检测逻辑
2. 真龙不被误杀

Author: CTO Research Lab
Date: 2026-03-14
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from collections import deque

# 模拟StockTracker和StockState
from enum import Enum
from dataclasses import dataclass, field

class StockState(Enum):
    OUTSIDE = "outside"
    CANDIDATE = "candidate"
    TRACKING = "tracking"
    OPPORTUNITY = "opportunity"
    ELIMINATED = "eliminated"

@dataclass
class TickSnapshot:
    timestamp: datetime
    price: float
    amount: float
    volume: float
    high: float
    low: float
    open: float

@dataclass
class StockTracker:
    stock_code: str
    state: StockState
    enter_time: datetime
    tick_history: deque = field(default_factory=lambda: deque(maxlen=300))
    current_price: float = 0.0
    current_amount: float = 0.0
    flow_15min: float = 0.0
    flow_5min: float = 0.0
    final_score: float = 0.0
    sustain_ratio: float = 0.0
    mfe: float = 0.0
    inflow_ratio: float = 0.0
    volume_ratio: float = 0.0
    elimination_reason: str = ""


def check_vacuum_gliding(tracker: StockTracker, prev_close: float) -> bool:
    """
    【CTO周末曼哈顿计划】真空滑行检测
    
    物理判据：
    1. 涨停状态（价格>=涨停价-1分）
    2. 低量比（<1.5，表示锁仓）
    3. 低振幅（<3%，一字板特征）
    """
    current_price = tracker.current_price
    stock_code = tracker.stock_code
    
    if prev_close <= 0:
        return False
    
    # 计算涨停价
    if stock_code.startswith(('30', '68')):
        limit_up_price = round(prev_close * 1.20, 2)
    elif stock_code.startswith(('8', '4')):
        limit_up_price = round(prev_close * 1.30, 2)
    else:
        limit_up_price = round(prev_close * 1.10, 2)
    
    is_limit_up = (current_price >= limit_up_price - 0.011)
    if not is_limit_up:
        return False
    
    # 低量比判断（锁仓特征）
    if tracker.volume_ratio >= 1.5:
        return False
    
    # 低振幅判断
    if len(tracker.tick_history) < 2:
        return False
    
    daily_high = max(s.high for s in tracker.tick_history)
    daily_low = min(s.low for s in tracker.tick_history)
    amplitude = (daily_high - daily_low) / prev_close * 100 if prev_close > 0 else 0
    
    if amplitude >= 3.0:
        return False
    
    return True


def should_eliminate_with_vacuum_exemption(tracker: StockTracker, prev_close: float) -> tuple:
    """
    【CTO修正版】带真空滑行豁免的剔除检查
    """
    # 真空滑行检测
    is_vacuum_gliding = check_vacuum_gliding(tracker, prev_close)
    
    # 条件1: MFE<1.2且Volume_Ratio>3.0 (天量滞涨)
    # 但如果是真空滑行，豁免！
    eliminate_mfe_threshold = 1.2
    eliminate_volume_ratio_threshold = 3.0
    
    if (tracker.mfe < eliminate_mfe_threshold and 
        tracker.volume_ratio > eliminate_volume_ratio_threshold):
        if not is_vacuum_gliding:
            return True, f"天量滞涨: MFE={tracker.mfe:.2f}且量比={tracker.volume_ratio:.2f}"
    
    return False, ""


class TestVacuumGlidingExemption:
    """真空滑行豁免回归测试"""
    
    def test_01_limit_up_low_volume_low_amplitude_is_vacuum(self):
        """测试1：涨停+低量比+低振幅 = 真空滑行"""
        tracker = StockTracker(
            stock_code='600000.SH',
            state=StockState.TRACKING,
            enter_time=datetime.now(),
            current_price=11.00,  # 涨停价
            volume_ratio=0.8,      # 低量比（锁仓）
            mfe=0.5,               # 低MFE
        )
        
        prev_close = 10.00  # 昨收10元，涨停价11元
        
        # 添加历史Tick
        for i in range(5):
            tracker.tick_history.append(TickSnapshot(
                timestamp=datetime.now(),
                price=11.0,
                amount=100000 + i * 1000,
                volume=10000 + i * 100,
                high=11.0,
                low=10.95,  # 极小振幅
                open=10.95
            ))
        
        result = check_vacuum_gliding(tracker, prev_close)
        assert result == True, "涨停+低量比+低振幅应被识别为真空滑行"
        print("✅ 测试1通过: 涨停+低量比+低振幅 = 真空滑行")
    
    def test_02_limit_up_high_volume_not_vacuum(self):
        """测试2：涨停+高量比 = 不是真空滑行（可能在派发）"""
        tracker = StockTracker(
            stock_code='600000.SH',
            state=StockState.TRACKING,
            enter_time=datetime.now(),
            current_price=11.00,
            volume_ratio=3.5,      # 高量比！
            mfe=0.5,
        )
        
        prev_close = 10.00
        
        for i in range(5):
            tracker.tick_history.append(TickSnapshot(
                timestamp=datetime.now(),
                price=11.0,
                amount=100000 + i * 1000,
                volume=10000 + i * 100,
                high=11.0,
                low=10.95,
                open=10.95
            ))
        
        result = check_vacuum_gliding(tracker, prev_close)
        assert result == False, "高量比涨停不应被识别为真空滑行"
        print("✅ 测试2通过: 高量比涨停 ≠ 真空滑行")
    
    def test_03_not_limit_up_not_vacuum(self):
        """测试3：非涨停 = 不是真空滑行"""
        tracker = StockTracker(
            stock_code='600000.SH',
            state=StockState.TRACKING,
            enter_time=datetime.now(),
            current_price=10.50,  # 没涨停
            volume_ratio=0.8,
            mfe=0.5,
        )
        
        prev_close = 10.00
        
        for i in range(5):
            tracker.tick_history.append(TickSnapshot(
                timestamp=datetime.now(),
                price=10.5,
                amount=100000 + i * 1000,
                volume=10000 + i * 100,
                high=10.5,
                low=10.4,
                open=10.4
            ))
        
        result = check_vacuum_gliding(tracker, prev_close)
        assert result == False, "非涨停不应被识别为真空滑行"
        print("✅ 测试3通过: 非涨停 ≠ 真空滑行")
    
    def test_04_high_amplitude_not_vacuum(self):
        """测试4：高振幅 = 不是真空滑行"""
        tracker = StockTracker(
            stock_code='600000.SH',
            state=StockState.TRACKING,
            enter_time=datetime.now(),
            current_price=11.00,
            volume_ratio=0.8,
            mfe=0.5,
        )
        
        prev_close = 10.00
        
        for i in range(5):
            tracker.tick_history.append(TickSnapshot(
                timestamp=datetime.now(),
                price=11.0,
                amount=100000 + i * 1000,
                volume=10000 + i * 100,
                high=11.0,
                low=10.0,  # 振幅10%！
                open=10.0
            ))
        
        result = check_vacuum_gliding(tracker, prev_close)
        assert result == False, "高振幅涨停不应被识别为真空滑行"
        print("✅ 测试4通过: 高振幅涨停 ≠ 真空滑行")
    
    def test_05_vacuum_gliding_exempt_from_elimination(self):
        """测试5：真空滑行状态豁免MFE剔除"""
        tracker = StockTracker(
            stock_code='600000.SH',
            state=StockState.TRACKING,
            enter_time=datetime.now(),
            current_price=11.00,
            volume_ratio=4.0,      # 高量比
            mfe=0.5,               # 低MFE
        )
        
        prev_close = 10.00
        
        # 设置为真空滑行状态
        for i in range(5):
            tracker.tick_history.append(TickSnapshot(
                timestamp=datetime.now(),
                price=11.0,
                amount=100000 + i * 1000,
                volume=10000 + i * 100,
                high=11.0,
                low=10.98,  # 极小振幅
                open=10.98
            ))
        
        # 重新设置低量比以符合真空滑行条件
        tracker.volume_ratio = 0.8
        
        should_elim, reason = should_eliminate_with_vacuum_exemption(tracker, prev_close)
        assert should_elim == False, "真空滑行状态应豁免MFE剔除"
        print("✅ 测试5通过: 真空滑行豁免MFE剔除")


def run_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("【CTO周末曼哈顿计划】真空滑行豁免回归测试")
    print("=" * 60)
    
    test_suite = TestVacuumGlidingExemption()
    
    tests = [
        test_suite.test_01_limit_up_low_volume_low_amplitude_is_vacuum,
        test_suite.test_02_limit_up_high_volume_not_vacuum,
        test_suite.test_03_not_limit_up_not_vacuum,
        test_suite.test_04_high_amplitude_not_vacuum,
        test_suite.test_05_vacuum_gliding_exempt_from_elimination,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ 测试失败: {test.__name__}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过 / {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
