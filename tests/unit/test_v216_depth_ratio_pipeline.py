"""
【CTO V218】深度比管道测试 - Sigmoid归一化版本

测试目标：验证depth_ratio的Sigmoid归一化防爆盾
- raw_depth_ratio: 原始对数值[-∞,+∞]
- depth_ratio: Sigmoid归一化[0,1]

测试铁律：
1. depth_ratio永远在[0,1]区间，永不爆炸
2. 0.5是绝对平衡点，>0.5买盘强，<0.5卖盘强
3. 必须测试边界条件（极端买压逼近1.0，极端卖压逼近0.0）
"""

import pytest
import math
from datetime import datetime


class TestStandardTickDepthRatio:
    """【CTO V218】StandardTick.depth_ratio Sigmoid归一化测试"""
    
    def test_depth_ratio_calculation(self):
        """测试depth_ratio的Sigmoid归一化计算"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_prices=[9.99, 9.98, 9.97, 9.96, 9.95],
            ask_prices=[10.01, 10.02, 10.03, 10.04, 10.05],
            bid_vols=[100, 200, 300, 400, 500],  # sum=1500
            ask_vols=[50, 100, 150, 200, 250],   # sum=750
        )
        
        # raw_depth_ratio = ln(1501/751) ≈ 0.69
        raw_expected = math.log(1501.0 / 751.0)
        # sigmoid(0.69) ≈ 0.666
        expected = 1.0 / (1.0 + math.exp(-raw_expected))
        
        assert abs(tick.depth_ratio - expected) < 0.001, \
            f"Expected {expected}, got {tick.depth_ratio}"
        # 【V218】必须在[0,1]区间
        assert 0.0 <= tick.depth_ratio <= 1.0, \
            f"depth_ratio must be in [0,1], got {tick.depth_ratio}"
    
    def test_depth_ratio_empty_vols(self):
        """测试空盘口情况 - 应返回0.5（绝对平衡）"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_prices=[],
            ask_prices=[],
            bid_vols=[],
            ask_vols=[],
        )
        
        # 空盘口：raw=ln(1/1)=0，sigmoid(0)=0.5
        assert abs(tick.depth_ratio - 0.5) < 0.001, \
            f"Empty orderbook should return 0.5, got {tick.depth_ratio}"
    
    def test_depth_ratio_none_vols(self):
        """测试None盘口情况 - 应返回0.5（类型收敛+绝对平衡）"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_prices=None,
            ask_prices=None,
            bid_vols=None,
            ask_vols=None,
        )
        
        # None盘口也应返回0.5
        assert abs(tick.depth_ratio - 0.5) < 0.001, \
            f"None orderbook should return 0.5, got {tick.depth_ratio}"
    
    def test_depth_ratio_sell_pressure(self):
        """测试卖压大于买压情况 - 应<0.5"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_prices=[9.99, 9.98, 9.97, 9.96, 9.95],
            ask_prices=[10.01, 10.02, 10.03, 10.04, 10.05],
            bid_vols=[100, 100, 100, 100, 100],  # sum=500
            ask_vols=[500, 500, 500, 500, 500],  # sum=2500
        )
        
        # 卖压>买压，depth_ratio应该<0.5
        assert tick.depth_ratio < 0.5, \
            f"Sell pressure should have depth_ratio < 0.5, got {tick.depth_ratio}"
        assert 0.0 <= tick.depth_ratio <= 1.0, \
            f"Must be in [0,1], got {tick.depth_ratio}"


class TestRawDepthRatio:
    """【CTO V218】raw_depth_ratio原始对数值测试"""
    
    def test_raw_depth_ratio_returns_raw_log(self):
        """测试raw_depth_ratio返回原始对数值（可正可负）"""
        from logic.data_providers.standard_tick import StandardTick
        
        # 极端买压
        tick_buy = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=11.0,
            bid_vols=[100000, 100000, 100000, 100000, 100000],
            ask_vols=[10, 10, 10, 10, 10],
        )
        assert tick_buy.raw_depth_ratio > 0, "Extreme buy should be positive"
        
        # 极端卖压
        tick_sell = StandardTick(
            code='000002.SZ',
            time='20260318094500',
            last_price=9.0,
            bid_vols=[10, 10, 10, 10, 10],
            ask_vols=[100000, 100000, 100000, 100000, 100000],
        )
        assert tick_sell.raw_depth_ratio < 0, "Extreme sell should be negative"


