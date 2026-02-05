# 事件记录器使用指南

## 📖 功能说明

事件记录器可以自动记录所有检测到的事件，并支持后续更新和统计分析。

### 核心特性

1. **自动记录**：检测到事件时自动记录到数据库
2. **后续更新**：支持更新收盘价、次日开盘、3天表现等数据
3. **统计分析**：自动计算胜率、平均盈利/亏损等指标
4. **表格导出**：一键导出为Excel/CSV表格

---

## 🚀 使用方法

### 1. 自动记录（无需手动操作）

事件会在检测到时自动记录到数据库，无需手动操作。

当运行事件驱动监控器时，检测到的事件会自动记录：
```bash
python tasks/run_event_driven_monitor.py --mode fixed_interval
```

日志会显示：
```
🔔 检测到事件: 000592.SZ - 竞价弱转强：高开6.00%，量比2.00
💾 事件已记录到数据库 (ID: 5)
```

### 2. 导出事件记录

#### 方式一：使用批处理文件（推荐）
```bash
export_records.bat
```

#### 方式二：使用Python脚本
```bash
python export_event_records.py
```

#### 输出文件
- `data/event_records.xlsx` - Excel表格
- `data/event_records.csv` - CSV表格

---

## 📊 表格字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| 时间 | 事件触发时间 | 2026-02-06 09:25:00 |
| 股票代码 | 股票代码 | 000592.SZ |
| 事件类型 | 事件类型 | opening_weak_to_strong |
| 事件描述 | 事件描述 | 竞价弱转强：高开6.00%，量比2.00 |
| 置信度 | 事件置信度 | 0.85 |
| 触发条件 | 触发条件（JSON） | {"gap_pct": 0.06, "volume_ratio": 2.0} |
| 昨收价 | 昨日收盘价 | 10.00 |
| 开盘价 | 开盘价 | 10.60 |
| 当前价 | 当前价 | 10.60 |
| 收盘价 | 当日收盘价 | 10.81 |
| 收盘涨幅 | 当日收盘涨幅 | 0.0812 |
| 次日开盘 | 次日开盘价 | 10.92 |
| 次日开盘涨幅 | 次日开盘涨幅 | 0.0918 |
| 3天最大涨幅 | 3天内最大涨幅 | 0.15 |
| 3天最大跌幅 | 3天内最大跌幅 | -0.03 |
| 是否赚钱 | 是否赚钱（3天内） | TRUE |
| 盈利金额 | 盈利金额 | 15000 |
| 备注 | 备注 | - |

---

## 📈 统计分析

事件记录器会自动生成统计信息：

```
================================================================================
📊 事件记录统计
================================================================================
总记录数: 8

按事件类型统计:
   dip_buy_candidate: 2 次
   halfway_breakout: 2 次
   leader_candidate: 2 次
   opening_weak_to_strong: 2 次

盈利统计:
   盈利次数: 4
   亏损次数: 4
   平均盈利: 15000.00
   平均亏损: -5000.00
   胜率: 50.00%
================================================================================
```

---

## 🔍 查询和筛选

### 按事件类型筛选

```python
from logic.event_recorder import get_event_recorder

recorder = get_event_recorder()
records = recorder.get_records(event_type='opening_weak_to_strong')
```

### 按股票代码筛选

```python
records = recorder.get_records(stock_code='000592.SZ')
```

### 按日期筛选

```python
records = recorder.get_records(
    start_date='2026-02-01',
    end_date='2026-02-28'
)
```

---

## 📝 手动更新数据

如果需要手动更新后续数据，可以使用以下方法：

### 更新收盘价

```python
recorder.update_day_close(record_id=5, day_close=10.81)
```

### 更新次日开盘

```python
recorder.update_next_day_open(record_id=5, next_day_open=10.92)
```

### 更新3天表现

```python
recorder.update_3days_performance(
    record_id=5,
    max_gain=0.15,
    max_loss=-0.03,
    is_profitable=True,
    profit_amount=15000
)
```

---

## 🎯 实盘使用建议

### 每天收盘后

1. **导出事件记录**
   ```bash
   export_records.bat
   ```

2. **打开Excel表格**
   - 打开 `data/event_records.xlsx`
   - 查看当天触发的事件

3. **更新收盘价**
   - 使用Excel筛选当天的事件
   - 手动更新收盘价和收盘涨幅

4. **分析事件质量**
   - 统计每种事件的胜率
   - 计算平均收益
   - 识别高胜率事件

### 每周复盘

1. **导出周报**
   - 筛选一周的事件
   - 更新所有后续数据

2. **统计分析**
   - 每种事件的胜率
   - 平均盈利/亏损
   - 最优事件类型

3. **调整参数**
   - 胜率低的事件：调严阈值
   - 触发少的事件：调宽阈值

---

## 🔧 高级功能

### 自定义查询

```python
from logic.event_recorder import get_event_recorder

recorder = get_event_recorder()

# 查询最近10条竞价弱转强事件
records = recorder.get_records(
    event_type='opening_weak_to_strong',
    limit=10
)

# 查询指定股票的所有事件
records = recorder.get_records(
    stock_code='000592.SZ',
    limit=100
)
```

### 导出特定数据

```python
# 只导出竞价弱转强事件
records = recorder.get_records(event_type='opening_weak_to_strong')

# 转换为DataFrame
import pandas as pd
data = [record.to_dict() for record in records]
df = pd.DataFrame(data)

# 自定义筛选
df_filtered = df[df['day_close_pct'] > 0.05]  # 只看收盘涨幅>5%的

# 导出
df_filtered.to_excel('filtered_events.xlsx', index=False)
```

---

## 📞 常见问题

### Q1: 数据库文件在哪里？

A: 数据库文件位于 `data/event_records.db`

### Q2: 如何备份数据？

A: 直接复制 `data/event_records.db` 文件即可

### Q3: 如何清空数据？

A: 删除 `data/event_records.db` 文件，系统会自动重新创建

### Q4: Excel导出失败怎么办？

A: 需要安装pandas和openpyxl：
```bash
pip install pandas openpyxl
```

### Q5: 如何分析数据？

A: 打开Excel表格，使用透视表、筛选、排序等功能进行分析

---

## 📚 相关文档

- [事件驱动监控使用指南](EVENT_DRIVEN_MONITOR_GUIDE.md)
- [第二阶段总结](PHASE2_SUMMARY.md)

---

**版本**: V2.0
**最后更新**: 2026-02-06
**作者**: iFlow CLI