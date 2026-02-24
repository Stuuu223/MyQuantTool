# -*- coding: utf-8 -*-
"""
MyQuantTool - 小资金专用右侧起爆本地私有化量化程序
逻辑层统一入口

Phase 9.2 重构后核心模块暴露
"""

# Core基础设施层
from logic.core.error_handler import (
    AppError,
    DataError,
    NetworkError,
    ValidationError,
    ConfigError,
    handle_errors,
    safe_execute,
)
from logic.core.log_config import (
    setup_scan_logging,
    setup_logging_from_env,
    setup_ultra_quiet_logging,
    use_debug_mode,
    use_normal_mode,
    use_quiet_mode,
)
from logic.core.metric_definitions import MetricDefinitions
from logic.core.path_resolver import PathResolver
from logic.core.sanity_guards import SanityGuards, sanity_check
from logic.core.version import VERSION as __version__

# 策略层
from logic.strategies.sentiment_engine import SentimentEngine
from logic.strategies.strategy_config import StrategyConfig, get_strategy_config

# 工具层
from logic.utils.failsafe import FailSafeManager
from logic.utils.shared_config_manager import SharedConfigManager

# 数据提供层
from logic.data_providers.data_adapter import DataAdapter
from logic.data_providers.qmt_manager import QMTManager

# 交易执行层
from logic.execution.trade_gatekeeper import TradeGatekeeper

__all__ = [
    # Core基础设施
    'AppError',
    'DataError',
    'NetworkError',
    'ValidationError',
    'ConfigError',
    'handle_errors',
    'safe_execute',
    'setup_scan_logging',
    'setup_logging_from_env',
    'setup_ultra_quiet_logging',
    'use_debug_mode',
    'use_normal_mode',
    'use_quiet_mode',
    'MetricDefinitions',
    'PathResolver',
    'SanityGuards',
    'sanity_check',
    '__version__',
    
    # 策略层
    'SentimentEngine',
    'StrategyConfig',
    'get_strategy_config',
    
    # 工具层
    'QuantAlgo',
    'FailSafeManager',
    'SharedConfigManager',
    
    # 数据提供层
    'DataAdapter',
    'QMTManager',
    
    # 交易执行层
    'TradeGatekeeper',
]

__phase__ = 'Phase 9.2'
