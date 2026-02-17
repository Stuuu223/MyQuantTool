#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
契约一致性测试 (Contract Compliance Test)

目的：验证代码实现是否符合 SIGNAL_AND_PORTFOLIO_CONTRACT.md 的接口契约
范围：结构校验，不动业务逻辑
优先级：P0（必须在CI中通过）

检查项：
1. Detector返回值必须是TradingEvent格式
2. strategies目录不允许import交易执行模块
3. CapitalAllocator输入输出契约合规性

Author: AI项目总监
Date: 2026-02-17
Version: V1.0
"""

import sys
import ast
import inspect
from pathlib import Path
from typing import List, Dict, Any, Optional
import unittest

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.strategies.event_detector import TradingEvent, EventType
from logic.strategies.unified_warfare_core import get_unified_warfare_core


class TestContractCompliance(unittest.TestCase):
    """契约一致性测试套件"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.strategies_dir = PROJECT_ROOT / "logic" / "strategies"
        cls.trading_modules = [
            "xttrader", "XtQuantTrader", "submit_order", "place_order",
            "broker_api", "paper_trading_system", "order_manager"
        ]
    
    # ==========================================================================
    # 测试1: Detector返回值schema合规性
    # ==========================================================================
    
    def test_detector_return_type(self):
        """测试Detector返回值必须是TradingEvent或None"""
        from logic.strategies.halfway_breakout_detector import HalfwayBreakoutDetector
        from logic.strategies.leader_candidate_detector import LeaderCandidateDetector
        from logic.strategies.dip_buy_candidate_detector import DipBuyCandidateDetector
        from logic.strategies.opening_weak_to_strong_detector import OpeningWeakToStrongDetector
        
        detectors = [
            ("HalfwayBreakoutDetector", HalfwayBreakoutDetector()),
            ("LeaderCandidateDetector", LeaderCandidateDetector()),
            ("DipBuyCandidateDetector", DipBuyCandidateDetector()),
            ("OpeningWeakToStrongDetector", OpeningWeakToStrongDetector()),
        ]
        
        for name, detector in detectors:
            with self.subTest(detector=name):
                # 准备测试数据
                tick_data = {
                    'stock_code': '300750',
                    'datetime': __import__('datetime').datetime.now(),
                    'price': 100.0,
                    'volume': 1000000,
                    'amount': 100000000,
                }
                
                context = {
                    'price_history': [99.0, 99.5, 100.0, 100.5] * 5,  # 20个数据点
                    'volume_history': [900000, 950000, 1000000, 1050000] * 5,
                    'ma5': 100.0,
                    'ma20': 99.0,
                }
                
                # 调用detect
                result = detector.detect(tick_data, context)
                
                # 验证返回类型
                if result is not None:
                    self.assertIsInstance(result, TradingEvent,
                        f"{name}.detect() 返回值必须是 TradingEvent 或 None，"
                        f"实际返回 {type(result)}")
                    
                    # 验证TradingEvent字段完整性
                    self.assertTrue(hasattr(result, 'event_type'),
                        f"{name} 返回的 TradingEvent 缺少 event_type 字段")
                    self.assertTrue(hasattr(result, 'stock_code'),
                        f"{name} 返回的 TradingEvent 缺少 stock_code 字段")
                    self.assertTrue(hasattr(result, 'timestamp'),
                        f"{name} 返回的 TradingEvent 缺少 timestamp 字段")
                    self.assertTrue(hasattr(result, 'confidence'),
                        f"{name} 返回的 TradingEvent 缺少 confidence 字段")
                    self.assertTrue(hasattr(result, 'data'),
                        f"{name} 返回的 TradingEvent 缺少 data 字段")
                    self.assertTrue(hasattr(result, 'description'),
                        f"{name} 返回的 TradingEvent 缺少 description 字段")
                    
                    # 验证confidence范围
                    self.assertGreaterEqual(result.confidence, 0.0,
                        f"{name} 返回的 confidence 必须 >= 0")
                    self.assertLessEqual(result.confidence, 1.0,
                        f"{name} 返回的 confidence 必须 <= 1")
    
    def test_trading_event_fields_type(self):
        """测试TradingEvent字段类型合规性"""
        from datetime import datetime
        
        # 构造一个合规的TradingEvent
        event = TradingEvent(
            event_type=EventType.HALFWAY_BREAKOUT,
            stock_code="300750.SZ",
            timestamp=datetime.now(),
            data={"test": "data"},
            confidence=0.75,
            description="测试事件"
        )
        
        # 验证字段类型
        self.assertIsInstance(event.event_type, EventType)
        self.assertIsInstance(event.stock_code, str)
        self.assertIsInstance(event.timestamp, datetime)
        self.assertIsInstance(event.data, dict)
        self.assertIsInstance(event.confidence, (int, float))
        self.assertIsInstance(event.description, str)
    
    # ==========================================================================
    # 测试2: strategies目录无交易接口import
    # ==========================================================================
    
    def test_strategies_no_trading_imports(self):
        """测试strategies目录不允许import交易执行模块"""
        violations = []
        
        # 遍历strategies目录下的所有.py文件
        for py_file in self.strategies_dir.glob("*.py"):
            if py_file.name.startswith("test_"):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    # 检查import语句
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if any(trading_mod in alias.name 
                                   for trading_mod in self.trading_modules):
                                violations.append(
                                    f"{py_file.name}: 禁止import '{alias.name}'"
                                )
                    
                    # 检查from ... import语句
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            if any(trading_mod in node.module 
                                   for trading_mod in self.trading_modules):
                                violations.append(
                                    f"{py_file.name}: 禁止from '{node.module}' import"
                                )
                            # 检查从logic.trading import
                            if "trading" in node.module:
                                violations.append(
                                    f"{py_file.name}: 禁止从 '{node.module}' import "
                                    f"(strategies目录不应依赖trading层)"
                                )
            
            except Exception as e:
                violations.append(f"{py_file.name}: 解析失败 - {e}")
        
        # 报告违规
        if violations:
            self.fail("发现strategies目录违规import交易模块:\n" + 
                     "\n".join(f"  - {v}" for v in violations))
    
    def test_strategies_no_order_placement(self):
        """测试strategies目录没有下单相关函数调用"""
        forbidden_functions = [
            'submit_order', 'place_order', 'buy', 'sell',
            'xt_trader', 'XtQuantTrader', 'order_manager'
        ]
        
        violations = []
        
        for py_file in self.strategies_dir.glob("*.py"):
            if py_file.name.startswith("test_"):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    # 检查函数调用
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in forbidden_functions:
                                violations.append(
                                    f"{py_file.name}: 禁止调用 '{node.func.id}()'"
                                )
                        elif isinstance(node.func, ast.Attribute):
                            if node.func.attr in forbidden_functions:
                                violations.append(
                                    f"{py_file.name}: 禁止调用 'xxx.{node.func.attr}()'"
                                )
            
            except Exception as e:
                violations.append(f"{py_file.name}: 解析失败 - {e}")
        
        if violations:
            self.fail("发现strategies目录违规下单调用:\n" +
                     "\n".join(f"  - {v}" for v in violations))
    
    # ==========================================================================
    # 测试3: CapitalAllocator输入输出契约合规性
    # ==========================================================================
    
    def test_capital_allocator_interface(self):
        """测试CapitalAllocator接口符合契约"""
        try:
            from logic.portfolio.capital_allocator import CapitalAllocator
            
            # 检查allocate_capital方法签名（契约文档中的allocate）
            import inspect
            sig = inspect.signature(CapitalAllocator.allocate_capital)
            params = list(sig.parameters.keys())
            
            self.assertIn('opportunities', params,
                "CapitalAllocator.allocate_capital() 必须接受 'opportunities' 参数")
            self.assertIn('available_capital', params,
                "CapitalAllocator.allocate_capital() 必须接受 'available_capital' 参数")
            
        except ImportError:
            self.skipTest("CapitalAllocator未实现，跳过测试")
        except AttributeError:
            # 如果allocate_capital不存在，检查make_rebalance_decision
            try:
                from logic.portfolio.capital_allocator import CapitalAllocator
                import inspect
                sig = inspect.signature(CapitalAllocator.make_rebalance_decision)
                params = list(sig.parameters.keys())
                
                self.assertIn('current_positions', params,
                    "CapitalAllocator.make_rebalance_decision() 必须接受 'current_positions' 参数")
                self.assertIn('opportunity_pool', params,
                    "CapitalAllocator.make_rebalance_decision() 必须接受 'opportunity_pool' 参数")
            except AttributeError:
                self.fail("CapitalAllocator缺少决策方法（allocate_capital或make_rebalance_decision）")
    
    def test_capital_allocator_no_direct_data_provider(self):
        """测试CapitalAllocator不直接创建DataProvider"""
        allocator_file = PROJECT_ROOT / "logic" / "portfolio" / "capital_allocator.py"
        
        if not allocator_file.exists():
            self.skipTest("capital_allocator.py不存在，跳过测试")
        
        with open(allocator_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否直接实例化DataProvider或QMTHistoricalProvider
        forbidden_patterns = [
            'QMTHistoricalProvider(',
            'DataProvider(',
            'get_qmt_manager()',
            'xtdata.',
        ]
        
        violations = []
        for pattern in forbidden_patterns:
            if pattern in content:
                violations.append(f"CapitalAllocator不应直接调用 '{pattern}'")
        
        if violations:
            self.fail("CapitalAllocator违规直接访问数据层:\n" +
                     "\n".join(f"  - {v}" for v in violations))
    
    # ==========================================================================
    # 测试4: UnifiedWarfareCore冻结状态检查
    # ==========================================================================
    
    def test_unified_warfare_config_exists(self):
        """测试统一战法配置存在且有冻结开关"""
        config_file = PROJECT_ROOT / "config" / "portfolio_config.json"
        
        if not config_file.exists():
            self.skipTest("portfolio_config.json不存在，跳过测试")
        
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查是否有unified_warfare配置节
        if 'unified_warfare' not in config:
            self.fail("""portfolio_config.json 缺少 'unified_warfare' 配置节
根据SIGNAL_AND_PORTFOLIO_CONTRACT.md，必须添加:
{
  "unified_warfare": {
    "enabled": false,
    "mode": "observe_only",
    "participate_in_allocation": false
  }
}""")
        
        uw_config = config['unified_warfare']
        
        # 检查必要字段
        self.assertIn('enabled', uw_config,
            "unified_warfare配置缺少 'enabled' 字段")
        self.assertIn('participate_in_allocation', uw_config,
            "unified_warfare配置缺少 'participate_in_allocation' 字段")
        
        # V17阶段应为冻结状态
        if uw_config.get('participate_in_allocation', True):
            self.warning("""统一战法未冻结：participate_in_allocation=true
根据V17生产约束，应设为false""")


class TestBacktestEngineCompliance(unittest.TestCase):
    """回测引擎合规性测试"""
    
    def test_official_backtest_engine_exists(self):
        """测试官方统一回测引擎存在"""
        engine_file = PROJECT_ROOT / "logic" / "strategies" / "backtest_engine.py"
        self.assertTrue(engine_file.exists(),
            """logic/strategies/backtest_engine.py 不存在
这是V17唯一认可的回测引擎""")
    
    def test_private_engines_marked(self):
        """测试私有回测引擎已标记为研究用途"""
        private_engines = [
            PROJECT_ROOT / "backtest" / "run_halfway_replay_backtest.py",
            PROJECT_ROOT / "backtest" / "run_tick_backtest.py",
            PROJECT_ROOT / "backtest" / "run_comprehensive_backtest.py",
        ]
        
        for engine_file in private_engines:
            if not engine_file.exists():
                continue
                
            with open(engine_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含研究用途声明
            self.assertIn("研究用途", content,
                f"""{engine_file.name} 缺少'研究用途'声明
根据V17生产约束，私有回测引擎必须明确标记""")
            
            # 检查是否包含V17禁用声明
            self.assertTrue(
                "V17" in content or "v17" in content or "生产" in content,
                f"{engine_file.name} 缺少V17生产约束声明"
            )


def run_tests():
    """运行所有契约一致性测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestContractCompliance))
    suite.addTests(loader.loadTestsFromTestCase(TestBacktestEngineCompliance))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    print("="*80)
    print("🧪 契约一致性测试 (Contract Compliance Test)")
    print("="*80)
    print()
    print("测试范围：")
    print("  1. Detector返回值schema合规性")
    print("  2. strategies目录无交易接口import")
    print("  3. CapitalAllocator输入输出契约合规性")
    print("  4. 回测引擎合规性")
    print()
    
    success = run_tests()
    
    print()
    print("="*80)
    if success:
        print("✅ 所有契约一致性测试通过")
        print("="*80)
        sys.exit(0)
    else:
        print("❌ 契约一致性测试失败，请修复违规项")
        print("="*80)
        sys.exit(1)
