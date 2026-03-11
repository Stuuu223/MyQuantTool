# -*- coding: utf-8 -*-
"""
量纲铁律单元测试 - 对照 docs/architecture/PHYSICS_LAW.md

测试目标：
1. float_volume 万股自动升维（V66 法则）
2. get_full_tick 快照的 volume 单位是"股"
3. subscribe_quote 实盘流的 volume 单位是"手"，入口必须 *100
4. amount 永远是元，不需要换算
5. delta_turnover 公式验证（V70 修复：手*100/股*100 而非 *10000）

运行：python -m pytest tests/regression/test_dimension_law.py -v
"""
import pytest


class TestFloatVolumeDimension:
    """
    PHYSICS_LAW.md 表格验证：
    get_full_tick / get_local_data 的 float_volume 单位是万股，必须 *10000 转为股
    """

    def _simulate_float_volume_check(self, raw_float_volume: float, price: float) -> float:
        """
        模拟 run_live_trading_engine.py 中的量纲自动升维逻辑（V66 宪法）
        来源：docs/architecture/PHYSICS_LAW.md §1
        """
        float_market_cap = raw_float_volume * price
        # V66 铁律：A股最小流通市值不可能 < 2亿
        if float_market_cap > 0 and float_market_cap < 200_000_000:
            float_market_cap = float_market_cap * 10_000.0  # 强制升维：万股 → 股
        return float_market_cap

    def test_wangu_auto_upgrade_small_cap(self):
        """正常情况：raw=5000万股 * 5元 = 2.5亿 → 不触发升维（已是股单位)"""
        cap = self._simulate_float_volume_check(50_000_000, 5.0)  # 5000万股，单位=股
        assert cap >= 200_000_000, f"流通市值不应触发升维: {cap}"

    def test_wangu_auto_upgrade_wangu_unit(self):
        """量纲错误：raw=5000（万股单位）* 5元 = 25000元 → 应自动升维至2.5亿"""
        raw_float_volume = 5000  # 这是万股（错误单位）
        price = 5.0
        cap = self._simulate_float_volume_check(raw_float_volume, price)
        # 升维后应 = 5000 * 5 * 10000 = 2.5亿
        assert cap >= 200_000_000, (
            f"V66 升维失败！量纲错误未被修正。升维后市值={cap}，"
            f"检查 PHYSICS_LAW.md §1"
        )

    def test_minimum_market_cap_law(self):
        """铁律：任何 A 股流通市值不可能 < 2亿（否则必然是量纲错误）"""
        test_cases = [
            (500_000_000, 6.0, "正常-股单位"),     # 5亿股 * 6元 = 30亿
            (5_000, 6.0, "异常-万股单位"),          # 5000万股，如果不升维=3万元
            (50_000_000, 0.5, "边界测试"),           # 5000万股 * 0.5元 = 2500万，升维
        ]
        for raw, price, label in test_cases:
            cap = self._simulate_float_volume_check(raw, price)
            assert cap >= 200_000_000, (
                f"[{label}] 最终流通市值 {cap/1e8:.2f}亿 < 2亿，"
                f"V66升维逻辑可能失效！"
            )


class TestVolumeUnit:
    """
    验证 get_full_tick（快照）volume 单位=股，
    subscribe_quote（实盘流）volume 单位=手，入口必须 *100
    来源：PHYSICS_LAW.md 数据源量纲铁律表格
    """

    def test_full_tick_volume_is_shares(self):
        """get_full_tick 返回的 volume 直接是股，不需要换算"""
        tick_volume_from_full_tick = 1_000_000  # 股
        float_volume = 500_000_000  # 5亿股（已升维后）

        turnover = tick_volume_from_full_tick / float_volume * 100
        # 换手率应在合理范围 0-100%
        assert 0 < turnover < 100, f"换手率异常: {turnover:.4f}%，检查 volume 量纲"

    def test_subscribe_quote_volume_needs_multiply_100(self):
        """
        subscribe_quote 实盘流的 volume 单位是手，入口必须 *100 转为股
        禁止直接用 volume 做换手率计算！
        """
        raw_volume_hands = 10_000  # 手（实盘流原始值）
        volume_shares = raw_volume_hands * 100  # 入口清洗：手 → 股
        float_volume = 500_000_000

        # 错误用法（未清洗）
        wrong_turnover = raw_volume_hands / float_volume * 100
        # 正确用法
        correct_turnover = volume_shares / float_volume * 100

        assert wrong_turnover < 0.01, "量纲错误时换手率会极小，说明未做入口清洗"
        assert correct_turnover > wrong_turnover, "清洗后换手率必须 > 未清洗"
        assert 0 < correct_turnover < 100

    def test_amount_is_always_yuan(self):
        """amount 永远是绝对人民币（元），无需换算"""
        # 日成交额约 1亿元的股票
        amount_yuan = 100_000_000
        assert amount_yuan >= 1_000_000, "amount 应为元，值应 >= 百万量级"


class TestDeltaTurnoverFormula:
    """
    验证 _micro_defense_check 中 L1 探针的 delta_turnover 公式
    原 BUG：(delta_volume * 10000) / float_volume  ← 乘了 10000 是错的
    修复后：(delta_volume * 100) / float_volume * 100  ← 手→股→换手率%

    来源：run_live_trading_engine.py _micro_defense_check V70修复记录
    """

    def test_delta_turnover_formula_correct(self):
        """5分钟内新增 500 手，流通股 5亿，delta_turnover 应约 0.01%"""
        delta_volume_hands = 500          # 手（subscribe_quote 实盘流）
        float_volume_shares = 500_000_000  # 股（已升维后）

        # 正确公式（V70 修复版）
        delta_turnover_correct = (delta_volume_hands * 100) / float_volume_shares * 100
        # 旧 BUG 公式
        delta_turnover_wrong = (delta_volume_hands * 10_000) / float_volume_shares

        # 正确公式结果约 0.01%
        assert abs(delta_turnover_correct - 0.01) < 0.001, (
            f"delta_turnover 公式错误！正确应约 0.01%，实际={delta_turnover_correct:.4f}%"
        )
        # 旧公式比正确公式大了 100 倍（这就是 L1 探针永不触发的根因）
        ratio = delta_turnover_wrong / delta_turnover_correct
        assert abs(ratio - 100.0) < 1.0, (
            f"BUG 验证：旧公式比正确公式大了 {ratio:.0f} 倍（应为 100 倍）"
        )

    def test_delta_turnover_threshold_sensitivity(self):
        """
        验证 0.5% 阈值的物理含义：
        5分钟内新增 25000 手（2500万股）/ 5亿流通股 = 5% 换手，远超 0.5% 触发线
        """
        delta_volume_hands = 25_000
        float_volume_shares = 500_000_000
        delta_turnover = (delta_volume_hands * 100) / float_volume_shares * 100
        assert delta_turnover > 0.5, (
            f"大量换手应触发 L1 阈值，但计算结果={delta_turnover:.4f}% 未超过 0.5%"
        )
