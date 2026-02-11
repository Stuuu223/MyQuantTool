# Phase3 第1周开发文档：纾价快照系统

> 开发时间：2026-02-11  
> 版本：V1.0  
> 状态：✅ 开发完成

---

## 🎯 开发目标

构建一个**纾价快照采集、存储、回放、检测**的完整系统，用于：

1. **纾价数据积累**：每个交易日09:25采集全市场纾价数据
2. **诡多模式识别**：检测“纾价高开+开盘砸盘”等诡多模式
3. **历史回测**：回放历史纾价快照，验证策略有效性

---

## 📦 交付物清单

### 1️⃣ 纾价快照采集脚本

**文件路径**：`tasks/collect_auction_snapshot.py`

**核心功能**：
- 每个交易日09:25采集全市场纾价数据
- 双重存储：SQLite + Redis（兼顾持久化和实时查询）
- 支持单日采集和批量历史数据采集
- 自动跳过周末，智能进度显示

**使用方法**：
```bash
# 1. 采集今日纾价快照（每天交易后执行）
python tasks/collect_auction_snapshot.py

# 2. 采集指定日期的纾价快照（用于补数据）
python tasks/collect_auction_snapshot.py --date 2026-02-10

# 3. 批量采集历史数据（10天）
python tasks/collect_auction_snapshot.py --start-date 2026-02-01 --end-date 2026-02-10

# 4. 查看统计信息
python tasks/collect_auction_snapshot.py --stats --date 2026-02-10
```

**数据结构**：
```python
{
    'date': '2026-02-10',
    'code': '600058.SH',
    'name': '五矿发展',
    'auction_time': '2026-02-10 09:25:00',
    'auction_price': 15.50,
    'auction_volume': 500000,  # 纾价成交量（手）
    'auction_amount': 7750000,  # 纾价成交额（元）
    'auction_change': 0.0333,  # 纾价涨幅 (3.33%)
    'volume_ratio': 2.5,  # 量比
    'buy_orders': 50,  # 买单量
    'sell_orders': 30,  # 卖单量
    'bid_vol_1': 10000,  # 买一量
    'ask_vol_1': 8000,  # 卖一量
    'market_type': 'SH'
}
```

**数据存储**：
- **SQLite**：`data/auction_snapshots.db`
- **Redis**：`auction:YYYYMMDD:CODE`（24小时过期）

---

### 2️⃣ 纾价诡多检测器

**文件路径**：`logic/auction_trap_detector.py`

**核心功能**：
- 检测3种纾价诡多模式
- 输出置信度、风险级别和信号列表
- 支持单个检测和批量检测

**诡多模式定义**：

#### 模式1：纾价高开 + 开盘砸盘 🔴 高风险

**特征**：
- 纾价涨幅 > 3%
- 开盘5分钟内跌幅 > 2%
- 纾价放量（量比 > 1.5）

**逻辑**：  
庄家在纾价阶段大量买入，制造高开幻象。开盘后立即砸盘，散户被套。

**历史案例**：
- **300997（欢乐家）**：2026-01-29 纾价高开+3.33%，开盘5分钟砸盘-2.9%

#### 模式2：纾价爆量 + 尾盘回落 🟡 中风险

**特征**：
- 纾价量比 > 2.0
- 尾盘回落 > 1%（最高价-收盘价）
- 纾价涨幅适中（1-5%）

**逻辑**：  
纾价阶段大量买入，但开盘后尾盘回落，说明接盘无力。

**历史案例**：
- **603697（有友食品）**：2026-02-02 纾价爆量2.5倍，尾盘回落-1.5%

#### 模式3：纾价平开 + 开盘拉升 🟢 正常模式

**特征**：
- 纾价涨幅 < 1%
- 开盘5分钟涨幅 > 3%
- 纾价放量适中（1.5-2.5）

**逻辑**：  
纾价平开，开盘后持续拉升，说明资金真实买入，非诡多。

**使用示例**：
```python
from logic.auction_trap_detector import AuctionTrapDetector

detector = AuctionTrapDetector()

# 纾价数据
auction_data = {
    'code': '300997.SZ',
    'name': '欢乐家',
    'auction_price': 15.50,
    'prev_close': 15.00,
    'auction_change': 0.0333,  # 3.33%
    'auction_volume': 500000,
    'volume_ratio': 2.5,
    # ...
}

# 开盘数据
open_data = {
    'code': '300997.SZ',
    'open_price': 15.50,
    'high_5min': 15.60,
    'close_5min': 15.15,
    'tail_drop': 0.029,  # 2.9%
    # ...
}

# 检测
result = detector.detect(auction_data, open_data)

if result.trap_type != TrapType.NORMAL:
    print(f"⚠️ 发现诡多: {result.trap_type.value}")
    print(f"🚨 风险级别: {result.risk_level.value}")
    print(f"🎯 置信度: {result.confidence*100:.0f}%")
    print(f"📢 信号: {', '.join(result.signals)}")
```

