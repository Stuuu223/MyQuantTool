# -*- coding: utf-8 -*-
"""
数据提供层 - 统一数据接口
"""

import logging

logger = logging.getLogger(__name__)

# TODO: Phase 9.2-A3 实现真正的provider工厂
def get_provider(provider_name: str = "qmt", **kwargs):
    """
    获取数据提供者实例
    
    Args:
        provider_name: 提供者名称 (qmt, mock, etc.)
        **kwargs: 传递给提供者的参数
        
    Returns:
        数据提供者实例
    """
    logger.warning(f"get_provider() 是占位符实现，provider_name={provider_name}")
    return None


from logic.data_providers.qmt_manager import QMTManager

__all__ = ['get_provider', 'QMTManager']
