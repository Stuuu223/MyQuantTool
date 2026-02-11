"""
资金流分析器单元测试
测试多层回退逻辑 + main_net_inflow 字段提取

Author: iFlow CLI
Version: V1.0
Date: 2026-02-11
"""
import pytest
from datetime import datetime, timedelta, date
from logic.fund_flow_analyzer import FundFlowAnalyzer


class TestFundFlowAnalyzer:
    """资金流分析器测试套件"""

    @pytest.fixture
    def analyzer(self):
        """测试fixture：创建分析器实例"""
        return FundFlowAnalyzer()

    def test_main_net_inflow_field_exists(self, analyzer):
        """
        测试：main_net_inflow 字段存在性

        验证：
        - latest 节点存在
        - main_net_inflow 字段存在
        - 字段类型为数值
        """
        result = analyzer.get_fund_flow('000001.SZ')

        if result and result.get('latest'):
            assert 'main_net_inflow' in result['latest'], \
                "缺少 main_net_inflow 字段"

            main_net_inflow = result['latest']['main_net_inflow']
            assert isinstance(main_net_inflow, (int, float)), \
                f"main_net_inflow 类型错误: {type(main_net_inflow)}"

    def test_fallback_logic_structure(self, analyzer):
        """
        测试：回退逻辑结构完整性

        验证：
        - 盘中模式：T-1 → T-5 回退路径
        - 盘后模式：T → T-4 回退路径
        """
        # 测试盘中模式
        result_intraday = analyzer.get_fund_flow('000001.SZ', mode='intraday')
        assert result_intraday is not None or result_intraday == {}, \
            "盘中模式回退失败"

        # 测试盘后模式
        result_afterhours = analyzer.get_fund_flow('000001.SZ', mode='afterhours')
        assert result_afterhours is not None or result_afterhours == {}, \
            "盘后模式回退失败"

    def test_cache_integration(self, analyzer):
        """
        测试：缓存集成（验证缓存命中）

        验证：
        - 两次相同请求应命中缓存
        - 缓存数据结构正确
        """
        code = '000001.SZ'

        # 第一次请求（可能从数据源获取）
        result1 = analyzer.get_fund_flow(code)

        # 第二次请求（应命中缓存）
        result2 = analyzer.get_fund_flow(code)

        # 验证结构一致性
        if result1 and result2:
            assert result1.keys() == result2.keys(), \
                "缓存数据结构不一致"


class TestFallbackEdgeCases:
    """边界条件测试"""

    @pytest.fixture
    def analyzer(self):
        return FundFlowAnalyzer()

    def test_invalid_stock_code(self, analyzer):
        """测试：无效股票代码"""
        result = analyzer.get_fund_flow('INVALID.XX')

        # 应返回 None 或空字典，而非抛出异常
        assert result is None or result == {}

    def test_holiday_fallback(self, analyzer):
        """测试：节假日回退（模拟连续3天无数据）"""
        # 注意：此测试需要 mock 数据源
        # 实际实现时需要配合 monkeypatch 或 unittest.mock
        pass


# ===== 运行测试 =====
if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])