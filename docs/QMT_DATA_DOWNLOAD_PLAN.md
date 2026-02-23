# QMT历史数据下载计划

## 1. 数据存储路径

| 路径类型 | 位置 | 说明 |
|---------|------|------|
| QMT主数据目录 | `E:\qmt\userdata_mini\datadir` | QMT软件自带数据目录 |
| 项目数据目录 | `E:\MyQuantTool\data\qmt_data\datadir` | 项目自定义数据目录 |

## 2. 需要下载的数据类型

### 2.1 第一段粗筛所需数据（5000→200）

#### Layer 1: 静态过滤（无需下载）
- 使用Tushare实时获取：股票基础信息、ST标记、停牌状态

#### Layer 2: 日线过滤（必须下载）
- **数据类型**: 日线数据（1d）
- **时间范围**: 2025-12-24 至 2025-12-31（共5个交易日）
- **字段**: amount（成交额）、volume（成交量）、close（收盘价）
- **用途**: 计算5日日均成交额，过滤<3000万的股票
- **存储位置**: `datadir/minute/lday/`（QMT自动存储）

#### Layer 3: 分钟线过滤（必须下载）
- **数据类型**: 1分钟线数据（1m）
- **时间范围**: 2025-12-31 09:30-10:00
- **字段**: volume（成交量）
- **用途**: 计算早盘量比（09:30-10:00 vs 历史同期）
- **存储位置**: `datadir/minute/minute_20251231/`（QMT自动存储）

### 2.2 第二段Tick炼蛊所需数据（200→Top 10）

#### Tick级精细分析（必须下载）
- **数据类型**: Tick数据（tick）
- **时间范围**: 2025-12-31 09:30-10:30
- **字段**: 
  - time（时间戳）
  - lastPrice（最新价）
  - volume（成交量）
  - open（开盘价，用于昨收验证）
- **用途**: 
  - 计算真实振幅（基于昨收价）
  - 计算ATR比率
  - 计算5分钟资金净流入
- **存储位置**: `datadir/tick/`（QMT自动存储）

## 3. 下载方法

### 3.1 使用xtdata.download_history_data

```python
from xtquant import xtdata

# 下载日线数据（5日）
xtdata.download_history_data(
    stock_code='300986.SZ',
    period='1d',
    start_time='20251224',
    end_time='20251231'
)

# 下载分钟线数据（1天早盘）
xtdata.download_history_data(
    stock_code='300986.SZ', 
    period='1m',
    start_time='20251231',
    end_time='20251231'
)

# 下载Tick数据（1天早盘）
xtdata.download_history_data(
    stock_code='300986.SZ',
    period='tick', 
    start_time='20251231',
    end_time='20251231'
)
```

### 3.2 批量下载策略

由于需要下载5000只股票的5日数据：
- **分批下载**: 每批100只，避免QMT接口限流
- **异步下载**: 使用多线程加速
- **增量下载**: 只下载缺失的数据
- **预计耗时**: 
  - 日线：5000只×5天 ≈ 30分钟
  - 分钟线：5000只×1天 ≈ 20分钟  
  - Tick线：200只×1天 ≈ 10分钟（只需下载通过粗筛的）

## 4. 数据完整性验证

下载后需要验证：
```python
# 验证日线数据完整性
df = xtdata.get_local_data(
    field_list=['time', 'amount'],
    stock_list=['300986.SZ'],
    period='1d',
    start_time='20251224',
    end_time='20251231'
)
print(f"日线数据条数: {len(df)}")  # 应该=5

# 验证分钟线数据完整性
df = xtdata.get_local_data(
    field_list=['time', 'volume'],
    stock_list=['300986.SZ'],
    period='1m', 
    start_time='20251231',
    end_time='20251231'
)
print(f"分钟线数据条数: {len(df)}")  # 应该=240（4小时×60分钟）

# 验证Tick数据完整性
df = xtdata.get_local_data(
    field_list=['time', 'lastPrice', 'volume'],
    stock_list=['300986.SZ'],
    period='tick',
    start_time='20251231',
    end_time='20251231'
)
print(f"Tick数据条数: {len(df)}")  # 应该=4800左右（全天）
```

## 5. 真实全息回演执行步骤

### Step 1: 配置环境（5分钟）
1. ✅ 配置Tushare Token（已完成）
2. 关闭演示模式：`demo_mode: False`
3. 确认QMT连接正常

### Step 2: 下载历史数据（60分钟）
1. 下载5000只股票5日日线数据
2. 下载5000只股票12.31分钟线数据
3. 等待第一段粗筛完成后，下载200只股票Tick数据

### Step 3: 执行真实回演（5分钟）
```bash
python tasks/run_time_machine_backtest.py --date 20251231 --save
```

### Step 4: 验证结果（10分钟）
1. 检查志特新材是否进入Top 10
2. 验证所有股票名称是否真实（而非"股票168"）
3. 验证所有指标是否基于真实数据计算

## 6. 风险提示

1. **数据缺失风险**: QMT可能缺少某些股票的历史数据
2. **下载超时风险**: 5000只股票批量下载可能触发QMT限流
3. **存储空间风险**: Tick数据量大，确保磁盘有足够空间（预计5-10GB）

## 7. 建议

考虑到数据下载耗时较长（约60分钟），建议：

**方案A**: 先下载单只股票（志特新材）验证整个流程
**方案B**: 直接下载全量5000只股票数据（后台执行）

请老板和CTO指示采用哪种方案？
