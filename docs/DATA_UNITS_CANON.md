# 【量纲宪法】MyQuantTool 数据单位权威定义

**最后验证日期**: 2026-03-17  
**验证人**: CTO审计团队  
**声明**: 其他文件的量纲注释一律以本文件为准，本文件错误请提 PR 修改

---

## 一、QMT 数据源单位定义

| 数据源 API | 字段 | 单位 | 验证方法 | 备注 |
|-----------|------|------|----------|------|
| `get_instrument_detail` FloatVolume | float_volume_raw | **万股** | 平安银行≈192万 | QMT原始返回值 |
| TrueDictionary._float_volume（升维后）| float_volume | **股** | 平安银行≈192亿 | 已×10000，可直接使用 |
| `get_full_tick` volume | volume | **手** | 实盘快照验证 | 需×100转股 |
| `get_local_data(period='1d')` volume | avg_vol_5d | **手** | 对比东方财富 | 需×100转股 |
| `get_local_data(period='tick')` volume | tick_volume | **手** | 历史Tick验证 | 需×100转股 |
| `subscribe_quote` 实时流 volume | volume | **手** | 实盘订阅验证 | 需×100转股 |
| 所有数据源 amount | amount | **元** | 无需转换 | 成交额单位统一 |

**重要说明**：QMT `get_instrument_detail` 返回的 `FloatVolume` 原始单位是**万股**。TrueDictionary 内部自动执行 `×10000` 升维为**股**，外部调用者通过 `get_float_volume()` 获取的已经是股单位，无需再次转换。

---

## 二、核心公式（唯一版本）

### 2.1 换手率公式
```python
# 换手率 = (成交量[手] × 100[股/手]) / 流通股本[股] × 100
volume_gu = current_volume * 100  # 手 → 股
current_turnover = volume_gu / float_volume * 100  # 结果单位：%
```

### 2.2 成交额公式
```python
# 成交额 = 5日均量[手] × 100[股/手] × 价格[元/股]
avg_amount_5d = avg_volume_5d * 100 * prev_close  # 结果单位：元
```

### 2.3 VWAP公式
```python
# VWAP = 成交额[元] / (成交量[手] × 100[股/手])
tick_volume_gu = tick_volume * 100  # 手 → 股
vwap = current_amount / tick_volume_gu  # 结果单位：元/股
```

---

## 三、死亡换手防线

**阈值: 70%**

代码位置: `tasks/run_live_trading_engine.py` 细筛环节

```python
if current_turnover >= 70.0:
    # 死亡换手，跳过
```

---

## 四、量纲自适应规则（V66物理法则）

当流通市值 < 2亿元时，QMT可能返回"万股"单位，需强制升维：

```python
est_market_cap = float_volume * current_price
if est_market_cap < 200_000_000:  # 2亿元
    float_volume = float_volume * 10000  # 万股 → 股
```

---

## 五、修改日志

| 日期 | 修改内容 | 修改人 |
|------|----------|--------|
| 2026-03-17 | 创建量纲宪法，统一死亡换手率为70% | CTO V186 |

---

**警告**: 任何人修改量纲相关代码前，必须先运行 `tests/test_turnover_unit.py` 验证！
