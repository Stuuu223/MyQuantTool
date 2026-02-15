# MyQuantTool - 小资金右侧起爆点量化交易系统

**版本**: V12.1.0  
**核心定位**: Windows本地化私有交易工具（Python 3.10 + QMT）  
**战法**: 半路战法 + 龙头战法 + 三把斧风控

---

## ⚡ 5分钟快速开始

### 1. 核心系统（心脏+大脑）
- 🫀 **心脏**: `logic/strategies/full_market_scanner.py` - 三漏斗扫描器
- 🧠 **大脑**: `tasks/run_event_driven_monitor.py` - 事件驱动监控

### 2. 启动命令
```bash
# 启动事件驱动监控（推荐）
python main.py monitor

# 启动Rich CLI监控终端
python main.py cli-monitor
```

### 3. 文档导航
- 🔴 **核心文档（开发前必读）**:
  - [docs/KNOWLEDGE_BASE_V12_1_0.md](docs/KNOWLEDGE_BASE_V12_1_0.md) - 数据源/战法/CTO裁决
  - [docs/CORE_ARCHITECTURE.md](docs/CORE_ARCHITECTURE.md) - 核心系统定位
  - [docs/MyQuantTool-Architecture-Iron-Laws.md](docs/MyQuantTool-Architecture-Iron-Laws.md) - 10条铁律

---

## 🧪 pytest测试说明

### 测试环境
- ✅ **虚拟环境已激活**: `E:\MyQuantTool\venv_qmt\Scripts\python.exe`
- ✅ **xtquant已安装**: `from xtquant import xtdata` 成功
- ✅ **导入正常**: 核心模块导入无问题

### pytest测试问题
**注意**: pytest测试失败是因为测试逻辑问题，不是导入问题或虚拟环境问题。

**原因**:
- QMT外部依赖（xtdata）需要QMT客户端运行时
- pytest测试需要mock QMT外部依赖才能运行
- 这不是虚拟环境问题，而是QMT外部依赖设计

**解决方案**:
- 实盘测试：直接运行系统，无需pytest
- pytest测试：需要创建QMT mock配置（待开发）

---

## 📂 文档状态

### V15清理成果
- ✅ **删除**: 10个过时文档
- ✅ **保留**: 8个核心文档
- ✅ **提取**: 10个精华snippets到docs/core_snippets/
- ✅ **重命名**: 中文文件名 → 英文文件名
- ✅ **新增**: 根目录README.md + docs/README.md

### 当前文档结构
```
docs/
├── README.md                      # 文档导航（新增）
├── KNOWLEDGE_BASE_V12_1_0.md      # 核心知识库
├── CORE_ARCHITECTURE.md           # 核心架构
├── MONITOR_SYSTEM_GUIDE.md        # 监控系统（重命名）
├── CLI_USAGE.md                   # CLI使用
├── BACKTEST_V2_GUIDE.md           # 回测指南
├── DYNAMIC_THRESHOLD_USAGE.md     # 动态阈值
├── NAMING_CONVENTIONS.md          # 命名规范
├── core_snippets/                 # 精华快照（10个文件）
└── setup/
    └── QMT配置指南.md              # QMT配置
```

---

## 🚨 10条铁律（禁止碰）

1. **Tick优先**：禁用分钟K（3秒 vs 60秒）
2. **事件驱动**：禁止固定间隔扫描
3. **三把斧完整**：防守斧+时机斧+资金斧，缺一不可
4. **板块共振**：Leaders≥3, Breadth≥35%，否则降级观察池
5. **数据抽象层**：策略层永远不直接调用QMT API
6. **ratio决策**：买入决策必须基于 ratio = 主力净流入 / 流通市值
7. **预测优先**：顽主杯是训练集，不是信号源
8. **Level-2可选**：Level-1推断足够，Level-2是性能优化
9. **状态指纹**：只有状态变化才保存快照
10. **实时为真**：回测跟着实时对齐，不是反过来

---

## 📁 项目架构

```
MyQuantTool/
├── logic/                    # 核心业务逻辑
│   ├── strategies/
│   │   ├── full_market_scanner.py   # 🫀 三漏斗扫描器（心脏）
│   │   ├── triple_funnel_scanner.py # 三把斧体系
│   │   └── trap_detector.py         # 诱多陷阱检测器
│   ├── data_providers/           # 数据抽象层（Level2→Level1→DongCai）
│   │   ├── level2_provider.py      # Level-2逐笔（试用）
│   │   ├── level1_provider.py      # Level-1推断
│   │   └── qmt_manager.py          # QMT管理器
│   └── core/                     # 核心工具
│       ├── failsafe.py           # Fail-Safe机制
│       └── rate_limiter.py        # 速率限制
├── tasks/                    # 任务调度
│   └── run_event_driven_monitor.py  # 🧠 事件驱动监控（大脑）
├── tools/                    # 便捷工具
│   └── cli_monitor.py       # Rich CLI监控终端
├── data/                     # 数据存储
│   └── qmt_data/             # QMT官方数据（38GB，不可删）
└── docs/                     # 文档
    ├── README.md            # 文档导航
    └── KNOWLEDGE_BASE_V12_1_0.md  # 核心知识库
```

---

## 🔧 开发规范

### 修改代码前三问
1. ❓ 我的修改是否影响 `FullMarketScanner`？
2. ❓ 我的修改是否影响 `EventDrivenMonitor`？
3. ❓ 我能否在实时环境里复现这个问题/效果？

### 紧箍咒
> "如果三句话里没有提到 `run_event_driven_monitor.py` 或 `FullMarketScanner`，默认视为没对齐核心系统。"

---

## 📞 紧急救火文档

- **QMT连接失败**: [docs/setup/QMT配置指南.md](docs/setup/QMT配置指南.md)
- **数据单位错误**: [docs/KNOWLEDGE_BASE_V12_1_0.md#数据源知识库](docs/KNOWLEDGE_BASE_V12_1_0.md)
- **诱多识别失败**: [docs/KNOWLEDGE_BASE_V12_1_0.md#战法知识库](docs/KNOWLEDGE_BASE_V12_1_0.md)
- **常见错误纠正**: [docs/KNOWLEDGE_BASE_V12_1_0.md#常见错误纠正](docs/KNOWLEDGE_BASE_V12_1_0.md)

---

## 📊 数据源架构

```
Level-2（试用，逐笔/队列）
    ↓
Level-1（Tick推断，50ms）
    ↓
AkShare T+1（资金流）
```

**核心铁律**：策略层必须永远不直接连接数据源，必须通过抽象层

---

## 📝 开发环境

- **Python**: 3.10+
- **OS**: Windows 10/11
- **QMT**: 券商版（Level-1免费，Level-2试用）
- **虚拟环境**: `venv_qmt`

**安装依赖**:
```bash
python -m venv venv_qmt
venv_qmt\Scripts\activate
pip install -r requirements.txt
```

---

## 🎯 核心战法

### 半路战法（Halfway）
- 右侧起爆点捕捉
- 平台突破 + 分时形态 + 资金流确认

### 龙头战法（Leader）
- 板块龙头识别
- 龙头特征 + 板块共振

### 时机斧（Timing）
- 板块共振检测
- 情绪周期判断

---

## 📈 交易目标

- **单只股票**: 30%-50%收益
- **月度账户**: 30%-50%目标
- **止损**: -5%硬止损，动态基于资金流
- **止盈**: 动态基于信号（主力流出、上升动能丧失）

---

**最后强调**：所有东西最终要喂给 `FullMarketScanner` 和事件驱动监控。回测只是验货，不是主角。