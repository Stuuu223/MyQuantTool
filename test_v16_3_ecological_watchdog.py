#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V16.3 生态看门人 - 测试用例
测试功能：
1. 换手率背离检测
2. 流动性黑洞检测
3. 决策熔断
4. 批量生态风险检查
"""

import unittest
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, '.')

from logic.iron_rule_monitor import IronRuleMonitor
from logic.signal_generator import SignalGenerator


class TestIronRuleMonitor(unittest.TestCase):
    """测试铁律监控器"""
    
    def setUp(self):
        """初始化测试环境"""
        self.iron_monitor = IronRuleMonitor()
    
    def test_check_value_distortion_normal(self):
        """测试检查价值扭曲（正常情况）"""
        # 模拟正常实时数据
        real_time_data = {
            'turnover': 2.0,  # 换手率 2%
            'pct_chg': 3.0,  # 涨幅 3%
            'amount': 100000000  # 成交额 1 亿
        }
        
        # 模拟历史数据（平均换手率 1.5%）
        mock_df = pd.DataFrame({
            'turnover': [1.0, 1.2, 1.5, 1.8, 2.0]
        })
        
        with patch.object(self.iron_monitor.data_manager, 'get_realtime_data') as mock_realtime:
            mock_realtime.return_value = real_time_data
            
            with patch.object(self.iron_monitor.data_manager, 'get_stock_daily') as mock_daily:
                mock_daily.return_value = mock_df
                
                # 检查价值扭曲
                result = self.iron_monitor.check_value_distortion('600519', real_time_data)
                
                # 验证结果
                self.assertFalse(result['has_risk'])
                self.assertEqual(result['risk_level'], 'LOW')
                self.assertFalse(result['turnover_anomaly'])
                self.assertFalse(result['liquidity_blackhole'])
    
    def test_check_value_distortion_turnover_anomaly(self):
        """测试检查价值扭曲（换手率异常）"""
        # 模拟异常实时数据（换手率爆炸）
        real_time_data = {
            'turnover': 10.0,  # 换手率 10%
            'pct_chg': 7.0,  # 涨幅 7%
            'amount': 500000000  # 成交额 5 亿
        }
        
        # 模拟历史数据（平均换手率 1%）
        mock_df = pd.DataFrame({
            'turnover': [0.8, 0.9, 1.0, 1.1, 1.2]
        })
        
        with patch.object(self.iron_monitor.data_manager, 'get_realtime_data') as mock_realtime:
            mock_realtime.return_value = real_time_data
            
            with patch.object(self.iron_monitor.data_manager, 'get_stock_daily') as mock_daily:
                mock_daily.return_value = mock_df
                
                # 检查价值扭曲
                result = self.iron_monitor.check_value_distortion('600519', real_time_data)
                
                # 验证结果
                self.assertTrue(result['has_risk'])
                self.assertEqual(result['risk_level'], 'DANGER')
                self.assertTrue(result['turnover_anomaly'])
                self.assertGreater(result['turnover_ratio'], 5.0)
                self.assertIn('换手率爆炸', result['reason'])
    
    def test_check_value_distortion_liquidity_blackhole(self):
        """测试检查价值扭曲（流动性黑洞）"""
        # 模拟正常实时数据
        real_time_data = {
            'turnover': 2.0,  # 换手率 2%
            'pct_chg': 3.0,  # 涨幅 3%
            'amount': 300000000  # 成交额 3 亿
        }
        
        # 模拟历史数据（平均换手率 1.5%）
        mock_df = pd.DataFrame({
            'turnover': [1.0, 1.2, 1.5, 1.8, 2.0]
        })
        
        # 模拟股票信息
        mock_stock_info = {
            'industry': '银行',
            'concept': '金融'
        }
        
        # 模拟板块股票
        mock_sector_stocks = ['600519', '000001', '000002', '601318', '600036']
        
        # 模拟板块总成交额（1 亿）
        def mock_get_realtime_data(code):
            if code == '600519':
                return real_time_data
            else:
                return {'amount': 10000000}  # 其他股票成交额 1000 万
        
        with patch.object(self.iron_monitor.data_manager, 'get_realtime_data') as mock_realtime:
            mock_realtime.side_effect = mock_get_realtime_data
            
            with patch.object(self.iron_monitor.data_manager, 'get_stock_daily') as mock_daily:
                mock_daily.return_value = mock_df
                
                with patch.object(self.iron_monitor.data_manager, 'get_stock_info') as mock_info:
                    mock_info.return_value = mock_stock_info
                    
                    with patch.object(self.iron_monitor.data_manager, 'get_industry_stocks') as mock_sector:
                        mock_sector.return_value = mock_sector_stocks
                        
                        # 检查价值扭曲
                        result = self.iron_monitor.check_value_distortion('600519', real_time_data)
                        
                        # 验证结果（板块占比 > 30%）
                        self.assertTrue(result['has_risk'])
                        self.assertEqual(result['risk_level'], 'WARNING')
                        self.assertTrue(result['liquidity_blackhole'])
                        self.assertGreater(result['sector_ratio'], 0.30)
                        self.assertIn('吸干板块流动性', result['reason'])
    
    def test_get_ecological_risk_summary(self):
        """测试获取生态风险摘要"""
        # 模拟风险数据
        mock_risk_danger = {
            'has_risk': True,
            'risk_level': 'DANGER',
            'turnover_anomaly': True,
            'liquidity_blackhole': False,
            'turnover_ratio': 8.0,
            'sector_ratio': 0.1,
            'reason': '🔥 [生态异常] 价值票游资化，换手率爆炸(8.0倍均值)，涨幅7.0%，谨防接盘'
        }
        
        mock_risk_warning = {
            'has_risk': True,
            'risk_level': 'WARNING',
            'turnover_anomaly': False,
            'liquidity_blackhole': True,
            'turnover_ratio': 2.0,
            'sector_ratio': 0.35,
            'reason': '🌪️ [虹吸效应] 个股吸干板块流动性(35.0%)，独木难支'
        }
        
        mock_risk_normal = {
            'has_risk': False,
            'risk_level': 'LOW',
            'turnover_anomaly': False,
            'liquidity_blackhole': False,
            'turnover_ratio': 1.0,
            'sector_ratio': 0.05,
            'reason': '生态正常'
        }
        
        with patch.object(self.iron_monitor, 'check_value_distortion') as mock_method:
            mock_method.side_effect = [
                mock_risk_danger,
                mock_risk_warning,
                mock_risk_normal
            ]
            
            # 获取生态风险摘要
            stock_codes = ['600519', '000001', '000002']
            summary = self.iron_monitor.get_ecological_risk_summary(stock_codes)
            
            # 验证结果
            self.assertEqual(summary['total_stocks'], 3)
            self.assertEqual(len(summary['danger_stocks']), 1)
            self.assertEqual(len(summary['warning_stocks']), 1)
            self.assertEqual(len(summary['normal_stocks']), 1)
            self.assertIn('600519', summary['danger_stocks'])
            self.assertIn('000001', summary['warning_stocks'])
            self.assertIn('000002', summary['normal_stocks'])


class TestSignalGenerator(unittest.TestCase):
    """测试信号生成器"""
    
    def setUp(self):
        """初始化测试环境"""
        self.signal_generator = SignalGenerator()
    
    def test_calculate_final_signal_with_eco_danger(self):
        """测试计算最终信号（存在生态危险）"""
        # 模拟生态危险数据
        mock_eco_risk = {
            'has_risk': True,
            'risk_level': 'DANGER',
            'turnover_anomaly': True,
            'liquidity_blackhole': False,
            'turnover_ratio': 8.0,
            'sector_ratio': 0.1,
            'reason': '🔥 [生态异常] 价值票游资化，换手率爆炸(8.0倍均值)，涨幅7.0%，谨防接盘'
        }
        
        with patch.object(IronRuleMonitor, 'check_value_distortion') as mock_method:
            mock_method.return_value = mock_eco_risk
            
            # 计算最终信号
            result = self.signal_generator.calculate_final_signal(
                stock_code='600519',
                ai_score=90.0,
                capital_flow=10000000,  # 资金流入
                trend='UP',
                current_pct_change=7.0,
                yesterday_lhb_net_buy=0,
                open_pct_change=3.0,
                circulating_market_cap=1000000000,
                market_sentiment_score=50,
                market_status='震荡'
            )
            
            # 验证结果
            self.assertEqual(result['signal'], 'WAIT')
            self.assertEqual(result['score'], 0)
            self.assertIn('生态熔断', result['reason'])
            self.assertIn('eco_risk', result)
    
    def test_calculate_final_signal_with_eco_warning(self):
        """测试计算最终信号（存在生态警告）"""
        # 模拟生态警告数据
        mock_eco_risk = {
            'has_risk': True,
            'risk_level': 'WARNING',
            'turnover_anomaly': False,
            'liquidity_blackhole': True,
            'turnover_ratio': 2.0,
            'sector_ratio': 0.35,
            'reason': '🌪️ [虹吸效应] 个股吸干板块流动性(35.0%)，独木难支'
        }
        
        with patch.object(IronRuleMonitor, 'check_value_distortion') as mock_method:
            mock_method.return_value = mock_eco_risk
            
            # 计算最终信号
            result = self.signal_generator.calculate_final_signal(
                stock_code='000001',
                ai_score=90.0,
                capital_flow=10000000,
                trend='UP',
                current_pct_change=3.0,
                yesterday_lhb_net_buy=0,
                open_pct_change=2.0,
                circulating_market_cap=1000000000,
                market_sentiment_score=50,
                market_status='震荡'
            )
            
            # 验证结果（AI 分数应该降权 50%）
            self.assertEqual(result['score'], 45.0)  # 90.0 * 0.5
            self.assertIn('生态降权', result['reason'])
    
    def test_calculate_final_signal_without_eco_risk(self):
        """测试计算最终信号（无生态风险）"""
        # 模拟无生态风险数据
        mock_eco_risk = {
            'has_risk': False,
            'risk_level': 'LOW',
            'turnover_anomaly': False,
            'liquidity_blackhole': False,
            'turnover_ratio': 1.0,
            'sector_ratio': 0.05,
            'reason': '生态正常'
        }
        
        with patch.object(IronRuleMonitor, 'check_value_distortion') as mock_method:
            mock_method.return_value = mock_eco_risk
            
            # 计算最终信号
            result = self.signal_generator.calculate_final_signal(
                stock_code='000002',
                ai_score=90.0,
                capital_flow=10000000,
                trend='UP',
                current_pct_change=3.0,
                yesterday_lhb_net_buy=0,
                open_pct_change=2.0,
                circulating_market_cap=1000000000,
                market_sentiment_score=50,
                market_status='震荡'
            )
            
            # 验证结果（不应该被生态熔断）
            self.assertNotEqual(result['signal'], 'WAIT')
            self.assertNotIn('生态熔断', result.get('reason', ''))


class TestV16_3_Integration(unittest.TestCase):
    """V16.3 集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        # 初始化组件
        iron_monitor = IronRuleMonitor()
        signal_generator = SignalGenerator()
        
        # 模拟多只股票的风险数据
        stock_codes = ['600519', '000001', '000002']
        
        # 获取生态风险摘要
        summary = iron_monitor.get_ecological_risk_summary(stock_codes)
        
        # 验证风险摘要
        self.assertEqual(summary['total_stocks'], 3)
        self.assertIn('risk_details', summary)
        
        # 测试信号生成（假设 600519 有生态危险）
        mock_eco_risk = {
            'has_risk': True,
            'risk_level': 'DANGER',
            'turnover_anomaly': True,
            'liquidity_blackhole': False,
            'turnover_ratio': 8.0,
            'sector_ratio': 0.1,
            'reason': '🔥 [生态异常] 价值票游资化，换手率爆炸(8.0倍均值)，涨幅7.0%，谨防接盘'
        }
        
        with patch.object(IronRuleMonitor, 'check_value_distortion') as mock_method:
            mock_method.return_value = mock_eco_risk
            
            # 计算最终信号
            result = signal_generator.calculate_final_signal(
                stock_code='600519',
                ai_score=90.0,
                capital_flow=10000000,
                trend='UP',
                current_pct_change=7.0,
                yesterday_lhb_net_buy=0,
                open_pct_change=3.0,
                circulating_market_cap=1000000000,
                market_sentiment_score=50,
                market_status='震荡'
            )
            
            # 验证结果
            self.assertEqual(result['signal'], 'WAIT')
            self.assertEqual(result['score'], 0)
            self.assertIn('生态熔断', result['reason'])


def run_tests():
    """运行所有测试"""
    print("=" * 80)
    print("V16.3 生态看门人 - 测试")
    print("=" * 80)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试
    suite.addTests(loader.loadTestsFromTestCase(TestIronRuleMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestSignalGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestV16_3_Integration))
    
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
