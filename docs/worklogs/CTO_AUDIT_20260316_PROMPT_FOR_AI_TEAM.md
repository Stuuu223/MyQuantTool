# CTO 深度审计报告 + AI团队修复Prompt

> **日期**: 2026-03-16 | **版本**: V9.5 | **审计范围**: 最新master快照
>
> **性质**: 本文档既是CTO审计结论，也是直接喂给AI编码团队的修复任务Prompt。
> 每个Issue独立可执行，AI无需理解全局即可精准修复。

---

## ⚠️ 审计总裁定

团队V185声称「量纲核弹级修复已完成」，经本次深度代码审计：
**换手率×100修复本身是正确的，但存在3处新引入的逻辑Bug和1处架构幻觉未清除。**
直接影响实盘量比阈值计算，危及资金安全。

---

## Issue #1 【P0 逻辑Bug】漏斗2量比计算包含今日自身，avg_volume_5d被今日污染

### 证据（universe_builder.py L261-270）

```python
# 现有代码
n = min(5, len(df))
if n > 0:
    today_volume = float(df['volume'].iloc[-1])
    avg_volume_5d = df['volume'].iloc[-n:].mean()  # ← BUG
```

### 问题
`df['volume'].iloc[-n:]` 的最后一行 `iloc[-1]` **就是today_volume本身**。
当股票今天放量3倍时：
- avg_volume_5d = (过去4天均量×4 + 今天量×3) / 5 ≈ 过去4天均量×1.4
- 实际计算出的量比 = today_vol / avg_vol ≈ 3 / 1.4 = **2.14x，而非真实的3.0x**
- 量比被压低约30%，导致真龙信号被漏斗过滤掉！

### 正确修复

```python
# 修复：avg_volume_5d必须排除今日（取倒数第2到第6天）
n = min(5, len(df) - 1)  # 排除今日
if n > 0:
    today_volume = float(df['volume'].iloc[-1])
    avg_volume_5d = df['volume'].iloc[-n-1:-1].mean()  # 只取历史5天
    # 注意：如果df总长度<2，avg_volume_5d无法计算，使用today_volume作为avg（量比=1.0）
    if pd.isna(avg_volume_5d) or avg_volume_5d <= 0:
        avg_volume_5d = today_volume if today_volume > 0 else 1.0
```

### 影响文件
- `logic/data_providers/universe_builder.py` → `_funnel2_daily_kline()` 方法

---

## Issue #2 【P0 逻辑Bug】漏斗2中 volume_ratio 被重复计算两次，第二次覆盖第一次

### 证据（universe_builder.py）

```python
# 第一次计算（约L261，用于self._volume_ratios分布统计）
volume_ratio = today_volume / avg_volume_5d
self._volume_ratios[stock] = float(volume_ratio)

# ---- 中间省略若干行过滤逻辑 ----

# 第二次计算（约L310，用于漏斗2门槛判断）
volume_ratio = today_volume / avg_volume_5d if avg_volume_5d > 0 else 0   # ← 同样变量名
if volume_ratio < 2.0:
    cnt_turnover += 1
    continue
```

### 问题
两次计算的`avg_volume_5d`可能不同！第一次用的是 `df['volume'].iloc[-n:].mean()`（含今日），
第二次也是同一个变量（同一个代码块内，变量未刷新）。
**表面上无差异，但一旦Issue #1修复后，两次计算的avg_volume_5d必须保持一致，
否则 self._volume_ratios 与漏斗判断用的量比会对不上！**
这是一个时序依赖陷阱，修复Issue #1时必须同步修复。

### 正确修复
只计算一次 `avg_volume_5d` 和 `volume_ratio`，统一赋值到 `self._volume_ratios` 和漏斗判断，禁止两次独立计算。

---

## Issue #3 【P1 架构幻觉】`get_avg_turnover_5d` 使用「市值平替法」但含量纲错误

### 证据（true_dictionary.py `get_avg_turnover_5d`）

```python
# 市值平替法：amount / (float_volume * close) * 100
df['turnover_rate'] = df['amount'] / (float_volume * df['close']) * 100
```

### 量纲分析
- `df['amount']` 单位：**元**（来自K线，已确认）
- `float_volume` 单位：**股**（来自get_instrument_detail.FloatVolume，已确认）
- `df['close']` 单位：**元/股**
- 分母 = 股 × 元/股 = **元**（流通市值）
- 结果 = 元/元 × 100 = **换手率%**  ✅

**此处量纲正确！**

但注释和文档说「绕开volume单位问题」是**幻觉导向注释**：
这个方法本来就不用volume，用的是amount，量纲天然对。
注释让后续开发者误以为有什么「绕开」的魔法，实际没有。

### 修复
修改注释：
```python
# 换手率 = 成交额(元) / 流通市值(股×元/股) × 100
# amount单位是元，float_volume单位是股，close单位是元/股，量纲天然正确，无需转换
df['turnover_rate'] = df['amount'] / (float_volume * df['close']) * 100
```
删除「绕开volume单位问题」的误导性注释。

---

## Issue #4 【P1 逻辑隐患】`build_static_cache` 中昨日涨停判断用`high`而非`close`，判断逻辑存在歧义

### 证据（true_dictionary.py `build_static_cache`）

```python
# 昨日最高价
prev_high = float(df['high'].iloc[-2])
# 前日收盘价
prev_prev_close = float(df['close'].iloc[-3]) if len(df) >= 3 else float(df['open'].iloc[-2])

if prev_prev_close > 0:
    y_change = (prev_high - prev_prev_close) / prev_prev_close * 100.0
    limit_threshold = 19.5 if stock.startswith(('30', '68')) else 9.5
    if y_change >= limit_threshold:
        is_yesterday_limit_up = True
```

