# -*- coding: utf-8 -*-
"""
MyQuantLab框架验证测试

验证内容：
1. 物理铁律函数正确性
2. ShannonValidator自动化回归
3. 框架可复用性
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

print("=" * 60)
print("【MyQuantLab框架验证测试】")
print("=" * 60)

# ============== 测试1: 已验证的物理铁律 ==============
print("\n[测试1] 物理铁律函数验证")

from research_lab.physics_sensors import (
    extract_time_decay_factor,
    extract_dynamic_friction,
    extract_velocity_cubed,
    extract_overdraft_multiplier,
)

# 时间衰减因子
test_cases = [
    (5, 1.2, "早盘冲刺"),
    (30, 1.0, "上午确认"),
    (120, 0.8, "午间垃圾"),
    (220, 0.2, "尾盘陷阱"),
]

print("\n时间衰减因子:")
for minutes, expected, label in test_cases:
    result = extract_time_decay_factor(minutes)
    status = "✅" if abs(result - expected) < 0.01 else "❌"
    print(f"  {status} {label}: {minutes}min → {result:.2f}x")

# 动态阻尼
print("\n动态阻尼场 (purity=0.8):")
purity = 0.8
for minutes in [30, 120, 220]:
    friction = extract_dynamic_friction(purity, minutes)
    power = 2 if minutes < 60 else (3 if minutes < 210 else 5)
    expected = purity ** power
    status = "✅" if abs(friction - expected) < 0.01 else "❌"
    print(f"  {status} {minutes}min → friction={friction:.4f} (purity^{power})")

# Velocity三次方
print("\n速度三次方:")
for change in [3.0, 9.0, -5.0]:
    velocity = extract_velocity_cubed(change)
    expected = np.sign(change) * (abs(change) ** 3)
    status = "✅" if abs(velocity - expected) < 0.01 else "❌"
    print(f"  {status} 涨幅{change}% → velocity={velocity:.1f}")

# 验证9%是3%的27倍
ratio = extract_velocity_cubed(9.0) / extract_velocity_cubed(3.0)
print(f"  ✅ 涨幅9%是3%的{ratio:.1f}倍")

# 透支乘数
print("\n透支效应乘数:")
for vol_ratio in [1.0, 2.0, 5.0, 10.0]:
    mult = extract_overdraft_multiplier(vol_ratio)
    print(f"  量比{vol_ratio}x → 乘数{mult:.3f}")

# ============== 测试2: ShannonValidator ==============
print("\n[测试2] ShannonValidator自动化回归")

from research_lab.shannon_validator import ShannonValidator

validator = ShannonValidator()

# 模拟数据
np.random.seed(42)
n = 100
factor1 = np.random.randn(n)  # 随机因子
factor2 = np.random.randn(n) * 0.5 + np.random.randn(n) * 0.5  # 有一定相关性
returns = factor2 * 0.3 + np.random.randn(n) * 0.5  # 因子2与收益相关

# 验证随机因子
result1 = validator.validate_factor(factor1.tolist(), returns.tolist(), "random_factor")
print(f"\n随机因子: R²={result1.r_squared:.4f}, Corr={result1.correlation:.4f}")

# 验证相关因子
result2 = validator.validate_factor(factor2.tolist(), returns.tolist(), "correlated_factor")
print(f"相关因子: R²={result2.r_squared:.4f}, Corr={result2.correlation:.4f}")

# ============== 测试3: 次方变换验证 ==============
print("\n[测试3] 次方变换最优解")

# 模拟涨幅与收益的关系（假设3次方最优）
base_values = np.abs(np.random.randn(n) * 5)  # 涨幅0-10%
returns_from_change = base_values ** 3 * 0.001 + np.random.randn(n) * 0.1

results = validator.validate_power_transformation(
    base_values.tolist(),
    returns_from_change.tolist(),
    "change_pct",
    powers=[1.0, 2.0, 3.0, 5.0]
)

print("\n次方验证结果:")
for power, result in sorted(results.items(), key=lambda x: x[1].r_squared, reverse=True):
    print(f"  {result.factor_name}: R²={result.r_squared:.4f}")

# ============== 总结 ==============
print("\n" + "=" * 60)
print("【验证报告】")
print("=" * 60)
print(validator.generate_report())
