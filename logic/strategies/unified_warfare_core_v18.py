#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一战法核心V18 - 兼容性转发模块

⚠️ 弃用警告: 此模块已迁移至 logic.strategies.production.unified_warfare_core
请更新导入路径:
    from logic.strategies.production.unified_warfare_core import UnifiedWarfareCoreV18
"""

import warnings

warnings.warn(
    "unified_warfare_core_v18 已弃用，"
    "请使用 logic.strategies.production.unified_warfare_core",
    DeprecationWarning,
    stacklevel=2
)

# 转发导入
from logic.strategies.production.unified_warfare_core import (
    UnifiedWarfareCoreV18,
    DailyVolumeAnchor,
    CrossDayRelayEngine,
    ShortTermMemory
)

__all__ = [
    'UnifiedWarfareCoreV18',
    'DailyVolumeAnchor',
    'CrossDayRelayEngine',
    'ShortTermMemory'
]