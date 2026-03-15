# -*- coding: utf-8 -*-
"""
【MyQuantLab 探索性验证框架】

⚠️ 此文件仅供手动触发执行，禁止被pytest自动发现！
确定性测试已迁移至 tests/unit/core/test_physics_sensors.py

保留功能：
- ShannonValidator: 探索性因子验证
- 次方变换最优解: 数据驱动的参数寻优

Author: CTO
Date: 2026-03-15
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np


def run_exploratory_validation():
    """
    探索性验证实验
    
    ⚠️ 此函数包含随机数据生成，仅限手动触发！
    """
    print("=" * 60)
    print("【MyQuantLab探索性验证】")
    print("=" * 60)
    
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
    
    # 次方变换验证
    print("\n[次方变换最优解]")
    
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
    
    # 总结
    print("\n" + "=" * 60)
    print("【验证报告】")
    print("=" * 60)
    print(validator.generate_report())


if __name__ == "__main__":
    # ⚠️ 仅在直接运行时执行，禁止被import触发
    run_exploratory_validation()