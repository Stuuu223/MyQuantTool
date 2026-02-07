# MyQuantTool 项目架构

## 系统概述

MyQuantTool 是一个基于资金流向分析的短线交易辅助系统，核心目标是在短线交易中避免被资金出货坑杀，同时捕捉资金有序进攻的标的。

## 核心架构

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                     应用层 (Application)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  事件驱动监控  │  │  UI展示界面   │  │  回测引擎     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      逻辑层 (Logic)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  决策树引擎    │  │  特征计算层    │  │  风险评分     │      │
│  │  (4关+3.5关)  │  │  (资金/情绪)  │  │  (综合评分)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      数据层 (Data)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  QMT实时数据  │  │  东方财富API  │  │  快照存储     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 核心模块详解

### 1. 决策树引擎 (full_market_scanner.py)

**职责**：实现买入决策树，对每只股票进行分类

**关键方法**：
- `_calculate_decision_tag()`: 决策树核心逻辑
- `_classify_candidates()`: 候选股票分类
- `_calculate_risk_score()`: 风险评分计算

**决策树关卡**：
```
第1关：ratio < 0.5% → PASS❌
第2关：ratio > 5% → TRAP❌
第3关：诱多 + 高风险 → BLOCK❌
第3.5关：3日连涨资金不跟 + ratio < 1% → TRAP❌
第4关：1-3% + 低风险 + 无诱多 → FOCUS✅
兜底：BLOCK❌
```

### 2. 特征计算层

#### 2.1 多日风险特征 (rolling_risk_features.py)

**职责**：计算多日资金流向和价格变化特征

**核心函数**：
```python
compute_multi_day_risk_features(code, trade_date, flow_records, price_3d_change)
```

**输出特征**：
- `is_price_up_3d_capital_not_follow`: 3日连涨但资金不跟
- `price_3d_change`: 3日价格涨幅
- `capital_3d_net_sum`: 3日资金净流入合计

#### 2.2 诱多陷阱检测 (trap_detector.py)

**职责**：检测诱多陷阱信号

**检测信号**：
- 长期流出+单日巨量
- 暴量*2 (连续两天暴量)
- 暴量*3 (连续三天暴量)
- 游资突袭
- 冲高回落

#### 2.3 资金性质分类 (capital_classifier.py)

**职责**：根据资金流向模式分类资金性质

**分类类型**：
- `HOTMONEY`: 游资（短期、波动大）
- `INSTITUTIONAL`: 机构（长期、稳定）
- `RETAIL`: 散户（接盘）
- `UNKNOWN`: 未知

### 3. 数据层

#### 3.1 快照存储 (cache_replay_provider.py)

**职责**：快照的保存和回放

**快照格式**：
```json
{
  "scan_time": "2026-02-06T09:45:21.390438",
  "mode": "intraday",
  "results": {
    "opportunities": [...],
    "watchlist": [...]
  }
}
```

**关键方法**：
- `save_snapshot()`: 保存快照
- `load_snapshot()`: 加载快照
- `list_snapshots()`: 列出所有快照

#### 3.2 股本数据 (data/equity_info_tushare.json)

**职责**：存储股票股本信息，用于计算ratio

**数据结构**：
```json
{
  "2026-02-06": {
    "601869.SH": {
      "total_share": 10000000000,
      "float_share": 5000000000,
      "circ_mv": 71015747138
    }
  }
}
```

## 数据流

### 实时扫描流程

```
1. QMT获取实时Tick数据
   ↓
2. full_market_scanner 初始化
   ↓
3. 对每只股票：
   - 获取资金流向数据 (flow_data)
   - 计算ratio = main_net_inflow / circ_mv * 100
   - 计算风险特征 (trap_signals, risk_features)
   - 计算风险评分 (risk_score)
   - 分类资金性质 (capital_type)
   ↓
4. 决策树判断 (_calculate_decision_tag)
   ↓
5. 生成快照 (save_snapshot)
```

### 回放流程

