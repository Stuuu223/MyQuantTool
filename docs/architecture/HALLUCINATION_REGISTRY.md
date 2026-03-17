# 幻觉注册表 (HALLUCINATION REGISTRY)

> **版本**: V1.0 | **日期**: 2026-03-16 | **维护人**: CTO
>
> **用途**: 集中登记所有已知的、会导致AI或人类产生错误认知的「致幻剂」代码/注释/文档。
> 每次AI代码生成前，必须先检查本表，确认不复活任何已登记的幻觉。
>
> ⚠️ **这不是Bug表。这是「产生错误信念的信息源」登记表。**
> Bug是行为错误；幻觉是认知污染，比Bug更危险，因为它会传播并复制自身。

---

## 幻觉等级定义

| 等级 | 含义 | 例子 |
|---|---|---|
| 🔴 **L3-致命** | 直接导致错误代码被生成，且难以自检 | 注释说单位是「股」但实际是「手」 |
| 🟠 **L2-误导** | 导致理解偏差，可能引发间接Bug | 注释说「绕开了XX问题」但实际没有 |
| 🟡 **L1-混淆** | 表述含糊，增加认知负担 | 「禁止×100」但某些场景合法需要×100 |

---

## 注册表（按文件分类）

### `logic/core/physics_sensors.py`

| ID | 等级 | 位置 | 幻觉内容 | 真相 | 状态 |
|---|---|---|---|---|---|
| H-001 | 🔴 L3 | `extract_volume_ratio` 函数注释 | 注释写「current_volume: 今日成交量（股）」「avg_volume_5d: 5日平均成交量（股）」 | 函数本体是纯除法，无任何单位转换。入参是手则输出手/手；入参是股则输出股/股。注释是幻觉。 | ⚠️ 待修正 |
| H-002 | 🟠 L2 | 文件底部使用示例注释 | 引用了 `extract_mfe_efficiency` | 该函数不存在，只有 `extract_mfe`（且已标DEAD CODE） | ⚠️ 待删除 |

### `logic/data_providers/true_dictionary.py`

| ID | 等级 | 位置 | 幻觉内容 | 真相 | 状态 |
|---|---|---|---|---|---|
| H-003 | 🟠 L2 | `get_avg_turnover_5d` 函数注释 | 「优点：绕开volume单位问题，避免历史流通股本漂移」 | 该方法用 `amount(元) / (FloatVolume(股) × close(元/股))` 计算，根本不用volume，注释是无中生有的幻觉。 | ⚠️ 待修正 |
| H-004 | 🔴 L3 | `build_static_cache` 函数体 L801-802 | `today = datetime.now().strftime('%Y%m%d')` 硬编码当前时间 | 回测模式下会用今天的日期拉「昨日涨停」数据，未来函数污染历史回测 | 🚨 P1 待修复 |
| H-005 | 🔴 L3 | `build_static_cache` 函数体 | `prev_high = float(df['high'].iloc[-2])` 用最高价判断涨停 | 冲高回落票（盘中摸涨停但未收于涨停）会被误判为昨日涨停。应用 `df['close'].iloc[-2]` 与 `up_stop_price` 对比 | 🚨 P1 待修复 |

### `logic/data_providers/universe_builder.py`

| ID | 等级 | 位置 | 幻觉内容 | 真相 | 状态 |
|---|---|---|---|---|---|
| H-006 | 🔴 L3 | `_funnel2_daily_kline` 约L261-270 | `avg_volume_5d = df['volume'].iloc[-n:].mean()` 看起来正确 | `iloc[-n:]` 最后一行是今日，今日放量3倍会污染均值，导致量比被低估30%，真龙信号被误杀 | 🚨 P0 待修复 |
| H-007 | 🟠 L2 | `_funnel2_daily_kline` 约L261, L372 | `volume_ratio` 被计算两次，变量名相同 | 修复H-006后两次计算的avg来源必须一致，否则self._volume_ratios与漏斗判断用的量比不同，产生「存入分布统计」vs「实际过滤」的值对不上问题 | 🚨 P0 待修复（与H-006同批修复）|

