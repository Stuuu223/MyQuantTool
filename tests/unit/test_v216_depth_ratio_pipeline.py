"""
【CTO V219】深度比管道测试 - 经典物理版本

测试目标：验证depth_ratio回归经典物理
- 废除Sigmoid魔法
- 保留对数对称公式的狂野极值[-∞,+∞]
- 物理意义：>0买盘强，<0卖盘强，=0平衡

【V219核心】depth_ratio必须转化为MFE惩罚装甲，而非展示项！
"""

import pytest
import math
from datetime import datetime


class TestStandardTickDepthRatio:
    """【CTO V219】StandardTick.depth_ratio 经典物理测试"""
    
    def test_depth_ratio_calculation(self):
        """测试depth_ratio的对数计算（废除Sigmoid）"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_prices=[9.99, 9.98, 9.97, 9.96, 9.95],
            ask_prices=[10.01, 10.02, 10.03, 10.04, 10.05],
            bid_vols=[100, 200, 300, 400, 500],  # sum=1500
            ask_vols=[50, 100, 150, 200, 250],   # sum=750
        )
        
        # 【V219】直接返回对数值，不再Sigmoid
        expected = math.log(1501.0 / 751.0)  # ≈0.69
        assert abs(tick.depth_ratio - expected) < 0.001, \
            f"Expected {expected}, got {tick.depth_ratio}"
        # 应该是正数（买盘强）
        assert tick.depth_ratio > 0
    
    def test_depth_ratio_empty_vols(self):
        """测试空盘口情况 - 应返回0（绝对平衡）"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_vols=[],
            ask_vols=[],
        )
        
        # 空盘口：ln(1/1)=0
        assert abs(tick.depth_ratio - 0.0) < 0.001, \
            f"Empty orderbook should return 0, got {tick.depth_ratio}"
    
    def test_depth_ratio_sell_pressure(self):
        """测试卖压大于买压 - 应返回负数"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=10.0,
            bid_vols=[100, 100, 100, 100, 100],  # sum=500
            ask_vols=[500, 500, 500, 500, 500],  # sum=2500
        )
        
        # 【V219】卖压>买压，应该返回负数！
        assert tick.depth_ratio < 0, \
            f"Sell pressure should be negative, got {tick.depth_ratio}"
        # ln(501/2501) ≈ -1.61
        expected = math.log(501.0 / 2501.0)
        assert abs(tick.depth_ratio - expected) < 0.01


class TestDepthRatioPhysicalPunishment:
    """【CTO V219核心】深度比转化为物理惩罚测试"""
    
    def test_extreme_buy_pressure_value(self):
        """测试极端买压的对数值"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=11.0,
            bid_vols=[100000, 100000, 100000, 100000, 100000],  # sum=500000
            ask_vols=[10, 10, 10, 10, 10],  # sum=50
        )
        
        # 【V219】极端买压应返回较大正数（≈+9.2）
        # ln(500001/51) ≈ 9.2
        expected = math.log(500001.0 / 51.0)
        assert abs(tick.depth_ratio - expected) < 0.1, \
            f"Extreme buy should be ~9.2, got {tick.depth_ratio}"
        assert tick.depth_ratio > 5.0  # 明显买压
    
    def test_extreme_sell_pressure_value(self):
        """测试极端卖压的对数值"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=9.0,
            bid_vols=[10, 10, 10, 10, 10],  # sum=50
            ask_vols=[100000, 100000, 100000, 100000, 100000],  # sum=500000
        )
        
        # 【V219】极端卖压应返回较大负数（≈-9.2）
        # ln(51/500001) ≈ -9.2
        expected = math.log(51.0 / 500001.0)
        assert abs(tick.depth_ratio - expected) < 0.1, \
            f"Extreme sell should be ~-9.2, got {tick.depth_ratio}"
        assert tick.depth_ratio < -5.0  # 明显卖压
    
    def test_neutral_pressure(self):
        """测试中性盘口 - 应等于0"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=10.0,
            bid_vols=[100, 100, 100, 100, 100],  # sum=500
            ask_vols=[100, 100, 100, 100, 100],  # sum=500
        )
        
        # ln(501/501)=0
        assert abs(tick.depth_ratio - 0.0) < 0.001, \
            f"Neutral should be 0, got {tick.depth_ratio}"
    
    def test_symmetry_verification(self):
        """验证对数对称性：买压N:1 vs 卖压1:N"""
        from logic.data_providers.standard_tick import StandardTick
        
        # 买压100:卖压1
        tick_buy = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=10.0,
            bid_vols=[100, 0, 0, 0, 0],
            ask_vols=[1, 0, 0, 0, 0],
        )
        
        # 卖压1:买压100
        tick_sell = StandardTick(
            code='000002.SZ',
            time='20260319094500',
            last_price=10.0,
            bid_vols=[1, 0, 0, 0, 0],
            ask_vols=[100, 0, 0, 0, 0],
        )
        
        # 【V219验证】对数对称性：depth_ratio_buy ≈ -depth_ratio_sell
        assert abs(tick_buy.depth_ratio + tick_sell.depth_ratio) < 0.001, \
            f"Symmetry broken: {tick_buy.depth_ratio} vs {tick_sell.depth_ratio}"


