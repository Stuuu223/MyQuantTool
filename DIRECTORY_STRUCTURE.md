# MyQuantTool 目录结构规范 (渐进式重构)

## 目标
- 新文件按规范命名和存放
- 旧文件逐步迁移，不破坏现有功能
- 建立清晰的分类体系

## 新目录结构

```
MyQuantTool/
│
├── logic/                          # 核心业务逻辑 (保持不变)
│   ├── strategies/
│   │   ├── production/             # 【新建】实盘生产策略
│   │   │   ├── unified_warfare_core.py      # V18核心 (从根目录移入)
│   │   │   └── cross_day_relay_engine.py    # 跨日接力引擎
│   │   ├── research/               # 【新建】研究策略
│   │   │   └── (新研究脚本放这里)
│   │   └── archive/                # 【已有】归档策略
│   │
├── tasks/                          # 任务脚本
│   ├── production/                 # 【新建】实盘运行任务
│   │   ├── event_driven_monitor.py
│   │   └── full_market_scan.py
│   ├── backtest/                   # 【新建】回测任务
│   │   └── behavior_replay.py      # (原holographic_replay)
│   └── research/                   # 【新建】研究任务
│       └── breakout_analysis.py    # (原climax_scanner)
│
├── tools/                          # 工具脚本
│   ├── analysis/                   # 【新建】分析工具
│   │   ├── benchmark_extractor.py  # (原golden_benchmark)
│   │   └── volume_validator.py     # (原verify_daily_volume)
│   ├── data/                       # 【新建】数据工具
│   │   └── tick_processor.py
│   └── archive/                    # 【已有】归档工具
│       └── v1_deprecated/
│
└── docs/                           # 文档 (保持不变)
```

## 命名规范

### 1. 文件命名
```python
# ✅ 推荐
production/unified_warfare_core.py
research/breakout_scanner.py
analysis/benchmark_extractor.py

# ❌ 避免
unified_warfare_core_v18.py      # 无版本号
holographic_replay.py            # 无意义术语
wangsu_case.py                   # 无拼音
climax_scanner_v2.py             # 无版本号
```

### 2. 函数命名
```python
# ✅ 推荐
def analyze_breakout_momentum()
def calculate_turnover_ratio()
def validate_tick_integrity()

# ❌ 避免
def scan_day()                     # 太泛
def check()                        # 太简
def process()                      # 无意义
```

### 3. 类命名
```python
# ✅ 推荐
class UnifiedWarfareCore
class CrossDayRelayEngine
class BreakoutAnalyzer

# ❌ 避免
class V18Core                      # 带版本号
class Scanner                      # 太泛
```

## 迁移计划

### Phase 1: 建立新目录 (本次执行)
- 创建 production/, research/, analysis/ 目录
- 移动V18核心到新位置
- 建立兼容性导入

### Phase 2: 新文件规范 (后续执行)
- 所有新文件按规范命名
- 放入对应目录

### Phase 3: 旧文件迁移 (逐步执行)
- 旧文件添加弃用警告
- 创建转发导入
- 验证无影响后删除旧文件

## 兼容性保证

### 旧文件保留兼容性
```python
# 在旧文件中添加
import warnings
warnings.warn(
    "此模块已弃用，请使用 logic.strategies.production.unified_warfare_core",
    DeprecationWarning,
    stacklevel=2
)

# 转发导入
from logic.strategies.production.unified_warfare_core import (
    UnifiedWarfareCore as UnifiedWarfareCoreV18
)
```
