#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 Iron Rule 性能测试脚本
测试铁律引擎和持仓管理的性能
"""

import sys
import time
from logic.iron_rule_engine import IronRuleEngine
from logic.position_manager import PositionManager
from logic.logger import get_logger

logger = get_logger(__name__)


def test_iron_rule_engine_performance():
    """
    测试 Iron Rule Engine 性能
    """
    logger.info("=" * 50)
    logger.info("开始测试 V13 Iron Rule Engine 性能")
    logger.info("=" * 50)
    
    engine = IronRuleEngine()
    
    # 测试 1：逻辑证伪检测性能
    logger.info("\n[性能测试 1] 逻辑证伪检测性能")
    
    test_cases = [
        ("公司发布新产品，市场反应热烈", 2.5),
        ("公司澄清：未形成收入，无相关业务", -2.5),
        ("公司澄清：尚不具备相关业务", 1.5),
        ("公司发布业绩预告，净利润增长50%", -2.5),
    ]
    
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        for news_text, dde_flow in test_cases:
            engine.check_absolute_logic(news_text, dde_flow)
    
    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / (iterations * len(test_cases))
    
    logger.info(f"迭代次数: {iterations}")
    logger.info(f"总耗时: {elapsed_time:.4f} 秒")
    logger.info(f"平均耗时: {avg_time * 1000:.4f} 毫秒/次")
    
    # 性能要求：每次检测 < 1 毫秒
    if avg_time * 1000 < 1.0:
        logger.info("✅ 性能测试通过：平均耗时 < 1 毫秒")
    else:
        logger.warning(f"⚠️ 性能测试警告：平均耗时 {avg_time * 1000:.4f} 毫秒，建议优化")
    
    # 测试 2：股票锁定性能
    logger.info("\n[性能测试 2] 股票锁定性能")
    
    test_codes = [f"00000{i}" for i in range(1, 11)]  # 10 只股票
    
    start_time = time.time()
    
    for code in test_codes:
        engine.check_stock_iron_rule(code, "公司澄清：未形成收入，无相关业务", -2.5)
    
    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / len(test_codes)
    
    logger.info(f"锁定股票数: {len(test_codes)}")
    logger.info(f"总耗时: {elapsed_time:.4f} 秒")
    logger.info(f"平均耗时: {avg_time * 1000:.4f} 毫秒/只")
    
    # 性能要求：每次锁定 < 10 毫秒
    if avg_time * 1000 < 10.0:
        logger.info("✅ 性能测试通过：平均耗时 < 10 毫秒")
    else:
        logger.warning(f"⚠️ 性能测试警告：平均耗时 {avg_time * 1000:.4f} 毫秒，建议优化")
    
    # 测试 3：获取锁定股票列表性能
    logger.info("\n[性能测试 3] 获取锁定股票列表性能")
    
    iterations = 100
    start_time = time.time()
    
    for _ in range(iterations):
        engine.get_locked_stocks()
    
    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / iterations
    
    logger.info(f"迭代次数: {iterations}")
    logger.info(f"总耗时: {elapsed_time:.4f} 秒")
    logger.info(f"平均耗时: {avg_time * 1000:.4f} 毫秒/次")
    
    # 性能要求：每次获取 < 5 毫秒
    if avg_time * 1000 < 5.0:
        logger.info("✅ 性能测试通过：平均耗时 < 5 毫秒")
    else:
        logger.warning(f"⚠️ 性能测试警告：平均耗时 {avg_time * 1000:.4f} 毫秒，建议优化")
    
    # 清理：解锁所有股票
    engine.unlock_all()
    
    logger.info("\n" + "=" * 50)
    logger.info("✅ Iron Rule Engine 性能测试完成")
    logger.info("=" * 50)


def test_position_manager_performance():
    """
    测试 Position Manager 性能
    """
    logger.info("\n" + "=" * 50)
    logger.info("开始测试 V13 Position Manager 性能")
    logger.info("=" * 50)
    
    pm = PositionManager()
    
    # 测试 1：计算加仓大小性能
    logger.info("\n[性能测试 1] 计算加仓大小性能")
    
    test_cases = [
        (0.05, "000001"),  # 浮盈 5%
        (-0.02, "000002"),  # 浮亏 -2%
        (-0.03, "000003"),  # 浮亏 -3%
        (-0.05, "000004"),  # 浮亏 -5%
        (-0.08, "000005"),  # 浮亏 -8%
        (-0.10, "000006"),  # 浮亏 -10%
    ]
    
    iterations = 1000
    start_time = time.time()
    
    for _ in range(iterations):
        for profit, code in test_cases:
            pm.calculate_add_position_size(profit, code)
    
    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / (iterations * len(test_cases))
    
    logger.info(f"迭代次数: {iterations}")
    logger.info(f"总耗时: {elapsed_time:.4f} 秒")
    logger.info(f"平均耗时: {avg_time * 1000:.4f} 毫秒/次")
    
    # 性能要求：每次计算 < 1 毫秒
    if avg_time * 1000 < 1.0:
        logger.info("✅ 性能测试通过：平均耗时 < 1 毫秒")
    else:
        logger.warning(f"⚠️ 性能测试警告：平均耗时 {avg_time * 1000:.4f} 毫秒，建议优化")
    
    logger.info("\n" + "=" * 50)
    logger.info("✅ Position Manager 性能测试完成")
    logger.info("=" * 50)


def test_integration_performance():
    """
    测试集成性能
    """
    logger.info("\n" + "=" * 50)
    logger.info("开始测试 V13 Iron Rule 集成性能")
    logger.info("=" * 50)
    
    engine = IronRuleEngine()
    pm = PositionManager()
    
    # 测试场景：模拟交易决策流程
    logger.info("\n[集成性能测试] 模拟交易决策流程")
    
    test_stocks = [
        ("000001", "公司澄清：未形成收入，无相关业务", -2.5, -0.05),  # 铁律锁定 + 浮亏 -5%
        ("000002", "公司发布新产品，市场反应热烈", 2.5, 0.03),  # 正常 + 浮盈 3%
        ("000003", "公司澄清：尚不具备相关业务", 1.5, -0.02),  # 正常 + 浮亏 -2%
    ]
    
    iterations = 100
    start_time = time.time()
    
    for _ in range(iterations):
        for code, news, dde, profit in test_stocks:
            # 步骤 1：铁律检查
            iron_result = engine.check_stock_iron_rule(code, news, dde)
            
            # 步骤 2：持仓管理检查
            if iron_result['can_buy']:
                pm_result = pm.calculate_add_position_size(profit, code)
            else:
                pm_result = {'can_add_position': False, 'reason': '铁律锁定'}
    
    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / (iterations * len(test_stocks))
    
    logger.info(f"迭代次数: {iterations}")
    logger.info(f"测试股票数: {len(test_stocks)}")
    logger.info(f"总耗时: {elapsed_time:.4f} 秒")
    logger.info(f"平均耗时: {avg_time * 1000:.4f} 毫秒/股")
    
    # 性能要求：每次决策 < 5 毫秒
    if avg_time * 1000 < 5.0:
        logger.info("✅ 性能测试通过：平均耗时 < 5 毫秒")
    else:
        logger.warning(f"⚠️ 性能测试警告：平均耗时 {avg_time * 1000:.4f} 毫秒，建议优化")
    
    # 清理
    engine.unlock_all()
    
    logger.info("\n" + "=" * 50)
    logger.info("✅ 集成性能测试完成")
    logger.info("=" * 50)


def main():
    """
    主测试函数
    """
    logger.info("\n" + "=" * 70)
    logger.info("V13 Iron Rule 性能测试开始")
    logger.info("=" * 70)
    
    start_time = time.time()
    
    try:
        # 测试 1：Iron Rule Engine 性能
        test_iron_rule_engine_performance()
        
        # 测试 2：Position Manager 性能
        test_position_manager_performance()
        
        # 测试 3：集成性能
        test_integration_performance()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ 所有性能测试完成！")
        logger.info(f"总耗时: {elapsed_time:.2f} 秒")
        logger.info("=" * 70)
        
        print("\n" + "=" * 70)
        print("✅ V13 Iron Rule 性能测试全部完成！")
        print(f"总耗时: {elapsed_time:.2f} 秒")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        logger.error(f"\n❌ 测试出错: {e}")
        logger.exception(e)
        print(f"\n❌ 测试出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
