# -*- coding: utf-8 -*-
"""
【物理铁律单元测试】CTO V183 架构纠偏与量纲清洗

确定性测试：输入A必须输出B，不允许概率性结果。
这些物理定律已通过大样本验证，是系统核心城墙。

V183变更：
- 删除TestVelocityCubed（违背Law1无量纲化原则）
- 参数化extract_overdraft_multiplier测试

V184变更：
- 强制参数注入，禁止魔法默认值
- 精确断言替换弱断言

Author: CTO
Date: 2026-03-15
"""

import pytest
import math

from logic.core.physics_sensors import (
    extract_time_decay_factor,
    extract_dynamic_friction,
    extract_overdraft_multiplier,
)
from logic.core.config_manager import get_config_manager


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


class TestOverdraftMultiplier:
    """透支效应乘数测试"""
    
    @pytest.fixture(autouse=True)
    def setup_config(self):
        """从config读取参数"""
        cfg = get_config_manager()
        self.min_limit = cfg.get('kinetic_physics.overdraft_min_limit', 0.5)
        self.log_coeff = cfg.get('kinetic_physics.overdraft_log_coeff', 0.5)
    
    def test_normal_volume(self):
        """正常量比(1.0x): 无透支"""
        assert extract_overdraft_multiplier(1.0, self.min_limit, self.log_coeff) == 1.0
    
    def test_low_volume(self):
        """低量比(<1.0): 无透支"""
        assert extract_overdraft_multiplier(0.5, self.min_limit, self.log_coeff) == 1.0
    
    def test_moderate_overdraft(self):
        """中等透支(2.0x): 精确值约0.7614"""
        expected = max(self.min_limit, 1.0 - math.log10(1.0 + 2.0) * self.log_coeff)
        result = extract_overdraft_multiplier(2.0, self.min_limit, self.log_coeff)
        assert abs(result - expected) < 0.001
    
    def test_severe_overdraft(self):
        """严重透支(10.0x): 命中下界保护，精确等于min_limit"""
        result = extract_overdraft_multiplier(10.0, self.min_limit, self.log_coeff)
        assert result == self.min_limit
    
    def test_lower_bound_default(self):
        """下界保护: 精确等于min_limit"""
        result1 = extract_overdraft_multiplier(100.0, self.min_limit, self.log_coeff)
        result2 = extract_overdraft_multiplier(1000.0, self.min_limit, self.log_coeff)
        assert result1 == self.min_limit
        assert result2 == self.min_limit
    
    def test_monotonic_decreasing(self):
        """单调递减: 量比越高，乘数越低"""
        mult1 = extract_overdraft_multiplier(1.0, self.min_limit, self.log_coeff)
        mult2 = extract_overdraft_multiplier(5.0, self.min_limit, self.log_coeff)
        mult3 = extract_overdraft_multiplier(10.0, self.min_limit, self.log_coeff)
        assert mult1 >= mult2 >= mult3
    
    # ============== 参数化测试 ==============
    
    def test_custom_min_limit(self):
        """自定义下界: min_limit=0.3"""
        mult = extract_overdraft_multiplier(100.0, min_limit=0.3, log_coefficient=self.log_coeff)
        assert mult >= 0.3
        assert mult < 0.5  # 比默认0.5更低
    
    def test_custom_log_coefficient(self):
        """自定义对数系数: log_coefficient=0.8加速衰减"""
        mult_default = extract_overdraft_multiplier(5.0, self.min_limit, self.log_coeff)
        mult_faster = extract_overdraft_multiplier(5.0, self.min_limit, 0.8)
        assert mult_faster < mult_default  # 更大系数衰减更快
    
    def test_custom_params_combination(self):
        """自定义参数组合"""
        mult = extract_overdraft_multiplier(
            10.0,
            min_limit=0.2,
            log_coefficient=0.3
        )
        # 较小系数(0.3)衰减较慢，较低下界(0.2)允许更低值
        assert 0.2 <= mult < 1.0
    
    def test_missing_params_raises(self):
        """缺失参数必须抛出ValueError"""
        with pytest.raises(ValueError, match="必须由上层注入"):
            extract_overdraft_multiplier(5.0)  # 不传参数应该抛异常
        with pytest.raises(ValueError, match="必须由上层注入"):
            extract_overdraft_multiplier(5.0, min_limit=None, log_coefficient=self.log_coeff)
        with pytest.raises(ValueError, match="必须由上层注入"):
            extract_overdraft_multiplier(5.0, min_limit=self.min_limit, log_coefficient=None)