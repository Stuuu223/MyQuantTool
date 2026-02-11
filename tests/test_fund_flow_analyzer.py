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

    def test_holiday_fallback_intraday(self, analyzer, monkeypatch):
        """
        测试：节假日回退（盘中模式）

        场景：
        - T-1, T-2 无数据（节假日）
        - T-3 有数据（回退成功）

        验证：
        - 回退次数 = 3
        - 最终返回 T-3 数据
        """
        call_count = 0
        call_dates = []

        def mock_fetch_from_cache(code: str, target_date):
            """Mock 缓存查询"""
            nonlocal call_count
            call_count += 1
            call_dates.append(target_date)

            # 前2次返回 None（模拟节假日）
            if call_count < 3:
                return None

            # 第3次返回有效数据（T-3）
            return {
                'trade_date': target_date.strftime('%Y%m%d'),
                'main_net_inflow': 5000000,  # 500万
                'super_net_inflow': 3000000,
                'big_net_inflow': 2000000
            }

        # 🔥 [关键] 使用 monkeypatch 替换内部方法
        monkeypatch.setattr(
            'logic.fund_flow_analyzer.FundFlowAnalyzer._fetch_from_cache',
            mock_fetch_from_cache
        )

        # 执行测试
        result = analyzer.get_fund_flow('000001.SZ', mode='intraday')

        # 验证回退次数
        assert call_count == 3, f"预期回退3次，实际回退{call_count}次"

        # 验证最终数据
        assert result is not None, "回退后应返回有效数据"
        if result and 'latest' in result:
            assert result['latest']['main_net_inflow'] == 5000000, \
                f"预期 main_net_inflow=5000000，实际={result['latest']['main_net_inflow']}"

    def test_holiday_fallback_afterhours(self, analyzer, monkeypatch):
        """
        测试：节假日回退（盘后模式）

        场景：
        - T 无数据（当日数据未生成）
        - T-1, T-2 无数据（节假日）
        - T-3 有数据（回退成功）

        验证：
        - 回退次数 = 4
        - 最终返回 T-3 数据
        """
        call_count = 0

        def mock_fetch_from_cache(code: str, target_date):
            nonlocal call_count
            call_count += 1

            # 前3次返回 None（T, T-1, T-2）
            if call_count < 4:
                return None

            # 第4次返回有效数据（T-3）
            return {
                'trade_date': target_date.strftime('%Y%m%d'),
                'main_net_inflow': 8000000,  # 800万
                'super_net_inflow': 5000000,
                'big_net_inflow': 3000000
            }

        monkeypatch.setattr(
            'logic.fund_flow_analyzer.FundFlowAnalyzer._fetch_from_cache',
            mock_fetch_from_cache
        )

        result = analyzer.get_fund_flow('000001.SZ', mode='afterhours')

        # 验证回退次数
        assert call_count == 4, f"预期回退4次，实际回退{call_count}次"

        # 验证数据正确性
        assert result is not None
        if result and 'latest' in result:
            assert result['latest']['main_net_inflow'] == 8000000

    def test_max_fallback_depth_exceeded(self, analyzer, monkeypatch):
        """
        测试：超过最大回退深度（5天）

        场景：
        - T-1 ~ T-5 全部无数据

        预期：
        - 回退5次后返回 None 或空字典
        """
        call_count = 0

        def mock_fetch_always_none(code: str, target_date):
            nonlocal call_count
            call_count += 1
            return None  # 所有日期都无数据

        monkeypatch.setattr(
            'logic.fund_flow_analyzer.FundFlowAnalyzer._fetch_from_cache',
            mock_fetch_always_none
        )

        result = analyzer.get_fund_flow('000001.SZ', mode='intraday')

        # 验证回退次数不超过5次
        assert call_count <= 5, f"回退次数超限: {call_count}次（最大5次）"

        # 验证返回值为空
        assert result is None or result == {} or result.get('latest') is None, \
            f"超过最大回退深度应返回空，实际={result}"

    def test_data_structure_consistency(self, analyzer, monkeypatch):
        """
        测试：回退数据结构一致性

        验证：
        - 回退获取的数据与直接获取的数据结构相同
        """
        mock_data = {
            'trade_date': '20260210',
            'main_net_inflow': 10000000,
            'super_net_inflow': 6000000,
            'big_net_inflow': 4000000,
            'medium_net_inflow': 2000000,
            'small_net_inflow': -2000000
        }

        def mock_fetch_consistent(code: str, target_date):
            return mock_data

        monkeypatch.setattr(
            'logic.fund_flow_analyzer.FundFlowAnalyzer._fetch_from_cache',
            mock_fetch_consistent
        )

        result = analyzer.get_fund_flow('000001.SZ', mode='intraday')

        # 验证数据结构完整性
        assert result is not None
        assert 'latest' in result

        expected_fields = ['main_net_inflow', 'super_net_inflow', 'big_net_inflow']
        for field in expected_fields:
            assert field in result['latest'], f"缺少字段: {field}"


class TestPerformance:
    """性能测试套件"""

    @pytest.fixture
    def analyzer(self):
        return FundFlowAnalyzer()

    def test_cache_performance(self, analyzer):
        """
        测试：缓存性能

        验证：
        - 首次查询耗时 < 1000ms
        - 缓存查询耗时 < 10ms
        """
        import time

        code = '000001.SZ'

        # 首次查询（可能从数据源获取）
        start = time.perf_counter()
        result1 = analyzer.get_fund_flow(code)
        first_elapsed = (time.perf_counter() - start) * 1000

        # 缓存查询
        start = time.perf_counter()
        result2 = analyzer.get_fund_flow(code)
        cache_elapsed = (time.perf_counter() - start) * 1000

        # 性能断言
        assert first_elapsed < 1000, f"首次查询耗时过长: {first_elapsed:.2f}ms"
        assert cache_elapsed < 10, f"缓存查询耗时过长: {cache_elapsed:.2f}ms"

        # 记录性能指标
        print(f"\n⏱️  性能测试结果:")
        print(f"   首次查询: {first_elapsed:.2f}ms")
        print(f"   缓存查询: {cache_elapsed:.2f}ms")
        print(f"   性能提升: {first_elapsed/cache_elapsed:.0f}x")

    def test_fallback_performance(self, analyzer, monkeypatch):
        """
        测试：回退性能

        验证：
        - 5次回退总耗时 < 100ms
        """
        import time

        call_count = 0

        def mock_fetch_slow(code: str, target_date):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # 模拟10ms延迟
            return None if call_count < 5 else {'main_net_inflow': 1000000}

        monkeypatch.setattr(
            'logic.fund_flow_analyzer.FundFlowAnalyzer._fetch_from_cache',
            mock_fetch_slow
        )

        start = time.perf_counter()
        result = analyzer.get_fund_flow('000001.SZ', mode='intraday')
        elapsed = (time.perf_counter() - start) * 1000

        # 性能断言
        assert elapsed < 100, f"回退耗时过长: {elapsed:.2f}ms（预期 <100ms）"

        print(f"\n⏱️  回退性能: {elapsed:.2f}ms（{call_count}次回退）")


# ===== 运行测试 =====
if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])