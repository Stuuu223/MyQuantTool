# -*- coding: utf-8 -*-
"""
MyQuantTool - 小资金专用右侧起爆本地私有化量化程序
逻辑层统一入口

V20 极致全息架构
"""

# Core基础设施层
from logic.core.log_config import (
    setup_scan_logging,
    setup_logging_from_env,
    setup_ultra_quiet_logging,
    use_debug_mode,
    use_normal_mode,
    use_quiet_mode,
)
from logic.core.path_resolver import PathResolver
from logic.core.sanity_guards import SanityGuards, sanity_check

# 【CTO剃刀行动】version.py已删除，Git管理版本
# 如需版本号，运行: git describe --tags 或查看 README.md
__version__ = "V20.0.0"  # 硬编码兜底，实际版本由Git管理

# 数据提供层
from logic.data_providers.qmt_manager import QmtDataManager, get_qmt_manager
from logic.data_providers.universe_builder import UniverseBuilder
from logic.data_providers.true_dictionary import get_true_dictionary

__all__ = [
    # Core基础设施
    'setup_scan_logging',
    'setup_logging_from_env',
    'setup_ultra_quiet_logging',
    'use_debug_mode',
    'use_normal_mode',
    'use_quiet_mode',
    'PathResolver',
    'SanityGuards',
    'sanity_check',
    '__version__',
    
    # 数据提供层
    'QmtDataManager',
    'UniverseBuilder',
    'get_true_dictionary',
]

__phase__ = 'V20'