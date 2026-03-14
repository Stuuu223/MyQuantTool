# -*- coding: utf-8 -*-
"""
MyQuantLab 工业级量化研究框架

架构：
├── data_collider.py    - 全息数据对撞机（多维时空切片器）
├── physics_sensors.py  - 物理特征提取矩阵
└── shannon_validator.py - 香农真理试金石

设计哲学：
1. 香农六把钥匙：降维、逆向思考、信息熵、冗余验证、边界条件、基础概率
2. 博弈论智猪效应：大猪出汗 vs 小猪白嫖
3. 非牛顿流体力学：盘口粘滞系数、剪切增稠

Author: CTO
Date: 2026-03-14
Version: V1.0
"""

from .data_collider import HolographicSample, DataCollider
from .physics_sensors import (
    extract_mfe,
    extract_volume_ratio,
    extract_acceleration,
    extract_purity,
    extract_non_newtonian_viscosity,
    extract_smart_pig_signal,
)
from .shannon_validator import ShannonValidator

__all__ = [
    'HolographicSample',
    'DataCollider',
    'extract_mfe',
    'extract_volume_ratio',
    'extract_acceleration',
    'extract_purity',
    'extract_non_newtonian_viscosity',
    'extract_smart_pig_signal',
    'ShannonValidator',
]
