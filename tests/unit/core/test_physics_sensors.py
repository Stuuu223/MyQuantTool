# -*- coding: utf-8 -*-
"""
【物理铁律单元测试】CTO V182 测试防线降维收编

确定性测试：输入A必须输出B，不允许概率性结果。
这些物理定律已通过大样本验证，是系统核心城墙。

Author: CTO
Date: 2026-03-15
"""

import pytest
import numpy as np

from research_lab.physics_sensors import (
    extract_time_decay_factor,
    extract_dynamic_friction,
    extract_velocity_cubed,
    extract_overdraft_multiplier,
)


class TestTimeDecayFactor:
    """时间衰减因子测试"""
    
    def test_early_morning_surge(self):
        """早盘冲刺期(0-10min): 1.2x放大"""
        assert abs(extract_time_decay_factor(0) - 1.2) < 0.01
        assert abs(extract_time_decay_factor(5) - 1.2) < 0.01
        assert abs(extract_time_decay_factor(9) - 1.2) < 0.01
    
    def test_morning_confirmation(self):
        """上午确认期(10-60min): 1.0x基准"""
        assert abs(extract_time_decay_factor(10) - 1.0) < 0.01
        assert abs(extract_time_decay_factor(30) - 1.0) < 0.01
        assert abs(extract_time_decay_factor(59) - 1.0) < 0.01
    
    def test_noon_trash(self):
        """午间垃圾时间(60-210min): 0.8x打折"""
        assert abs(extract_time_decay_factor(60) - 0.8) < 0.01
        assert abs(extract_time_decay_factor(120) - 0.8) < 0.01
        assert abs(extract_time_decay_factor(209) - 0.8) < 0.01
    
    def test_tail_trap(self):
        """尾盘陷阱期(210-240min): 0.2x腰斩"""
        assert abs(extract_time_decay_factor(210) - 0.2) < 0.01
        assert abs(extract_time_decay_factor(220) - 0.2) < 0.01
        assert abs(extract_time_decay_factor(240) - 0.2) < 0.01


class TestDynamicFriction:
    """时间动态阻尼场测试"""
    
    def test_early_morning_mild(self):
        """早盘: purity^2 温和阻尼"""
        purity = 0.8
        assert abs(extract_dynamic_friction(purity, 30) - purity ** 2) < 0.01
    
    def test_midday_moderate(self):
        """盘中: purity^3 中等阻尼"""
        purity = 0.8
        assert abs(extract_dynamic_friction(purity, 120) - purity ** 3) < 0.01
    
    def test_afternoon_severe(self):
        """午后: purity^5 极刑阻尼"""
        purity = 0.8
        assert abs(extract_dynamic_friction(purity, 220) - purity ** 5) < 0.01
    
    def test_gravitational_escape_exemption(self):
        """重力逃逸豁免: purity^1.5 温和"""
        purity = 0.8
        friction = extract_dynamic_friction(purity, 220, is_gravitational_escape=True)
        assert abs(friction - purity ** 1.5) < 0.01
    
    def test_boundary_protection(self):
        """边界保护: purity必须clip到[0,1]"""
        assert extract_dynamic_friction(1.5, 30) == 1.0  # 上界
        assert extract_dynamic_friction(-0.5, 30) == 0.0  # 下界


class TestVelocityCubed:
    """速度三次方测试"""
    
    def test_positive_velocity(self):
        """正涨幅: 3% → 27"""
        assert abs(extract_velocity_cubed(3.0) - 27.0) < 0.01
    
    def test_negative_velocity(self):
        """负涨幅: -5% → -125"""
        assert abs(extract_velocity_cubed(-5.0) - (-125.0)) < 0.01
    
    def test_nine_percent_vs_three_percent(self):
        """核心铁律: 涨幅9%是涨幅3%的27倍"""
        v9 = extract_velocity_cubed(9.0)
        v3 = extract_velocity_cubed(3.0)
        assert abs(v9 / v3 - 27.0) < 0.01
    
    def test_zero_velocity(self):
        """零涨幅: 0"""
        assert extract_velocity_cubed(0.0) == 0.0
    
    def test_small_change(self):
        """小涨幅: 1% → 1"""
        assert abs(extract_velocity_cubed(1.0) - 1.0) < 0.01
    
    def test_large_change(self):
        """大涨幅: 10% → 1000"""
        assert abs(extract_velocity_cubed(10.0) - 1000.0) < 0.01


class TestOverdraftMultiplier:
    """透支效应乘数测试"""
    
    def test_normal_volume(self):
        """正常量比(1.0x): 无透支"""
        assert extract_overdraft_multiplier(1.0) == 1.0
    
    def test_low_volume(self):
        """低量比(<1.0): 无透支"""
        assert extract_overdraft_multiplier(0.5) == 1.0
    
    def test_moderate_overdraft(self):
        """中等透支(2.0x): 轻微折扣"""
        mult = extract_overdraft_multiplier(2.0)
        assert 0.7 < mult < 1.0
    
    def test_severe_overdraft(self):
        """严重透支(10.0x): 明显折扣"""
        mult = extract_overdraft_multiplier(10.0)
        assert mult < 1.0  # 放量滞涨被折扣
    
    def test_lower_bound(self):
        """下界保护: 最低0.5"""
        mult = extract_overdraft_multiplier(100.0)
        assert mult >= 0.5
    
    def test_monotonic_decreasing(self):
        """单调递减: 量比越高，乘数越低"""
        mult1 = extract_overdraft_multiplier(1.0)
        mult2 = extract_overdraft_multiplier(5.0)
        mult3 = extract_overdraft_multiplier(10.0)
        assert mult1 >= mult2 >= mult3