```
1. cache_replay_provider 加载快照
   ↓
2. 读取快照中的 results.opportunities
   ↓
3. 显示决策结果和原因
   ↓
4. 可选：与实际交易记录对比
```

## 模块依赖关系

```
full_market_scanner.py
├── trap_detector.py (诱多信号)
├── rolling_risk_features.py (多日特征)
├── capital_classifier.py (资金性质)
└── data_manager.py (数据获取)

cache_replay_provider.py
└── data/scan_results/*.json (快照文件)

run_event_driven_monitor.py
├── full_market_scanner.py
└── cache_replay_provider.py
```

## 开发规范

### 1. 添加新特征

**步骤**：
1. 在 `logic/` 下创建特征计算模块（如 `rolling_risk_features.py`）
2. 实现特征计算函数，返回字典形式
3. 在 `full_market_scanner.py` 的 `_classify_candidates()` 中调用
4. 将特征挂载到 `result['risk_features']`
5. 在决策树中使用特征

**示例**：
```python
# logic/rolling_risk_features.py
def compute_multi_day_risk_features(...) -> Dict:
    return {
        "is_price_up_3d_capital_not_follow": True,
        "price_3d_change": 3.5,
        "capital_3d_net_sum": -4200000.0
    }

# full_market_scanner.py
risk_features = compute_multi_day_risk_features(...)
result['risk_features'] = risk_features
decision_tag = self._calculate_decision_tag(
    ratio=ratio,
    risk_score=risk_score,
    trap_signals=trap_signals,
    is_price_up_3d_capital_not_follow=risk_features['is_price_up_3d_capital_not_follow']
)
```

### 2. 添加新关卡

**步骤**：
1. 在 `_calculate_decision_tag()` 中添加新的if条件
2. 确保关卡顺序正确（从严格到宽松）
3. 添加单元测试到 `tests/test_decision_tree_regression.py`
4. 运行测试确保不破坏现有逻辑

**示例**：
```python
def _calculate_decision_tag(self, ratio, risk_score, trap_signals, new_feature=False):
    # 第1关
    if ratio < 0.5:
        return "PASS❌"
    # 第2关
    if ratio > 5:
        return "TRAP❌"
    # 新关卡
    if new_feature and ratio < 1:
        return "NEW_TAG❌"
    # ...
```

### 3. 单元测试

**测试覆盖**：
- 每个关卡的边界条件
- 特征组合的各种情况
- 回归测试（确保不破坏现有逻辑）

**测试文件**：`tests/test_decision_tree_regression.py`

## 性能优化

### 1. 数据缓存
- 股本数据使用 Tushare 缓存
- 快照数据按时间点保存

### 2. 并发处理
- 使用多线程获取资金流向数据
- 批量处理股票数据

### 3. 增量更新
- 只更新变化的股票
- 避免重复计算

## 扩展方向

### 1. 卖出决策树
- 创建独立的卖出决策树模块
- 定义卖出触发条件
- 实现持仓管理

### 2. 回测引擎
- 模拟持仓
- 计算收益率、胜率
- 验证策略有效性

### 3. 历史数据重建
- 使用 Tushare 重建历史快照
- 长周期回测
- 策略优化

## 常见问题

### Q1: ratio 是怎么计算的？
```python
ratio = main_net_inflow / circ_mv * 100
```
- `main_net_inflow`: 主力净流入（元）
- `circ_mv`: 流通市值（元）
- 结果表示主力资金占流通市值的百分比

### Q2: 如何添加新的诱多信号？
在 `trap_detector.py` 中添加新的检测函数，然后在 `full_market_scanner.py` 中调用。

### Q3: 快照文件太大怎么办？
快照只保存必要的数据，不保存原始Tick数据。如果快照仍然太大，可以压缩存储。

### Q4: 如何调试决策树？
1. 查看 `temp_gate35_example.json` 了解快照结构
2. 使用 `--debug` 参数运行监控
3. 查看单元测试用例理解边界条件

## 联系方式

如有问题，请参考：
- TASK_PLAN.md：任务进度
- tests/test_decision_tree_regression.py：测试用例
- temp_gate35_example.json：快照示例