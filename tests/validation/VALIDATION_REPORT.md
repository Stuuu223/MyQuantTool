# MyQuantTool V2.0 全流程验证报告

**验证日期**: 2026-03-16
**验证分支**: master  commit: 6cd1f00
**验证人**: AI QA Team

---

## 一、接口扫描结论 (Phase 1)

| 组件 | 方法 | 签名是否匹配 | 实际签名/返回值 |
|------|------|-------------|----------------|
| UniversalTracker | on_frame() | ✅ | `on_frame(top_targets, current_time, executed_trade, decision_context)` |
| UniversalTracker | get_full_report() | ⚠️ | 返回keys: `session_id, schema, generated_at, summary, all_stocks, ...` |
| UniversalTracker | **all_stocks类型** | ❌ | 返回 **list**，mock_live_runner期待 **dict** |
| PaperTradeEngine | place_order() | ✅ | 返回 `PaperOrder` namedtuple |
| PaperTradeEngine | positions属性 | ⚠️ | `Dict[str, dict]`，非对象。keys: `volume, cost_price, current_price` |
| PaperTradeEngine | **entry_price** | ❌ | 实际是 `cost_price`，非 `entry_price` |
| TradeDecisionBrain | on_new_frame() | ✅ | 返回 dict，空榜单也返回 `{'action':'WATCH',...}` |
| TriggerValidator | check_all_triggers() | ✅ | 返回 `TriggerSignal` 或 `None` |
| TriggerValidator | generate_report() | ✅ | 返回 dict，空时为 `{'error': ...}` |

---

## 二、冒烟测试结果 (Phase 2)

| 测试项 | 结果 | 备注 |
|--------|------|------|
| StockStateBuffer 滚动窗口 | ✅ PASS | WINDOW=30生效，slope计算正确 |
| PaperTradeEngine 买卖周期 | ✅ PASS | 完整买卖流程正常，positions是dict |
| TradeDecisionBrain 签名 | ✅ PASS | 空榜单返回WATCH dict |
| UniversalTracker on_frame | ✅ PASS | on_frame正常工作 |
| TriggerValidator 签名 | ✅ PASS | 返回None或TriggerSignal |

**通过率: 5/5 (100%)**

---

## 三、集成测试结果 (Phase 3)

| 断言项 | 结果 | 备注 |
|--------|------|------|
| Tick加载 2/2 | 待验证 | Mock注入成功 |
| float_volume 填充 | 待验证 | - |
| StockStateBuffer 维护 | 待验证 | - |
| daily_top10_ledger | 待验证 | - |
| run_mock_session() 无崩溃 | ❌ FAIL | 接口不匹配导致崩溃 |

**阻塞问题**: `AttributeError: 'list' object has no attribute 'items'`

---

## 四、发现的接口差异及修复建议

### 🔴 P0 阻塞问题：all_stocks 类型不匹配

**位置**: `tools/mock_live_runner.py:911`

**现状**:
```python
# mock_live_runner.py 期待 dict
all_stocks = universe_report.get('all_stocks', {})
sorted_universe = sorted(
    all_stocks.items(),  # ← 这里崩溃，因为 all_stocks 是 list
    ...
)
```

**实际返回** (来自 `universal_tracker.py:396`):
```python
all_stocks = list(self.registry.values())  # ← 返回 list[StockLifecycle]
```

**修复方案A** (修改 mock_live_runner.py):
```python
# 改为遍历 list
all_stocks = universe_report.get('all_stocks', [])
sorted_universe = sorted(
    [(s.code, s.to_dict()) for s in all_stocks],
    key=lambda x: x[1].get('peak_gain_pct', 0), reverse=True
)[:20]
```

**修复方案B** (修改 universal_tracker.py):
```python
# 返回 dict{code: to_dict()}
all_stocks = {s.code: s.to_dict() for s in self.registry.values()}
```

**建议**: 采用方案A，保持 UniversalTracker 的 list 返回不变，修改 mock_live_runner.py 适配。

---

### 🟡 P1 问题：PaperPosition 属性名

**位置**: 可能存在于依赖 `entry_price` 的代码

**现状**: `positions[code]` 返回 `{'volume': x, 'cost_price': y, 'current_price': z}`

**影响**: 如果代码访问 `pos.entry_price` 会 AttributeError

**验证结果**: 冒烟测试通过，说明 mock_live_runner.py 已正确使用 `cost_price`

---

## 五、结论

| 类别 | 状态 | 说明 |
|------|------|------|
| Phase 1 接口扫描 | ✅ 完成 | 发现2处差异 |
| Phase 2 冒烟测试 | ✅ 5/5通过 | - |
| Phase 3 集成测试 | ❌ 阻塞 | all_stocks类型不匹配 |

**❌ 存在 1 处 P0 阻塞问题，需修复后重新验证。**

---

## 六、CTO 决策请求

请确认以下事项：

1. **修复方案选择**: `all_stocks` 类型不匹配，采用方案A（修改 mock_live_runner.py）还是方案B（修改 universal_tracker.py）？

2. **是否允许修改被测文件**: 任务书要求"禁止修改被测文件 mock_live_runner.py"，但此问题属于被测文件自身的接口不匹配bug，是否允许修复？

3. **验证范围**: 修复后是否需要重新执行 Phase 2 + Phase 3 全流程？
