# 【量纲宪法】MyQuantTool 数据单位权威定义

**版本**: V188 白盒防腐层架构  
**最后验证日期**: 待补充（需开盘实测 H-0 五票诊断）  
**验证人**: 待实盘验证  
**声明**: 其他文件的量纲注释一律以本文件为准，本文件错误请提 PR 修改

---

## 一、QMT 数据源单位定义

| 数据源 API | 字段 | 单位 | 验证方法 | 备注 |
|-----------|------|------|----------|------|
| `get_instrument_detail` FloatVolume | float_volume_raw | **万股** | 待开盘实测（H-0） | QMT原始返回值 |
| TrueDictionary._float_volume（升维后）| float_volume | **股** | QMTNormalizer归一化 | 由Normalizer自动升维 |
| `get_full_tick` volume | volume | **手** | 待开盘实测（H-0） | QMTNormalizer归一化 |
| `get_local_data(period='1d')` volume | avg_vol_5d | **手** | 待开盘实测（H-0） | QMTNormalizer归一化 |
| `get_local_data(period='tick')` volume | tick_volume | **手** | 待开盘实测（H-0） | QMTNormalizer归一化 |
| `subscribe_quote` 实时流 volume | volume | **手** | 待开盘实测（H-0） | QMTNormalizer归一化 |
| 所有数据源 amount | amount | **元** | 无需转换 | 成交额单位统一 |

**【V188白盒防腐层架构】**：
- 所有量纲转换**必须且只能**通过 `QMTNormalizer` 进行
- 禁止业务代码直接写 `*100` 或 `*10000`
- 每次升维触发必须打 `WARNING` 日志（白盒可观测）

---

## 二、核心公式（唯一版本）

### 2.1 换手率公式（V188白盒版）
```python
from logic.data_providers.qmt_normalizer import QMTNormalizer

# 白盒防腐层统一入口
turnover_rate = QMTNormalizer.calculate_turnover_rate(
    volume_raw=current_volume,      # QMT原始值（手）
    float_volume_raw=float_volume,  # QMT原始值（可能是万股）
    price=current_price,
    volume_source='live_tick'
)
```

### 2.2 量比公式（无量纲自消除）
```python
# 量比 = 今日成交量 / 5日平均成交量
# 注意：分子分母单位相同（都是手），量纲自然消除，无需转换！
volume_ratio = today_volume / avg_volume_5d
```

### 2.3 成交额公式
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
