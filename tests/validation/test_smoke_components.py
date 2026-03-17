"""
V2.0 冒烟测试 - 验证五个核心组件接口
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
import traceback

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

# 【Fix-4修复】使用固定的测试时间，确保测试幂等性
TEST_TIME = datetime(2026, 3, 17, 10, 30, 0)

def check(name, fn):
    try:
        fn()
        results.append((PASS, name))
        print(f"{PASS} {name}")
    except Exception as e:
        results.append((FAIL, name))
        print(f"{FAIL} {name}")
        traceback.print_exc()

# ── TEST 1: StockStateBuffer 基础功能
def test_stock_state_buffer():
    from tools.mock_live_runner import StockStateBuffer
    buf = StockStateBuffer("000001.SZ")
    for i in range(35):  # 超过WINDOW=30，测试滚动
        buf.update(price=10.0+i*0.01, mfe=1.0+i*0.01, sustain_ratio=1.5)
    assert len(buf.price_history) == 30, f"WINDOW应=30，实际={len(buf.price_history)}"
    slope = buf.get_current_slope()
    assert isinstance(slope, float), "slope应为float"
    print(f"  → price_history长度={len(buf.price_history)}, slope={slope:.4f}")

check("StockStateBuffer 滚动窗口+斜率计算", test_stock_state_buffer)

# ── TEST 2: PaperTradeEngine 完整买卖周期
def test_paper_engine():
    from logic.execution.paper_trade_engine import PaperTradeEngine
    e = PaperTradeEngine(initial_capital=100_000)
    
    # 买入
    order = e.place_order('000001.SZ', 10.0, 'BUY',
                          trigger_type='test', timestamp=TEST_TIME)
    assert order is not None, "买入应返回非None"
    assert '000001.SZ' in e.positions, "买入后应有持仓"
    
    # 【接口修正】positions是Dict[str, dict]，不是对象
    pos = e.positions['000001.SZ']
    assert isinstance(pos, dict), "position应为dict"
    assert 'cost_price' in pos, "position应有cost_price key"
    print(f"  → 买入成本={pos['cost_price']}, 持仓数量={pos.get('volume', 'N/A')}")
    
    # 更新价格
    e.update_position_price('000001.SZ', 10.5)
    pnl = e.get_unrealized_pnl_pct('000001.SZ')
    assert pnl > 0, f"涨价后pnl应>0，实际={pnl}"
    print(f"  → 更新价格后pnl={pnl:.2f}%")
    
    # 总资产
    total = e.get_total_asset()
    assert total > 100_000, f"总资产应>初始本金，实际={total}"
    
    # 卖出
    sell_order = e.place_order('000001.SZ', 10.5, 'SELL',
                                timestamp=TEST_TIME)
    assert sell_order is not None, "卖出应返回非None"
    
    # 【Fix-4修复】卖出后验证持仓清空+资金增加
    assert '000001.SZ' not in e.positions, "卖出后持仓应清空"
    post_capital = e.get_total_asset()  # 使用正确的方法名
    assert post_capital > 100_000, f"卖出盈利后总资产应>初始本金，实际={post_capital}"
    print(f"  → 卖出完成，持仓已清空，总资产={post_capital:.2f}")
    
    # 绩效报告
    report = e.get_performance_report()
    assert isinstance(report, dict), "get_performance_report应返回dict"
    print(f"  → 绩效报告keys={list(report.keys())}")

check("PaperTradeEngine 完整买卖周期", test_paper_engine)

# ── TEST 3: TradeDecisionBrain 签名验证
def test_decision_brain():
    from logic.execution.trade_decision_brain import TradeDecisionBrain
    brain = TradeDecisionBrain()
    
    # 空榜单 - 【接口确认】返回dict而非None
    result_empty = brain.on_new_frame(
        top_targets=[],
        current_time=TEST_TIME,
        held_stock_current_price=0.0
    )
    print(f"  → 空榜单返回: action={result_empty.get('action')}")
    assert result_empty is not None, "空榜单应返回dict而非None"
    assert result_empty.get('action') == 'WATCH', "空榜单应返回WATCH"
    
    # 【Fix-4修复】扩充榜单到12只票，使用正确的trigger_type
    # VALID_TRIGGERS = {'vacuum_ignition', 'stair_breakout', 'gravity_slingshot'}
    # 榜首score设为其余票的3x以上触发里氏震级条件
    top_targets = []
    # 榜首：高分+有效trigger
    top_targets.append({
        'code': '000001.SZ', 'score': 30000, 'price': 10.0,
        'trigger_type': 'gravity_slingshot', 'trigger_confidence': 0.85,
        'ignition_prob': 70.0,  # 【R4-4修复】百分比形式(70%)，非小数(0.7)
        'mfe': 1.5, 'sustain_ratio': 2.0,
    })
    # 其余11只票：分数远低于榜首
    for i in range(1, 12):
        top_targets.append({
            'code': f'600{str(i).zfill(3)}.SH', 'score': 5000 + i*100, 'price': 10.0 + i,
            'trigger_type': 'none', 'trigger_confidence': 0.0,
            'ignition_prob': 30.0,  # 【R4-4修复】百分比形式
            'mfe': 0.8, 'sustain_ratio': 1.2,
        })
    
    result = brain.on_new_frame(
        top_targets=top_targets,
        current_time=TEST_TIME,
        held_stock_current_price=0.0
    )
    print(f"  → 通道A测试: action={result.get('action')}, code={result.get('stock_code')}")
    required_keys = ['action', 'stock_code', 'price', 'reason',
                     'score', 'trigger_type']
    for k in required_keys:
        assert k in result, f"返回字典缺少key: {k}"
    
    # 【Fix-4修复】验证入场逻辑是否正确触发 - 使用assert而非print
    # 榜首30000分，其余<10000，p90应该远低于榜首，应触发BUY
    assert result.get('action') == 'BUY', \
        f"通道A入场验证失败: 期望BUY，实际={result.get('action')} " \
        f"原因={result.get('reason', 'N/A')}"
    print(f"  → ✅ 通道A入场正确触发: BUY {result.get('stock_code')}")
    
    # ── 【R4-4新增】通道B测试：无有效trigger但高点火概率
    print("\n  ── 通道B测试（无trigger，高点火概率）──")
    brain_b = TradeDecisionBrain()
    top_targets_b = []
    # 榜首：无trigger但高点火概率(75% > 门槛20%)
    top_targets_b.append({
        'code': '000002.SZ', 'score': 30000, 'price': 12.0,
        'trigger_type': 'none',  # 无有效trigger → 走通道B
        'trigger_confidence': 0.0,
        'ignition_prob': 75.0,  # 百分比形式，>=20%门槛
        'mfe': 1.5, 'sustain_ratio': 2.0,
    })
    for i in range(1, 12):
        top_targets_b.append({
            'code': f'601{str(i).zfill(3)}.SH', 'score': 5000 + i*100, 'price': 12.0 + i,
            'trigger_type': 'none', 'trigger_confidence': 0.0,
            'ignition_prob': 15.0,  # < 20%门槛，不满足通道B
            'mfe': 0.8, 'sustain_ratio': 1.2,
        })
    
    result_b = brain_b.on_new_frame(
        top_targets=top_targets_b,
        current_time=TEST_TIME,
        held_stock_current_price=0.0
    )
    print(f"  → 通道B测试: action={result_b.get('action')}, code={result_b.get('stock_code')}")
    # 通道B：无trigger但ignition_prob=75% >= 20%门槛，应触发BUY
    assert result_b.get('action') == 'BUY', \
        f"通道B入场验证失败: 期望BUY，实际={result_b.get('action')} " \
        f"原因={result_b.get('reason', 'N/A')}"
    assert result_b.get('stock_code') == '000002.SZ', \
        f"通道B应买入榜首000002.SZ，实际={result_b.get('stock_code')}"
    
    # 【R5-3新增】验证通道B的路径（应该包含ignition相关信息）
    reason_b = result_b.get('reason', '')
    assert 'ignition' in reason_b.lower() or result_b.get('trigger_type') == 'none', \
        f"通道B应通过ignition_prob触发，但reason={reason_b!r}, trigger_type={result_b.get('trigger_type')}"
    print(f"  → ✅ 通道B路径验证: trigger_type={result_b.get('trigger_type')}, reason={reason_b[:50]}")
    
    # 【R5-3新增】边界情况：ignition_prob刚好低于门槛不应触发BUY
    print("\n  ── 通道B边界测试（ignition_prob=19.9%，低于20%门槛）──")
    brain_b_fail = TradeDecisionBrain()
    top_targets_b_fail = []
    top_targets_b_fail.append({
        'code': '000003.SZ', 'score': 30000, 'price': 12.0,
        'trigger_type': 'none', 'trigger_confidence': 0.0,
        'ignition_prob': 19.9,  # 低于20%门槛
        'mfe': 1.5, 'sustain_ratio': 2.0,
    })
    for i in range(1, 12):
        top_targets_b_fail.append({
            'code': f'602{str(i).zfill(3)}.SH', 'score': 5000 + i*100, 'price': 12.0 + i,
            'trigger_type': 'none', 'trigger_confidence': 0.0,
            'ignition_prob': 10.0,
            'mfe': 0.8, 'sustain_ratio': 1.2,
        })
    
    result_b_fail = brain_b_fail.on_new_frame(
        top_targets=top_targets_b_fail,
        current_time=TEST_TIME,
        held_stock_current_price=0.0
    )
    assert result_b_fail.get('action') != 'BUY', \
        f"通道B边界验证: ignition_prob=19.9%时不应触发BUY，实际={result_b_fail.get('action')}"
    print(f"  → ✅ 通道B边界验证: ignition_prob=19.9%不触发BUY（正确），action={result_b_fail.get('action')}")

    print(f"  → ✅ 通道B入场正确触发: BUY {result_b.get('stock_code')}")

check("TradeDecisionBrain on_new_frame签名+返回值", test_decision_brain)

# ── TEST 4: UniversalTracker on_frame + get_full_report
def test_universal_tracker():
    from logic.execution.universal_tracker import UniversalTracker
    tracker = UniversalTracker()
    
    targets = [
        {'code': '000001.SZ', 'score': 200, 'price': 10.0,
         'trigger_type': 'none', 'trigger_confidence': 0.0,
         'ignition_prob': 50.0, 'mfe': 1.2, 'sustain_ratio': 1.5},  # 百分比形式
    ]
    
    # 无成交帧
    tracker.on_frame(top_targets=targets, current_time=TEST_TIME,
                     executed_trade=None, decision_context=None)
    
    # 有买入成交帧
    trade = {'action': 'BUY', 'stock_code': '000001.SZ',
             'price': 10.0, 'reason': '测试买入'}
    tracker.on_frame(top_targets=targets, current_time=TEST_TIME,
                     executed_trade=trade, decision_context=None)
    
    # 价格更新
    if hasattr(tracker, 'on_price_update'):
        tracker.on_price_update('000001.SZ', 10.5, TEST_TIME)
        print("  → on_price_update 存在且可调用")
    
    # 报告 - 【接口确认】keys与预期不同
    report = tracker.get_full_report()
    assert isinstance(report, dict), "get_full_report应返回dict"
    print(f"  → report keys={list(report.keys())}")
    
    # 【Bug-New-5修复】关键key验证 - 改为硬验证
    # expected_keys与实际返回对齐
    expected_keys = ['session_id', 'generated_at', 'summary',
                     'schema_b_analysis', 'dual_engine_comparison',
                     'decision_log_summary', 'all_stocks', 'scan_validation']
    missing_keys = [k for k in expected_keys if k not in report]
    assert not missing_keys, f"get_full_report缺少key: {missing_keys}"
    print(f"  → ✅ 所有必需keys存在: {expected_keys}")

check("UniversalTracker on_frame+get_full_report", test_universal_tracker)

# ── TEST 5: TriggerValidator 签名+返回值
def test_trigger_validator():
    from research_lab.trigger_validator import TriggerValidator
    tv = TriggerValidator()
    
    # 历史不足（<3条），应返回 None 不报错
    sig_none = tv.check_all_triggers(
        stock_code='000001.SZ',
        current_price=10.0, prev_close=9.8, vwap=9.9,
        volume_ratio=1.5, current_mfe=1.2,
        recent_mfe_list=[1.0], price_history=[9.9],
        recent_volume_ratios=[1.2], current_slope=0.01,
        timestamp=TEST_TIME
    )
    print(f"  → 历史不足时返回: {sig_none}")
    
    # 足够历史
    sig = tv.check_all_triggers(
        stock_code='000001.SZ',
        current_price=10.0, prev_close=9.8, vwap=9.9,
        volume_ratio=2.0, current_mfe=1.8,
        recent_mfe_list=[1.2, 1.5, 1.8],
        price_history=[9.7, 9.8, 10.0],
        recent_volume_ratios=[1.5, 1.8, 2.0],
        current_slope=0.02,
        timestamp=TEST_TIME
    )
    print(f"  → 足够历史时返回: {sig}")
    if sig is not None:
        assert hasattr(sig, 'trigger_type'), "signal应有trigger_type属性"
        assert hasattr(sig, 'confidence'), "signal应有confidence属性"
        print(f"  → trigger_type={sig.trigger_type}, confidence={sig.confidence}")
    
    # generate_report
    rpt = tv.generate_report()
    assert isinstance(rpt, dict), "generate_report应返回dict"
    print(f"  → generate_report keys={list(rpt.keys())}")

check("TriggerValidator check_all_triggers+generate_report", test_trigger_validator)

# ── 汇总
print("\n" + "="*60)
print("冒烟测试结果汇总")
print("="*60)
for status, name in results:
    print(f"  {status}  {name}")
total = len(results)
passed = sum(1 for s, _ in results if s == PASS)
print(f"\n通过: {passed}/{total}")
if passed < total:
    print("⛔ 存在失败项，禁止进入 PHASE 3！先修复上述报错。")
else:
    print("✅ 全部通过，可进入 PHASE 3 集成测试。")
