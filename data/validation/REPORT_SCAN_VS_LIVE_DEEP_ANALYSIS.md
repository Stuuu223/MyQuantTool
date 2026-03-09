# Scan复盘 vs 盘中实时 深度研究报告

**报告日期**: 2026-03-09  
**研究目标**: 为什么Scan复盘结果与盘中实盘差异巨大？

---

## 一、核心问题定义

### 现象
- **盘中实盘** (11:28战报): 拓维信息002261.SZ被识别，分数53.47
- **Scan复盘** (23:41): 拓维信息不在榜单，只有11只"臭狗屎"

### 关键差异
| 维度 | 盘中实盘 | Scan复盘 |
|------|---------|----------|
| 数据时间 | 实时Tick流 (09:30-15:00) | 收盘快照 (15:00) |
| 粗筛逻辑 | LiveTradingEngine实时计算 | UniverseBuilder日K线筛选 |
| 量比计算 | 盘中动态加权 | 日K线静态比值 |
| 股票数量 | 动态变化 | 固定25只粗筛→11只结果 |

---

## 二、根因分析

### 2.1 粗筛漏斗差异

#### 盘中实盘 (LiveTradingEngine)
```python
# 实时计算，每分钟更新
def _on_tick_data(self, tick_event):
    # 1. 实时计算量比（时间进度加权）
    volume_ratio = (当前成交量/开盘分钟) / (5日均量/240)
    
    # 2. 实时价格位置
    price_position = (price - low) / (high - low)
    
    # 3. 动态进入watchlist
    if volume_ratio > 阈值 and price_position > 0.9:
        self.watchlist.add(stock)
```

**关键**: 盘中11:13时拓维信息量比可能>3.0，被实时纳入观察池

#### Scan复盘 (UniverseBuilder)
```python
# logic/data_providers/universe_builder.py L349
if (price_momentum >= 0.90 and volume_ratio >= 2.0) or volume_ratio > 3.0 or is_yesterday_limit_up:
    passed.append(stock)
```

**关键**: 使用日K线数据计算
- 量比 = 今日总成交量 / 5日均量 = 1.42x ❌
- 动能 = (close - low) / (high - low) = 1.00 ✅
- 结果: 1.42x < 2.0门槛，被过滤

### 2.2 为什么盘中量比 > 收盘量比？

#### 拓维信息002261.SZ数据
```
盘中11:13 (战报时间)
- 可能已经成交了全天60%的成交量
- 量比实时计算 = (60%成交量/130分钟) / (5日均量/240) ≈ 2.5x ✅

收盘15:00
- 全天成交量 / 5日均量 = 1.42x ❌
```

**结论**: 盘中量比是"加速度"，收盘量比是"总位移"

### 2.3 架构级缺陷

#### 当前Scan实现 (main.py scan_cmd)
```python
# Step 1: 用UniverseBuilder粗筛（基于日K线）
builder = UniverseBuilder(target_date=target_date)
base_pool, volume_ratios = builder.build()  # ❌ 用日K线，非盘中Tick

# Step 2: 90th分位截断
base_pool = [s for s in base_pool if volume_ratios.get(s, 0) >= min_vr_threshold]

# Step 3: 逐只读取收盘Tick（15:00快照）
for stock in base_pool:
    local_data = xtdata.get_local_data(period='tick', ...)
    tick = df.iloc[-1]  # ❌ 只取最后一笔Tick
    # 计算分数...
```

**问题**:
1. 粗筛基于日K线，错过盘中瞬间放量
2. 只读取收盘Tick，丢失盘中所有时间切片
3. 没有模拟实时流的连续计算

#### Live实盘实现 (LiveTradingEngine)
```python
# 实时订阅Tick流
xtdata.subscribe_whole_quote(watchlist)

# 每3秒一个Tick帧，实时计算
def _on_tick_data(self, tick_event):
    # 量比动态更新
    # 价格位置实时监控
    # 满足条件立即入池
```

---

## 三、为什么Scan不用盘中数据？

### 3.1 技术原因

| 问题 | 说明 |
|------|------|
| 数据量爆炸 | 一只票一天~4000笔Tick，全市场~2000万只票 = 80亿条记录 |
| 计算量巨大 | 每Tick都要重算量比/分数，CPU压力巨大 |
| 存储成本 | 保存所有时间切片数据需要TB级存储 |
| 时间对齐 | 不同票的Tick时间戳不完全对齐，难以统一比较 |

### 3.2 设计妥协

当前Scan的设计哲学:
- **简化假设**: 用收盘快照代替全天实时流
- **近似计算**: 用日K线量比代替盘中动态量比
- **快速回测**: 牺牲精度换取速度

**代价**: 错过盘中"瞬间起爆"的真龙

---

## 四、解决方案

### 方案1: 分钟级复盘 (推荐)
**思路**: 不用逐Tick，改用分钟K线
```python
# 获取分钟线数据
df_minute = xtdata.get_local_data(period='1m', ...)

# 对每个分钟切片计算
for timestamp in df_minute.index:
    if timestamp.hour == 11 and timestamp.minute == 13:
        # 计算11:13时的量比和分数
        calculate_score_at_time(timestamp)
```

**优点**:
- 数据量减少240倍 (240分钟 vs 4000 Tick)
- 仍能捕捉盘中关键时间点
- 计算成本可控

### 方案2: 事件驱动复盘
**思路**: 只记录"入池事件"时间点
```python
# 模拟盘中实时流
engine = LiveTradingEngine(mode='scan')
engine.run_historical_stream(tick_stream)  # V56已实现！

# 记录每个股票首次入池时间和分数
entry_log = {
    '002261.SZ': {'time': '11:13:14', 'score': 53.47},
    ...
}
```

**优点**:
- 100%对齐实盘逻辑
- 记录完整时间线
- 可回放任意时刻状态

**缺点**:
- 需要预先准备Tick流数据
- 计算时间较长

### 方案3: 多时间点快照
**思路**: 保存盘中关键时间点数据
```python
# 每小时保存一个快照
snapshots = {
    '09:45': {...},
    '10:30': {...},
    '11:13': {...},  # 拓维信息在此时入池
    '13:00': {...},
    '14:00': {...},
}
```

**优点**:
- 简单实现
- 数据量可控

**缺点**:
- 可能错过非整点起爆
- 需要预判关键时间点

---

## 五、结论与建议

### 核心结论
1. **Scan复盘 ≠ 盘中实盘**: 两者数据粒度完全不同
2. **日K线粗筛是罪魁祸首**: 错过盘中瞬间放量
3. **收盘快照丢失信息**: 只用15:00数据无法还原全天

### 对Boss问题的回答
> "为什么不把盘中符合条件都加入scan复盘？"

**因为当前Scan架构做了简化假设**:
- 用日K线代替盘中Tick流（节省99%计算量）
- 用收盘快照代替实时流（简化实现）

**代价是精度**: 只能抓到"全天强势"的票，错过"盘中起爆"的票。

### 建议
1. **短期**: 降低粗筛门槛（量比2.0→1.0），让更多票进入细筛
2. **中期**: 实现分钟级复盘，捕捉关键时间点
3. **长期**: 使用`run_historical_stream`实现真正的事件驱动复盘

---

**报告完成**  
**研究员**: AI项目总监  
**日期**: 2026-03-09
