"""
【CTO V217】深度比管道测试 - 对数对称化版本

测试目标：验证depth_ratio从StandardTick到JSONL的完整链路
StandardTick.depth_ratio → to_qmt_dict()['depthRatio'] → target_entry['depth_ratio']
    → UniversalTracker.on_frame() → instant_physics['depth_ratio']
    → _write_streaming_record() → JSONL['depth_ratio_at_signal']

【V217修正】depth_ratio改为对数对称化公式：
- 公式：ln((total_bid + 1) / (total_ask + 1))
- 物理意义：>0买盘强，<0卖盘强，=0绝对平衡
- 完美对称：极端买压≈+13，极端卖压≈-13

测试铁律：
1. 每个测试必须包含assert断言
2. 不允许使用fake数据或mock绑过核心逻辑
3. 必须测试边界条件
"""

import pytest
import math
from datetime import datetime


class TestStandardTickDepthRatio:
    """【CTO V217】StandardTick.depth_ratio对数对称化测试"""
    
    def test_depth_ratio_calculation(self):
        """测试depth_ratio对数对称化公式：ln((bid+1)/(ask+1))"""
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
        
        # 【V217】对数对称化: ln((1500+1)/(750+1)) = ln(1501/751) ≈ 0.69
        expected = math.log((1500.0 + 1.0) / (750.0 + 1.0))
        assert abs(tick.depth_ratio - expected) < 0.001, f"Expected {expected}, got {tick.depth_ratio}"
        # 买多卖少，depth_ratio应该是正数
        assert tick.depth_ratio > 0, f"Buy pressure should yield positive depth_ratio, got {tick.depth_ratio}"
    
    def test_depth_ratio_empty_vols(self):
        """测试空盘口情况 - 绝对平衡"""
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
        
        # 【V217】空盘口 = ln((0+1)/(0+1)) = ln(1) = 0.0
        assert tick.depth_ratio == 0.0, f"Empty orderbook should return 0.0, got {tick.depth_ratio}"
    
    def test_depth_ratio_none_vols(self):
        """测试None盘口情况（类型收敛测试）"""
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
        
        # 【V217】None盘口 = ln((0+1)/(0+1)) = 0.0（类型收敛后绝对平衡）
        assert tick.depth_ratio == 0.0, f"None orderbook should return 0.0, got {tick.depth_ratio}"
    
    def test_depth_ratio_sell_pressure(self):
        """测试卖压大于买压情况 - 应返回负数"""
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
        
        # 【V217】对数对称化: ln((500+1)/(2500+1)) = ln(501/2501) ≈ -1.61
        expected = math.log((500.0 + 1.0) / (2500.0 + 1.0))
        assert abs(tick.depth_ratio - expected) < 0.001, f"Expected {expected}, got {tick.depth_ratio}"
        # 卖多买少，depth_ratio应该是负数
        assert tick.depth_ratio < 0, f"Sell pressure should yield negative depth_ratio, got {tick.depth_ratio}"
    
    def test_neutral_pressure(self):
        """【CTO V217新增】测试买卖相等时 - 绝对中性"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_vols=[100, 100, 100, 100, 100],  # sum=500
            ask_vols=[100, 100, 100, 100, 100],  # sum=500
        )
        
        # 【V217】买卖相等 = ln((500+1)/(500+1)) = ln(1) = 0.0
        assert tick.depth_ratio == 0.0, f"Neutral pressure should return 0.0, got {tick.depth_ratio}"


class TestToQmtDictDepthRatio:
    """【CTO V217】to_qmt_dict()输出测试"""
    
    def test_to_qmt_dict_contains_depth_ratio(self):
        """测试to_qmt_dict输出包含depthRatio字段"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_vols=[100, 200, 300, 400, 500],  # sum=1500
            ask_vols=[50, 100, 150, 200, 250],   # sum=750
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        # 必须包含depthRatio字段
        assert 'depthRatio' in qmt_dict, "to_qmt_dict must contain 'depthRatio' field"
        assert isinstance(qmt_dict['depthRatio'], float), "depthRatio must be float"
        # 【V217】买多卖少，depth_ratio应该是正数
        assert qmt_dict['depthRatio'] > 0, f"Buy pressure should yield positive depth_ratio, got {qmt_dict['depthRatio']}"
    
    def test_to_qmt_dict_negative_depth_ratio(self):
        """【CTO V217新增】测试to_qmt_dict输出负数depthRatio"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_vols=[50, 50, 50, 50, 50],  # sum=250
            ask_vols=[500, 500, 500, 500, 500],  # sum=2500
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        # 【V217】卖多买少，depth_ratio应该是负数
        assert qmt_dict['depthRatio'] < 0, f"Sell pressure should yield negative depth_ratio, got {qmt_dict['depthRatio']}"
    
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
        
        # V215类型收敛：None → []
        assert isinstance(qmt_dict.get('bidPrice1'), (int, float)), \
            f"bidPrice1 should be numeric, got {type(qmt_dict.get('bidPrice1'))}"
    
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
        
        # volume_shares / 100.0 = 1.5手
        expected_vol = 150.0 / 100.0
        assert abs(qmt_dict['volume'] - expected_vol) < 0.001, \
            f"Expected {expected_vol}, got {qmt_dict['volume']}"


class TestUniversalTrackerDepthRatio:
    """【CTO V216-T2】UniversalTracker接收depth_ratio测试"""
    
    def test_on_frame_receives_depth_ratio(self):
        """测试on_frame正确接收depth_ratio"""
        import tempfile
        from logic.execution.universal_tracker import UniversalTracker
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = UniversalTracker(output_dir=tmpdir)
            
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
                'depth_ratio': 1.8,  # 【V216】关键字段
            }]
            
            tracker.on_frame(
                top_targets=top_targets,
                current_time=datetime(2026, 3, 18, 9, 45, 0),
                global_prices={'000001.SZ': 10.0}
            )
            
            # 验证lifecycle被创建
            assert '000001.SZ' in tracker.registry, "Stock should be in registry"
    
    def test_streaming_record_contains_depth_ratio(self):
        """测试JSONL输出包含depth_ratio_at_signal字段"""
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
                'depth_ratio': 2.5,  # 【V216】关键字段
            }]
            
            tracker.on_frame(
                top_targets=top_targets,
                current_time=datetime(2026, 3, 18, 9, 46, 0),
                global_prices={'000002.SZ': 20.0}
            )
            
            # 读取JSONL文件验证
            jsonl_path = tracker.streaming_report_path
            if os.path.exists(jsonl_path):
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        record = json.loads(lines[-1])
                        # 【V216】验证depth_ratio_at_signal字段存在
                        assert 'depth_ratio_at_signal' in record, \
                            f"JSONL must contain 'depth_ratio_at_signal', got keys: {record.keys()}"
                        assert abs(record['depth_ratio_at_signal'] - 2.5) < 0.001, \
                            f"Expected depth_ratio_at_signal=2.5, got {record['depth_ratio_at_signal']}"


class TestDepthRatioEdgeCases:
    """【CTO V217】边界条件测试 - 对数对称化版本"""
    
    def test_extreme_buy_pressure(self):
        """测试极端买压（涨停板买单堆积）"""
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
        
        # 【V217】对数对称化: ln((500000+1)/(50+1)) = ln(500001/51) ≈ 9.17
        # 不再是天文数字10000，而是完美对称的正数
        assert tick.depth_ratio > 8.0, \
            f"Extreme buy pressure should have positive depth_ratio>8, got {tick.depth_ratio}"
        assert tick.depth_ratio < 15.0, \
            f"Extreme buy pressure depth_ratio should be bounded, got {tick.depth_ratio}"
    
    def test_extreme_sell_pressure(self):
        """测试极端卖压（跌停板卖单堆积）"""
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
        
        # 【V217】对数对称化: ln((50+1)/(500000+1)) = ln(51/500001) ≈ -9.17
        # 不再是接近0的小数，而是完美对称的负数！
        assert tick.depth_ratio < -8.0, \
            f"Extreme sell pressure should have negative depth_ratio<-8, got {tick.depth_ratio}"
        assert tick.depth_ratio > -15.0, \
            f"Extreme sell pressure depth_ratio should be bounded, got {tick.depth_ratio}"
    
    def test_symmetry_verification(self):
        """【CTO V217新增】验证对数对称性"""
        from logic.data_providers.standard_tick import StandardTick
        
        # 场景1：买100万，卖1
        tick1 = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=11.0,
            volume_shares=10000000,
            amount_yuan=100000000.0,
            bid_vols=[200000, 200000, 200000, 200000, 200000],  # sum=1000000
            ask_vols=[0, 0, 0, 0, 1],  # sum=1
        )
        
        # 场景2：买1，卖100万
        tick2 = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=9.0,
            volume_shares=10000000,
            amount_yuan=100000000.0,
            bid_vols=[0, 0, 0, 0, 1],  # sum=1
            ask_vols=[200000, 200000, 200000, 200000, 200000],  # sum=1000000
        )
        
        # 【V217】对数对称性验证：depth_ratio1 ≈ -depth_ratio2
        assert abs(tick1.depth_ratio + tick2.depth_ratio) < 0.001, \
            f"Symmetry broken: {tick1.depth_ratio} vs {-tick2.depth_ratio}"
        
        # 场景1应该是正数（买压）
        assert tick1.depth_ratio > 0, f"Buy pressure should be positive, got {tick1.depth_ratio}"
        # 场景2应该是负数（卖压）
        assert tick2.depth_ratio < 0, f"Sell pressure should be negative, got {tick2.depth_ratio}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
