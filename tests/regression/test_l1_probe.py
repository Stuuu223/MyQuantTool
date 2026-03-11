# -*- coding: utf-8 -*-
"""
L1 探针存活测试 - 验证 _micro_defense_check 中放量滞涨拦截逻辑

测试目标：
1. 正常主力建仓（爆量+涨价）→ 通过防线
2. 主力派发（爆量+跌价）→ 被 L1 探针拦截，返回 False
3. 早盘15分钟内爆量 → 豁免，不触发 L1 探针
4. delta_turnover 公式验证（V70 量纲修复后）

运行：python -m pytest tests/regression/test_l1_probe.py -v
"""
import sys
import os
import pytest
from collections import deque
from datetime import datetime
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _make_engine_mock(stock_code: str, history: list):
    """
    创建一个轻量级 LiveTradingEngine mock，
    注入 tick_history + trade_gatekeeper，不需要 QMT 环境
    """
    mock_gatekeeper = MagicMock()
    mock_gatekeeper.check_capital_flow.return_value = True
    mock_gatekeeper.check_sector_resonance.return_value = True

    engine = MagicMock()
    engine.trade_gatekeeper = mock_gatekeeper
    engine.tick_history = {stock_code: deque(history, maxlen=300)}
    engine.get_current_time = MagicMock()

    # 绑定真实方法
    try:
        from tasks.run_live_trading_engine import LiveTradingEngine
        engine._micro_defense_check = LiveTradingEngine._micro_defense_check.__get__(engine)
        return engine
    except ImportError:
        return None


def _make_tick_history(n: int, start_vol: int, end_vol: int,
                       start_price: float, end_price: float) -> list:
    """生成 n 个 tick 的历史数组（线性插值）"""
    result = []
    for i in range(n):
        frac = i / max(n - 1, 1)
        result.append({
            'price': start_price + (end_price - start_price) * frac,
            'volume': int(start_vol + (end_vol - start_vol) * frac),
            'timestamp': datetime(2026, 1, 29, 9, 35, i % 60)
        })
    return result


class TestL1Probe:

    def test_L1_爆量涨价_通过防线(self):
        """爆量+价格上涨 → 主力建仓，应通过 L1 防线"""
        history = _make_tick_history(100, 10_000_000, 15_000_000, 14.0, 15.0)
        engine = _make_engine_mock('300001', history)
        if engine is None:
            pytest.skip("无法导入 LiveTradingEngine")

        engine.get_current_time.return_value = datetime(2026, 1, 29, 10, 0, 0)
        tick_data = {'price': 15.0, 'volume': 15_000_000, 'amount': 50_000_000}

        with patch('logic.data_providers.true_dictionary.get_true_dictionary') as mock_td:
            mock_td.return_value.get_float_volume.return_value = 500_000_000
            mock_td.return_value.get_up_stop_price.return_value = 16.5
            mock_td.return_value.get_down_stop_price.return_value = 12.6
            result = engine._micro_defense_check('300001', tick_data)

        assert result is True, "正常建仓应通过 L1 防线"

    def test_L1_爆量跌价_拦截派发(self):
        """
        爆量+价格下跌 > 0.5% → 主力派发，应被 L1 探针拦截
        V70 修复验证：原 'true_dict' in dir() 永假导致此测试必然失败
        """
        # 价格从 15 跌到 14（跌幅 6.7%），成交量大幅增加
        history = _make_tick_history(100, 10_000_000, 15_000_000, 15.0, 14.0)
        engine = _make_engine_mock('300002', history)
        if engine is None:
            pytest.skip("无法导入 LiveTradingEngine")

        # 10:30，09:45 之后，L1 探针应激活
        engine.get_current_time.return_value = datetime(2026, 1, 29, 10, 30, 0)
        # current volume = 15_500_000（比 history[-100] 的 10_000_000 多 550万股）
        # delta_turnover = 5_500_000 / 500_000_000 * 100 = 1.1% > 0.5% 且价格下跌
        tick_data = {'price': 14.0, 'volume': 15_500_000, 'amount': 50_000_000}

        with patch('logic.data_providers.true_dictionary.get_true_dictionary') as mock_td:
            mock_td.return_value.get_float_volume.return_value = 500_000_000
            mock_td.return_value.get_up_stop_price.return_value = 16.5
            mock_td.return_value.get_down_stop_price.return_value = 12.6
            result = engine._micro_defense_check('300002', tick_data)

        assert result is False, (
            "爆量跌价应被 L1 探针拦截！"
            "如果此测试失败，检查 _micro_defense_check 中 true_dict 获取逻辑（V70修复项）"
        )

    def test_L1_早盘豁免_09_40不触发(self):
        """09:40（早盘豁免区）内爆量跌价 → 豁免，不触发 L1"""
        history = _make_tick_history(100, 10_000_000, 15_000_000, 15.0, 14.0)
        engine = _make_engine_mock('300003', history)
        if engine is None:
            pytest.skip("无法导入 LiveTradingEngine")

        engine.get_current_time.return_value = datetime(2026, 1, 29, 9, 40, 0)  # 早盘豁免区
        tick_data = {'price': 14.0, 'volume': 15_500_000, 'amount': 50_000_000}

        with patch('logic.data_providers.true_dictionary.get_true_dictionary') as mock_td:
            mock_td.return_value.get_float_volume.return_value = 500_000_000
            mock_td.return_value.get_up_stop_price.return_value = 16.5
            mock_td.return_value.get_down_stop_price.return_value = 12.6
            result = engine._micro_defense_check('300003', tick_data)

        assert result is True, "09:45前早盘豁免区应忽略 L1 探针"

    def test_L1_history不足100_直接通过(self):
        """历史 tick 不足 100 个时，L1 探针无法工作，应直接通过"""
        history = _make_tick_history(50, 10_000_000, 12_000_000, 15.0, 14.0)  # 只有50个
        engine = _make_engine_mock('300004', history)
        if engine is None:
            pytest.skip("无法导入 LiveTradingEngine")

        engine.get_current_time.return_value = datetime(2026, 1, 29, 10, 30, 0)
        tick_data = {'price': 14.0, 'volume': 12_000_000, 'amount': 30_000_000}

        with patch('logic.data_providers.true_dictionary.get_true_dictionary') as mock_td:
            mock_td.return_value.get_float_volume.return_value = 500_000_000
            mock_td.return_value.get_up_stop_price.return_value = 16.5
            mock_td.return_value.get_down_stop_price.return_value = 12.6
            result = engine._micro_defense_check('300004', tick_data)

        assert result is True, "历史不足100个tick时，L1 探针应豁免"
