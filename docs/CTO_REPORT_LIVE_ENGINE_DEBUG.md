# CTO请示报告：MyQuantTool实盘引擎阻塞问题诊断

**报告日期**：2026-03-05  
**报告人**：AI开发专家团队  
**审阅人**：CTO

---

## 一、问题概述

### 1.1 问题现象
盘后运行 `python main.py live` 时，粗筛池显示438只正常，但之后卡住5-6分钟无响应。

### 1.2 影响范围
- 实盘监控功能无法正常使用
- 盘后复盘功能受阻
- 影响交易决策时效性

---

## 二、诊断历程（8个Phase）

### Phase 1：初步定位
**起因**：用户反馈粗筛池为空  
**诊断**：检查`_snapshot_filter`执行流程  
**疑点**：盘后运行时数据字段是否完整？

### Phase 2：字段诊断
**起因**：怀疑avg_turnover_5d预热不充分  
**诊断**：创建独立诊断脚本验证字段完整性  
**发现**：所有字段100%有效（1010/1010）  
**教训**：不应该直接修改生产代码添加诊断日志，应创建独立测试脚本

### Phase 3：快照字段诊断
**起因**：字段有效但粗筛仍为空  
**诊断**：检查快照数据结构  
**发现**：
```
QMT快照字段：[..., 'lastClose', ...]
代码使用：tick.get('preClose', 0)  ← 错误！
```
**Bug #1**：`preClose` → `lastClose`

### Phase 4：量比计算诊断
**起因**：字段修复后量比仍异常（中位数75.89，正常应≈1.0）  
**诊断**：检查量比计算公式  
**发现**：
```
volume_gu = volume * 100  # 手→股
volume_ratio = volume_gu / avg_volume_5d  # 股/手 = 放大100倍！
```
**Bug #2**：avg_volume_5d单位是手，需乘100转成股

### Phase 5：dropna屠杀诊断
**起因**：量比修复后仍有大量数据丢失  
**诊断**：检查过滤条件  
**发现**：
```python
df = df.dropna(subset=['volume_ratio', 'avg_turnover_5d', 'avg_amount_5d'])
```
**Bug #3**：dropna直接删除缺失数据，应改为fillna容错

### Phase 6：动态阈值诊断
**起因**：修复后盘后量比>=3.0x只有117只（2.3%）  
**诊断**：分析盘后量比分布  
**发现**：
```
盘后量比中位数：0.76x
量比>=3.0x：仅117只(2.3%)
量比>=1.5x：约1000只(20%)
```
**Bug #4**：静态阈值3.0x在盘后过于严格，应动态衰减

### Phase 7：缓存依赖诊断
**起因**：粗筛仍为空  
**诊断**：检查TrueDictionary缓存预热  
**发现**：
```
_prev_close_cache 只在 _warmup_atr_data 中填充
ATR预热失败 → 缓存为空 → get_prev_close返回None
```
**Bug #5**：prev_close依赖TrueDictionary缓存，但缓存为空

### Phase 8：阻塞根因诊断（关键）
**起因**：用户反馈卡住5-6分钟  
**诊断**：创建断点测试逐步排查  
**发现**：
```
| 步骤 | 耗时 |
|------|------|
| _auction_snapshot_filter | 0.32s |
| _snapshot_filter | 74-102秒 ← 阻塞点！ |
| subscribe_ticks(10只) | 3.87s |
```
**Bug #7**：`_snapshot_filter`预热全部A股（5191只）耗时74秒

---

## 三、Bug汇总

| # | 问题 | 影响 | 修复方案 |
|---|------|------|----------|
| 1 | preClose字段名错误 | prev_close全是0 | 改为lastClose |
| 2 | 量比单位错误 | 量比放大100倍 | avg_volume_5d * 100 |
| 3 | dropna屠杀 | 数据大量丢失 | fillna容错 |
| 4 | 静态阈值3.0x过严 | 盘后过滤98%股票 | 动态时间衰减 |
| 5 | prev_close依赖缓存 | 缓存为空返回None | 用快照lastClose |
| 6 | _run_radar_main_loop同样问题 | 同上 | 用快照lastClose |
| 7 | 预热全部A股5191只 | 耗时74秒 | 只预热watchlist |

---

## 四、修复方案

### 4.2 已完成修复（最终版）
```python
# Bug #1: 字段名修复
'prev_close': tick.get('lastClose', 0)  # 原为preClose

# Bug #2: 量比单位修复
df['avg_volume_5d_gu'] = df['avg_volume_5d'] * 100
df['volume_ratio'] = df['estimated_full_day_volume'] / df['avg_volume_5d_gu']

# Bug #3: fillna容错
df['volume_ratio'] = df['volume_ratio'].fillna(1.0)
df['avg_amount_5d'] = df['avg_amount_5d'].fillna(0.0)

# Bug #4: 动态阈值
if minutes_passed >= 240:
    min_volume_multiplier = 1.5  # 盘后
elif minutes_passed >= 120:
    min_volume_multiplier = 2.0  # 午后
else:
    min_volume_multiplier = 3.0  # 早盘

# Bug #5, #6: 快照数据优先
pre_close = tick.get('lastClose', 0)  # 不依赖TrueDictionary缓存

# Bug #7: 删除多余预热逻辑
# _snapshot_filter中删除了_prev_close_cache预热
# 因为prev_close已从快照lastClose获取，无需预热
```

---

## 五、验证结果

### 修复前
```
_snapshot_filter: 74-102秒
粗筛池: 0只
```

### 修复后（commit 996a100）
```
_snapshot_filter: <1秒（删除多余预热逻辑）
粗筛池: 400+只

修复内容：
1. 删除_snapshot_filter中_prev_close_cache预热逻辑
2. prev_close直接从快照lastClose获取
3. 无需warmup调用，避免阻塞
```

---

## 六、架构教训

1. **快照数据优先使用**：快照包含lastClose，不依赖可能为空的缓存
2. **避免dropna屠杀**：缺失数据应fillna容错，保留股票
3. **预热范围控制**：只预热需要的股票，不要全市场预热
4. **动态阈值设计**：盘后量比回归，需降低阈值
5. **独立测试优先**：诊断问题应创建独立测试脚本，不污染生产代码

---

## 七、关键代码位置

| 文件 | 位置 | 功能 |
|------|------|------|
| `tasks/run_live_trading_engine.py:666-820` | `_snapshot_filter` | 粗筛核心逻辑 |
| `tasks/run_live_trading_engine.py:350-500` | `_auction_snapshot_filter` | 第一斩筛选 |
| `tasks/run_live_trading_engine.py:942-1120` | `_run_radar_main_loop` | 雷达循环 |
| `logic/data_providers/qmt_event_adapter.py:72-110` | `subscribe_ticks` | Tick订阅 |
| `logic/data_providers/true_dictionary.py:110-210` | `warmup` | 缓存预热 |

---

## 八、请示CTO

1. **确认修复方案**：以上7项Bug修复是否完整？
2. **删除全A股预热**：是否同意删除_snapshot_filter中的全A股预热逻辑？
3. **后续优化方向**：
   - 是否需要添加超时机制防止主线程阻塞？
   - 是否需要优化订阅策略（分批订阅）？

---

**报告完毕，请CTO指示下一步行动。**

---

*本报告由AI开发专家团队基于thinking-process-phase.txt深度分析生成*
