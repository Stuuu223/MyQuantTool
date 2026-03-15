# -*- coding: utf-8 -*-
"""
【时间工具单元测试】CTO V184 午休时间轴修正

验证get_effective_minutes_from_open函数的正确性。
"""

import pytest
from datetime import datetime

from tasks.run_live_trading_engine import get_effective_minutes_from_open


class TestEffectiveMinutesFromOpen:
    """午休时间轴修正测试"""
    
    def test_before_lunch(self):
        """早盘时间：10:30 = 60分钟"""
        t = datetime(2026, 3, 15, 10, 30, 0)
        assert get_effective_minutes_from_open(t) == 60
    
    def test_lunch_start(self):
        """午休开始：11:30 = 120分钟（早盘结束）"""
        t = datetime(2026, 3, 15, 11, 30, 0)
        assert get_effective_minutes_from_open(t) == 120
    
    def test_during_lunch(self):
        """午休中：12:00 = 120分钟（保持早盘结束值）"""
        t = datetime(2026, 3, 15, 12, 0, 0)
        assert get_effective_minutes_from_open(t) == 120
    
    def test_after_lunch(self):
        """午后开盘：13:00 = 120分钟（扣90分钟后）"""
        t = datetime(2026, 3, 15, 13, 0, 0)
        assert get_effective_minutes_from_open(t) == 120
    
    def test_afternoon_30min(self):
        """午后30分钟：13:30 = 150分钟"""
        t = datetime(2026, 3, 15, 13, 30, 0)
        assert get_effective_minutes_from_open(t) == 150
    
    def test_afternoon_1hour(self):
        """午后1小时：14:00 = 180分钟"""
        t = datetime(2026, 3, 15, 14, 0, 0)
        assert get_effective_minutes_from_open(t) == 180
    
    def test_tail_trap_start(self):
        """尾盘陷阱开始：14:30 = 210分钟"""
        t = datetime(2026, 3, 15, 14, 30, 0)
        assert get_effective_minutes_from_open(t) == 210
    
    def test_market_close(self):
        """收盘：15:00 = 240分钟"""
        t = datetime(2026, 3, 15, 15, 0, 0)
        assert get_effective_minutes_from_open(t) == 240
    
    def test_market_open(self):
        """开盘：09:30 = 1分钟（最小值）"""
        t = datetime(2026, 3, 15, 9, 30, 0)
        assert get_effective_minutes_from_open(t) == 1
    
    def test_early_morning_10min(self):
        """早盘10分钟：09:40 = 10分钟"""
        t = datetime(2026, 3, 15, 9, 40, 0)
        assert get_effective_minutes_from_open(t) == 10
