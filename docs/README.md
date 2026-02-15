# MyQuantTool 文档导航

**版本**: V12.1.0  
**更新日期**: 2026-02-15

---

## 🔴 核心文档（必读，开发前强制阅读）

### 1. 核心知识库
**[KNOWLEDGE_BASE_V12_1_0.md](KNOWLEDGE_BASE_V12_1_0.md)**  
**价值**: ⭐⭐⭐⭐⭐  
**内容**: 数据源知识库、战法知识库、架构知识库、CTO裁决知识库、常见错误纠正  
**何时阅读**: 第一次接触项目时，必须通读

### 2. 核心架构
**[CORE_ARCHITECTURE.md](CORE_ARCHITECTURE.md)**  
**价值**: ⭐⭐⭐⭐⭐  
**内容**: 核心系统定位（FullMarketScanner + EventDrivenMonitor）、紧箍咒约束、常见错误  
**何时阅读**: 第一次修改核心代码前必读

### 3. 10条铁律
**[MyQuantTool-Architecture-Iron-Laws.md](MyQuantTool-Architecture-Iron-Laws.md)**  
**价值**: ⭐⭐⭐⭐⭐  
**内容**: Tick优先、事件驱动、三把斧完整、板块共振、数据抽象层等10条铁律  
**何时阅读**: 每次开发前快速浏览

---

## 🟡 参考文档（按需查阅）

### 4. CLI使用指南
**[CLI_USAGE.md](CLI_USAGE.md)**  
**价值**: ⭐⭐⭐  
**内容**: Rich CLI监控终端使用方法  
**何时阅读**: 使用CLI监控时

### 5. 回测指南
**[BACKTEST_V2_GUIDE.md](BACKTEST_V2_GUIDE.md)**  
**价值**: ⭐⭐⭐  
**内容**: 回测引擎使用方法  
**何时阅读**: 进行回测时

### 6. 动态阈值
**[DYNAMIC_THRESHOLD_USAGE.md](DYNAMIC_THRESHOLD_USAGE.md)**  
**价值**: ⭐⭐⭐  
**内容**: 动态阈值管理器使用方法  
**何时阅读**: 使用动态阈值时

### 7. 监控系统
**[MONITOR_SYSTEM_GUIDE.md](MONITOR_SYSTEM_GUIDE.md)**  
**价值**: ⭐⭐⭐⭐  
**内容**: 监控系统详细使用指南  
**何时阅读**: 配置监控系统时

### 8. 命名规范
**[NAMING_CONVENTIONS.md](NAMING_CONVENTIONS.md)**  
**价值**: ⭐⭐⭐  
**内容**: 代码命名规范  
**何时阅读**: 新增代码时

---

## ⚪ 设置文档（首次部署）

### 9. QMT配置
**[QMT_SETUP_GUIDE.md](QMT_SETUP_GUIDE.md)**  
**价值**: ⭐⭐⭐⭐⭐  
**内容**: QMT券商版配置、Level-2试用配置  
**何时阅读**: 首次部署系统时

---

## 🚨 常见问题

### Q1: pytest测试失败怎么办？
**A**: pytest测试失败是因为测试逻辑问题，不是导入问题。QMT外部依赖需要mock才能运行pytest。

### Q2: 如何运行系统？
**A**: 
```bash
# 启动事件驱动监控（推荐）
python main.py monitor

# 启动Rich CLI监控终端
python main.py cli-monitor
```

### Q3: QMT连接失败？
**A**: 查看 [QMT_SETUP_GUIDE.md](QMT_SETUP_GUIDE.md)

### Q4: 数据单位错误？
**A**: 查看 [KNOWLEDGE_BASE_V12_1_0.md#数据源知识库](KNOWLEDGE_BASE_V12_1_0.md)

---

## 📊 文档统计

| 类型 | 数量 | 总大小 |
|------|------|--------|
| 核心文档 | 3 | ~60KB |
| 参考文档 | 5 | ~70KB |
| 设置文档 | 1 | ~21KB |

---

**最后强调**: 核心文档（前3个）必须通读，其他文档按需查阅。