class TestToQmtDictDepthRatio:
    """【V219】to_qmt_dict()输出测试"""
    
    def test_to_qmt_dict_contains_depth_ratio(self):
        """测试to_qmt_dict输出包含对数depthRatio"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=10.0,
            bid_vols=[100, 200, 300, 400, 500],  # 买压强
            ask_vols=[50, 100, 150, 200, 250],
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        assert 'depthRatio' in qmt_dict
        # 【V219】应该返回对数值，可能是正数
        assert qmt_dict['depthRatio'] > 0  # 买压强
    
    def test_to_qmt_dict_negative_depth_ratio(self):
        """测试卖压下to_qmt_dict输出负数"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260319094500',
            last_price=10.0,
            bid_vols=[50, 50, 50, 50, 50],    # 买压弱
            ask_vols=[500, 500, 500, 500, 500],  # 卖压强
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        # 【V219】卖压强应该返回负数
        assert qmt_dict['depthRatio'] < 0


class TestUniversalTrackerDepthRatio:
    """【V219】UniversalTracker接收depth_ratio测试"""
    
    def test_on_frame_receives_depth_ratio(self):
        """测试on_frame正确接收对数depth_ratio"""
        import tempfile
        from logic.execution.universal_tracker import UniversalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = UniversalTracker(output_dir=tmpdir)
            
            # 【V219】depth_ratio可能是负数
            top_targets = [{
                'code': '000001.SZ',
                'score': 100.0,
                'price': 10.0,
                'change': 5.0,
                'inflow_ratio': 2.0,
                'ratio_stock': 3.0,
                'sustain_ratio': 1.5,
                'mfe': 2.5,
                'purity': 0.8,
                'depth_ratio': -2.5,  # 【V219】卖压，负数
            }]
            
            tracker.on_frame(
                top_targets=top_targets,
                current_time=datetime(2026, 3, 19, 9, 45, 0),
                global_prices={'000001.SZ': 10.0}
            )
            
            assert '000001.SZ' in tracker.registry


class TestMfePunishmentIntegration:
    """【V219核心】MFE惩罚装甲集成测试"""
    
    def test_depth_ratio_thresholds(self):
        """测试深度比阈值定义"""
        from logic.data_providers.standard_tick import StandardTick
        
        # 构造不同深度比的场景
        scenarios = [
            ([1000], [1], "极端买压", 6.9),      # ln(1001/2) ≈ 6.2
            ([100], [1], "强买压", 4.6),          # ln(101/2) ≈ 3.9
            ([10], [1], "中等买压", 2.4),         # ln(11/2) ≈ 1.7
            ([1], [1], "平衡", 0.0),              # ln(2/2) = 0
            ([1], [10], "中等卖压", -2.4),        # ln(2/11) ≈ -1.7
            ([1], [100], "强卖压", -4.6),         # ln(2/101) ≈ -3.9
            ([1], [1000], "极端卖压", -6.9),      # ln(2/1001) ≈ -6.2
        ]
        
        for bid, ask, desc, expected_range in scenarios:
            tick = StandardTick(
                code='000001.SZ',
                time='20260319094500',
                last_price=10.0,
                bid_vols=bid,
                ask_vols=ask,
            )
            
            # 验证方向
            if "买压" in desc and "极端" not in desc:
                assert tick.depth_ratio > 0, f"{desc} should be positive"
            elif "卖压" in desc and "极端" not in desc:
                assert tick.depth_ratio < 0, f"{desc} should be negative"
            elif "平衡" in desc:
                assert abs(tick.depth_ratio) < 0.1, f"{desc} should be near 0"
            
            print(f"  {desc}: depth_ratio={tick.depth_ratio:.2f}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
