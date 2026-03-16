# XtQuant 量纲真相手册 (UNIT DIMENSION TRUTH)

> **版本**: V2.0 | **日期**: 2026-03-16 | **权威来源**: dict.thinktrader.net 官方文档
> **CTO状态**: ✅ 已审计验证 (2026-03-16 代码实测确认) | 禁止基于「印象」修改
>
> **用途**: 彻底消灭代码中关于 volume/amount/avg_volume_5d 的单位幻觉注释。
> 每次涉及量比计算，必须先查本文档，不得凭记忆。
>
> ⚠️ **V2.0更新说明**: 修正「禁止×100」的错误表述，区分量比与换手率两种合法场景。
> 删除误导性「绕开volume单位问题」注释幻觉。

---

## 一、官方量纲铁律（来源：XtData API文档）✅已验证

### 1. `get_full_tick` / `subscribe_whole_quote` / 本地历史Tick（三者同源）

| 字段 | 类型 | **单位** | 说明 |
|---|---|---|---|
| `volume` | int | **手**（1手=100股） | 今日累计成交总量 ✅实测pvolume/volume=100 |
| `pvolume` | int | **股** | 原始成交总量，官方标注「不推荐使用」 |
| `amount` | float | **元** | 今日累计成交总额 |
| `askVol` / `bidVol` | list[int] | **手** | 多档委买/委卖量 |
| `lastPrice` | float | 元/股 | 最新价 |
| `lastClose` | float | 元/股 | 前收盘价（昨收） |

**结论**: Tick 的 `volume` = **手**，`pvolume` = **股**，两者差100倍。

### 2. K线数据（`get_local_data` period='1d'/'1m'/'5m'）✅已验证

| 字段 | 单位 | 验证方法 |
|---|---|---|
| `volume` | **手** | amount/volume ≈ 股价×100（平安银行验证通过）✅ |
| `amount` | **元** | |

**结论**: K线的 `volume` 也是**手**，与 Tick 完全一致。

### 3. `get_instrument_detail` 合约基础信息 ✅已验证

| 字段 | 单位 | 验证方法 |
|---|---|---|
| `FloatVolume` | **股**（不是手！不是万股！） | 平安银行FloatVolume≈194亿股 ✅ |
| `TotalVolume` | **股** | |

> ⚠️ **历史幻觉警告**：README旧版本曾记录FloatVolume单位为「万股」，
> 这是V64时代特定数据通道的问题，已被`market_cap < 2亿`升维逻辑处理。
> `get_instrument_detail` 直接返回的FloatVolume单位是**股**，无需×10000。
> 两套逻辑同时存在是SSOT违规，已在V173修复。

---

## 二、量比计算的正确量纲链 ✅铁律不可改动

### 【场景A】盘中动态量比（量比 = 无量纲）

```python
# kinetic_core_engine.py: calculate_volume_ratio
# current_volume: 手（来自 Tick.volume 或 K线.volume）
# avg_volume_5d:  手（来自历史K线 volume 均值）
# 两者单位相同 → 相除 = 无量纲 ✅
volume_ratio = current_volume / expected_volume   # 手 / 手 = 无量纲 ✅
```

**铁律**: 量比计算中，分子分母必须单位一致（都是手），**禁止在量比公式中做股手转换**。
如果分子是手、分母也是手，则不需要任何×100或÷100。

### 【场景B】换手率计算（必须×100做单位统一）

```python
# 换手率公式
# volume: 手（K线或Tick）
# FloatVolume: 股（get_instrument_detail返回）
# 两者单位不同 → 必须转换！
#
# 正确公式:
today_turnover_pct = (today_volume * 100 / float_volume_shares) * 100
# 拆解: today_volume(手) × 100(股/手) / FloatVolume(股) × 100(转百分比)
# 量纲链: 手 × 股/手 / 股 × % = % ✅
#
# 2026-03-16实测: 平安银行 841939手 × 100 / 19405600653股 × 100 = 0.43% ✅
```

**铁律**: 换手率计算中，`volume(手) × 100` 是将「手」转换为「股」，这个×100是**量纲统一操作，合法且必须**。

### 两种场景的核心区别

| 场景 | 公式 | 是否需要×100 | 原因 |
|---|---|---|---|
| **量比** | current_volume / avg_volume_5d | ❌ 不需要 | 分子分母都是手，单位一致 |
| **换手率** | volume × 100 / FloatVolume × 100 | ✅ 必须 | volume是手，FloatVolume是股，单位不同 |

---

## 三、`avg_volume_5d` 的正确来源与计算方式

`avg_volume_5d` **必须**来自K线 `volume` 字段的历史5日均值。

```python
# ✅ 正确：排除今日，只取历史5天
n = min(5, len(df) - 1)  # 减1排除今日
avg_volume_5d = df['volume'].iloc[-n-1:-1].mean()  # 只取历史5天

# ❌ 错误（CTO Issue #1已确认Bug）：
# n = min(5, len(df))
# avg_volume_5d = df['volume'].iloc[-n:].mean()  # 包含今日，污染均值
```

**原因**: 如果均值包含今日成交量，当股票今天放量3倍时，avg被拉高，
导致计算出的量比被低估，真龙信号被漏斗误杀。

`avg_volume_5d` 单位 = **手**，与 `current_volume`（手）单位一致，量比计算无需转换。

