# XtQuant 量纲真相手册 (UNIT DIMENSION TRUTH)

> **版本**: V1.0 | **日期**: 2026-03-16 | **权威来源**: dict.thinktrader.net 官方文档
>
> **用途**: 彻底消灭代码中关于 volume/amount/avg_volume_5d 的单位幻觉注释。
> 每次涉及量比计算，必须先查本文档，不得凭记忆。

---

## 一、官方量纲铁律（来源：XtData API文档）

### 1. `get_full_tick` / `subscribe_whole_quote` / 本地历史Tick（三者同源）

| 字段 | 类型 | **单位** | 说明 |
|---|---|---|---|
| `volume` | int | **手**（1手=100股） | 今日累计成交总量 |
| `pvolume` | int | **股** | 原始成交总量，官方标注「不推荐使用」 |
| `amount` | float | **元** | 今日累计成交总额 |
| `askVol` / `bidVol` | list[int] | **手** | 多档委买/委卖量 |
| `lastPrice` | float | 元/股 | 最新价 |
| `lastClose` | float | 元/股 | 前收盘价（昨收） |

**结论**: Tick 的 `volume` = **手**，`pvolume` = **股**，两者差100倍。

### 2. K线数据（`period='1d'/'1m'/'5m'`）

| 字段 | 单位 |
|---|---|
| `volume` | **手** |
| `amount` | **元** |

**结论**: K线的 `volume` 也是**手**，与 Tick 完全一致。

### 3. `get_instrument_detail` 合约基础信息

| 字段 | 单位 |
|---|---|
| `FloatVolume` | **股**（不是手！） |
| `TotalVolume` | **股** |

---

## 二、量比计算的正确量纲链

### 盘中动态量比（`KineticCoreEngine.calculate_volume_ratio`）

```python
# 函数签名（kinetic_core_engine.py）
def calculate_volume_ratio(
    self,
    current_volume: float,   # 单位: 手（来自 Tick.volume）
    elapsed_seconds: int,
    avg_volume_5d: float     # 单位: 手（来自历史K线 volume 均值）
) -> float:
    time_progress = elapsed_seconds / 14400
    expected_volume = avg_volume_5d * time_progress
    volume_ratio = current_volume / expected_volume   # 手 / 手 = 无量纲 ✅
```

**铁律**: `current_volume`（手）÷ `avg_volume_5d`（手）= 量比（无量纲）。
**禁止**在分子或分母上乘以100做股手转换，否则量比被放大或缩小100倍。

### `physics_sensors.extract_volume_ratio` 函数（注意陷阱！）

```python
# physics_sensors.py 函数文档注释写的是：
# Args:
#     current_volume: 今日成交量（股）   ← ⚠️ 注释错误！
#     avg_volume_5d: 5日平均成交量（股）  ← ⚠️ 注释错误！
```

**事实**: 该函数本体是纯除法 `current_volume / avg_volume_5d`，
**没有任何单位转换逻辑**。入参是什么单位，输出就基于什么单位。
注释里写「股」是历史幻觉注释，**已被此文档作废**。

实际调用时：
- 如果传入的是手/手 → 量比正确 ✅
- 如果传入的是股/手 → 量比被放大100倍 ❌

---

## 三、`avg_volume_5d` 的正确来源

`avg_volume_5d` **必须**来自K线 `volume` 字段的5日均值。

K线 `volume` 单位 = **手**，因此 `avg_volume_5d` 单位 = **手**。

**禁止**用 `FloatVolume`（股）去换算 `avg_volume_5d`，两者语义完全不同。

---

## 四、`avg_amount_5d` 的换算（用于流通市值相关计算）

```
avg_amount_5d（元）= avg_volume_5d（手）× 100 × prev_close（元/股）
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

## 六、已确认的错误注释清单（禁止复活）

| 文件 | 错误注释内容 | 真相 |
|---|---|---|
| `logic/core/physics_sensors.py` | `extract_volume_ratio` 注释: 入参单位「股」 | 入参无单位约束，调用方传手，结果就是手/手；传股，就是股/股。注释是幻觉。 |
| 历史对话 | "今天3月16日全市场95%的股票量比 < 2.0" | 无实盘数据支撑，纯幻觉，作废。 |
| 历史对话 | "漏斗2崩溃根因是量比门槛" | 未经代码验证的经验判断。真正根因需检查调用 `calculate_volume_ratio` 时传入的参数单位是否一致。 |

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
    avg_volume_5d=100000     # 手
)
assert abs(vol_ratio - 1.0) < 0.01, f"量比异常: {vol_ratio}（预期1.0）"
print(f"✅ 量比验证通过: {vol_ratio:.2f}")

# 如果结果是 100.0，说明某处多乘了100（股手混淆）
# 如果结果是 0.01，说明某处多除了100
```

---

*本文档由 CTO 于 2026-03-16 基于官方文档生成，禁止基于"印象"修改。如需修改必须附上官方文档原文链接。*
