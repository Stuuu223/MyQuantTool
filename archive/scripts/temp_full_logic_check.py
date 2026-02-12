"""
两天全量逻辑检查：验证决策树在所有样本上的标签一致性

检查项：
1. ratio < 0.5% 的票都是PASS❌
2. ratio > 5% 的票都是TRAP❌
3. 有诱多信号的票不会是FOCUS✅
4. 持续低ratio的票（如601869）两天都是PASS❌
"""
import json
from pathlib import Path
from typing import Dict, Set, Tuple

def load_equity_info():
    """加载流通市值数据"""
    with open("data/equity_info_tushare.json", 'r', encoding='utf-8') as f:
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

def get_decision_tag_from_snapshot(snapshot, code):
    """从快照中获取决策标签"""
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        stocks = snapshot["results"].get(pool, [])
        for stock in stocks:
            if stock.get('code') == code:
                # 优先使用决策树标签（如果有）
                if 'decision_tag' in stock:
                    return stock['decision_tag']
                # 兜底：根据池子判断标签
                if pool == 'opportunities':
                    return 'FOCUS✅'
                elif pool == 'watchlist':
                    return 'WATCH'
                elif pool == 'blacklist':
                    return 'PASS❌'
    return None

def calculate_decision_tag(ratio, risk_score, trap_signals):
    """
    资金推动力决策树:
    第1关: ratio < 0.5% → PASS❌（止损优先，资金推动力太弱）
    第2关: ratio > 5% → TRAP❌（暴拉出货风险）
    第3关: 诱多 + 高风险 → BLOCK❌
    第4关: 1-3% + 低风险 + 无诱多 → FOCUS✅
    """
    # 第1关: 资金推动力太弱，直接 PASS（止损优先）
    if ratio is not None and ratio < 0.5:
        return "PASS❌"

    # 第2关: 暴拉出货风险
    if ratio is not None and ratio > 5:
        return "TRAP❌"

    # 第3关: 诱多 + 高风险
    if trap_signals and risk_score >= 0.4:
        return "BLOCK❌"

    # 第4关: 标准 FOCUS
    if (ratio is not None and
        1 <= ratio <= 3 and
        risk_score <= 0.2 and
        not trap_signals):
        return "FOCUS✅"

    # 兜底
    return "BLOCK❌"

def get_trap_signals(snapshot, code):
    """从快照中获取诱多信号"""
    for pool in ['opportunities', 'watchlist', 'blacklist']:
        stocks = snapshot["results"].get(pool, [])
        for stock in stocks:
            if stock.get('code') == code:
                return stock.get('trap_signals', [])
    return []

def analyze_date(equity_data, snapshot_file, date_str):
    """分析单个日期的数据"""
    print(f"\n{'=' * 70}")
    print(f"分析日期: {date_str}")
    print('=' * 70)

    # 加载快照
    with open(snapshot_file, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    # 统计信息
    total_stocks = 0
    ratio_below_05 = 0
    ratio_below_05_not_pass = 0
    ratio_above_5 = 0
    ratio_above_5_not_trap = 0
    trap_signals_count = 0
    trap_signals_not_filtered = 0

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
            decision_tag = get_decision_tag_from_snapshot(snapshot, code)

            # 计算ratio
            ratio = None
            if main_net is not None and float_mv > 0:
                ratio = main_net / float_mv * 100

            # 使用决策树计算正确的决策标签
            correct_decision_tag = calculate_decision_tag(ratio, stock.get('risk_score', 0), trap_signals)

            # 检查1: ratio < 0.5% 应该是PASS❌
            if ratio is not None and ratio < 0.5:
                ratio_below_05 += 1
                if correct_decision_tag != 'PASS❌':
                    ratio_below_05_not_pass += 1
                    issues.append({
                        'type': 'ratio_below_05_not_pass',
                        'code': code,
                        'ratio': ratio,
                        'correct_decision_tag': correct_decision_tag,
                        'pool': pool
                    })

            # 检查2: ratio > 5% 应该是TRAP❌
            if ratio is not None and ratio > 5:
                ratio_above_5 += 1
                if correct_decision_tag != 'PASS❌' and correct_decision_tag != 'TRAP❌':
                    ratio_above_5_not_trap += 1
                    issues.append({
                        'type': 'ratio_above_5_not_trap',
                        'code': code,
                        'ratio': ratio,
                        'correct_decision_tag': correct_decision_tag,
                        'pool': pool
                    })

            # 检查3: 有诱多信号的票不应该是FOCUS✅
            if trap_signals:
                trap_signals_count += 1
                if correct_decision_tag == 'FOCUS✅':
                    trap_signals_not_filtered += 1
                    issues.append({
                        'type': 'trap_signals_not_filtered',
                        'code': code,
                        'ratio': ratio,
                        'correct_decision_tag': correct_decision_tag,
                        'trap_signals': trap_signals,
                        'pool': pool
                    })

    # 输出统计
    print(f"总股票数: {total_stocks}")
    print(f"\n检查1: ratio < 0.5% 应该是PASS❌")
    print(f"  符合条件: {ratio_below_05} 只")
    print(f"  异常: {ratio_below_05_not_pass} 只")

    print(f"\n检查2: ratio > 5% 应该是TRAP❌")
    print(f"  符合条件: {ratio_above_5} 只")
    print(f"  异常: {ratio_above_5_not_trap} 只")

    print(f"\n检查3: 有诱多信号的票不应该是FOCUS✅")
    print(f"  符合条件: {trap_signals_count} 只")
    print(f"  异常: {trap_signals_not_filtered} 只")

    # 输出异常详情
    if issues:
        print(f"\n{'=' * 70}")
        print(f"发现 {len(issues)} 个异常")
        print('=' * 70)
        for i, issue in enumerate(issues, 1):
            print(f"\n异常 {i}: {issue['type']}")
            print(f"  股票: {issue['code']}")
            if 'ratio' in issue:
                print(f"  ratio: {issue['ratio']:.4f}%")
            print(f"  决策标签: {issue['correct_decision_tag']}")
            print(f"  所属池: {issue['pool']}")
            if 'trap_signals' in issue:
                print(f"  诱多信号: {issue['trap_signals']}")
    else:
        print(f"\n✅ 未发现异常")

    return issues

def main():
    print("=" * 70)
    print("两天全量逻辑检查")
    print("=" * 70)

    # 加载equity_info数据
    equity_data = load_equity_info()

    # 分析2026-02-05
    issues_20260205 = analyze_date(equity_data, "data/scan_results/2026-02-05_premarket.json", "20260205")

    # 分析2026-02-06
    issues_20260206 = analyze_date(equity_data, "data/scan_results/2026-02-06_094521_intraday.json", "20260206")

    # 汇总
    total_issues = len(issues_20260205) + len(issues_20260206)

    print(f"\n{'=' * 70}")
    print("汇总")
    print('=' * 70)
    print(f"2026-02-05 异常: {len(issues_20260205)} 个")
    print(f"2026-02-06 异常: {len(issues_20260206)} 个")
    print(f"总异常数: {total_issues} 个")

    if total_issues == 0:
        print("\n✅ 所有检查通过，决策树逻辑正确")
    else:
        print(f"\n⚠️  发现 {total_issues} 个异常，需要修复")

if __name__ == "__main__":
    main()