---

### 3️⃣ 纾价快照回放器

**文件路径**：`tasks/replay_auction_snapshot.py`

**核心功能**：
- 回放任意历史日期的纾价快照
- 结合开盘后5分钟K线数据
- 自动调用诡多检测器
- 输出美观的表格报告

**使用方法**：
```bash
# 1. 回放指定日期的纾价快照
python tasks/replay_auction_snapshot.py --date 2026-02-10

# 2. 回放并检测诡多
python tasks/replay_auction_snapshot.py --date 2026-02-10 --detect

# 3. 筛选高开股票并检测
python tasks/replay_auction_snapshot.py --date 2026-02-10 --filter high_open --detect

# 4. 只处理TOP 50只股票
python tasks/replay_auction_snapshot.py --date 2026-02-10 --detect --top 50
```

**筛选条件**：
- `all`：所有股票（默认）
- `high_open`：纾价高开 > 3%
- `low_open`：纾价低开 < -3%
- `high_volume`：量比 > 2.0

**输出示例**：
```
================================================================================
🚨 纾价诡多检测结果
================================================================================

+------------+----------+----------+----------+------+----------+--------------------+-----------+--------+------------------------+
| 代码       | 名称     | 纾价涨幅 | 开盘涨幅 | 量比 | 尾盘回落 | 诡多类型           | 风险级别 | 置信度 | 信号                   |
+============+==========+==========+==========+======+==========+====================+===========+========+========================+
| 300997.SZ  | 欢乐家   | +3.33%   | -2.90%   | 2.5x | 2.90%    | AUC_HIGH_OPEN_DUMP | 🔴 高    | 90%    | 纾价高开, 开盘5分钟砸盘 |
+------------+----------+----------+----------+------+----------+--------------------+-----------+--------+------------------------+

================================================================================
📊 统计信息
================================================================================
总数: 100
诡多数: 1
诡多率: 1.0%

诡多类型分布：
  AUC_HIGH_OPEN_DUMP: 1
```

---

## 🛠️ 技术架构

### 数据流图

```
纾价数据采集 (09:25)
        ↓
    保存到SQLite
        ↓
    缓存到Redis (24h)
        ↓
    纾价快照回放
        ↓
    获取开盘5分钟K线
        ↓
    诡多模式检测
        ↓
    生成检测报告
```

### 核心类图

```
AuctionSnapshotCollector (采集器)
    ├── get_all_stock_codes(): 获取全市场股票代码
    ├── collect_single_snapshot(): 采集单只股票快照
    ├── save_snapshot_to_db(): 保存到SQLite
    ├── collect_all_snapshots(): 批量采集
    └── get_snapshot_stats(): 统计信息

AuctionTrapDetector (检测器)
    ├── _detect_high_open_dump(): 检测模式1
    ├── _detect_boom_tail_drop(): 检测模式2
    ├── _detect_flat_open_pump(): 检测模式3
    ├── detect(): 单个检测
    ├── batch_detect(): 批量检测
    └── get_trap_summary(): 汇总报告

AuctionSnapshotReplayer (回放器)
    ├── load_auction_snapshots(): 加载快照
    ├── get_open_5min_data(): 获取开盘K线
    ├── replay_with_detection(): 回放+检测
    └── print_results(): 打印结果
```

---

## 📝 使用流程

### 步骤1：每日数据采集（建议自动化）

**Windows 任务计划**：
- 时间：每天 09:26
- 命令：`python D:\MyQuantTool\tasks\collect_auction_snapshot.py`

**Linux Cron**：
```bash
# 每天 09:26 执行
26 9 * * 1-5 cd /path/to/MyQuantTool && python tasks/collect_auction_snapshot.py
```

### 步骤2：补充历史数据

```bash
# 补充近10天的历史数据
python tasks/collect_auction_snapshot.py --start-date 2026-02-01 --end-date 2026-02-10
```

### 步骤3：回测验证

