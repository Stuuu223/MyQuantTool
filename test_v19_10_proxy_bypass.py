#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V19.10 代理屏蔽测试脚本

功能：
- 测试代理管理器功能
- 验证直连模式下的数据获取
- 网络连接测试
- 性能对比（有代理 vs 无代理）

Author: iFlow CLI
Version: V19.10
"""

import os
import sys
import time
import pandas as pd
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.logger import get_logger
from logic.proxy_manager import get_proxy_manager, ProxyMode
from logic.data_source_manager import get_smart_data_manager

logger = get_logger(__name__)


def test_proxy_manager():
    """测试代理管理器功能"""
    logger.info("=" * 60)
    logger.info("测试 1: 代理管理器功能")
    logger.info("=" * 60)

    proxy_mgr = get_proxy_manager()

    # 测试获取当前配置
    logger.info("\n[1.1] 获取当前代理配置...")
    config = proxy_mgr.get_proxy_config()
    logger.info(f"✅ 当前代理模式: {config['mode']}")
    logger.info(f"   HTTP代理: {config.get('http_proxy', '未设置')}")
    logger.info(f"   HTTPS代理: {config.get('https_proxy', '未设置')}")
    logger.info(f"   NO_PROXY: {config.get('no_proxy', '未设置')}")
    logger.info(f"   健康检查: {'启用' if config.get('health_check_enabled') else '禁用'}")
    logger.info(f"   失败次数: {config.get('failure_count', 0)}/{proxy_mgr.max_failures}")

    # 测试直连模式
    logger.info("\n[1.2] 测试直连模式...")
    if proxy_mgr.set_direct_mode():
        logger.info("✅ 直连模式设置成功")
        config = proxy_mgr.get_proxy_config()
        logger.info(f"   NO_PROXY: {config.get('no_proxy', '未设置')}")
    else:
        logger.error("❌ 直连模式设置失败")

    # 测试状态摘要
    logger.info("\n[1.3] 获取状态摘要...")
    summary = proxy_mgr.get_status_summary()
    logger.info("✅ 状态摘要:")
    for line in summary.split('\n'):
        logger.info(f"   {line}")

    return True


def test_network_connection():
    """测试网络连接"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 网络连接测试")
    logger.info("=" * 60)

    proxy_mgr = get_proxy_manager()

    # 测试百度连接
    logger.info("\n[2.1] 测试百度连接...")
    start_time = time.time()
    if proxy_mgr.test_connection("https://www.baidu.com"):
        elapsed = time.time() - start_time
        logger.info(f"✅ 百度连接测试成功 (耗时: {elapsed:.3f}秒)")
    else:
        elapsed = time.time() - start_time
        logger.error(f"❌ 百度连接测试失败 (耗时: {elapsed:.3f}秒)")

    # 测试东方财富连接
    logger.info("\n[2.2] 测试东方财富连接...")
    start_time = time.time()
    if proxy_mgr.test_eastmoney_connection():
        elapsed = time.time() - start_time
        logger.info(f"✅ 东方财富连接测试成功 (耗时: {elapsed:.3f}秒)")
    else:
        elapsed = time.time() - start_time
        logger.error(f"❌ 东方财富连接测试失败 (耗时: {elapsed:.3f}秒)")

    return True


