# QMT数据源量纲知识库 (Domain Knowledge Base)

**版本**: v1.0.0  
**生效日期**: 2026-02-26  
**制定者**: CTO + Boss  
**适用范围**: 所有AI开发团队成员  

---

## 量纲铁律 (不可违背)

### [量纲铁律 1] QMT get_full_tick 返回的 volume 单位是**手**！

**关键事实**:
- `xtdata.get_full_tick()` 返回的 `volume` 字段单位是**手** (1手 = 100股)
- 计算量比、换手率时，必须先将**手转换为股** (乘以100)

**错误示例**:
```python
# ❌ 错误：直接用手除以股
volume_ratio = tick_volume / avg_volume_5d  # 结果会缩小100倍！
```

**正确示例**:
```python
# ✅ 正确：先统一单位为股
volume_gu = tick_volume * 100  # 手→股
volume_ratio = volume_gu / avg_volume_5d
```

---

### [量纲铁律 2] 计算量比时，分子和分母的单位必须绝对一致！

**数据来源**:
- `tick_volume`: 手 (来自get_full_tick)
- `avg_volume_5d`: 股 (来自日K数据volume字段的均值)

**强制对齐**:
```python
# 统一转换为"股"单位
current_volume_gu = tick_volume_shou * 100
volume_ratio = current_volume_gu / avg_volume_5d_gu
```

---

### [量纲铁律 3] 计算换手率时，流通股本需要探针检查其量级！

**数据来源**:
- `tick_volume`: 手 (来自get_full_tick)
- `float_volume`: 股 (来自get_instrument_detail)

**强制计算**:
```python
# 统一转换为"股"单位
current_volume_gu = tick_volume_shou * 100
turnover_rate = (current_volume_gu / float_volume_gu) * 100  # 输出百分比
```

**输出要求**:
- 换手率最终输出必须是**百分比** (如 5.0 表示 5%)
- 禁止输出小数形式 (如 0.05 表示 5%)

---

### [量纲铁律 4] 常见QMT字段单位速查表

| 字段名 | 单位 | 来源 | 备注 |
|--------|------|------|------|
| volume (tick) | 手 | get_full_tick | 必须×100转股通 |
| volume (日K) | 股 | get_local_data(1d) | 已经是股 |
| amount | 元 | get_full_tick | 成交额 |
| FloatVolume | 股 | get_instrument_detail | 流通股本 |
| avg_volume_5d | 股 | 计算值 | 日K volume均值 |

---

## 防错自检清单

写任何涉及成交量、换手率的代码前，必须自检：

1. [ ] 当前volume单位是手还是股？
2. [ ] 对比的基准volume单位是手还是股？
3. [ ] 两者是否已经统一为相同单位？
4. [ ] 换手率输出是百分比(5.0)还是小数(0.05)？

---

## 违规处罚

违反量纲铁律导致计算错误的：
- 🔴 代码拒绝合并
- 🔴 回滚重来
- 🔴 重新阅读本知识库

---

**记住：单位错位是量化开发中最愚蠢的错误，没有之一！**
