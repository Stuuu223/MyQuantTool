# MyQuantTool 回测体系 V2 统一方案

## 1. 架构概览

### 1.1 四层架构
```
backtest/                    # 回测作业模板层
├── run_t1_backtest.py       # T+1回测作业
├── run_tick_replay_backtest.py # Tick回放回测作业  
├── run_comprehensive_backtest.py # 综合策略回测作业
├── run_signal_density_scan.py # 信号密度扫描作业
├── run_param_heatmap_analysis.py # 参数热力图分析作业
└── ...

logic/strategies/           # 策略逻辑层
├── halfway_core.py          # Halfway统一战法定义
├── tick_strategy_interface.py # Tick策略接口
├── halfway_tick_strategy.py # Tick版Halfway策略
├── tick_strategy_adapter.py # Tick策略适配器
├── backtest_engine.py       # 统一回测引擎
└── ...

tools/                     # 工具脚本层
├── run_tick_backtest.py     # Tick回测统一入口（调用backtestengine）
├── check_qmt_data.py        # QMT数据检查工具
├── fetch_1m_data.py         # 1分钟数据获取工具
└── ...

tasks/                     # 任务脚本层
└── ...
```

### 1.2 角色定义

**策略逻辑层 (logic/strategies/)**
- 包含纯策略逻辑，无I/O操作
- 所有策略必须通过统一接口实现
- 核心战法逻辑在`halfway_core.py`等文件中定义

**回测引擎层 (logic/strategies/backtest_engine.py)**
- 统一的回测执行引擎
- 处理资金管理、持仓、风险控制等
- Tick策略通过适配器接入

**作业模板层 (backtest/)**
- 具体的回测作业实现
- 调用统一回测引擎执行特定回测任务
- 生成标准化的回测结果

**工具层 (tools/)**
- 日常运维和单次任务工具
- 不包含回测逻辑，只提供辅助功能

## 2. 策略统一方案

### 2.1 半路战法定于统一
为避免同一战法在多处实现，建立统一的Halfway核心定义：

```python
# logic/strategies/halfway_core.py
def evaluate_halfway_state(prices, volumes, current_time, current_price, params):
    """统一的Halfway战法评估函数"""
    # 实现统一的Halfway逻辑
    pass
```

**使用场景：**
- `HalfwayEventDetector` - 实时检测使用
- `HalfwayTickStrategy` - Tick回测使用  
- `backtest/*.py` - 各测中硬编码逻辑迁移至此

### 2.2 Tick策略接口标准化
```python
# logic/strategies/tick_strategy_interface.py
class ITickStrategy(Protocol):
    def on_tick(self, tick: TickData) -> List[Signal]: ...
```

## 3. 回测引擎集成

### 3.1 Tick策略适配器
```python
# logic/strategies/tick_strategy_adapter.py
class TickStrategyAdapter:
    """将ITickStrategy适配到backtestengine接口"""
```

### 3.2 数据提供器
```python
class TickDataFeed:
    """为backtestengine提供Tick数据流"""
```

## 4. 文件职责规范

### 4.1 logic/ - 纯逻辑模块
- ✅ 策略实现、数据提供器、回测引擎
- ❌ 不允许 `if __name__ == "__main__":`，不允许I/O操作

### 4.2 backtest/ - 回测作业模板
- ✅ 标准回测作业：`run_t1_backtest.py`、`run_tick_replay_backtest.py`
- ✅ 所有回测走统一的`backtestengine`
- ❌ 不允许再写自制小引擎

### 4.3 tools/ - 工具脚本
- ✅ 日常运维/单次任务：数据下载、环境检查等
- ❌ 不允许放新的回测逻辑

### 4.4 tasks/ - 计划任务
- ✅ cron/Windows计划任务入口
- ✅ 业务流程导向

## 5. 已废弃文件

以下旧脚本已废弃，不再维护：
- `tools/signal_density_scanner.py` → 功能迁移到 `backtest/run_signal_density_scan.py`
- `tools/param_heatmap_analyzer.py` → 功能迁移到 `backtest/run_param_heatmap_analysis.py`
- `tools/halfway_sample_validator.py` → 功能整合到其他作业脚本

## 6. 迀续开发指南

### 6.1 新策略开发流程
1. 在 `logic/strategies/` 中实现策略接口
2. 如需要，更新 `halfway_core.py` 统一战法定义
3. 在 `backtest/` 中创建新的作业脚本
4. 使用统一 `backtestengine` 运行

### 6.2 回测任务开发流程
1. 在 `backtest/` 中创建作业脚本
2. 调用统一的 `backtestengine`
3. 生成标准化结果输出
4. 避免编写独立的回测引擎