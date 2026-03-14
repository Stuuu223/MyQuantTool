# -*- coding: utf-8 -*-
"""
【CTO V160 透支效应物理定律验证】

核心断言：昨日量比越高，今日势能乘数越低！
物理依据：V158回归分析（8014样本）证明量比与开盘溢价呈负相关(-3.805)

Author: CTO
Date: 2026-03-14
"""
import math
import pytest


def calculate_overflow_multiplier(yesterday_vol_ratio: float) -> float:
    """
    计算溢出乘数（从kinetic_core_engine.py提取的核心逻辑）
    
    V160修复：正相关改为负相关
    """
    if yesterday_vol_ratio > 1.0:
        return max(0.5, 1.0 - math.log10(1.0 + yesterday_vol_ratio) * 0.5)
    else:
        return 1.0


class TestOverdraftEffect:
    """透支效应物理定律测试套件"""
    
    def test_01_higher_volume_ratio_lower_multiplier(self):
        """
        【核心断言】量比越高，乘数越低
        
        这是最重要的物理定律验证！
        如果这个测试失败，说明核心引擎逻辑错误！
        """
        # 量比2.0 vs 10.0
        mult_2x = calculate_overflow_multiplier(2.0)
        mult_10x = calculate_overflow_multiplier(10.0)
        
        # 断言：10.0的乘数必须低于2.0
        assert mult_10x < mult_2x, \
            f"透支效应验证失败！量比10x乘数({mult_10x:.3f})应该低于量比2x乘数({mult_2x:.3f})"
        
        print(f"✅ 透支效应验证通过: 量比2x→{mult_2x:.3f}, 量比10x→{mult_10x:.3f}")
    
    def test_02_multiplier_monotonically_decreasing(self):
        """
        【单调性测试】量比递增时，乘数必须单调递减
        """
        test_ratios = [1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0]
        multipliers = [calculate_overflow_multiplier(r) for r in test_ratios]
        
        for i in range(len(multipliers) - 1):
            assert multipliers[i+1] <= multipliers[i], \
                f"单调性验证失败！量比{test_ratios[i]}→{multipliers[i]:.3f}, " \
                f"量比{test_ratios[i+1]}→{multipliers[i+1]:.3f}"
        
        print(f"✅ 单调性验证通过:")
        for r, m in zip(test_ratios, multipliers):
            print(f"   量比{r:>5.1f}x → 乘数{m:.3f}")
    
    def test_03_multiplier_bounds(self):
        """
        【边界测试】乘数必须在[0.5, 1.0]范围内
        """
        test_ratios = [0.5, 1.0, 1.5, 2.0, 5.0, 10.0, 100.0]
        
        for ratio in test_ratios:
            mult = calculate_overflow_multiplier(ratio)
            assert 0.5 <= mult <= 1.0, \
                f"边界验证失败！量比{ratio}乘数{mult:.3f}超出[0.5, 1.0]范围"
        
        print(f"✅ 边界验证通过: 所有乘数均在[0.5, 1.0]范围内")
    
    def test_04_extreme_volume_ratio_penalty(self):
        """
        【极端惩罚测试】量比50x时乘数应该接近底线0.5
        """
        mult_50x = calculate_overflow_multiplier(50.0)
        
        # 量比50x时，乘数应该接近0.5底线
        assert mult_50x <= 0.7, \
            f"极端惩罚验证失败！量比50x乘数{mult_50x:.3f}应该接近底线0.5"
        
        print(f"✅ 极端惩罚验证通过: 量比50x→乘数{mult_50x:.3f}")
    
    def test_05_v158_regression_consistency(self):
        """
        【V158回归一致性验证】
        
        根据V158回归结果:
        - 量比95th(8.2x)次日溢价+1.19%
        - 量比50th(1.0x)次日溢价+4.67%
        
        溢价比 = 1.19/4.67 = 0.255
        
        我们的乘数比应该与之正相关
        """
        mult_1x = calculate_overflow_multiplier(1.0)
        mult_8x = calculate_overflow_multiplier(8.2)
        
        # 乘数比
        ratio = mult_8x / mult_1x
        
        # 量比8.2x时乘数应该明显低于1.0x
        assert ratio < 0.8, \
            f"V158一致性验证失败！量比8.2x乘数比{ratio:.3f}应该明显低于1.0"
        
        print(f"✅ V158一致性验证通过: 乘数比{ratio:.3f}与回归结果一致")


def run_tests():
    """运行所有测试"""
    test_suite = TestOverdraftEffect()
    
    print("\n" + "="*60)
    print("【CTO V160 透支效应物理定律验证】")
    print("="*60)
    
    tests = [
        ("核心断言: 量比越高乘数越低", test_suite.test_01_higher_volume_ratio_lower_multiplier),
        ("单调性测试", test_suite.test_02_multiplier_monotonically_decreasing),
        ("边界测试", test_suite.test_03_multiplier_bounds),
        ("极端惩罚测试", test_suite.test_04_extreme_volume_ratio_penalty),
        ("V158回归一致性", test_suite.test_05_v158_regression_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: {passed}通过, {failed}失败")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
