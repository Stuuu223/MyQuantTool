#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据提供者切换功能

Author: MyQuantTool Team
Date: 2026-02-12
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from logic.data_providers import get_provider, DataProviderFactory
from logic.logger import get_logger

logger = get_logger(__name__)


def test_data_provider_switch():
    """测试数据提供者切换功能"""
    logger.info("=" * 80)
    logger.info("🧪 测试数据提供者切换功能")
    logger.info("=" * 80)

    # 测试1: 测试Level-1提供者
    logger.info("\n📋 测试1: Level-1提供者")
    try:
        provider = get_provider('level1')
        logger.info(f"✅ 创建成功: {provider.get_provider_name()}")
        logger.info(f"   可用状态: {provider.is_available()}")

        # 尝试获取平安银行的资金流
        signal = provider.get_realtime_flow('000001')
        if signal:
            logger.info(f"   资金流数据: 主力净流入={signal.main_net_inflow:.2f} "
                       f"置信度={signal.confidence:.2f} "
                       f"来源={signal.source}")
        else:
            logger.warning("   警告: 无法获取资金流数据")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")

    # 测试2: 测试东方财富提供者
    logger.info("\n📋 测试2: 东方财富T-1提供者")
    try:
        provider = get_provider('dongcai')
        logger.info(f"✅ 创建成功: {provider.get_provider_name()}")
        logger.info(f"   可用状态: {provider.is_available()}")

        # 尝试获取平安银行的资金流
        signal = provider.get_realtime_flow('000001')
        if signal:
            logger.info(f"   资金流数据: 主力净流入={signal.main_net_inflow:.2f} "
                       f"置信度={signal.confidence:.2f} "
                       f"来源={signal.source}")
        else:
            logger.warning("   警告: 无法获取资金流数据")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")

    # 测试3: 测试自动降级
    logger.info("\n📋 测试3: 自动降级（强制使用不存在的level2）")
    try:
        DataProviderFactory.reset()  # 重置单例
        provider = get_provider('level2')
        logger.info(f"✅ 创建成功: {provider.get_provider_name()}")
        logger.info(f"   降级机制: level2 → level1 → dongcai")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")

    # 测试4: 测试数据新鲜度
    logger.info("\n📋 测试4: 数据新鲜度")
    try:
        DataProviderFactory.reset()
        provider = get_provider('level1')
        freshness = provider.get_data_freshness('000001')
        logger.info(f"✅ 数据新鲜度: {freshness} 秒")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("🎉 测试完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_data_provider_switch()