#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V17 Time-Lord 性能测试
测试时间策略管理器的性能
"""

import unittest
from datetime import datetime, time
from logic.time_strategy_manager import TimeStrategyManager, get_time_strategy_manager, TradingMode


class TestV17TimeLordPerformance(unittest.TestCase):
    """V17 Time-Lord 性能测试"""
    
    def setUp(self):
        """初始化测试环境"""
        self.time_manager = TimeStrategyManager()
    
    def test_get_current_mode_performance(self):
        """测试 get_current_mode 性能"""
        print("\n测试 get_current_mode 性能...")
        
        import time
        
        # 测试性能
        start_time = time.time()
        result = self.time_manager.get_current_mode()
        end_time = time.time()
        
        elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        print(f"✅ get_current_mode 耗时: {elapsed_time:.2f}ms")
        print(f"   当前模式: {result['mode_name']}")
        print(f"   描述: {result['description']}")
        print(f"   建议: {result['recommendation']}")
        
        # 性能要求：应该在 10ms 内完成
        self.assertLess(elapsed_time, 10, "get_current_mode 性能不达标")
    
    def test_should_filter_signal_performance(self):
        """测试 should_filter_signal 性能"""
        print("\n测试 should_filter_signal 性能...")
        
        import time
        
        # 测试不同信号的过滤
        signals = ["BUY", "SELL", "WAIT"]
        
        start_time = time.time()
        for signal in signals:
            filtered_signal, reason = self.time_manager.should_filter_signal(signal)
            print(f"   {signal} -> {filtered_signal}: {reason if reason else '保留'}")
        end_time = time.time()
        
        elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        print(f"✅ should_filter_signal (3个信号) 耗时: {elapsed_time:.2f}ms")
        print(f"   平均耗时: {elapsed_time/3:.2f}ms")
        
        # 性能要求：应该在 20ms 内完成
        self.assertLess(elapsed_time, 20, "should_filter_signal 性能不达标")
    
    def test_get_next_mode_switch_performance(self):
        """测试 get_next_mode_switch 性能"""
        print("\n测试 get_next_mode_switch 性能...")
        
        import time
        
        # 测试性能
        start_time = time.time()
        result = self.time_manager.get_next_mode_switch()
        end_time = time.time()
        
        elapsed_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        print(f"✅ get_next_mode_switch 耗时: {elapsed_time:.2f}ms")
        print(f"   下次切换: {result['next_mode_name']} @ {result['switch_time'].strftime('%H:%M')}")
        print(f"   剩余时间: {result['remaining_minutes']} 分钟 ({result['remaining_seconds']} 秒)")
        
        # 性能要求：应该在 10ms 内完成
        self.assertLess(elapsed_time, 10, "get_next_mode_switch 性能不达标")
    
    def test_mode_switching_accuracy(self):
        """测试模式切换准确性"""
        print("\n测试模式切换准确性...")
        
        # 测试不同时间点的模式
        test_cases = [
            (time(9, 30), TradingMode.AGGRESSIVE, "进攻模式"),
            (time(10, 30), TradingMode.DEFENSIVE, "防守模式"),
            (time(14, 45), TradingMode.SNIPE, "尾盘偷袭"),
            (time(16, 0), TradingMode.DEFENSIVE, "休眠模式"),
        ]
        
        for test_time, expected_mode, expected_name in test_cases:
            test_datetime = datetime(2026, 1, 18, test_time.hour, test_time.minute)
            result = self.time_manager.get_current_mode(test_datetime)
            
            self.assertEqual(result['mode'], expected_mode, f"时间 {test_time.strftime('%H:%M')} 模式错误")
            self.assertEqual(result['mode_name'], expected_name, f"时间 {test_time.strftime('%H:%M')} 模式名称错误")
            print(f"   ✅ {test_time.strftime('%H:%M')} -> {expected_name}")
    
    def test_signal_filtering_accuracy(self):
        """测试信号过滤准确性"""
        print("\n测试信号过滤准确性...")
        
        # 测试防守模式下的信号过滤
        test_time = datetime(2026, 1, 18, 10, 30)  # 10:30 - 垃圾时间
        
        # BUY 信号应该被过滤
        filtered_signal, reason = self.time_manager.should_filter_signal("BUY", test_time)
        self.assertEqual(filtered_signal, "WAIT", "防守模式下 BUY 信号应该被过滤")
        self.assertIn("禁止买入", reason)
        print(f"   ✅ BUY -> WAIT (防守模式)")
        
        # SELL 信号应该保留
        filtered_signal, reason = self.time_manager.should_filter_signal("SELL", test_time)
        self.assertEqual(filtered_signal, "SELL", "防守模式下 SELL 信号应该保留")
        print(f"   ✅ SELL -> SELL (防守模式)")
        
        # WAIT 信号应该保留
        filtered_signal, reason = self.time_manager.should_filter_signal("WAIT", test_time)
        self.assertEqual(filtered_signal, "WAIT", "防守模式下 WAIT 信号应该保留")
        print(f"   ✅ WAIT -> WAIT (防守模式)")
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        print("\n测试单例模式...")
        
        # 获取两个实例
        manager1 = get_time_strategy_manager()
        manager2 = get_time_strategy_manager()
        
        # 验证是否是同一个实例
        self.assertIs(manager1, manager2, "应该返回同一个实例")
        print(f"   ✅ 单例模式验证通过")


if __name__ == '__main__':
    # 运行测试
    print("=" * 80)
    print("V17 Time-Lord 性能测试")
    print("=" * 80)
    
    unittest.main(verbosity=2)