### `docs/architecture/UNIT_DIMENSION_TRUTH.md`（V1.0，已升级V2.0）

| ID | 等级 | 位置 | 幻觉内容 | 真相 | 状态 |
|---|---|---|---|---|---|
| H-008 | 🟡 L1 | 第二章量比铁律 | 「**禁止**在分子或分母上乘以100做股手转换，否则量比被放大或缩小100倍」 | 表述过于绝对。量比场景确实禁止；但换手率场景 `volume(手) × 100 / FloatVolume(股)` 的×100是合法量纲转换，不是错误。 | ✅ V2.0已修正 |

### `README.md`（量纲铁律表）

| ID | 等级 | 位置 | 幻觉内容 | 真相 | 状态 |
|---|---|---|---|---|---|
| H-009 | 🔴 L3 | 量纲铁律表第二行 | `get_full_tick 快照: volume单位=股` | Tick.volume单位是**手**，2026-03-16实测pvolume/volume=100确认 | ✅ 本次已修正 |
| H-010 | 🔴 L3 | 量纲铁律表第三行 | `get_local_data 回测: volume单位=股` | K线.volume单位是**手**，2026-03-16实测amount/volume≈股价×100确认 | ✅ 本次已修正 |

### `tools/mock_live_runner.py`

| ID | 等级 | 位置 | 幻觉内容 | 真相 | 状态 |
|---|---|---|---|---|---|
| H-011 | 🔴 L3 | L258 附近 | `FloatVolume` 误以为单位是万股，代码写 `fv * 10000` 升维 | `get_instrument_detail` 返回的 `FloatVolume` 单位是**股**，无需×10000。×10000导致流通盘显示12642亿股（物理荒谬），inflow_ratio接近0，所有票得0分 | ✅ V173已修复 |
| H-012 | 🟠 L2 | 多处 | 用 `python -c` 裸调 `MockLiveRunner()` 不传 `stock_list` | CLI入口已写好 `UniverseBuilder` 路径，应使用 `python tools/mock_live_runner.py --date YYYYMMDD`，否则stock_list=[]导致无Tick数据 | ⚠️ 执行规范问题 |

---

## AI代码生成前强制自检清单

在生成任何涉及以下关键词的代码前，必须逐条检查：

```
[ ] volume / avg_volume_5d → 单位是手，量比计算不需要×100
[ ] FloatVolume → 单位是股，换手率计算需要 volume×100/FloatVolume
[ ] 涨停判断 → 用close与up_stop_price对比，不用high
[ ] avg_volume_5d计算 → 用 iloc[-n-1:-1]，排除今日
[ ] 回测函数 → 必须有target_date参数，禁止datetime.now()
[ ] build_static_cache调用 → 必须传入target_date
[ ] extract_mfe_efficiency → 该函数不存在，使用前确认
[ ] get_avg_turnover_5d注释 → 用amount/FloatVolume/close计算，与volume无关
```

---

## 幻觉溯源分析（CTO备注）

本项目中的幻觉主要来自以下三类根因：

**根因1：历史量纲混乱的遗留痕迹**

QMT在不同数据通道（subscribe_quote / get_full_tick / get_local_data）的volume字段单位历史上存在差异。V185之前代码在不同通道间来回修正，形成了「volume=股」的错误记忆，被固化进README和注释。实测证明三个通道volume单位均为**手**。

**根因2：注释超出代码描述的能力边界**

`get_avg_turnover_5d` 的「绕开volume单位问题」注释，把一个碰巧不用volume的实现，包装成了一个「刻意设计的绕过方案」，给读者注入了不存在的背景知识。这种「注释注水」是产生幻觉的高风险模式。

**根因3：修复时机错误导致的中间态Bug**

Issue #1（avg_volume_5d包含今日）是典型的「看起来正确的错误代码」。`iloc[-n:]` 在没有今日数据时完全正确，但在有今日数据时静默引入偏差。这类幻觉最危险，因为单元测试难以覆盖。

---

*本文档由 CTO 于 2026-03-16 创建。每次发现新幻觉，必须立即登记，不得口头传达。*
