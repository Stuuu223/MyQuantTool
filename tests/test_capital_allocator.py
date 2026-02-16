# -*- coding: utf-8 -*-
"""
CapitalAllocator单元测试

版本：V17.0.0
创建日期：2026-02-16
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logic.portfolio.capital_allocator import CapitalAllocator, Position
from logic.portfolio.portfolio_metrics import PortfolioMetrics


class TestCapitalAllocator:
    """CapitalAllocator测试"""
    
    def test_initialization(self):
        """测试初始化"""
        allocator = CapitalAllocator()
        
        assert allocator.max_positions == 3
        assert allocator.max_drawdown == -0.12
        assert allocator.single_threshold == 1.5
        assert len(allocator.positions) == 0
        
        print("✅ 测试通过: CapitalAllocator初始化")
    
    def test_calculate_comprehensive_score(self):
        """测试综合评分"""
        allocator = CapitalAllocator()
        
        # 测试高分机会（ratio=3%, 板块共振, 风险低）
        opportunity_high = {
            'code': '000001.SZ',
            'ratio': 0.03,
            'sector_resonance': {'is_resonance': True, 'score': 0.9},
            'risk_score': 0.05,
            'confidence': 0.9
        }
        score_high = allocator._calculate_comprehensive_score(opportunity_high)
        assert score_high > 0.7  # 高分
        
        # 测试低分机会（ratio=0.5%, 无板块共振, 风险高）
        opportunity_low = {
            'code': '000002.SZ',
            'ratio': 0.005,
            'sector_resonance': {'is_resonance': False, 'score': 0.0},
            'risk_score': 0.4,
            'confidence': 0.3
        }
        score_low = allocator._calculate_comprehensive_score(opportunity_low)
        assert score_low < 0.3  # 低分
        
        # 高分应该大于低分
        assert score_high > score_low
        
        print(f"✅ 测试通过: 综合评分 (高分={score_high:.2f}, 低分={score_low:.2f})")
    
    def test_check_position_exit(self):
        """测试平仓检查"""
        allocator = CapitalAllocator()
        
        # 测试主力出逃
        position_with_outflow = {
            'hold_days': 2,
            'main_net_inflow': -100_000_000,  # 主力大幅流出
            'risk_score': 0.1,
            'profit_rate': 0.05
        }
        should_exit, reason = allocator._check_position_exit(position_with_outflow)
        assert should_exit
        assert '主力出逃' in reason
        
        # 测试风险恶化
        position_with_high_risk = {
            'hold_days': 2,
            'main_net_inflow': 10_000_000,
            'risk_score': 0.5,  # 风险评分高
            'profit_rate': 0.05
        }
        should_exit, reason = allocator._check_position_exit(position_with_high_risk)
        assert should_exit
        assert '风险恶化' in reason
        
        # 测试极限回撤
        position_with_drawdown = {
            'hold_days': 2,
            'main_net_inflow': 10_000_000,
            'risk_score': 0.1,
            'profit_rate': -0.15  # 回撤超过-12%
        }
        should_exit, reason = allocator._check_position_exit(position_with_drawdown)
        assert should_exit
        assert '极限回撤' in reason
        
        # 测试机会成本过高
        position_with_opportunity_cost = {
            'hold_days': 10,  # 持有10天
            'main_net_inflow': 10_000_000,
            'risk_score': 0.1,
            'profit_rate': 0.02  # 收益只有2%，低于3%
        }
        should_exit, reason = allocator._check_position_exit(position_with_opportunity_cost)
        assert should_exit
        assert '机会成本过高' in reason
        
        # 测试继续持有
        position_ok = {
            'hold_days': 2,
            'main_net_inflow': 10_000_000,
            'risk_score': 0.1,
            'profit_rate': 0.05  # 正常持有
        }
        should_exit, reason = allocator._check_position_exit(position_ok)
        assert not should_exit
        assert '继续持有' in reason
        
        print("✅ 测试通过: 平仓检查（主力出逃、风险恶化、极限回撤、机会成本过高）")
    
    def test_allocate_capital_single_position(self):
        """测试单只股票仓位分配"""
        allocator = CapitalAllocator()
        
        # 只有1个机会
        opportunities = [
            {
                'code': '000001.SZ',
                'ratio': 0.03,
                'sector_resonance': {'is_resonance': True, 'score': 0.9},
                'risk_score': 0.05,
                'confidence': 0.9
            }
        ]
        
        allocation = allocator.allocate_capital(opportunities, available_capital=100000)
        
        assert len(allocation) == 1
        assert allocation[0]['code'] == '000001.SZ'
        assert allocation[0]['capital'] == 90000  # 90%仓位
        
        print(f"✅ 测试通过: 单只股票仓位分配 ({allocation[0]['capital']}元)")
    
    def test_allocate_capital_gap_advantage(self):
        """测试断层优势识别"""
        allocator = CapitalAllocator()
        
        # 2个机会，第1个明显优于第2个
        opportunities = [
            {
                'code': '000001.SZ',
                'ratio': 0.03,  # 3%
                'sector_resonance': {'is_resonance': True, 'score': 0.9},
                'risk_score': 0.05,
                'confidence': 0.9
            },
            {
                'code': '000002.SZ',
                'ratio': 0.01,  # 1%
                'sector_resonance': {'is_resonance': False, 'score': 0.0},
                'risk_score': 0.3,
                'confidence': 0.5
            }
        ]
        
        allocation = allocator.allocate_capital(opportunities, available_capital=100000)
        
        # 应该识别出断层优势，单吊第1个
        assert len(allocation) == 1
        assert allocation[0]['code'] == '000001.SZ'
        assert allocation[0]['capital'] == 90000  # 90%仓位
        
        print(f"✅ 测试通过: 断层优势识别（单吊{allocation[0]['code']}）")
    
    def test_allocate_capital_dual_positions(self):
        """测试2只股票分散"""
        allocator = CapitalAllocator()
        
        # 2个机会，没有断层优势
        opportunities = [
            {
                'code': '000001.SZ',
                'ratio': 0.02,  # 2%
                'sector_resonance': {'is_resonance': True, 'score': 0.7},
                'risk_score': 0.1,
                'confidence': 0.8
            },
            {
                'code': '000002.SZ',
                'ratio': 0.018,  # 1.8%
                'sector_resonance': {'is_resonance': True, 'score': 0.6},
                'risk_score': 0.15,
                'confidence': 0.7
            }
        ]
        
        allocation = allocator.allocate_capital(opportunities, available_capital=100000)
        
        # 应该2只分散
        assert len(allocation) == 2
        assert allocation[0]['code'] == '000001.SZ'
        assert allocation[1]['code'] == '000002.SZ'
        assert allocation[0]['capital'] == 60000  # 60%仓位
        assert allocation[1]['capital'] == 40000  # 40%仓位
        
        print(f"✅ 测试通过: 2只股票分散（{allocation[0]['code']}={allocation[0]['capital']}元, {allocation[1]['code']}={allocation[1]['capital']}元）")
    
    def test_allocate_capital_triple_positions(self):
        """测试3只股票分散"""
        allocator = CapitalAllocator()
        
        # 3个机会
        opportunities = [
            {
                'code': '000001.SZ',
                'ratio': 0.02,
                'sector_resonance': {'is_resonance': True, 'score': 0.7},
                'risk_score': 0.1,
                'confidence': 0.8
            },
            {
                'code': '000002.SZ',
                'ratio': 0.018,
                'sector_resonance': {'is_resonance': True, 'score': 0.6},
                'risk_score': 0.15,
                'confidence': 0.7
            },
            {
                'code': '000003.SZ',
                'ratio': 0.015,
                'sector_resonance': {'is_resonance': True, 'score': 0.5},
                'risk_score': 0.2,
                'confidence': 0.6
            }
        ]
        
        allocation = allocator.allocate_capital(opportunities, available_capital=100000)
        
        # 应该3只分散
        assert len(allocation) == 3
        assert allocation[0]['capital'] == 50000  # 50%仓位
        assert allocation[1]['capital'] == 30000  # 30%仓位
        assert allocation[2]['capital'] == 20000  # 20%仓位
        
        print(f"✅ 测试通过: 3只股票分散（50%+30%+20%）")


class TestPosition:
    """Position测试"""
    
    def test_position_properties(self):
        """测试Position属性"""
        position = Position(
            code='000001.SZ',
            name='平安银行',
            shares=1000,
            cost_price=10.0,
            current_price=10.0,
            buy_time=datetime.now()
        )
        
        # 测试市值
        assert position.market_value == 10000  # 1000 * 10.0
        
        # 测试浮动盈亏
        assert position.unrealized_pnl == 0.0  # (10.0 - 10.0) * 1000
        
        # 测试收益率
        assert position.return_pct == 0.0  # (10.0 - 10.0) / 10.0
        
        # 更新价格
        position.update_price(11.0)
        
        # 测试更新后的属性
        assert position.current_price == 11.0
        assert position.market_value == 11000  # 1000 * 11.0
        assert position.unrealized_pnl == 1000  # (11.0 - 10.0) * 1000
        assert position.return_pct == 0.1  # (11.0 - 10.0) / 10.0
        
        print("✅ 测试通过: Position属性（市值、浮动盈亏、收益率）")
    
    def test_position_close(self):
        """测试Position平仓"""
        buy_time = datetime.now()
        position = Position(
            code='000001.SZ',
            name='平安银行',
            shares=1000,
            cost_price=10.0,
            current_price=10.0,
            buy_time=buy_time
        )
        
        # 同一天平仓
        sell_time = buy_time
        position.close(sell_price=12.0, sell_time=sell_time)
        
        assert position.current_price == 12.0
        assert position.sell_time == sell_time
        assert position.is_sold_today == True  # 同一天卖出
        
        print("✅ 测试通过: Position平仓（T+1约束）")


class TestPortfolioMetrics:
    """PortfolioMetrics测试"""
    
    def test_record_opportunity(self):
        """测试记录起爆点捕捉"""
        metrics = PortfolioMetrics()
        
        metrics.record_opportunity('000001.SZ', '半路突破')
        
        assert metrics.current_metrics.起爆点捕捉数 == 1
        
        print("✅ 测试通过: 记录起爆点捕捉")
    
    def test_record_rebalance(self):
        """测试记录调仓操作"""
        metrics = PortfolioMetrics()
        
        metrics.record_rebalance('000001.SZ', '000002.SZ', 0.05)
        
        assert metrics.current_metrics.调仓次数 == 1
        assert metrics.current_metrics.换仓收益 == 0.05
        
        print("✅ 测试通过: 记录调仓操作")
    
    def test_record_exit(self):
        """测试记录平仓操作"""
        metrics = PortfolioMetrics()
        
        metrics.record_exit('000001.SZ', '主力出逃', 3, 0.08)
        
        assert metrics.current_metrics.退出原因分布['主力出逃'] == 1
        assert metrics.current_metrics.持仓天数分布[3] == 1
        
        print("✅ 测试通过: 记录平仓操作")
    
    def test_generate_daily_report(self):
        """测试生成每日报告"""
        metrics = PortfolioMetrics()
        
        # 模拟一些数据
        metrics.record_opportunity('000001.SZ', '半路突破')
        metrics.record_rebalance('000001.SZ', '000002.SZ', 0.05)
        metrics.record_exit('000002.SZ', '主力出逃', 3, 0.08)
        metrics.update_account_metrics(account_value=105000, peak_value=105000, available_capital=50000)
        
        report = metrics.generate_daily_report()
        
        assert 'MyQuantTool 每日业务报告' in report
        assert '起爆点捕捉: 1次' in report
        assert '调仓次数: 1次' in report
        assert '换仓收益: 5.00%' in report
        assert '主力出逃: 1次' in report
        
        print("✅ 测试通过: 生成每日报告")


if __name__ == '__main__':
    # 运行所有测试
    print("=" * 60)
    print("🧪 CapitalAllocator单元测试")
    print("=" * 60)
    
    # 测试CapitalAllocator
    print("\n📋 测试CapitalAllocator:")
    test_allocator = TestCapitalAllocator()
    test_allocator.test_initialization()
    test_allocator.test_calculate_comprehensive_score()
    test_allocator.test_check_position_exit()
    test_allocator.test_allocate_capital_single_position()
    test_allocator.test_allocate_capital_gap_advantage()
    test_allocator.test_allocate_capital_dual_positions()
    test_allocator.test_allocate_capital_triple_positions()
    
    # 测试Position
    print("\n📋 测试Position:")
    test_position = TestPosition()
    test_position.test_position_properties()
    test_position.test_position_close()
    
    # 测试PortfolioMetrics
    print("\n📋 测试PortfolioMetrics:")
    test_metrics = TestPortfolioMetrics()
    test_metrics.test_record_opportunity()
    test_metrics.test_record_rebalance()
    test_metrics.test_record_exit()
    test_metrics.test_generate_daily_report()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