**禁止**用 `FloatVolume`（股）去换算 `avg_volume_5d`，两者语义完全不同。

---

## 四、`avg_amount_5d` 的换算（用于流通市值相关计算）

```
avg_amount_5d（元）= avg_volume_5d（手）× 100 × prev_close（元/股）
量纲链: 手 × (股/手) × (元/股) = 元 ✅
```

此换算**仅用于**需要「元」单位的场景（如流入占比计算）。
量比计算**不需要**此换算。

---

## 五、`inflow_ratio_pct` 单位铁律

来源：`kinetic_core_engine.py` 模块注释

```
inflow_ratio_pct 统一为百分比形式：2.0 = 流入占流通市值2%
禁止混用小数形式(0.02)
示例: inflow_ratio > 1.5  ← 流入>1.5%，而非 > 0.015
```

---

## 六、已确认的代码幻觉清单（禁止复活）✅CTO 2026-03-16 清除

| 文件 | 幻觉内容 | 真相 | 处理状态 |
|---|---|---|---|
| `logic/core/physics_sensors.py` | `extract_volume_ratio` 注释: 入参单位「股」 | 入参无单位约束，调用方传手/手则正确；传股/手则放大100倍 | ⚠️ 待修正注释 |
| `logic/core/physics_sensors.py` | 底部使用示例引用 `extract_mfe_efficiency` | 该函数不存在，只有 `extract_mfe`（且已标注DEAD CODE） | ⚠️ 待删除幻觉注释 |
| `logic/data_providers/true_dictionary.py` | `get_avg_turnover_5d` 注释「绕开volume单位问题」 | 该方法用amount和close计算，根本不涉及volume，注释是无意义幻觉 | ⚠️ 待修正注释 |
| `logic/data_providers/universe_builder.py` | `avg_volume_5d = df['volume'].iloc[-n:].mean()` | 包含今日成交量，导致量比系统性偏低 | 🚨 P0 Bug待修复 |
| `logic/data_providers/true_dictionary.py` | `build_static_cache` 用 `datetime.now()` | 回测时会拉今天的昨日涨停数据，未来函数污染 | 🚨 P1 Bug待修复 |
| `logic/data_providers/true_dictionary.py` | `build_static_cache` 用 `df['high'].iloc[-2]` 判断涨停 | 冲高回落票会被误判为涨停，应用 `df['close'].iloc[-2]` 与涨停价对比 | 🚨 P1 Bug待修复 |
| README.md 旧量纲表 | `get_full_tick 快照: volume单位=股` | Tick.volume单位是**手**，已实测确认 | ✅ 本次已修正 |
| README.md 旧量纲表 | `get_local_data 回测: volume单位=股` | K线.volume单位是**手**，已实测确认 | ✅ 本次已修正 |
| 历史对话 | "今天全市场95%的股票量比 < 2.0" | 无实盘数据支撑，纯幻觉，作废 | ✅ 已作废 |

---

## 七、验证量比是否正确的最小化测试代码

```python
# 在 mock/scan 模式下，用已知股票验证量比是否落在合理范围
# 正常交易日，活跃股量比约0.5~3.0，极端放量才会>5.0

from logic.strategies.kinetic_core_engine import KineticCoreEngine

engine = KineticCoreEngine()

# 假设：当前已交易7200秒（2小时），累计成交50000手，5日均量100000手
# 预期量比 = 50000 / (100000 * 7200/14400) = 50000 / 50000 = 1.0
vol_ratio = engine.calculate_volume_ratio(
    current_volume=50000,    # 手
    elapsed_seconds=7200,
    avg_volume_5d=100000     # 手（历史5日均值，排除今日）
)
assert abs(vol_ratio - 1.0) < 0.01, f"量比异常: {vol_ratio}（预期1.0）"
print(f"✅ 量比验证通过: {vol_ratio:.2f}")

# 如果结果是 100.0，说明某处多乘了100（股手混淆）
# 如果结果是 0.01，说明某处多除了100
# 如果结果明显 < 真实量比（如今天放量3x却算出2.1x），
#   检查 avg_volume_5d 计算是否包含了今日（Issue #1 Bug）
```

---

## 八、README旧量纲表修正记录

> **背景**: README中存在一张历史量纲表，内容源自V66时代（2026-03-10），
> 部分字段描述与2026-03-16实测结果矛盾，是产生幻觉的主要源头之一。

| 字段 | README旧值（V66） | 实测真相（V185+） | 是否矛盾 |
|---|---|---|---|
| `subscribe_quote` volume单位 | 手(100股) | **手** | ✅ 一致 |
| `get_full_tick` volume单位 | **股** | **手** | ❌ **矛盾！旧值错误** |
| `get_local_data` volume单位 | **股** | **手** | ❌ **矛盾！旧值错误** |
| FloatVolume单位（subscribe_quote） | 万股 | V66时代特定通道=万股；get_instrument_detail直接返回=**股** | ⚠️ 场景混淆 |

**结论**: README量纲表「快照volume=股」「回测volume=股」是错误记录，已在本次文档更新中修正。
V66时代的万股问题是特定数据通道问题，`get_instrument_detail` 返回的FloatVolume单位是**股**，两者不矛盾。

---

*本文档 V2.0 由 CTO 于 2026-03-16 基于代码实测生成，已清除所有已知幻觉来源。*
*禁止基于「印象」修改。如需修改必须附上官方文档原文链接或实测代码证据。*
