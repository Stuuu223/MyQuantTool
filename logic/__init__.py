# -*- coding: utf-8 -*-
"""
MyQuantTool - 小资金专用右侧起爆本地私有化量化程序
逻辑层统一入口

Phase 1.5.3 精简后核心模块暴露
"""

# 数据服务层（统一数据入口）
from logic.services.data_service import DataService

# 评分层（Phase 1核心：资金强度评分）
from logic.scoring.flow_intensity_scorer import FlowIntensityScorer, calculate_intensity

# 检测器层（事件检测）
# NOTE: HalfwayBreakoutDetector已归档至archive/redundant_halfway/，使用UnifiedWarfareCore替代
from logic.strategies.unified_warfare_core import UnifiedWarfareCore
from logic.strategies.event_detector import BaseEventDetector, TradingEvent, EventType

# 数据源层（QMT历史数据）
from logic.qmt_historical_provider import QMTHistoricalProvider

__all__ = [
    # 数据服务
    'DataService',
    
    # 评分系统
    'FlowIntensityScorer',
    'calculate_intensity',
    
    # 事件检测 (V17: 使用UnifiedWarfareCore替代HalfwayBreakoutDetector)
    'UnifiedWarfareCore',
    'BaseEventDetector',
    'TradingEvent',
    'EventType',
    
    # 数据源
    'QMTHistoricalProvider',
]

__version__ = '10.5.0'
__phase__ = 'Phase 1.5.3'
