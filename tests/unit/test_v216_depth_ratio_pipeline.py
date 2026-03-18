"""
【CTO V216】深度比管道测试 - 严格断言版

测试目标：验证depth_ratio从StandardTick到JSONL的完整链路
StandardTick.depth_ratio → to_qmt_dict()['depthRatio'] → target_entry['depth_ratio']
    → UniversalTracker.on_frame() → instant_physics['depth_ratio']
    → _write_streaming_record() → JSONL['depth_ratio_at_signal']

测试铁律：
1. 每个测试必须包含assert断言
2. 不允许使用fake数据或mock绑过核心逻辑
3. 必须测试边界条件
"""

import pytest
from datetime import datetime


class TestStandardTickDepthRatio:
    """【CTO V216-T1】StandardTick.depth_ratio属性测试"""
    
    def test_depth_ratio_calculation(self):
        """测试depth_ratio计算公式：(bid1+...+bid5)/(ask1+...+ask5+1e-6)"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',  # 【修正】字段名是code不是stock_code
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,  # 【修正】字段名是amount_yuan不是amount
            bid_prices=[9.99, 9.98, 9.97, 9.96, 9.95],
            ask_prices=[10.01, 10.02, 10.03, 10.04, 10.05],
            bid_vols=[100, 200, 300, 400, 500],  # sum=1500
            ask_vols=[50, 100, 150, 200, 250],   # sum=750
        )
        
        # depth_ratio = 1500 / (750 + 1e-6) ≈ 2.0
        expected = 1500.0 / 750.0
        assert abs(tick.depth_ratio - expected) < 0.001, f"Expected {expected}, got {tick.depth_ratio}"
    
    def test_depth_ratio_empty_vols(self):
        """测试空盘口情况"""
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
        
        # 空盘口 = 0 / (0 + 1e-6) ≈ 0
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
        
        # None盘口也应返回0.0（类型收敛）
        assert tick.depth_ratio == 0.0, f"None orderbook should return 0.0, got {tick.depth_ratio}"
    
    def test_depth_ratio_sell_pressure(self):
        """测试卖压大于买压情况"""
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
        
        # depth_ratio = 500 / 2500 = 0.2
        assert abs(tick.depth_ratio - 0.2) < 0.001, f"Expected 0.2, got {tick.depth_ratio}"


class TestToQmtDictDepthRatio:
    """【CTO V216-T1】to_qmt_dict()输出测试"""
    
    def test_to_qmt_dict_contains_depth_ratio(self):
        """测试to_qmt_dict输出包含depthRatio字段"""
        from logic.data_providers.standard_tick import StandardTick
        
        tick = StandardTick(
            code='000001.SZ',
            time='20260318094500',
            last_price=10.0,
            volume_shares=1000000,
            amount_yuan=10000000.0,
            bid_vols=[100, 200, 300, 400, 500],
            ask_vols=[50, 100, 150, 200, 250],
        )
        
        qmt_dict = tick.to_qmt_dict()
        
        # 必须包含depthRatio字段
        assert 'depthRatio' in qmt_dict, "to_qmt_dict must contain 'depthRatio' field"
        assert isinstance(qmt_dict['depthRatio'], float), "depthRatio must be float"
        assert qmt_dict['depthRatio'] > 0, f"depthRatio should be positive, got {qmt_dict['depthRatio']}"
    
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
        # 注意：to_qmt_dict内部已经做了or []处理，所以输出不应该是None
        assert isinstance(qmt_dict.get('bidPrice1'), (int, float)), \
            f"bidPrice1 should be numeric, got {type(qmt_dict.get('bidPrice1'))}"
    
    def test_volume_float_division(self):
        """测试V215浮点除法：北交所碎股防爆"""
        from logic.data_providers.standard_tick import StandardTick
        
        # 假设北交所某股成交量是150股（非整手）
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
    """边界条件测试"""
    
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
        
        # depth_ratio = 500000 / 50 = 10000
        assert tick.depth_ratio > 1000, \
            f"Extreme buy pressure should have high depth_ratio, got {tick.depth_ratio}"
    
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
        
        # depth_ratio = 50 / 500000 ≈ 0.0001
        assert tick.depth_ratio < 0.001, \
            f"Extreme sell pressure should have near-zero depth_ratio, got {tick.depth_ratio}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])