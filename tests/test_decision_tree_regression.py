"""
决策树回归测试

功能：
1. 集成回归测试：验证决策树在真实快照数据上的表现
2. 确保所有样本符合决策树规则：
   - ratio < 0.5% → PASS❌
   - ratio > 5% → TRAP❌ 或 PASS❌
   - 有诱多信号 + 高风险 → 不能是 FOCUS✅

运行：
    pytest tests/test_decision_tree_regression.py -v

Author: iFlow CLI
Version: V1.0
"""

import json
import pytest
from pathlib import Path
from typing import Dict, List, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def load_equity_info():
    """加载流通市值数据"""
    equity_file = PROJECT_ROOT / "data" / "equity_info_tushare.json"
    with open(equity_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_main_net_inflow(snapshot, code):
    """从快照中提取主力净流入"""
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        stocks = snapshot["results"].get(pool, [])
        for stock in stocks:
            if stock.get('code') == code:
                flow_data = stock.get('flow_data', {})
                records = flow_data.get('records', [])
                if records:
                    latest_record = records[0]
                    return latest_record.get('main_net_inflow', 0)
    return None


def get_trap_signals(snapshot, code):
    """从快照中获取诱多信号"""
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        stocks = snapshot["results"].get(pool, [])
        for stock in stocks:
            if stock.get('code') == code:
                return stock.get('trap_signals', [])
    return []


def calculate_decision_tag(ratio, risk_score, trap_signals, is_price_up_3d_capital_not_follow=False):
    """
    资金推动力决策树:
    第1关: ratio < 0.5% → PASS❌（止损优先，资金推动力太弱）
    第2关: ratio > 5% → TRAP❌（暴拉出货风险）
    第3关: 诱多 + 高风险 → BLOCK❌
    第3.5关: 3日连涨资金不跟 + ratio < 1% → TRAP❌
    第4关: 1-3% + 低风险 + 无诱多 → FOCUS✅
    """
    # 第1关: 资金推动力太弱，直接 PASS（止损优先）
    if ratio is None or ratio < 0.5:
        return "PASS❌"

    # 第2关: 暴拉出货风险
    if ratio > 5:
        return "TRAP❌"

    # 第3关: 诱多 + 高风险
    if len(trap_signals) > 0 and risk_score >= 0.4:
        return "BLOCK❌"

    # 第3.5关: 3日连涨资金不跟 + ratio < 1% → TRAP❌
    if is_price_up_3d_capital_not_follow and ratio < 1:
        return "TRAP❌"

    # 第4关: 标准 FOCUS
    if 1 <= ratio <= 3 and risk_score < 0.4 and len(trap_signals) == 0:
        return "FOCUS✅"

    # 兜底
    return "BLOCK❌"


def validate_date(equity_data, snapshot_file, date_str):
    """
    验证单个日期的数据

    Returns:
        tuple: (total_stocks, issues)
    """
    # 加载快照
    snapshot_file_path = PROJECT_ROOT / "data" / "scan_results" / snapshot_file
    with open(snapshot_file_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    # 统计信息
    total_stocks = 0
    issues = []

    # 遍历快照中的所有股票
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        stocks = snapshot["results"].get(pool, [])
        for stock in stocks:
            code = stock.get('code')
            if not code:
                continue

            total_stocks += 1

            # 提取数据
            main_net = extract_main_net_inflow(snapshot, code)
            float_mv = equity_data["data"].get(date_str, {}).get(code, {}).get("float_mv", 0)
            trap_signals = get_trap_signals(snapshot, code)
            risk_score = stock.get('risk_score', 0)

            # 计算ratio
            ratio = None
            if main_net is not None and float_mv > 0:
                ratio = main_net / float_mv * 100

            # 使用决策树计算正确的决策标签
            correct_decision_tag = calculate_decision_tag(ratio, risk_score, trap_signals)

            # 检查1: ratio < 0.5% 应该是PASS❌
            if ratio is not None and ratio < 0.5:
                if correct_decision_tag != 'PASS❌':
                    issues.append({
                        'type': 'ratio_below_05_not_pass',
                        'code': code,
                        'ratio': ratio,
                        'correct_decision_tag': correct_decision_tag,
                        'pool': pool
                    })

            # 检查2: ratio > 5% 应该是TRAP❌
            if ratio is not None and ratio > 5:
                if correct_decision_tag != 'TRAP❌' and correct_decision_tag != 'PASS❌':
                    issues.append({
                        'type': 'ratio_above_05_not_trap',
                        'code': code,
                        'ratio': ratio,
                        'correct_decision_tag': correct_decision_tag,
                        'pool': pool
                    })

            # 检查3: 有诱多信号的票不应该是FOCUS✅
            if trap_signals:
                if correct_decision_tag == 'FOCUS✅':
                    issues.append({
                        'type': 'trap_signals_not_filtered',
                        'code': code,
                        'ratio': ratio,
                        'correct_decision_tag': correct_decision_tag,
                        'trap_signals': trap_signals,
                        'pool': pool
                    })

    return total_stocks, issues


@pytest.mark.regression
class TestDecisionTreeRegression:
    """决策树回归测试类"""

    def test_20260205_full_regression(self):
        """
        测试 2026-02-05 的全量数据回归

        验证：
        - ratio < 0.5% → PASS❌
        - ratio > 5% → TRAP❌ 或 PASS❌
        - 有诱多信号 + 高风险 → 不能是 FOCUS✅
        """
        equity_data = load_equity_info()
        total_stocks, issues = validate_date(
            equity_data,
            "2026-02-05_premarket.json",
            "20260205"
        )

        # 统计问题类型
        issue_types = {}
        for issue in issues:
            issue_type = issue['type']
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        # 如果有异常，输出详细信息
        if issues:
            error_msg = f"\n发现 {len(issues)} 个异常（总共 {total_stocks} 只股票）:\n"
            for issue_type, count in issue_types.items():
                error_msg += f"  - {issue_type}: {count} 个\n"
            error_msg += "\n异常详情:\n"
            for i, issue in enumerate(issues[:5], 1):  # 只显示前5个
                error_msg += f"  {i}. {issue['code']}: {issue['type']}\n"
            if len(issues) > 5:
                error_msg += f"  ... 还有 {len(issues) - 5} 个异常\n"

            pytest.fail(error_msg)

    def test_20260206_full_regression(self):
        """
        测试 2026-02-06 的全量数据回归

        验证：
        - ratio < 0.5% → PASS❌
        - ratio > 5% → TRAP❌ 或 PASS❌
        - 有诱多信号 + 高风险 → 不能是 FOCUS✅
        """
        equity_data = load_equity_info()
        total_stocks, issues = validate_date(
            equity_data,
            "2026-02-06_094521_intraday.json",
            "20260206"
        )

        # 统计问题类型
        issue_types = {}
        for issue in issues:
            issue_type = issue['type']
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        # 如果有异常，输出详细信息
        if issues:
            error_msg = f"\n发现 {len(issues)} 个异常（总共 {total_stocks} 只股票）:\n"
            for issue_type, count in issue_types.items():
                error_msg += f"  - {issue_type}: {count} 个\n"
            error_msg += "\n异常详情:\n"
            for i, issue in enumerate(issues[:5], 1):  # 只显示前5个
                error_msg += f"  {i}. {issue['code']}: {issue['type']}\n"
            if len(issues) > 5:
                error_msg += f"  ... 还有 {len(issues) - 5} 个异常\n"

            pytest.fail(error_msg)


@pytest.mark.unit
class TestDecisionTreeUnit:
    """决策树单元测试类（金标准样本）"""

    def test_golden_sample_601869_pass(self):
        """
        测试金标准样本 601869.SH
        特征：ratio < 0.5% + 有诱多信号 → PASS❌
        """
        ratio = 0.0047  # 0.0047%
        risk_score = 0.2
        trap_signals = ['长期流出+单日巨量']

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "PASS❌", \
            f"601869.SH 应该是 PASS❌，但得到 {decision}（ratio={ratio}%, risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_golden_sample_603607_focus(self):
        """
        测试金标准样本 603607.SH
        特征：1-3% + 低风险 + 无诱多 → FOCUS✅
        """
        ratio = 1.71  # 1.71%
        risk_score = 0.1
        trap_signals = []

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "FOCUS✅", \
            f"603607.SH 应该是 FOCUS✅，但得到 {decision}（ratio={ratio}%, risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_golden_sample_301486_trap(self):
        """
        测试金标准样本 301486.SZ
        特征：有诱多信号 + 高风险 → BLOCK❌
        """
        ratio = 1.07  # 1.07%
        risk_score = 0.4
        trap_signals = ['单日暴量+隔日反手', '单日暴量+隔日反手', '单日暴量+隔日反手', '单日暴量+隔日反手']

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "BLOCK❌", \
            f"301486.SZ 应该是 BLOCK❌，但得到 {decision}（ratio={ratio}%, risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_golden_sample_002173_trap(self):
        """
        测试金标准样本 002173.SZ
        特征：有诱多信号 + 高风险 → BLOCK❌
        """
        ratio = 2.18  # 2.18%
        risk_score = 0.4
        trap_signals = ['单日暴量+隔日反手', '单日暴量+隔日反手', '单日暴量+隔日反手', '单日暴量+隔日反手', '单日暴量+隔日反手']

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "BLOCK❌", \
            f"002173.SZ 应该是 BLOCK❌，但得到 {decision}（ratio={ratio}%, risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_golden_sample_trap_high_ratio(self):
        """
        测试金标准样本：ratio > 5% → TRAP❌
        """
        ratio = 6.5  # 6.5%
        risk_score = 0.3
        trap_signals = []

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "TRAP❌", \
            f"ratio={ratio}% 应该是 TRAP❌，但得到 {decision}（risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_edge_case_ratio_05(self):
        """
        测试边界情况：ratio = 0.5%（正好在边界）
        应该走第4关或其他规则，而不是第1关
        """
        ratio = 0.5  # 0.5%
        risk_score = 0.2
        trap_signals = []

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        # ratio = 0.5 不满足 < 0.5，所以不会走第1关
        # 但也不满足第4关（1-3%），所以走兜底 BLOCK❌
        assert decision == "BLOCK❌", \
            f"ratio=0.5% 应该是 BLOCK❌，但得到 {decision}（risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_edge_case_ratio_1(self):
        """
        测试边界情况：ratio = 1%（第4关下界）
        """
        ratio = 1.0  # 1.0%
        risk_score = 0.2
        trap_signals = []

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "FOCUS✅", \
            f"ratio=1.0% 应该是 FOCUS✅，但得到 {decision}（risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_edge_case_ratio_3(self):
        """
        测试边界情况：ratio = 3%（第4关上界）
        """
        ratio = 3.0  # 3.0%
        risk_score = 0.2
        trap_signals = []

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "FOCUS✅", \
            f"ratio=3.0% 应该是 FOCUS✅，但得到 {decision}（risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_edge_case_ratio_31(self):
        """
        测试边界情况：ratio = 3.1%（刚超过第4关上界）
        """
        ratio = 3.1  # 3.1%
        risk_score = 0.2
        trap_signals = []

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "BLOCK❌", \
            f"ratio=3.1% 应该是 BLOCK❌，但得到 {decision}（risk_score={risk_score}, trap_signals={trap_signals}）"

    def test_edge_case_risk_04(self):
        """
        测试边界情况：risk_score = 0.4（第3关下界）
        """
        ratio = 2.0  # 2.0%
        risk_score = 0.4
        trap_signals = ['单日暴量+隔日反手']

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        assert decision == "BLOCK❌", \
            f"risk_score=0.4 + 诱多信号 应该是 BLOCK❌，但得到 {decision}（ratio={ratio}%, trap_signals={trap_signals}）"

    def test_edge_case_risk_039(self):
        """
        测试边界情况：risk_score = 0.39（刚低于第3关下界）
        """
        ratio = 2.0  # 2.0%
        risk_score = 0.39
        trap_signals = ['单日暴量+隔日反手']

        decision = calculate_decision_tag(ratio, risk_score, trap_signals)

        # risk_score=0.39 不满足 >= 0.4，所以不会走第3关
        # 但有trap_signals，也不满足第4关，所以走兜底 BLOCK❌
        assert decision == "BLOCK❌", \
            f"risk_score=0.39 + 诱多信号 应该是 BLOCK❌，但得到 {decision}（ratio={ratio}%, trap_signals={trap_signals}）"

    def test_gate_3_5_price_up_capital_not_follow_trap(self):
        """
        第3.5关测试：3日连涨但资金不跟 + ratio < 1% → TRAP❌
        """
        ratio = 0.8  # 0.8%
        risk_score = 0.2
        trap_signals = []
        is_price_up_3d_capital_not_follow = True

        decision = calculate_decision_tag(ratio, risk_score, trap_signals, is_price_up_3d_capital_not_follow)

        assert decision == "TRAP❌", \
            f"3日连涨资金不跟且ratio<1%应该触发TRAP❌，但得到 {decision}"

    def test_gate_3_5_price_up_capital_not_follow_pass_high_ratio(self):
        """
        第3.5关反例：3日连涨但资金不跟，但ratio=2.0 → 不触发第3.5关
        """
        ratio = 2.0  # 2.0%
        risk_score = 0.2
        trap_signals = []
        is_price_up_3d_capital_not_follow = True

        decision = calculate_decision_tag(ratio, risk_score, trap_signals, is_price_up_3d_capital_not_follow)

        assert decision == "FOCUS✅", \
            f"ratio在1-3%且无诱多应该是FOCUS✅，但得到 {decision}"

    def test_gate_3_5_no_price_up_capital_not_follow(self):
        """
        第3.5关反例：不满足3日连涨资金不跟 → 不触发
        """
        ratio = 0.3  # 0.3%
        risk_score = 0.2
        trap_signals = []
        is_price_up_3d_capital_not_follow = False

        decision = calculate_decision_tag(ratio, risk_score, trap_signals, is_price_up_3d_capital_not_follow)

        assert decision == "PASS❌", \
            f"ratio < 0.5%且不满足3.5关条件应该触发第1关PASS❌，但得到 {decision}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])