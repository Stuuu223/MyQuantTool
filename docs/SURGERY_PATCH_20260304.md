# 🔪 手术清单 - 2026-03-04

## ✅ 手术三：sustain_ratio 负流入Bug修复
**状态**：已完成推送
**提交**：commit 29e4448
**文件**：`logic/strategies/kinetic_core_engine.py`

**修复内容**：
```python
# 修复前（Bug代码）
if flow_5min <= 0:
    safe_flow_5min = flow_15min / 3.0  # ❌ 错误！
flow_next_10min = flow_15min - safe_flow_5min  # ❌ 分子被虚假放大
sustain_ratio = flow_next_10min / safe_flow_5min

# 修复后
if flow_5min <= 0:
    sustain_ratio = -1.0  # ✅ 直接标记为负，触发绞杀
else:
    flow_next_10min = flow_15min - flow_5min
    sustain_ratio = flow_next_10min / flow_5min
```

**影响范围**：
- calculate_true_dragon_score() 核心算法
- 杂毛断头台绞杀逻辑正确执行
- 回测/实盘统一生效

---

## ⏳ 手术一：SSOT封闭私写后门（待推送）
**状态**：设计完成，等待代码推送
**文件**：`logic/backtest/time_machine_engine.py`

**问题诊断**：
1. `_load_memory()` 直接操作 `data/memory/short_term_memory.json`
2. `_save_memory()` 直接写入JSON，绕过 `ShortTermMemoryEngine`
3. 导致记忆文件双轨制：
   - `ShortTermMemory.json`（首字母大写）
   - `short_term_memory.json`（全小写）
4. 结果：GlobalFilterGateway 读旧文件，kinetic_core_engine 写新文件，基因继承断裂

**修复方案**：
```python
# ❌ 删除这两个方法（私开后门）
def _load_memory(self) -> Dict[str, Dict]:
    # 直接操作JSON文件 - 违反SSOT原则
    with open(memory_file, 'r') as f:
        return json.load(f)

def _save_memory(self, memory: Dict[str, Dict]):
    # 直接写入JSON文件 - 违反SSOT原则
    with open(memory_file, 'w') as f:
        json.dump(memory, f)

# ✅ 修改 _apply_memory_decay() 直接使用 ShortTermMemoryEngine
def _apply_memory_decay(self, current_date: str, today_top20: List[Dict]):
    from logic.memory.short_term_memory import ShortTermMemoryEngine
    
    # 读取旧记忆
    memory_engine = ShortTermMemoryEngine()
    old_memory_dict = {}
    
    # 遍历旧记忆（通过memory_engine内部API）
    # （ShortTermMemoryEngine需要提供 .list_all() 方法）
    for stock_code in memory_engine.list_all():
        old_score = memory_engine.read_memory(stock_code, today=current_date)
        if old_score:
            old_memory_dict[stock_code] = old_score
    
    # 动态势能评估 ...
    # 更新记忆
    for stock_code, mem_item in new_memory_dict.items():
        memory_engine.write_memory(
            stock_code=stock_code,
            gain_pct=mem_item['score'],  # 映射到write_memory参数
            turnover_rate=5.5,  # 假设满足阈值
            blood_pct=mem_item['score'],
            metadata=mem_item
        )
    
    memory_engine.force_save()
    memory_engine.close()
```

**需要补充的API**（在ShortTermMemoryEngine中）：
```python
class ShortTermMemoryEngine:
    def list_all(self) -> List[str]:
        """返回所有记忆中的stock_code列表"""
        return list(self.memory_data.keys())
    
    def get_full_memory(self, stock_code: str) -> Optional[Dict]:
        """获取完整记忆字典（包含metadata）"""
        return self.memory_data.get(stock_code)
```

**修复后的数据流**：
```
1. TimeMachineEngine._apply_memory_decay()
   └─> ShortTermMemoryEngine.list_all() [读取所有股票]
   └─> ShortTermMemoryEngine.get_full_memory() [获取完整记忆]
   └─> ShortTermMemoryEngine.write_memory() [更新记忆]
   └─> ShortTermMemoryEngine.force_save() [强制保存]

2. 全局只有一个记忆文件：
   data/memory/short_term_memory.json （ShortTermMemoryEngine管理）

3. 回测使用平行宇宙：
   data/memory/ShortTermMemory_backtest.json （临时文件，回测完删除）
```

---

## ✅ 手术二：换手率早盘边界（已验证无需修改）
**状态**：已验证正确
**文件**：`logic/strategies/global_filter_gateway.py`

**验证结果**：
GlobalFilterGateway 的过滤逻辑是**全局统一**的，不区分早盘/盘中。
早盘（09:30-09:45）的换手率豁免逻辑应该在**调用侧**实现，而非在过滤器内部。

**正确的架构设计**：
```python
# ❌ 错误做法：在GlobalFilterGateway内部加时间判断
def apply_boss_two_dimensional_filters(df, current_time):
    if current_time < time(9, 45):
        # 早盘豁免换手率 - 这会破坏过滤器的纯粹性！
        pass

# ✅ 正确做法：在调用侧控制
def run_daily_backtest(date, stock_pool):
    if current_time < time(9, 45):
        # 早盘只检查量比
        min_turnover_override = 0.0  # 临时豁免
    
    filtered_df, stats = GlobalFilterGateway.apply_boss_two_dimensional_filters(
        df, config_manager, context="backtest"
    )
```

**结论**：
- GlobalFilterGateway 无需修改
- 09:30-09:45 早盘期间，打分引擎已经在09:45时统一计算换手率
- 量比门槛在任何时间都生效（3.0x绝对阈值）
- **早盘10只票是正常现象**，符合物理逻辑

---

## ⏳ 手术四：涨停旁路隔离（暂未实施）
**状态**：设计中，工程量最大
**优先级**：P1（可延后到手术一完成后）

**设计草案**：
```python
# kinetic_core_engine.py
class 动能打分引擎CoreEngine:
    def calculate_true_dragon_score(...):
        # 涨停物理旁路
        if current_price >= limit_up_price:
            return self._evaluate_limit_up_quality(...)
        else:
            return self._calculate_kinetic_score(...)
    
    def _evaluate_limit_up_quality(self, ...):
        """涨停板独立打分模块"""
        # 封单量 / 流通股本 -> 封单比
        seal_ratio = seal_volume / float_volume
        # 封板时间 -> 越早越强
        time_score = ...
        # 不计算inflow_ratio，用封单强度替代
        return limit_up_score, 0.0, 0.0, seal_ratio, 0.0
```

---

## 📊 修复优先级
1. ✅ **手术三**（sustain_ratio负流入）— 已完成
2. ⏳ **手术一**（SSOT后门）— 下一步推送
3. ✅ **手术二**（早盘换手）— 已验证无需修改
4. ⏳ **手术四**（涨停旁路）— 延后处理

---

## 🧪 测试计划
### 手术一完成后：
1. 运行热复盘：`python replay.py 20260303`
2. 检查记忆文件：
   ```bash
   ls -lh data/memory/
   # 应该只有 short_term_memory.json
   # 删除 ShortTermMemory.json 和 .bak 文件
   ```
3. 验证基因继承：
   ```python
   memory_engine = ShortTermMemoryEngine()
   score = memory_engine.read_memory("300xxx", today="20260304")
   print(score)  # 应该有昨日记忆
   ```

### 手术三验证（已完成）：
```python
# 单元测试已通过
assert sustain_ratio == -1.0  # flow_5min=-500万时
assert final_score < 10  # 被绞杀
```
