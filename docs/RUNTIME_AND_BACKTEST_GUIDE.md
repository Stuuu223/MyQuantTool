---
version: V17.0.0
updated: 2026-02-19
scope: 运行时主线与回测
author: MyQuantTool Team
---

# MyQuantTool 运行时与回测指南

---

## 1. 实时监控主线

### 1.1 启动

```bash
# 推荐：事件驱动监控
python main.py monitor
```

### 1.2 监控流程

```
┌─────────────────────────────────────────────────────────┐
│  PreMarket预热 (9:15前)                                 │
│  - 加载顽主杯/龙虎榜候选池                               │
│  - 竞价数据收集                                         │
├─────────────────────────────────────────────────────────┤
│  盘中监控 (9:30-15:00)                                  │
│  - EventDrivenMonitor 事件驱动                          │
│  - 三漏斗实时筛选                                       │
│  - Portfolio决策                                        │
├─────────────────────────────────────────────────────────┤
│  盘后复盘 (15:00后)                                     │
│  - FullMarketScanner 全市场扫描                         │
│  - 结果保存与分析                                       │
└─────────────────────────────────────────────────────────┘
```

### 1.3 数据流检查

**实时模式强制验证**：
- QMT连接状态
- Tick数据新鲜度（< 60秒）
- 资金流数据可用性

```python
# 禁止使用T+1数据做实时决策
if provider.get_data_freshness(code) > 60:
    raise DataNotAvailableError("数据过期，禁止决策")
```

---

## 2. 三漏斗筛选

### 2.1 Level 1: 流动性

```python
# 相对阈值，非硬编码
liquidity_score = volume / avg_volume_20d
if liquidity_score < 0.5:
    return REJECT
```

### 2.2 Level 2: 形态

```python
# 价格相对位置
price_position = (current - low_20d) / (high_20d - low_20d)
if price_position < 0.3 or price_position > 0.95:
    return REJECT  # 不追高，不抄底
```

### 2.3 Level 3: 资金

```python
# 相对分位数
capital_percentile = get_percentile(main_net_inflow, all_stocks)
if capital_percentile < 0.95:
    return REJECT  # 只关注资金前列
```

---

## 3. Portfolio 决策

### 3.1 断层优势

```python
# Top1 明显领先时单吊
if top1_score > top2_score * 1.5:
    allocation = {top1: 0.9}
```

### 3.2 持仓PK

```python
# 持仓股票评分下降，候选池有更优机会
if candidate_score > holding_score * 1.2:
    action = SWITCH  # 换仓
```

### 3.3 动态仓位

| 持仓数 | 分配方案 |
|--------|----------|
| 1只 | 90% |
| 2只 | 60% + 40% |
| 3只 | 50% + 30% + 20% |

---

## 4. 回测系统

### 4.1 回测入口

```bash
# 热门样本回测
python backtest/run_hot_cases_suite.py

# 顽主杯回测
python backtest/run_comprehensive_backtest.py

# Tick回放回测
python backtest/run_tick_replay_backtest.py
```

### 4.2 回测模式

```python
# 回测使用历史数据源
provider = DataProviderFactory.create_for_mode('replay')
# 优先级: qmt_tick → dongcai
```

### 4.3 策略一致性

**关键原则**: 回测与实盘使用同一套策略逻辑。

```python
# 策略入口统一
from logic.services.strategy_service import StrategyService

strategy = StrategyService()
signals = strategy.evaluate(code, data, params)
```

---

## 5. 参数优化

### 5.1 动态阈值类

```python
from logic.strategies.dynamic_threshold import DynamicThreshold

threshold = DynamicThreshold(
    base_percentile=0.95,
    adjustment_factor=1.0
)
```

### 5.2 自校准

```python
# 根据历史表现自动调整
if hit_rate < 0.5:
    threshold.tighten()  # 收紧
elif false_positive_rate > 0.3:
    threshold.loosen()   # 放宽
```

---

## 6. 验证流程

### 6.1 热门样本验证

| 样本 | 标的 | 验证点 |
|------|------|--------|
| 网宿科技 | 300017.SZ | 资金攻击检测 |
| 顽主杯 | 131只 | 真实窗口触发率 |

### 6.2 验证命令

```bash
python backtest/run_hot_cases_suite.py --case wangsu
python backtest/run_hot_cases_suite.py --case wanzhu
```

---

## 7. 常见问题

### 7.1 回测与实盘结果不一致

**原因**: 数据源差异或参数硬编码

**解决**: 确保使用同一套 StrategyService

### 7.2 触发率过低

**原因**: 阈值过于严格

**解决**: 使用相对分位数，检查 V12 过滤器是否误启用

---

**详细架构**: 参见 `KNOWLEDGE_BASE_V17.md`
