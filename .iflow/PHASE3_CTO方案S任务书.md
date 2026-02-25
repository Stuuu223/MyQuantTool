# Phase 3: CTO方案S执行令

## 核心任务

### 任务1: 剥离V18核心引擎
**文件**: `logic/strategies/v18_core_engine.py`
**要求**:
- 从TimeMachineEngine抽取V18双Ratio算分逻辑
- 封装为无状态数学计算算子
- 支持时间衰减Ratio (1.2/1.0/0.8/0.5)
- 从ConfigManager读取参数

### 任务2: 向量化热复盘引擎
**文件**: `logic/backtest/hot_replay_engine.py`
**要求**:
- 使用Pandas向量化计算
- 严禁Python For循环遍历Tick
- 使用cumsum()计算累计成交量
- 使用向量化公式计算动态量比
- 使用first_valid_index()定位起爆点

## 核心技术要求

### 向量化算法规范
```python
# ✅ CTO强制: 向量化计算
# 计算累计成交量
df['volume_cumsum'] = df['volume'].cumsum()

# 计算时间进度
df['time_progress'] = (df['timestamp'] - market_open).dt.total_seconds() / (4*3600)

# 向量化计算动态量比
df['dynamic_volume_ratio'] = df['volume_cumsum'] / (avg_volume_5d * df['time_progress'])

# 向量化定位起爆点
explosion_idx = df[df['dynamic_volume_ratio'] > threshold].first_valid_index()
```

### 禁止事项
- ❌ 严禁 `for tick in df.itertuples()` 遍历
- ❌ 严禁逐行计算量比
- ❌ 严禁污染TimeMachineEngine
- ❌ 严禁硬编码参数

### 必须对齐
- ✅ ConfigManager参数读取
- ✅ MetricDefinitions计算规范
- ✅ SanityGuards数据校验
- ✅ 实盘与回测代码同源

## 输出文件规划

```
logic/strategies/
└── v18_core_engine.py          # V18核心算子(新增)

logic/backtest/
├── hot_replay_engine.py         # 热复盘引擎(新增)
├── hot_replay_models.py         # 数据模型(新增)
└── algorithms/
    └── vectorized_detector.py   # 向量化检测器(新增)
```

## 验收标准

1. 性能指标: 全市场5191只股票Tick级扫描 < 3分钟
2. 算法正确性: 向量化计算结果与理论值一致
3. 参数对齐: 全部从ConfigManager读取
4. 零For循环: 代码中无逐行遍历DataFrame
5. 真实数据验证: 使用20260224数据实测

---
任务发布: AI项目总监
执行团队: AI开发专家团队
CTO拍板: 方案S