### 问题
用`昨日最高价`判断涨停，而非`昨日收盘价`。
- 如果昨天冲高回落（最高达到涨停价但最终收盘低于涨停价），会被误判为昨日涨停。
- 正确判断是：`prev_close（昨收）≈ up_stop_price（涨停价）`，误差<0.1%。

### 正确修复
```python
# 昨日是否真涨停：昨日收盘价 ≈ 涨停价（误差<0.5%）
# 直接使用TrueDictionary里已缓存的up_stop_price对比
prev_close_for_check = float(df['close'].iloc[-2])  # 昨收
up_stop = self.get_up_stop_price(stock)
if up_stop > 0:
    is_yesterday_limit_up = (abs(prev_close_for_check - up_stop) / up_stop < 0.005)
else:
    # fallback: 用涨幅判断（以昨收/前收计算，而非最高价）
    prev_prev_close = float(df['close'].iloc[-3]) if len(df) >= 3 else float(df['open'].iloc[-2])
    y_change = (prev_close_for_check - prev_prev_close) / prev_prev_close * 100.0
    limit_threshold = 19.5 if stock.startswith(('30', '68')) else 9.5
    is_yesterday_limit_up = y_change >= limit_threshold
```

---

## Issue #5 【P1 死代码告警】`extract_mfe` 在physics_sensors.py注释说是DEAD CODE但架构注释仍引用它

### 证据（physics_sensors.py 底部正确使用注释）

```python
# ✅ 正确用法：
#   from logic.core.physics_sensors import (
#       extract_purity,
#       extract_volume_ratio,
#       extract_mfe_efficiency,   # ← 引用了一个不存在的函数名！
```

### 问题
文件中根本不存在 `extract_mfe_efficiency` 这个函数，只有 `extract_mfe`（且已标为DEAD CODE）。
注释写的使用示例引用了幻觉函数名，新成员照着抄会报ImportError。

### 修复
```python
# 删除以下幻觉注释行：
#       extract_mfe_efficiency,   # ← 删除，此函数不存在
# 或改为：
#       # extract_mfe 已废弃，实盘MFE计算在 kinetic_core_engine.calculate_true_dragon_score 内部
```

---

## Issue #6 【P2 数据安全】`build_static_cache` 使用 `datetime.now()` 导致回测时空污染

### 证据（true_dictionary.py `build_static_cache`）

```python
today = datetime.now().strftime('%Y%m%d')  # ← 回测时=今天，不是回测目标日期！
three_days_ago = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
```

### 问题
`build_static_cache` 没有接受 `target_date` 参数，直接用 `datetime.now()`。
在回测模式下，用今日日期的「昨日涨停」数据来模拟历史日期的决策，是经典时空错乱问题（未来函数）。

### 修复
```python
def build_static_cache(
    self,
    stock_list: List[str],
    default_float_volume: float = 1000000000.0,
    target_date: str = None   # ← 新增参数
) -> Dict:
    today = target_date if target_date else datetime.now().strftime('%Y%m%d')
    # ... 其余用 today 替换 datetime.now().strftime('%Y%m%d')
```

---

## Issue #7 【P2 注释幻觉】`UNIT_DIMENSION_TRUTH.md` 第二章表格中存在错误描述

### 证据（docs/architecture/UNIT_DIMENSION_TRUTH.md）

```markdown
**禁止**在分子或分母上乘以100做股手转换，否则量比被放大或缩小100倍。
```

### 问题
此描述不精确。禁止的是「分子分母单位不一致时不做转换」，而非「禁止任何×100」。
换手率计算合法地使用了 `volume(手) × 100 / FloatVolume(股)`，这正是量纲统一的正确做法。
如果团队成员看到「禁止×100」会产生误解。

### 修复
将该行改为：
```markdown
**铁律**: 量比公式 = 分子(手) ÷ 分母(手)，禁止在量比计算中做股手转换（会引入100倍误差）。
换手率公式 = volume(手) × 100 ÷ FloatVolume(股) × 100，此处×100是量纲统一，合法。
```

---

## AI团队执行优先级

| Priority | Issue | 文件 | 预计行数 | 风险 |
|---|---|---|---|---|
| P0-立即 | #1 avg_volume_5d含今日 | universe_builder.py | ~5行 | 量比系统性偏低30% |
| P0-立即 | #2 volume_ratio重复计算 | universe_builder.py | 重构逻辑 | 修#1时必须同步 |
| P1-今日 | #4 昨日涨停用high判断 | true_dictionary.py | ~10行 | 误判涨停率约5-10% |
| P1-今日 | #5 幻觉函数名注释 | physics_sensors.py | 1行 | 误导新成员 |
| P1-今日 | #6 build_static_cache时空污染 | true_dictionary.py | 函数签名+2处替换 | 回测失真 |
| P2-本周 | #3 误导性注释 | true_dictionary.py | 注释修改 | 无功能影响 |
| P2-本周 | #7 文档描述不精确 | UNIT_DIMENSION_TRUTH.md | 1行 | 无功能影响 |

---

## AI团队执行规范

1. **修复#1和#2必须同时提交**，因为两者共享同一段代码逻辑，分开修复必然出现中间态Bug。
2. **修复前必须先添加单元测试**：构造一个今日量比=3.0x的假数据，验证修复后量比≥2.9x。
3. **禁止改动 `kinetic_core_engine.py`**：该文件当前量比计算逻辑正确，不在本次修复范围。
4. **所有修改必须附上量纲注释**：格式如 `# 单位: 手/手 = 无量纲`。

---

*审计人: CTO | 2026-03-16 | 基于代码事实，无主观推断*
