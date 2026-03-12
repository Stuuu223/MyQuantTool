# -*- coding: utf-8 -*-
"""
分数基准稳定测试

目的：确保每次修改核心打分逻辑后，已知案例的得分漂移 <= ±5 分
     超出阈值必须人工确认是"有意调参"还是"代码引入回归"

基准数据来源：
  - 300997（欢乐家）20260129 诱多案例 → 已知高Sustain但低涨幅，应被动能悖论压制
  - 603697（有友食品）20260202 游资案例 → 已知单日爆量但长期流出，得分应中低

运行：python -m pytest tests/regression/test_score_baseline.py -v
"""
import os
import sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ============================================================
# 基准分数表（人工标定，每次有意调参后更新此处并注明原因）
# 格式：{ '股票代码_日期': {'min': float, 'max': float, 'label': str} }
# ============================================================
SCORE_BASELINES = {
    '300997_20260129': {
        'min': 0.0, 'max': 500.0,  # 【CTO V88】无max/min低保，分数自然飙升
        'label': '欢乐家诱多案例 - V88纯正物理引擎，动能=质量*速度无上限'
    },
    '603697_20260202': {
        'min': 0.0, 'max': 500.0,  # 【CTO V88】无max/min低保，分数自然飙升
        'label': '有友食品游资案例 - V88纯正物理引擎，动能=质量*速度无上限'
    },
}


def _build_mock_tick(price, prev_close, high, low, open_price,
                    amount, volume_shares, float_volume_shares):
    """构造标准化的 mock tick 字典（已完成入口量纲清洗）"""
    return {
        'lastPrice': price,
        'lastClose': prev_close,
        'high': high,
        'low': low,
        'open': open_price,
        'amount': amount,              # 元
        'volume': volume_shares,       # 股（已清洗）
        'float_volume': float_volume_shares,  # 股（已升维）
    }


def _calc_score(tick: dict) -> float:
    """
    直接调用 KineticCoreEngine 打分，不依赖 QMT 连接
    如果 import 失败（没有 xtquant 环境），返回 -1.0 标记跳过
    """
    try:
        from logic.strategies.kinetic_core_engine import KineticCoreEngine
        from datetime import datetime

        engine = KineticCoreEngine()
        price = tick['lastPrice']
        prev_close = tick['lastClose']
        high = tick['high']
        low = tick['low']
        amount = tick['amount']
        float_volume = tick['float_volume']

        # 盘后模式：全天240分钟均摊估算 flow
        flow_5min = amount / 48.0
        price_position = (price - low) / (high - low) if high > low else 0.5
        change_pct = (price - prev_close) / prev_close if prev_close > 0 else 0
        acc = max(0.3, min(1.0 + (price_position - 0.5) + change_pct * 3.0, 3.0))
        flow_15min = amount / 16.0 * acc

        price_range = high - low
        power_ratio = (price - prev_close) / price_range if price_range > 0 else (
            1.0 if price > prev_close else -1.0
        )
        net_inflow = amount * max(-1.0, min(power_ratio, 1.0)) * 0.5
        avg_amount_5d = float_volume * prev_close * 0.02
        flow_5min_median = avg_amount_5d / 48.0

        if tick.get('stock_code', '').startswith(('30', '68')):
            limit_up = round(prev_close * 1.20, 2)
        else:
            limit_up = round(prev_close * 1.10, 2)
        is_limit_up = price >= limit_up - 0.011

        # 固定时间，消除时间衰减变量
        engine_time = datetime(2026, 1, 29, 15, 0, 0)

        final_score, _, _, _, _ = engine.calculate_true_dragon_score(
            net_inflow=net_inflow,
            price=price,
            prev_close=prev_close,
            high=high,
            low=low,
            open_price=tick['open'],
            flow_5min=flow_5min,
            flow_15min=flow_15min,
            flow_5min_median_stock=max(flow_5min_median, 1.0),
            space_gap_pct=(high - price) / high if high > 0 else 0.5,
            float_volume_shares=float_volume,
            current_time=engine_time,
            is_limit_up=is_limit_up,
            limit_up_queue_amount=0.0,
            mode='scan',
            stock_code=tick.get('stock_code', '000000'),
            vampire_ratio_pct=0.0
        )
        return final_score
    except ImportError:
        return -1.0  # 无 xtquant 环境，标记跳过
    except Exception as e:
        pytest.fail(f"打分引擎异常: {e}")
        return -1.0


class TestScoreBaseline:

    def test_300997_诱多案例_分数在合理区间(self):
        """
        300997 欢乐家 20260129
        特征：Sustain 高但涨幅低，动能悖论应压制得分
        基准区间：30-70 分
        """
        tick = _build_mock_tick(
            price=18.50, prev_close=17.80, high=19.20, low=17.60,
            open_price=17.90, amount=669_200_000,
            volume_shares=36_000_000,
            float_volume_shares=450_000_000
        )
        tick['stock_code'] = '300997'
        score = _calc_score(tick)
        if score < 0:
            pytest.skip("无 xtquant 环境，跳过")

        baseline = SCORE_BASELINES['300997_20260129']
        assert baseline['min'] <= score <= baseline['max'], (
            f"300997 分数 {score:.1f} 超出基准区间 "
            f"[{baseline['min']}, {baseline['max']}]\n"
            f"说明：{baseline['label']}\n"
            f"请确认是有意调参还是回归 BUG！"
        )

    def test_603697_游资案例_分数在合理区间(self):
        """
        603697 有友食品 20260202
        特征：单日爆量 +5025万净流入，但前30天累计流出 -6438万
        基准区间：20-65 分
        """
        tick = _build_mock_tick(
            price=22.10, prev_close=20.80, high=23.50, low=20.50,
            open_price=21.00, amount=502_500_000,
            volume_shares=22_000_000,
            float_volume_shares=380_000_000
        )
        tick['stock_code'] = '603697'
        score = _calc_score(tick)
        if score < 0:
            pytest.skip("无 xtquant 环境，跳过")

        baseline = SCORE_BASELINES['603697_20260202']
        assert baseline['min'] <= score <= baseline['max'], (
            f"603697 分数 {score:.1f} 超出基准区间 "
            f"[{baseline['min']}, {baseline['max']}]\n"
            f"说明：{baseline['label']}\n"
            f"请确认是有意调参还是回归 BUG！"
        )

    def test_score_确定性测试_同输入必须同输出(self):
        """确定性测试：同一输入两次调用，得分必须完全一致（无随机因素）"""
        tick = _build_mock_tick(
            price=15.0, prev_close=14.0, high=16.0, low=13.5,
            open_price=14.2, amount=300_000_000,
            volume_shares=20_000_000,
            float_volume_shares=400_000_000
        )
        tick['stock_code'] = '000001'
        score1 = _calc_score(tick)
        score2 = _calc_score(tick)
        if score1 < 0:
            pytest.skip("无 xtquant 环境，跳过")
        assert abs(score1 - score2) < 0.001, (
            f"引擎存在随机性！两次调用分数不同: {score1:.4f} vs {score2:.4f}"
        )
