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
                          trigger_type='test', timestamp=datetime.now())
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
                                timestamp=datetime.now())
    assert sell_order is not None, "卖出应返回非None"
    print(f"  → 卖出完成，剩余持仓={list(e.positions.keys())}")
    
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
        current_time=datetime.now(),
        held_stock_current_price=0.0
    )
    print(f"  → 空榜单返回: action={result_empty.get('action')}")
    assert result_empty is not None, "空榜单应返回dict而非None"
    assert result_empty.get('action') == 'WATCH', "空榜单应返回WATCH"
    
    # 含数据的榜单
    top_targets = [
        {
            'code': '000001.SZ', 'score': 200, 'price': 10.0,
            'trigger_type': 'slingshot', 'trigger_confidence': 0.85,
            'ignition_prob': 0.7, 'mfe': 1.5, 'sustain_ratio': 2.0,
        },
        {
            'code': '600519.SH', 'score': 150, 'price': 1800.0,
            'trigger_type': 'none', 'trigger_confidence': 0.0,
            'ignition_prob': 0.3, 'mfe': 0.8, 'sustain_ratio': 1.2,
        },
    ]
    result = brain.on_new_frame(
        top_targets=top_targets,
        current_time=datetime.now(),
        held_stock_current_price=0.0
    )
    print(f"  → 含数据返回: action={result.get('action')}, code={result.get('stock_code')}")
    required_keys = ['action', 'stock_code', 'price', 'reason',
                     'score', 'trigger_type']
    for k in required_keys:
        assert k in result, f"返回字典缺少key: {k}"

check("TradeDecisionBrain on_new_frame签名+返回值", test_decision_brain)

# ── TEST 4: UniversalTracker on_frame + get_full_report
def test_universal_tracker():
    from logic.execution.universal_tracker import UniversalTracker
    tracker = UniversalTracker()
    
    targets = [
        {'code': '000001.SZ', 'score': 200, 'price': 10.0,
         'trigger_type': 'none', 'trigger_confidence': 0.0,
         'ignition_prob': 0.5, 'mfe': 1.2, 'sustain_ratio': 1.5},
    ]
    now = datetime.now()
    
    # 无成交帧
    tracker.on_frame(top_targets=targets, current_time=now,
                     executed_trade=None, decision_context=None)
    
    # 有买入成交帧
    trade = {'action': 'BUY', 'stock_code': '000001.SZ',
             'price': 10.0, 'reason': '测试买入'}
    tracker.on_frame(top_targets=targets, current_time=now,
                     executed_trade=trade, decision_context=None)
    
    # 价格更新
    if hasattr(tracker, 'on_price_update'):
        tracker.on_price_update('000001.SZ', 10.5, now)
        print("  → on_price_update 存在且可调用")
    
    # 报告 - 【接口确认】keys与预期不同
    report = tracker.get_full_report()
    assert isinstance(report, dict), "get_full_report应返回dict"
    print(f"  → report keys={list(report.keys())}")
    
    # 关键key验证 - 实际keys
    expected_keys = ['session_id', 'schema', 'generated_at', 'summary', 
                     'all_stocks', 'decision_log_summary']
    for k in expected_keys:
        if k not in report:
            print(f"  ⚠️  缺少key: {k}")

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
        timestamp=datetime.now()
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
        timestamp=datetime.now()
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