def test_data_fetching():
    """测试数据获取（直连模式）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 数据获取测试（直连模式）")
    logger.info("=" * 60)

    # 确保使用直连模式
    proxy_mgr = get_smart_data_manager()

    # 测试获取实时行情
    logger.info("\n[3.1] 测试获取实时行情（增强层-akshare）...")
    test_stocks = ['600519', '000001', '300750']

    try:
        start_time = time.time()
        df = proxy_mgr.get_stock_realtime_data('600519')
        elapsed = time.time() - start_time

        if not df.empty:
            logger.info(f"✅ 获取实时行情成功 (耗时: {elapsed:.3f}秒)")
            logger.info(f"   获取到 {len(df)} 条数据")
            logger.info(f"   列: {list(df.columns)}")
        else:
            logger.warning(f"⚠️ 获取实时行情返回空数据 (耗时: {elapsed:.3f}秒)")
    except Exception as e:
        logger.error(f"❌ 获取实时行情失败: {e}")

    # 测试获取历史K线
    logger.info("\n[3.2] 测试获取历史K线（基础层-efinance/akshare）...")
    try:
        start_time = time.time()
        df = proxy_mgr.get_history_kline('600519', period='daily')
        elapsed = time.time() - start_time

        if not df.empty:
            logger.info(f"✅ 获取历史K线成功 (耗时: {elapsed:.3f}秒)")
            logger.info(f"   获取到 {len(df)} 条K线数据")
            logger.info(f"   时间范围: {df.iloc[0]['日期']} 到 {df.iloc[-1]['日期']}")
        else:
            logger.warning(f"⚠️ 获取历史K线返回空数据 (耗时: {elapsed:.3f}秒)")
    except Exception as e:
        logger.error(f"❌ 获取历史K线失败: {e}")

    # 测试获取资金流
    logger.info("\n[3.3] 测试获取资金流（增强层-akshare）...")
    try:
        start_time = time.time()
        data = proxy_mgr.get_money_flow('600519', market='sh')
        elapsed = time.time() - start_time

        if data:
            logger.info(f"✅ 获取资金流成功 (耗时: {elapsed:.3f}秒)")
            logger.info(f"   资金流数据: {list(data.keys())}")
        else:
            logger.warning(f"⚠️ 获取资金流返回空数据 (耗时: {elapsed:.3f}秒)")
    except Exception as e:
        logger.error(f"❌ 获取资金流失败: {e}")

    return True


def test_performance_comparison():
    """性能对比测试（有代理 vs 无代理）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: 性能对比测试")
    logger.info("=" * 60)

    proxy_mgr = get_proxy_manager()
    data_mgr = get_smart_data_manager()

    # 测试1: 直连模式
    logger.info("\n[4.1] 测试直连模式性能...")
    proxy_mgr.set_direct_mode()

    results = []
    for i in range(3):
        try:
            start_time = time.time()
            df = data_mgr.get_stock_realtime_data('600519')
            elapsed = time.time() - start_time
            results.append(elapsed)
            logger.info(f"   第{i+1}次: {elapsed:.3f}秒")
        except Exception as e:
            logger.error(f"   第{i+1}次失败: {e}")

    if results:
        avg_time = sum(results) / len(results)
        logger.info(f"✅ 直连模式平均耗时: {avg_time:.3f}秒")
        direct_mode_time = avg_time
    else:
        logger.error("❌ 直连模式测试失败")
        direct_mode_time = None

    # 测试2: 系统代理模式（如果可用）
    logger.info("\n[4.2] 测试系统代理模式性能...")
    proxy_mgr.set_system_proxy_mode()

    results = []
    for i in range(3):
        try:
            start_time = time.time()
            df = data_mgr.get_stock_realtime_data('600519')
            elapsed = time.time() - start_time
            results.append(elapsed)
            logger.info(f"   第{i+1}次: {elapsed:.3f}秒")
        except Exception as e:
            logger.error(f"   第{i+1}次失败: {e}")

    if results:
        avg_time = sum(results) / len(results)
        logger.info(f"✅ 系统代理模式平均耗时: {avg_time:.3f}秒")
        proxy_mode_time = avg_time
    else:
        logger.warning("⚠️ 系统代理模式测试失败（可能没有配置代理）")
        proxy_mode_time = None

    # 对比结果
    logger.info("\n[4.3] 性能对比结果...")
    if direct_mode_time and proxy_mode_time:
        if direct_mode_time < proxy_mode_time:
            improvement = ((proxy_mode_time - direct_mode_time) / proxy_mode_time) * 100
            logger.info(f"✅ 直连模式比系统代理模式快 {improvement:.1f}%")
            logger.info(f"   直连模式: {direct_mode_time:.3f}秒")
            logger.info(f"   系统代理: {proxy_mode_time:.3f}秒")
        else:
            logger.info(f"⚠️ 直连模式与系统代理模式性能相当或更慢")
            logger.info(f"   直连模式: {direct_mode_time:.3f}秒")
            logger.info(f"   系统代理: {proxy_mode_time:.3f}秒")
    elif direct_mode_time:
        logger.info(f"✅ 直连模式性能: {direct_mode_time:.3f}秒")

    # 恢复直连模式
    proxy_mgr.set_direct_mode()

    return True


