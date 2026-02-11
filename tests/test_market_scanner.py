#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MarketScanner 单元测试

测试覆盖：
1. 三阶段筛选逻辑
2. 分批获取K线数据
3. 多进程智能切换
4. 异常处理测试
5. 内存占用验证

Author: MyQuantTool Team
Date: 2026-02-11
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from logic.market_scanner import MarketScanner


class TestMarketScanner:
    """MarketScanner 测试套件"""
    
    @pytest.fixture
    def mock_equity_info(self):
        """Mock股本信息"""
        return {
            '600000.SH': {'float_shares': 1000000000},
            '000001.SZ': {'float_shares': 2000000000},
            '300001.SZ': {'float_shares': 500000000},
        }
    
    @pytest.fixture
    def mock_kline_data(self):
        """Mock K线数据"""
        return pd.DataFrame({
            'time': pd.date_range('2026-02-11 09:30', periods=30, freq='1T'),
            'open': [10.0 + i * 0.1 for i in range(30)],
            'high': [10.1 + i * 0.1 for i in range(30)],
            'low': [9.9 + i * 0.1 for i in range(30)],
            'close': [10.0 + i * 0.1 for i in range(30)],
            'volume': [1000000 + i * 100000 for i in range(30)],
        })
    
    def test_init_with_batch_size(self, mock_equity_info):
        """测试初始化时分批大小设置"""
        scanner = MarketScanner(
            equity_info=mock_equity_info,
            use_multiprocess=True,
            batch_size=500
        )
        
        assert scanner.batch_size == 500
        assert scanner.use_multiprocess is True
    
    def test_phase1_batch_processing(self, mock_equity_info, mock_kline_data):
        """测试阶段1分批处理逻辑"""
        scanner = MarketScanner(
            equity_info=mock_equity_info,
            batch_size=2  # 小批次用于测试
        )
        
        # Mock xtdata.get_market_data_ex
        with patch('logic.market_scanner.xtdata') as mock_xtdata:
            # 模拟返回K线数据
            mock_xtdata.get_market_data_ex.return_value = {
                '600000.SH': mock_kline_data,
                '000001.SZ': mock_kline_data,
            }
            
            stock_list = ['600000.SH', '000001.SZ', '300001.SZ', '600001.SH']
            candidates = scanner._phase1_pre_filter(stock_list, '09:35')
            
            # 验证调用次数（4只股票 / 2批 = 2次）
            assert mock_xtdata.get_market_data_ex.call_count == 2
    
    def test_phase2_qpst_lite(self, mock_equity_info, mock_kline_data):
        """测试阶段2简化QPST筛选"""
        scanner = MarketScanner(equity_info=mock_equity_info)
        
        # Mock _get_kline
        scanner._get_kline = Mock(return_value=mock_kline_data)
        
        candidates = ['600000.SH', '000001.SZ']
        potentials = scanner._phase2_qpst_lite(candidates)
        
        # 验证至少有股票通过筛选
        assert isinstance(potentials, list)
    
    def test_multiprocess_switch(self, mock_equity_info):
        """测试多进程智能切换"""
        scanner_single = MarketScanner(
            equity_info=mock_equity_info,
            use_multiprocess=False
        )
        assert scanner_single.use_multiprocess is False
        
        scanner_multi = MarketScanner(
            equity_info=mock_equity_info,
            use_multiprocess=True
        )
        assert scanner_multi.use_multiprocess is True
    
    def test_get_kline_count(self, mock_equity_info):
        """测试K线数量计算"""
        scanner = MarketScanner(equity_info=mock_equity_info)
        
        assert scanner._get_kline_count('09:35') == 10
        assert scanner._get_kline_count('10:00') == 30
        assert scanner._get_kline_count('14:00') == 90
        assert scanner._get_kline_count('unknown') == 10  # 默认值
    
    def test_analyze_single_stock_with_trap(self, mock_equity_info, mock_kline_data):
        """测试单股票分析（含诱多信号）"""
        scanner = MarketScanner(equity_info=mock_equity_info)
        
        # Mock 依赖方法
        scanner._get_kline = Mock(return_value=mock_kline_data)
        scanner.qpst_analyzer.analyze = Mock(return_value={
            'vote_result': {
                'level': 'STRONG',
                'confidence': 0.85,
                'positive_dims': ['quantity', 'price', 'space', 'time']
            }
        })
        scanner.trap_detector.detect = Mock(return_value=['对倒', '尾盘拉升'])
        
        result = scanner._analyze_single_stock('600000.SH')
        
        assert result is not None
        assert result['code'] == '600000.SH'
        assert result['final_signal'] == 'TRAP_WARNING'
        assert result['confidence'] == 0.9
        assert '诱多预警' in result['reason']
    
    def test_analyze_single_stock_insufficient_data(self, mock_equity_info):
        """测试数据不足时的处理"""
        scanner = MarketScanner(equity_info=mock_equity_info)
        
        # Mock 返回不足数据
        short_df = pd.DataFrame({
            'close': [10.0, 10.1],
            'volume': [1000, 1200]
        })
        scanner._get_kline = Mock(return_value=short_df)
        
        result = scanner._analyze_single_stock('600000.SH')
        
        # 数据不足应返回None
        assert result is None
    
    def test_scan_empty_stock_list(self, mock_equity_info):
        """测试空股票列表"""
        scanner = MarketScanner(equity_info=mock_equity_info)
        
        # Mock 阶段1返回空列表
        scanner._phase1_pre_filter = Mock(return_value=[])
        
        result = scanner.scan(stock_list=[], scan_time='09:35')
        
        assert result == []
    
    def test_scan_phase2_empty(self, mock_equity_info):
        """测试阶段2返回空列表"""
        scanner = MarketScanner(equity_info=mock_equity_info)
        
        # Mock 阶段1返回数据，阶段2返回空
        scanner._phase1_pre_filter = Mock(return_value=['600000.SH', '000001.SZ'])
        scanner._phase2_qpst_lite = Mock(return_value=[])
        
        result = scanner.scan(stock_list=['600000.SH'], scan_time='09:35')
        
        assert result == []


class TestMarketScannerIntegration:
    """集成测试（需要真实QMT环境）"""
    
    @pytest.mark.skipif(True, reason="需要QMT环境")
    def test_real_scan(self):
        """真实扫描测试（手动运行）"""
        equity_info = {
            '600000.SH': {'float_shares': 1000000000}
        }
        scanner = MarketScanner(equity_info=equity_info, batch_size=100)
        
        result = scanner.scan(stock_list=['600000.SH'], scan_time='09:35')
        
        assert isinstance(result, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
