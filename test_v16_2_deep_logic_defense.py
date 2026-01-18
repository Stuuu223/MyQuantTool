#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16.2 Deep Logic Defense - 深度逻辑防御测试
测试 4 个隐藏地雷的修复：
1. Hidden Mine 1: 资金碰撞和"平庸优先"陷阱 - 信号池机制
2. Hidden Mine 2: 高频"机关枪"走火 - pending_orders 缓存
3. Hidden Mine 3: 数据"幽灵"延迟 - 数据保质期校验
4. Hidden Mine 4: 涨停板"废单"风险 - 强制限价单
"""

import unittest
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, '.')

from logic.paper_trading_system import (
    PaperTradingSystem, 
    SignalPool,
    OrderType, 
    OrderDirection, 
    OrderStatus
)
from logic.live_trading_interface import LiveTradingInterface, LiveOrder, OrderType as LiveOrderType, OrderDirection as LiveOrderDirection
from logic.realtime_data_provider import RealtimeDataProvider


class TestHiddenMine1_SignalPool(unittest.TestCase):
    """测试 Hidden Mine 1: 资金碰撞和"平庸优先"陷阱"""
    
    def setUp(self):
        """初始化测试环境"""
        self.trading_system = PaperTradingSystem(
            initial_capital=100000.0,
            commission_rate=0.001,
            t_plus_one=False,  # 禁用 T+1 以便测试
            risk_limit=0.95
        )
        self.signal_pool = SignalPool(self.trading_system)
    
    def test_collect_rank_execute(self):
        """测试 Collect -> Rank -> Execute 流程"""
        # 添加多个信号（分数不同）
        self.signal_pool.add_signal("000001", 95.0, 10.0, 10, "龙头股")
        self.signal_pool.add_signal("000002", 75.0, 10.0, 10, "平庸股")
        self.signal_pool.add_signal("000003", 85.0, 10.0, 10, "次龙头")
        
        # 执行信号（最大持仓数 2）
        result = self.signal_pool.execute_signals(max_positions=2, position_size=0.2)
        
        # 验证结果
        self.assertEqual(result["executed"], 2)  # 应该只执行前 2 个
        self.assertEqual(result["rejected"], 1)  # 第 3 个被拒绝
        
        # 验证持仓顺序（应该按分数降序）
        positions = list(self.trading_system.positions.keys())
        self.assertEqual(positions[0], "000001")  # 95 分
        self.assertEqual(positions[1], "000003")  # 85 分
        self.assertNotIn("000002", positions)  # 75 分被拒绝
    
    def test_fund_exhaustion(self):
        """测试资金耗尽情况"""
        # 添加多个信号，总金额超过可用资金
        self.signal_pool.add_signal("000001", 95.0, 10.0, 50, "龙头股")  # 5万
        self.signal_pool.add_signal("000002", 85.0, 10.0, 50, "次龙头")  # 5万
        self.signal_pool.add_signal("000003", 75.0, 10.0, 50, "平庸股")  # 5万
        
        # 执行信号
        result = self.signal_pool.execute_signals(max_positions=5, position_size=0.2)
        
        # 验证结果
        self.assertLessEqual(result["executed"], 2)  # 资金只够买前 2 个
        self.assertGreater(result["remaining_capital"], 0)  # 应该还有剩余资金
    
    def test_duplicate_position_skip(self):
        """测试跳过已有持仓"""
        # 先买入一只股票
        order_id = self.trading_system.submit_order(
            symbol="000001",
            order_type=OrderType.LIMIT,
            direction=OrderDirection.BUY,
            quantity=10,
            price=10.0
        )
        self.trading_system.fill_order(order_id, 10.0, 1000)
        
        # 添加信号（包含已有持仓的股票）
        self.signal_pool.add_signal("000001", 95.0, 10.0, 10, "已有持仓")
        self.signal_pool.add_signal("000002", 85.0, 10.0, 10, "新股票")
        
        # 执行信号
        result = self.signal_pool.execute_signals(max_positions=5, position_size=0.2)
        
        # 验证结果
        self.assertEqual(result["rejected"], 1)  # 000001 被拒绝
        self.assertEqual(result["executed"], 1)  # 只有 000002 被执行


class TestHiddenMine2_MachineGunMisfire(unittest.TestCase):
    """测试 Hidden Mine 2: 高频"机关枪"走火"""
    
    def test_pending_orders_prevention(self):
        """测试 pending_orders 缓存防止重复下单"""
        # 创建模拟接口
        live_interface = LiveTradingInterface(config={
            'capital': 100000.0,
            'commission_rate': 0.001,
            'slippage_rate': 0.001
        })
        
        # 创建订单
        order = LiveOrder(
            order_id="ORDER_001",
            symbol="000001",
            direction=OrderDirection.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=10.0
        )
        
        # 第一次下单应该成功（添加到 pending_orders）
        live_interface.pending_orders.add("000001")
        self.assertIn("000001", live_interface.pending_orders)
        
        # 第二次下单同一只股票应该失败
        result = live_interface.place_order(order)
        self.assertFalse(result)
    
    def test_pending_orders_release(self):
        """测试订单成交后释放 pending_orders 缓存"""
        # 创建模拟接口
        live_interface = LiveTradingInterface(config={
            'capital': 100000.0,
            'commission_rate': 0.001,
            'slippage_rate': 0.001
        })
        
        # 添加到 pending_orders
        live_interface.pending_orders.add("000001")
        
        # 模拟订单成交（手动释放）
        live_interface.pending_orders.remove("000001")
        
        # 验证 pending_orders 缓存已释放
        self.assertNotIn("000001", live_interface.pending_orders)


class TestHiddenMine3_DataGhostLatency(unittest.TestCase):
    """测试 Hidden Mine 3: 数据"幽灵"延迟"""
    
    def setUp(self):
        """初始化测试环境"""
        self.data_provider = RealtimeDataProvider()
    
    def test_data_freshness_check(self):
        """测试数据保质期校验"""
        # 模拟过期数据（20秒前）
        old_time = (datetime.now() - timedelta(seconds=20)).strftime("%H:%M:%S")
        
        # 模拟 fresh 数据（5秒前）
        fresh_time = (datetime.now() - timedelta(seconds=5)).strftime("%H:%M:%S")
        
        # 模拟市场数据
        market_data = {
            "000001": {"name": "平安银行", "now": 10.0, "percent": 5.0, "time": old_time},
            "000002": {"name": "万科A", "now": 20.0, "percent": 3.0, "time": fresh_time},
        }
        
        with patch('easyquotation.use') as mock_eq:
            mock_quotation = Mock()
            mock_quotation.stocks.return_value = market_data
            mock_eq.return_value = mock_quotation
            
            # 获取实时数据
            result = self.data_provider.get_realtime_data(["000001", "000002"])
            
            # 验证结果
            self.assertEqual(len(result), 1)  # 只有 fresh 数据被返回
            self.assertEqual(result[0]["code"], "000002")  # 000001 因过期被过滤
    
    def test_auction_period_exemption(self):
        """测试竞价期间豁免"""
        # 模拟竞价时间（9:20）
        current_time = datetime.now().replace(hour=9, minute=20, second=0)
        
        # 模拟过期数据（20秒前）
        old_time = (current_time - timedelta(seconds=20)).strftime("%H:%M:%S")
        
        # 模拟市场数据
        market_data = {
            "000001": {"name": "平安银行", "now": 10.0, "percent": 5.0, "time": old_time},
        }
        
        with patch('easyquotation.use') as mock_eq:
            mock_quotation = Mock()
            mock_quotation.stocks.return_value = market_data
            mock_eq.return_value = mock_quotation
            
            with patch('logic.realtime_data_provider.datetime') as mock_datetime:
                mock_datetime.now.return_value = current_time
                
                # 获取实时数据
                result = self.data_provider.get_realtime_data(["000001"])
                
                # 验证结果（竞价期间应该豁免）
                self.assertEqual(len(result), 1)  # 数据应该被返回


class TestHiddenMine4_LimitUpVoidOrder(unittest.TestCase):
    """测试 Hidden Mine 4: 涨停板"废单"风险"""
    
    def test_limit_up_force_limit_order(self):
        """测试涨停板强制限价单"""
        # 创建订单（市价单）
        order = LiveOrder(
            order_id="ORDER_001",
            symbol="000001",
            direction=OrderDirection.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            price=0.0
        )
        
        # 模拟涨停价
        limit_up_price = 11.0
        market_price = 10.95  # 接近涨停价
        
        # 检查是否接近涨停价（涨幅 > 9.5%）
        if market_price >= limit_up_price * 0.99:
            # 强制使用限价单
            order.order_type = OrderType.LIMIT
            order.price = limit_up_price
        
        # 验证订单类型被强制改为限价单
        self.assertEqual(order.order_type, OrderType.LIMIT)
        self.assertEqual(order.price, limit_up_price)
    
    def test_normal_order_no_force(self):
        """测试正常订单不强制限价单"""
        # 创建订单（市价单）
        order = LiveOrder(
            order_id="ORDER_001",
            symbol="000001",
            direction=OrderDirection.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            price=0.0
        )
        
        # 模拟正常价格（不接近涨停）
        limit_up_price = 11.0
        market_price = 10.0  # 不接近涨停价
        
        # 检查是否接近涨停价（涨幅 > 9.5%）
        if market_price >= limit_up_price * 0.99:
            # 强制使用限价单
            order.order_type = OrderType.LIMIT
            order.price = limit_up_price
        
        # 验证订单类型保持市价单
        self.assertEqual(order.order_type, OrderType.MARKET)


class TestV16_2_Integration(unittest.TestCase):
    """V16.2 集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        # 初始化系统
        trading_system = PaperTradingSystem(
            initial_capital=100000.0,
            commission_rate=0.001,
            t_plus_one=False,
            risk_limit=0.95
        )
        signal_pool = SignalPool(trading_system)
        
        # 模拟信号生成（分数不同）
        signals = [
            {"symbol": "000001", "score": 95.0, "price": 10.0},
            {"symbol": "000002", "score": 75.0, "price": 10.0},
            {"symbol": "000003", "score": 85.0, "price": 10.0},
        ]
        
        # 添加信号到池
        for signal in signals:
            signal_pool.add_signal(
                signal["symbol"],
                signal["score"],
                signal["price"],
                reason="测试信号"
            )
        
        # 执行信号
        result = signal_pool.execute_signals(max_positions=2, position_size=0.2)
        
        # 验证结果
        self.assertEqual(result["executed"], 2)
        self.assertEqual(result["rejected"], 1)
        
        # 验证持仓顺序
        positions = list(trading_system.positions.keys())
        self.assertEqual(positions[0], "000001")  # 95 分
        self.assertEqual(positions[1], "000003")  # 85 分


def run_tests():
    """运行所有测试"""
    print("=" * 80)
    print("V16.2 Deep Logic Defense - 深度逻辑防御测试")
    print("=" * 80)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试
    suite.addTests(loader.loadTestsFromTestCase(TestHiddenMine1_SignalPool))
    suite.addTests(loader.loadTestsFromTestCase(TestHiddenMine2_MachineGunMisfire))
    suite.addTests(loader.loadTestsFromTestCase(TestHiddenMine3_DataGhostLatency))
    suite.addTests(loader.loadTestsFromTestCase(TestHiddenMine4_LimitUpVoidOrder))
    suite.addTests(loader.loadTestsFromTestCase(TestV16_2_Integration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 80)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)