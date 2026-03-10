# V66 资金物理学宪法

> **AI 指令**：在修改打分逻辑前，必须强制阅读本文档，否则禁止提交！

---

## 🚨 核心逻辑防线 (CRITICAL LOGIC GUARDS)

### 1. 万股量纲自动升维法则 (V66)

**问题**：QMT/通达信返回的 `float_volume`（流通股本）单位混乱，可能是"股"或"万股"。

**铁律**：
```python
# A股最小流通市值不可能 < 2亿人民币
# 如果 float_volume * price < 2亿，100% 是单位错误（万股）
if float_market_cap > 0 and float_market_cap < 200000000:
    float_market_cap = float_market_cap * 10000.0  # 强制升维至真实人民币元
```

**物理依据**：A股目前最小流通市值约3-5亿。如果算出来的市值只有十几万或几百万，100%是单位错误。

---

### 2. 引力阻尼算法 (V65)

**问题**：微盘股历史成交额极低，稍微放量就产生虚假高倍数 Sustain。

**铁律**：
```python
# 引力阻尼器：市值越大，sustain 含金量越高
gravity_damper = 1.0 + math.log10(float_mc_yi / 50.0) * 0.5
# 20亿微盘: 0.7x 衰减 | 50亿基准: 1.0x | 500亿大卡车: 1.8x 加成
sustain_ratio = raw_sustain * gravity_damper
```

**物理真理**：推卡车的1.6倍，在物理做功上绝对大于推泡沫的10倍！

---

### 3. MFE 做功效率 (V64)

**公式**：
```python
MFE = price_range_pct / (inflow_ratio_pct / 100.0)
# price_range_pct = 振幅 / 昨收
# inflow_ratio_pct = 净流入 / 流通市值 * 100
```

**物理意义**：
- `MFE > 2.0`：真空无阻力，资金推力效率极高
- `MFE < 1.0`：老黄牛，堆钱推不动

**制衡规则**：
```python
if mfe < 1.0:
    mfe_factor = max(0.5, mfe)  # 下限保护，最惨打5折
    effective_sustain = sustain_ratio * mfe_factor
```

---

### 4. 时空切片绝对对齐 (V63)

**问题**：妖股80%成交额集中在早盘30分钟，全天均摊会稀释动能。

**铁律**：
```python
# 禁止使用 flow_15min = current_amount / 16.0（均摊算法）
# 必须调用真实时空切片获取早盘数据
slice_flows = self.calculate_time_slice_flows(stock_code, target_date)
flow_5min = slice_flows.get('flow_5min', 0.0)
flow_15min = slice_flows.get('flow_15min', 0.0)
```

---

### 5. Scan/Live 双层物理同源 (V61/V62)

**问题**：Scan模式走静态快照，Live模式走动态Tick，两条路线导致结果不一致。

**铁律**：
- 引擎只接收5个纯物理常量：`price/amount/high/low/pre_close` + 时间进度 `minutes_passed`
- 不接触原始格式（C++对象/字典/DataFrame）
- 数据清洗必须在入口处完成，引擎内部严禁猜测单位

---

## 📐 数据源量纲铁律

| 数据源 | volume单位 | amount单位 | float_volume单位 | 入口清洗 |
|--------|------------|------------|------------------|----------|
| `subscribe_quote` 实盘流 | 手(100股) | 元 | **万股** | `volume *= 100`, `float_volume *= 10000` |
| `get_full_tick` 快照 | 股 | 元 | **万股** | `float_volume *= 10000` |
| `get_local_data` 回测 | 股 | 元 | **万股** | `float_volume *= 10000` |

**统一规则**：
- `amount` 永远是绝对人民币（元）
- `volume` 入口统一转为股
- `float_volume` 入口统一转为股（×10000）

---

## 🚫 禁止事项

1. **禁止在引擎内部猜测单位** - 所有量纲清洗必须在入口处完成
2. **禁止用归零掩盖异常** - 量纲错了应该校准，不是一刀切归零
3. **禁止均摊算法** - 必须使用真实时空切片
4. **禁止硬编码涨幅阈值** - 使用无量纲化的 `price_momentum` 或 `MFE`

---

## 📖 版本历史

| 版本 | 核心修复 | 日期 |
|------|----------|------|
| V66 | 万股量纲自动升维 | 2026-03-10 |
| V65 | 引力阻尼器 | 2026-03-10 |
| V64 | MFE制衡Sustain | 2026-03-10 |
| V63 | 时空切片替代均摊 | 2026-03-10 |
| V61/V62 | Scan/Live同源 | 2026-03-09 |