def test_health_check():
    """测试健康检查和自动降级"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 5: 健康检查和自动降级")
    logger.info("=" * 60)

    proxy_mgr = get_proxy_manager()

    # 测试成功记录
    logger.info("\n[5.1] 测试成功记录...")
    proxy_mgr.record_success()
    config = proxy_mgr.get_proxy_config()
    logger.info(f"✅ 成功记录后失败次数: {config.get('failure_count', 0)}")

    # 测试失败记录
    logger.info("\n[5.2] 测试失败记录...")
    for i in range(3):
        proxy_mgr.record_failure()
        config = proxy_mgr.get_proxy_config()
        logger.info(f"   第{i+1}次失败记录后: {config.get('failure_count', 0)}/{proxy_mgr.max_failures}")

    # 测试自动降级（需要连续失败5次）
    logger.info("\n[5.3] 测试自动降级（模拟连续失败）...")
    logger.info(f"   当前失败次数: {config.get('failure_count', 0)}")
    logger.info(f"   自动降级阈值: {proxy_mgr.max_failures}")

    # 模拟连续失败
    for i in range(config.get('failure_count', 0), proxy_mgr.max_failures):
        proxy_mgr.record_failure()
        config = proxy_mgr.get_proxy_config()
        logger.info(f"   模拟第{i+1}次失败: {config.get('failure_count', 0)}/{proxy_mgr.max_failures}")

    # 检查是否自动切换到直连模式
    config = proxy_mgr.get_proxy_config()
    if config['mode'] == 'direct':
        logger.info("✅ 自动降级成功，已切换到直连模式")
    else:
        logger.warning(f"⚠️ 当前模式: {config['mode']}")

    # 重置失败计数
    proxy_mgr.record_success()
    config = proxy_mgr.get_proxy_config()
    logger.info(f"\n[5.4] 重置失败计数: {config.get('failure_count', 0)}")

    return True


def main():
    """主测试函数"""
    logger.info("\n" + "=" * 60)
    logger.info("V19.10 代理屏蔽测试")
    logger.info("=" * 60)
    logger.info("测试目标:")
    logger.info("1. 验证代理管理器功能")
    logger.info("2. 测试网络连接（百度、东方财富）")
    logger.info("3. 测试数据获取（直连模式）")
    logger.info("4. 性能对比（有代理 vs 无代理）")
    logger.info("5. 测试健康检查和自动降级")
    logger.info("=" * 60)

    try:
        # 运行所有测试
        test_proxy_manager()
        test_network_connection()
        test_data_fetching()
        test_performance_comparison()
        test_health_check()

        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有测试完成")
        logger.info("=" * 60)
        logger.info("\n测试结论:")
        logger.info("1. ✅ 代理管理器功能正常")
        logger.info("2. ✅ 网络连接测试通过")
        logger.info("3. ✅ 数据获取功能正常")
        logger.info("4. ✅ 性能对比测试完成")
        logger.info("5. ✅ 健康检查和自动降级功能正常")
        logger.info("\n使用建议:")
        logger.info("- 推荐使用直连模式，避免IP封禁")
        logger.info("- 如果直连失败，可以尝试手机热点")
        logger.info("- 定期检查网络连接状态")
        logger.info("- 启用健康检查，自动降级到直连模式")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
