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
from logic.core.version import VERSION as __version__

# 策略层
from logic.strategies.strategy_config import StrategyConfig, get_strategy_config

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
    
    # 策略层
    'StrategyConfig',
    'get_strategy_config',
    
    # 数据提供层
    'QMTManager',
    'UniverseBuilder',
    'get_true_dictionary',
]

__phase__ = 'V20'