# -*- coding: utf-8 -*-
"""
Logic层统一服务门面 (Services Facade)

禁止直接访问logic子模块，必须通过以下门面：
- MarketService: 行情数据（Tick/K线）
- CapitalService: 资金流数据
- StrategyService: 策略检测（Halfway/Leader/TrueAttack）
- RiskService: 风险控制
- ConfigService: 配置管理
"""

from .market_service import MarketService
from .capital_service import CapitalService
from .strategy_service import StrategyService
from .risk_service import RiskService
from .config_service import ConfigService

__all__ = [
    'MarketService',
    'CapitalService', 
    'StrategyService',
    'RiskService',
    'ConfigService'
]