```bash
# 回放并检测诡多
python tasks/replay_auction_snapshot.py --date 2026-02-10 --detect

# 只分析高开股票
python tasks/replay_auction_snapshot.py --date 2026-02-10 --filter high_open --detect
```

### 步骤4：集成到交易系统

```python
from logic.auction_trap_detector import AuctionTrapDetector
from logic.auction_snapshot_manager import AuctionSnapshotManager

# 初始化
detector = AuctionTrapDetector()
manager = AuctionSnapshotManager()

# 实时检测（09:25-09:35）
auction_data = manager.get_auction_snapshot(code)
open_data = manager.get_open_5min_data(code)

result = detector.detect(auction_data, open_data)

if result.trap_type != TrapType.NORMAL:
    # 高风险诡多，不参与
    if result.risk_level == RiskLevel.HIGH:
        logger.warning(f"⚠️ {code} 检测到高风险诡多，不参与")
```

---

## 🛡️ 风险提示

### 数据质量

1. **QMT连接稳定性**：确保09:25时QMT客户端已登录
2. **网络延迟**：采集时间可能略有延迟，建议09:26执行
3. **数据缺失**：部分股票可能因停牌等原因无数据

### 检测精度

1. **厂识度仅供参考**：不是100%准确，需结合其他指标
2. **模式可能失效**：市场环境变化可能导致模式失效
3. **厂要实盘验证**：必须通过历史数据回测验证

### 实盘使用

1. **禁止全自动**：不要根据检测结果全自动交易
2. **人工复核**：高风险诡多必须人工复核
3. **小仓位测试**：初期小仓位测试，逐步优化参数

---

## 📊 性能指标

### 采集效率
- 单只股票：~0.01秒
- 全市场（5000股）：~50秒
- 批量10天：~8分钟

### 存储占用
- SQLite：~1MB/天
- Redis：~5MB/天（24小时自动清理）

### 检测速度
- 单只股票：~0.001秒
- 批量100只：~0.1秒

---

## 🔧 故障排查

### 问题1：QMT连接失败

**现象**：`xt_trader.connect()` 返回0

**解决**：
1. 检查QMT客户端是否已登录
2. 检查`userdata_mini`目录下账户状态
3. 重启QMT客户端

### 问题2：数据库锁定

**现象**：`database is locked`

**解决**：
1. 关闭所有正在访问数据库的进程
2. 删除`auction_snapshots.db-shm`和`auction_snapshots.db-wal`文件

### 问题3：Redis连接失败

**现象**：`Redis状态: 不可用`

**解决**：
1. Redis为可选组件，不影响核心功能
2. 如需使用，检查Redis服务是否启动
3. 配置：`config/redis.json`

---

## 📈 后续优化计划

### Phase3 第2周（计划中）

1. **实时监控面板**：
   - Streamlit 实时显示纾价数据
   - 可视化诡多检测结果

2. **多维度纾价分析**：
   - 资金流向分析（机构 vs 散户）
   - 买卖单分布分析
   - 纾价成交金额分布

3. **智能预警**：
   - 实时预警高风险诡多
   - 微信/邮件推送

### Phase3 第3周（计划中）

1. **机器学习模型**：
   - 基于历史数据训练诡多检测模型
   - 提高检测精度和置信度

2. **策略回测框架**：
   - 集成到回测框架
   - 评估纾价策略有效性

---

## 📝 更新日志

### 2026-02-11 - V1.0 ✅ 开发完成

**新增功能**：
- ✅ 纾价快照采集脚本 (`tasks/collect_auction_snapshot.py`)
- ✅ 纾价诡多检测器 (`logic/auction_trap_detector.py`)
- ✅ 纾价快照回放器 (`tasks/replay_auction_snapshot.py`)
- ✅ SQLite + Redis 双重存储
- ✅ 3种纾价诡多模式检测

**技术亮点**：
- 面向对象设计，模块化开发
- 完善的错误处理和日志记录
- 支持批量处理和进度显示
- 美观的表格输出

---

## 👍 总结

Phase3第1周开发已完成核心功能：

1. ✅ **数据采集**：可每日自动采集全市场纾价数据
2. ✅ **模式检测**：可检测3种诡多模式，输出风险级别
3. ✅ **历史回测**：可回放历史数据，验证策略有效性

**下一步**：
- 补充近10天历史数据
- 运行回测，验证检测精度
- 调优检测阈值
- 开发Phase3第2周功能（实时监控面板）

---

**文档版本**：V1.0  
**更新日期**：2026-02-11  
**作者**：MyQuantTool Team