#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V13 Iron Rule 集成测试脚本
测试铁律监控、预警系统和 UI 集成
"""

import sys
import time
from logic.iron_rule_monitor import IronRuleMonitor
from logic.iron_rule_alert import IronRuleAlert
from logic.iron_rule_engine import IronRuleEngine
from logic.logger import get_logger

logger = get_logger(__name__)


def test_iron_rule_monitor():
    """
    测试铁律监控器
    """
    logger.info("=" * 50)
    logger.info("开始测试 V13 Iron Rule Monitor")
    logger.info("=" * 50)
    
    monitor = IronRuleMonitor()
    
    # 测试 1：获取股票铁律状态
    logger.info("\n[测试 1] 获取股票铁律状态")
    
    test_stocks = ['600519', '000001', '000002']
    
    for code in test_stocks:
        try:
            status = monitor.get_stock_iron_status(code)
            logger.info(f"股票 {code} 铁律状态:")
            logger.info(f"  是否锁定: {status['is_locked']}")
            logger.info(f"  预警级别: {status['warning_level']}")
            logger.info(f"  DDE净额: {status['dde_net_flow']:.2f}亿")
            logger.info(f"  逻辑状态: {status['logic_status']}")
            logger.info(f"  建议操作: {status['recommendation']}")
            
            if status['warning_messages']:
                logger.info(f"  预警消息: {', '.join(status['warning_messages'])}")
        except Exception as e:
            logger.error(f"获取股票 {code} 铁律状态失败: {e}")
    
    logger.info("\n✅ [测试 1] 获取股票铁律状态测试通过")
    
    # 测试 2：获取监控历史
    logger.info("\n[测试 2] 获取监控历史")
    
    try:
        history = monitor.get_monitor_history('600519', days=7)
        logger.info(f"股票 600519 监控历史记录数: {len(history)}")
        
        if history:
            logger.info("最近 3 条记录:")
            for i, record in enumerate(history[:3]):
                logger.info(f"  {i+1}. {record['timestamp']} - 预警级别: {record['warning_level']}, 建议: {record['recommendation']}")
    except Exception as e:
        logger.error(f"获取监控历史失败: {e}")
    
    logger.info("\n✅ [测试 2] 获取监控历史测试通过")
    
    # 测试 3：获取所有锁定股票
    logger.info("\n[测试 3] 获取所有锁定股票")
    
    try:
        locked_stocks = monitor.get_all_locked_stocks()
        logger.info(f"锁定股票数: {len(locked_stocks)}")
        
        for stock in locked_stocks:
            logger.info(f"  {stock['code']}: 剩余 {stock['remaining_hours']:.1f} 小时")
    except Exception as e:
        logger.error(f"获取锁定股票失败: {e}")
    
    logger.info("\n✅ [测试 3] 获取所有锁定股票测试通过")
    
    logger.info("\n" + "=" * 50)
    logger.info("✅ Iron Rule Monitor 测试全部通过")
    logger.info("=" * 50)


def test_iron_rule_alert():
    """
    测试铁律预警系统
    """
    logger.info("\n" + "=" * 50)
    logger.info("开始测试 V13 Iron Rule Alert")
    logger.info("=" * 50)
    
    alert_system = IronRuleAlert()
    
    # 测试 1：检查预警
    logger.info("\n[测试 1] 检查预警")
    
    test_stocks = ['600519', '000001', '000002']
    
    for code in test_stocks:
        try:
            alerts = alert_system.check_stock_alerts(code)
            logger.info(f"股票 {code} 预警数量: {len(alerts)}")
            
            for alert in alerts:
                logger.info(f"  - {alert['alert_type']} ({alert['alert_level']}): {alert['alert_message']}")
        except Exception as e:
            logger.error(f"检查股票 {code} 预警失败: {e}")
    
    logger.info("\n✅ [测试 1] 检查预警测试通过")
    
    # 测试 2：获取预警历史
    logger.info("\n[测试 2] 获取预警历史")
    
    try:
        history = alert_system.get_alert_history(days=7)
        logger.info(f"预警历史记录数: {len(history)}")
        
        if history:
            logger.info("最近 3 条记录:")
            for i, record in enumerate(history[:3]):
                logger.info(f"  {i+1}. {record['code']} - {record['alert_type']}: {record['alert_message']}")
    except Exception as e:
        logger.error(f"获取预警历史失败: {e}")
    
    logger.info("\n✅ [测试 2] 获取预警历史测试通过")
    
    # 测试 3：获取未读预警
    logger.info("\n[测试 3] 获取未读预警")
    
    try:
        unread_alerts = alert_system.get_unread_alerts()
        logger.info(f"未读预警数量: {len(unread_alerts)}")
        
        for alert in unread_alerts:
            logger.info(f"  - {alert['code']} - {alert['alert_type']}: {alert['alert_message']}")
    except Exception as e:
        logger.error(f"获取未读预警失败: {e}")
    
    logger.info("\n✅ [测试 3] 获取未读预警测试通过")
    
    logger.info("\n" + "=" * 50)
    logger.info("✅ Iron Rule Alert 测试全部通过")
    logger.info("=" * 50)


def test_integration_performance():
    """
    测试集成性能
    """
    logger.info("\n" + "=" * 50)
    logger.info("开始测试 V13 Iron Rule 集成性能")
    logger.info("=" * 50)
    
    monitor = IronRuleMonitor()
    alert_system = IronRuleAlert()
    
    # 测试场景：模拟多只股票的铁律检查
    logger.info("\n[集成性能测试] 模拟多只股票的铁律检查")
    
    test_stocks = ['600519', '000001', '000002', '000003', '000004']
    
    iterations = 10
    start_time = time.time()
    
    for _ in range(iterations):
        for code in test_stocks:
            # 步骤 1：获取铁律状态
            status = monitor.get_stock_iron_status(code)
            
            # 步骤 2：检查预警
            alerts = alert_system.check_stock_alerts(code)
    
    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / (iterations * len(test_stocks))
    
    logger.info(f"迭代次数: {iterations}")
    logger.info(f"测试股票数: {len(test_stocks)}")
    logger.info(f"总耗时: {elapsed_time:.4f} 秒")
    logger.info(f"平均耗时: {avg_time * 1000:.4f} 毫秒/股")
    
    # 性能要求：每次检查 < 100 毫秒
    if avg_time * 1000 < 100.0:
        logger.info("✅ 性能测试通过：平均耗时 < 100 毫秒")
    else:
        logger.warning(f"⚠️ 性能测试警告：平均耗时 {avg_time * 1000:.4f} 毫秒，建议优化")
    
    logger.info("\n" + "=" * 50)
    logger.info("✅ 集成性能测试完成")
    logger.info("=" * 50)


def main():
    """
    主测试函数
    """
    logger.info("\n" + "=" * 70)
    logger.info("V13 Iron Rule 集成测试开始")
    logger.info("=" * 70)
    
    start_time = time.time()
    
    try:
        # 测试 1：Iron Rule Monitor
        test_iron_rule_monitor()
        
        # 测试 2：Iron Rule Alert
        test_iron_rule_alert()
        
        # 测试 3：集成性能
        test_integration_performance()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ 所有集成测试通过！")
        logger.info(f"总耗时: {elapsed_time:.2f} 秒")
        logger.info("=" * 70)
        
        print("\n" + "=" * 70)
        print("✅ V13 Iron Rule 集成测试全部通过！")
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
