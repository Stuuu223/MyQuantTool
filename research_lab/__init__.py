# -*- coding: utf-8 -*-
"""
MyQuantLab 工业级量化研究框架

架构：
├── data_collider.py    - 全息数据对撞机（多维时空切片器）
├── shannon_validator.py - 香农真理试金石
└── validate_framework.py - 探索性验证脚本

⚠️ physics_sensors.py 已晋升至 logic/core/physics_sensors.py
   - 确定性物理铁律已进入核心城墙
   - 引用路径: from logic.core.physics_sensors import ...

设计哲学：
1. 香农六把钥匙：降维、逆向思考、信息熵、冗余验证、边界条件、基础概率
2. 博弈论智猪效应：大猪出汗 vs 小猪白嫖
3. 非牛顿流体力学：盘口粘滞系数、剪切增稠

Author: CTO
Date: 2026-03-14
Version: V1.1 (V183架构纠偏)
"""

from .data_collider import HolographicSample, DataCollider
from .shannon_validator import ShannonValidator

__all__ = [
    'HolographicSample',
    'DataCollider',
    'ShannonValidator',
]