class TestToQmtDictDepthRatio:
    """【CTO V218】to_qmt_dict()输出测试"""
    
    def test_to_qmt_dict_contains_depth_ratio(self):
        """测试to_qmt_dict输出包含归一化后的depthRatio"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_vols=[100, 200, 300, 400, 500],  # 买压强
            ask_vols=[50, 100, 150, 200, 250],
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        # 必须包含depthRatio字段
        assert 'depthRatio' in qmt_dict, "to_qmt_dict must contain 'depthRatio' field"
        # 【V218】必须在[0,1]区间
        assert 0.0 <= qmt_dict['depthRatio'] <= 1.0, \
            f"depthRatio must be in [0,1], got {qmt_dict['depthRatio']}"
        # 买压强，应该>0.5
        assert qmt_dict['depthRatio'] > 0.5, \
            f"Buy pressure should have depthRatio > 0.5, got {qmt_dict['depthRatio']}"
    
    def test_to_qmt_dict_sell_pressure(self):
        """测试卖压下to_qmt_dict输出<0.5"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            bid_vols=[50, 50, 50, 50, 50],    # 买压弱
            ask_vols=[500, 500, 500, 500, 500],  # 卖压强
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        # 卖压强，应该<0.5
        assert qmt_dict['depthRatio'] < 0.5, \
            f"Sell pressure should have depthRatio < 0.5, got {qmt_dict['depthRatio']}"
        assert 0.0 <= qmt_dict['depthRatio'] <= 1.0
    
    def test_to_qmt_dict_type_convergence(self):
        """测试V215类型收敛：None变为[]"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_prices=None,
            ask_prices=None,
            bid_vols=None,
            ask_vols=None,
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        # None盘口 → 0.5（绝对平衡）
        assert abs(qmt_dict['depthRatio'] - 0.5) < 0.001, \
            f"None orderbook should return 0.5, got {qmt_dict['depthRatio']}"
    
    def test_volume_float_division(self):
        """测试V215浮点除法：北交所碎股防爆"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='830001.BJ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=150,  # 1.5手
            amount_yuan=1500.0,
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        expected_vol = 150.0 / 100.0
        assert abs(qmt_dict['volume'] - expected_vol) < 0.001


class TestUniversalTrackerDepthRatio:
    """【CTO V218】UniversalTracker接收depth_ratio测试"""
    
    def test_on_frame_receives_depth_ratio(self):
        """测试on_frame正确接收归一化后的depth_ratio"""
        import tempfile
        from logic.execution.universal_tracker import UniversalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = UniversalTracker(output_dir=tmpdir)
            
            # 【V218】depth_ratio在[0,1]区间
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
                'depth_ratio': 0.7,  # 【V218】在[0,1]区间
            }]
            
            tracker.on_frame(
                top_targets=top_targets,
                current_time=datetime(2026, 3, 18, 9, 45, 0),
                global_prices={'000001.SZ': 10.0}
            )
            
            assert '000001.SZ' in tracker.registry
    
    def test_streaming_record_contains_depth_ratio(self):
        """测试JSONL输出包含归一化后的depth_ratio_at_signal"""
        import tempfile
        import os
        import json
        from logic.execution.universal_tracker import UniversalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = UniversalTracker(output_dir=tmpdir)
            
            top_targets = [{
                'code': '000002.SZ',
                'score': 90.0,
                'price': 20.0,
                'change': 3.0,
                'inflow_ratio': 1.5,
                'ratio_stock': 2.0,
                'sustain_ratio': 1.2,
                'mfe': 1.8,
                'purity': 0.7,
                'depth_ratio': 0.35,  # 【V218】卖压<0.5
            }]
            
            tracker.on_frame(
                top_targets=top_targets,
                current_time=datetime(2026, 3, 18, 9, 46, 0),
                global_prices={'000002.SZ': 20.0}
            )
            
            jsonl_path = tracker.streaming_report_path
            if os.path.exists(jsonl_path):
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        record = json.loads(lines[-1])
                        assert 'depth_ratio_at_signal' in record
                        # 【V218】必须在[0,1]区间
                        assert 0.0 <= record['depth_ratio_at_signal'] <= 1.0


