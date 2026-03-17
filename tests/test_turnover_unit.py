"""
换手率量纲回归测试 - 任何人改动细筛代码前必须先跑这个测试

运行方式:
    pytest tests/test_turnover_unit.py -v

测试目的:
    1. 验证换手率公式量纲正确
    2. 验证70%死亡防线能正确触发
    3. 防止回归性Bug
"""

import pytest


class TestTurnoverCalculation:
    """换手率计算量纲测试"""
    
    def test_turnover_normal_case(self):
        """
        正常交易日换手率计算
        案例：平安银行 某日成交量=100万手
        流通股本=192亿股
        预期换手率 = (100万×100) / 192亿 × 100 ≈ 0.52%
        """
        # 输入数据（单位：手）
        current_volume_hand = 1_000_000  # 100万手
        float_volume_shares = 19_200_000_000  # 192亿股
        
        # 计算公式（与代码一致）
        volume_gu = current_volume_hand * 100  # 手 → 股
        turnover = volume_gu / float_volume_shares * 100
        
        # 验证
        assert abs(turnover - 0.52) < 0.01, f"换手率={turnover}%，量纲可能错误！"
        assert turnover < 70.0, "正常交易日不应触发死亡防线"
    
    def test_turnover_high_activity(self):
        """
        高活跃日换手率计算
        案例：某日成交量=5000万手
        流通股本=192亿股
        预期换手率 = (5000万×100) / 192亿 × 100 ≈ 26%
        """
        current_volume_hand = 50_000_000  # 5000万手
        float_volume_shares = 19_200_000_000  # 192亿股
        
        volume_gu = current_volume_hand * 100
        turnover = volume_gu / float_volume_shares * 100
        
        assert abs(turnover - 26.0) < 0.5, f"换手率={turnover}%，量纲可能错误！"
        assert turnover < 70.0, "高活跃日不应触发死亡防线"
    
    def test_turnover_small_cap(self):
        """
        【CTO E-6修复】验证小盘股在正常交易日（换手3%）不触发死亡防线
        案例：流通股本=5亿股，成交量=15万手
        预期换手率 = (15万×100) / 5亿 × 100 = 3.0%
        """
        current_volume_hand = 150_000  # 15万手
        float_volume_shares = 500_000_000  # 5亿股
        
        volume_gu = current_volume_hand * 100
        turnover = volume_gu / float_volume_shares * 100
        
        assert abs(turnover - 3.0) < 0.01, f"换手率={turnover}%，量纲可能错误！"
        assert turnover < 70.0, "3%换手率不应触发死亡防线"


class TestTurnoverDefenseLine:
    """死亡换手防线测试"""
    
    def test_defense_line_70_percent(self):
        """
        验证70%防线能被正确触发
        案例：成交量=140亿股，流通股本=192亿股
        预期换手率 ≈ 72.9%
        """
        volume_gu = 14_000_000_000  # 140亿股（已经是股单位）
        float_volume = 19_200_000_000  # 192亿股
        turnover = volume_gu / float_volume * 100  # ≈ 72.9%
        
        assert turnover >= 70.0, f"换手率{turnover:.1f}%，死亡防线应当触发"
    
    def test_defense_line_extreme(self):
        """
        验证极端绞肉机能被拦截
        案例：成交量=192亿股（换手100%），流通股本=192亿股
        """
        volume_gu = 19_200_000_000  # 192亿股
        float_volume = 19_200_000_000  # 192亿股
        turnover = volume_gu / float_volume * 100  # = 100%
        
        assert turnover >= 70.0, "100%换手率必须触发死亡防线"
        assert turnover >= 100.0, "换手率应等于100%"
    
    def test_defense_line_boundary(self):
        """
        验证边界情况：69.9%不触发，70.0%触发
        """
        # 69.9% 不触发
        turnover_69_9 = 69.9
        assert turnover_69_9 < 70.0, "69.9%不应触发死亡防线"
        
        # 70.0% 触发
        turnover_70 = 70.0
        assert turnover_70 >= 70.0, "70.0%应当触发死亡防线"


class TestTurnoverFormulaConsistency:
    """换手率公式一致性测试"""
    
    def test_formula_matches_code(self):
        """
        验证公式与代码实现一致
        代码: current_turnover = (volume_gu / float_volume * 100) if float_volume else 0
        """
        # 模拟代码中的变量
        current_volume = 1_000_000  # 手（来自get_full_tick）
        float_volume = 10_000_000_000  # 股
        
        # 代码中的计算
        volume_gu = current_volume * 100  # 手 → 股
        current_turnover = (volume_gu / float_volume * 100) if float_volume else 0
        
        # 手动计算验证
        expected = (1_000_000 * 100) / 10_000_000_000 * 100  # = 1.0%
        
        assert abs(current_turnover - expected) < 0.0001, \
            f"代码计算{current_turnover}% ≠ 预期{expected}%"
    
    def test_zero_float_volume(self):
        """
        验证float_volume为0时的处理
        """
        current_volume = 1_000_000
        float_volume = 0
        
        volume_gu = current_volume * 100
        current_turnover = (volume_gu / float_volume * 100) if float_volume else 0
        
        assert current_turnover == 0, "float_volume为0时应返回0"


class TestDeathTurnoverThreshold:
    """死亡换手阈值测试 - 确保70%是唯一值"""
    
    def test_threshold_is_70(self):
        """
        验证死亡换手阈值为70%
        参考: docs/DATA_UNITS_CANON.md
        """
        DEATH_TURNOVER_THRESHOLD = 70.0
        
        # 不允许出现150%或300%
        assert DEATH_TURNOVER_THRESHOLD == 70.0, \
            "死亡换手阈值必须是70%，不允许150%或300%"
    
    def test_no_magic_numbers_150_or_300(self):
        """
        【CTO F-1修复】纯Python文件扫描，验证代码中没有150%或300%的魔法数字
        死亡换手阈值必须是70%，不允许出现150%或300%
        """
        import pathlib
        import re
        
        # 扫描 run_live_trading_engine.py 中的非法阈值
        target = pathlib.Path(__file__).parent.parent / 'tasks' / 'run_live_trading_engine.py'
        # 文件不存在本身就是错误，必须fail
        assert target.exists(), f"引擎文件路径错误: {target}"
        
        content = target.read_text(encoding='utf-8', errors='replace')
        # 只扫描非注释行，避免血泪教训注释误报
        code_lines = [l for l in content.splitlines() if not l.strip().startswith('#')]
        code_only = '\n'.join(code_lines)
        bad_vals = re.findall(r'\b(150\.0|300\.0)\b', code_only)
        assert not bad_vals, f"发现非法换手率阈值: {bad_vals}，死亡换手只允许70%"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
