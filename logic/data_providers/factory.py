#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据提供者工厂

根据配置文件自动选择数据源

Author: MyQuantTool Team
Date: 2026-02-12
"""

import json
from pathlib import Path
from typing import Optional

from .base import ICapitalFlowProvider
from logic.logger import get_logger

logger = get_logger(__name__)


class DataProviderFactory:
    """
    数据提供者工厂

    根据配置文件自动选择数据源：
    1. 优先使用配置指定的数据源
    2. 如果不可用，自动降级到备用数据源
    3. 最终降级到东方财富T-1
    """

    _instance: Optional[ICapitalFlowProvider] = None
    _config_path = Path(__file__).parent.parent.parent / 'config' / 'market_scan_config.json'

    @classmethod
    def create(cls, force_provider: Optional[str] = None) -> ICapitalFlowProvider:
        """
        创建数据提供者实例（单例模式）

        Args:
            force_provider: 强制指定数据源
                - 'level1': Level-1推断
                - 'level2': Level-2逐笔（未来实现）
                - 'dongcai': 东方财富T-1

        Returns:
            ICapitalFlowProvider: 数据提供者实例
        """
        if cls._instance is not None:
            return cls._instance

        # 读取配置
        provider_type = force_provider or cls._load_config()

        # 创建实例
        cls._instance = cls._create_provider(provider_type)

        logger.info(f"✅ 数据提供者: {cls._instance.get_provider_name()}")

        return cls._instance

    @classmethod
    def _load_config(cls) -> str:
        """
        从配置文件加载数据源类型

        Returns:
            str: 'level1' / 'level2' / 'dongcai'
        """
        try:
            with open(cls._config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            provider_config = config.get('data_provider', {})
            provider_type = provider_config.get('type', 'level1')

            logger.info(f"📄 配置文件指定数据源: {provider_type}")
            return provider_type

        except Exception as e:
            logger.warning(f"⚠️ 配置文件加载失败: {e}，使用默认数据源 level1")
            return 'level1'

    @classmethod
    def _create_provider(cls, provider_type: str) -> ICapitalFlowProvider:
        """
        根据类型创建数据提供者

        Args:
            provider_type: 'level1' / 'level2' / 'dongcai'

        Returns:
            ICapitalFlowProvider: 数据提供者实例
        """
        # 尝试创建指定类型
        if provider_type == 'level2':
            try:
                from .level2_provider import Level2TickProvider
                provider = Level2TickProvider()
                if provider.is_available():
                    logger.info("✅ 使用 Level-2 逐笔数据（付费）")
                    return provider
                else:
                    logger.warning("⚠️ Level-2不可用，降级到Level-1")
            except ImportError:
                logger.warning("⚠️ Level-2未实现，降级到Level-1")

        if provider_type == 'level1' or provider_type == 'level2':
            try:
                from .level1_provider import Level1InferenceProvider
                provider = Level1InferenceProvider()
                if provider.is_available():
                    logger.info("✅ 使用 Level-1 推断数据（免费）")
                    return provider
                else:
                    logger.warning("⚠️ Level-1不可用（QMT未运行），降级到东方财富")
            except Exception as e:
                logger.warning(f"⚠️ Level-1创建失败: {e}，降级到东方财富")

        # 最终降级到东方财富T-1
        from .dongcai_provider import DongCaiT1Provider
        logger.info("✅ 使用 东方财富T-1数据（降级）")
        return DongCaiT1Provider()

    @classmethod
    def reset(cls):
        """重置单例（用于测试）"""
        cls._instance = None


def get_provider(provider_type: str = 'level1') -> ICapitalFlowProvider:
    """
    获取数据提供者实例（便捷函数）

    Args:
        provider_type: 数据源类型

    Returns:
        ICapitalFlowProvider: 数据提供者实例
    """
    return DataProviderFactory.create(provider_type)