class TestDepthRatioEdgeCases:
    """边界条件测试 - Sigmoid归一化防爆验证"""
    
    def test_extreme_buy_pressure(self):
        """测试极端买压（涨停板） - 应逼近1.0"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=11.0,
            volume_shares=10000000,
            amount_yuan=100000000.0,
            bid_vols=[100000, 100000, 100000, 100000, 100000],  # sum=500000
            ask_vols=[10, 10, 10, 10, 10],  # sum=50 (涨停板卖单稀少)
        )
        
        # 【V218】极端买压应逼近1.0，但永不越界
        assert tick.depth_ratio > 0.99, \
            f"Extreme buy pressure should approach 1.0, got {tick.depth_ratio}"
        assert tick.depth_ratio <= 1.0, \
            f"Must never exceed 1.0, got {tick.depth_ratio}"
    
    def test_extreme_sell_pressure(self):
        """测试极端卖压（跌停板） - 应逼近0.0"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=9.0,
            volume_shares=10000000,
            amount_yuan=100000000.0,
            bid_vols=[10, 10, 10, 10, 10],  # sum=50 (跌停板买单稀少)
            ask_vols=[100000, 100000, 100000, 100000, 100000],  # sum=500000
        )
        
        # 【V218】极端卖压应逼近0.0，但永不越界
        assert tick.depth_ratio < 0.01, \
            f"Extreme sell pressure should approach 0.0, got {tick.depth_ratio}"
        assert tick.depth_ratio >= 0.0, \
            f"Must never go below 0.0, got {tick.depth_ratio}"
    
    def test_neutral_pressure(self):
        """测试中性盘口 - 应等于0.5"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            bid_vols=[100, 100, 100, 100, 100],  # sum=500
            ask_vols=[100, 100, 100, 100, 100],  # sum=500
        )
        
        # raw=ln(501/501)=0, sigmoid(0)=0.5
        assert abs(tick.depth_ratio - 0.5) < 0.001, \
            f"Neutral should be 0.5, got {tick.depth_ratio}"
    
    def test_symmetry_verification(self):
        """验证Sigmoid对称性：买压N手 vs 卖压N手"""
        from logic.data_providers.standard_tick import StandardTick
        
        # 买压100:卖压1
        tick_buy = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            bid_vols=[100, 0, 0, 0, 0],
            ask_vols=[1, 0, 0, 0, 0],
        )
        
        # 卖压100:买压1
        tick_sell = StandardTick(
            code='000002.SZ',
            time='20260318094500',
            last_price=10.0,
            bid_vols=[1, 0, 0, 0, 0],
            ask_vols=[100, 0, 0, 0, 0],
        )
        
        # 【V218验证】对称性：depth_ratio + depth_ratio_sell ≈ 1.0
        symmetry_sum = tick_buy.depth_ratio + tick_sell.depth_ratio
        assert abs(symmetry_sum - 1.0) < 0.001, \
            f"Symmetry broken: {tick_buy.depth_ratio} + {tick_sell.depth_ratio} = {symmetry_sum}"
    
    def test_depth_ratio_never_negative(self):
        """【V218核心铁律】depth_ratio永不可能是负数"""
        from logic.data_providers.standard_tick import StandardTick
        
        # 构造各种极端情况
        test_cases = [
            # (bid_vols, ask_vols, description)
            ([1000000], [1], "extreme buy"),
            ([1], [1000000], "extreme sell"),
            ([], [], "empty"),
            (None, None, "none"),
            ([0, 0, 0, 0, 0], [0, 0, 0, 0, 0], "all zeros"),
        ]
        
        for bid_vols, ask_vols, desc in test_cases:
            tick = StandardTick(
                code='000001.SZ',
                time='20260318094500',
                last_price=10.0,
                bid_vols=bid_vols,
                ask_vols=ask_vols,
            )
            
            # 【V218铁律】永不可能是负数！
            assert tick.depth_ratio >= 0.0, \
                f"[{desc}] depth_ratio must never be negative, got {tick.depth_ratio}"
            assert tick.depth_ratio <= 1.0, \
                f"[{desc}] depth_ratio must never exceed 1.0, got {tick.depth_ratio}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])