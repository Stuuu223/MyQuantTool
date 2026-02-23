"""
SanityGuards单元测试
验证常识护栏的各项检查逻辑
"""
import pytest
import sys
sys.path.insert(0, r'E:\MyQuantTool')

from logic.core.sanity_guards import SanityGuards


class TestPriceChangeCheck:
    """测试涨幅检查"""
    
    def test_gem_normal_change(self):
        """创业板正常涨幅"""
        passed, msg = SanityGuards.check_price_change(15.0, "300001.SZ")
        assert passed is True
        assert "通过" in msg
    
    def test_gem_limit_up(self):
        """创业板涨停"""
        passed, msg = SanityGuards.check_price_change(20.0, "300001.SZ")
        assert passed is True
        assert "通过" in msg or "涨跌停" in msg
    
    def test_gem_abnormal_change(self):
        """创业板异常涨幅（超过40%）"""
        passed, msg = SanityGuards.check_price_change(50.0, "300001.SZ")
        assert passed is False
        assert "涨幅异常" in msg
    
    def test_main_board_normal(self):
        """主板正常涨幅"""
        passed, msg = SanityGuards.check_price_change(5.0, "000001.SZ")
        assert passed is True
    
    def test_main_board_limit_up(self):
        """主板涨停"""
        passed, msg = SanityGuards.check_price_change(10.0, "000001.SZ")
        assert passed is True
        assert "通过" in msg or "涨跌停" in msg
    
    def test_main_board_abnormal(self):
        """主板异常涨幅（超过20%）"""
        passed, msg = SanityGuards.check_price_change(25.0, "000001.SZ")
        assert passed is False
    
    def test_star_board(self):
        """科创板"""
        passed, msg = SanityGuards.check_price_change(18.0, "688001.SH")
        assert passed is True
    
    def test_negative_change(self):
        """跌停情况"""
        passed, msg = SanityGuards.check_price_change(-10.0, "000001.SZ")
        assert passed is True
        assert "通过" in msg or "涨跌停" in msg


class TestScoreConsistency:
    """测试得分一致性检查"""
    
    def test_normal_scores(self):
        """正常得分情况"""
        passed, msg = SanityGuards.check_score_consistency(50.0, 45.0, "000001.SZ")
        assert passed is True
        assert "通过" in msg
    
    def test_zero_final_score_bug(self):
        """最终得分为0但基础分>0 - 这是bug！"""
        passed, msg = SanityGuards.check_score_consistency(30.0, 0.0, "300986.SZ")
        assert passed is False
        assert "得分逻辑错误" in msg
        assert "300986.SZ" in msg
    
    def test_both_zero(self):
        """两个得分都是0 - 可能是没触发策略"""
        passed, msg = SanityGuards.check_score_consistency(0.0, 0.0, "000001.SZ")
        assert passed is True  # 这种情况是正常的
    
    def test_negative_final_score(self):
        """最终得分为负数"""
        passed, msg = SanityGuards.check_score_consistency(50.0, -10.0, "000001.SZ")
        assert passed is False
        assert "超出合理范围" in msg
    
    def test_too_high_final_score(self):
        """最终得分过高"""
        passed, msg = SanityGuards.check_score_consistency(50.0, 250.0, "000001.SZ")
        assert passed is False
        assert "超出合理范围" in msg
    
    def test_boundary_score(self):
        """边界值测试"""
        passed, msg = SanityGuards.check_score_consistency(100.0, 200.0, "000001.SZ")
        assert passed is True  # 200是边界值，应该通过


class TestVolumeCheck:
    """测试成交量检查"""
    
    def test_normal_volume(self):
        """正常成交量"""
        passed, msg = SanityGuards.check_volume_reasonable(10000, 8000)
        assert passed is True
        assert "通过" in msg
    
    def test_zero_volume(self):
        """成交量为0"""
        passed, msg = SanityGuards.check_volume_reasonable(0, 10000)
        assert passed is False
        assert "为0或负数" in msg
    
    def test_negative_volume(self):
        """成交量为负数"""
        passed, msg = SanityGuards.check_volume_reasonable(-100, 10000)
        assert passed is False
    
    def test_extreme_volume(self):
        """成交量异常放大（50倍以上）"""
        passed, msg = SanityGuards.check_volume_reasonable(500000, 1000)
        assert passed is False
        assert "50倍以上" in msg
    
    def test_high_but_reasonable_volume(self):
        """成交量高但合理（30倍）"""
        passed, msg = SanityGuards.check_volume_reasonable(30000, 1000)
        assert passed is True  # 30倍小于50倍，应该通过


class TestFullSanityCheck:
    """测试完整Sanity Check"""
    
    def test_all_pass(self):
        """所有检查都通过"""
        data = {
            'stock_code': '300001.SZ',
            'change_pct': 15.0,
            'base_score': 50.0,
            'final_score': 45.0,
            'volume': 10000,
            'avg_volume_5d': 8000
        }
        passed, errors = SanityGuards.full_sanity_check(data)
        assert passed is True
        assert len(errors) == 0
    
    def test_multiple_errors(self):
        """多个错误同时存在"""
        data = {
            'stock_code': '000001.SZ',
            'change_pct': 50.0,  # 异常涨幅
            'base_score': 30.0,
            'final_score': 0.0,  # 得分逻辑错误
            'volume': 0,  # 成交量为0
            'avg_volume_5d': 1000
        }
        passed, errors = SanityGuards.full_sanity_check(data)
        assert passed is False
        assert len(errors) == 3  # 应该有3个错误
        assert any("涨幅异常" in e for e in errors)
        assert any("得分逻辑错误" in e for e in errors)
        assert any("为0或负数" in e for e in errors)
    
    def test_partial_data(self):
        """部分数据缺失"""
        data = {
            'stock_code': '300001.SZ',
            'change_pct': 10.0
            # 其他字段缺失
        }
        passed, errors = SanityGuards.full_sanity_check(data)
        # 应该使用默认值处理缺失字段
        assert isinstance(passed, bool)
        assert isinstance(errors, list)
    
    def test_real_world_bug_case(self):
        """
        真实场景：老板指出的bug
        base_score > 0 但 final_score = 0
        """
        data = {
            'stock_code': '300986.SZ',
            'change_pct': 5.0,
            'base_score': 30.0,
            'final_score': 0.0,
            'volume': 5000,
            'avg_volume_5d': 4000
        }
        passed, errors = SanityGuards.full_sanity_check(data)
        assert passed is False
        assert any("得分逻辑错误" in e for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
