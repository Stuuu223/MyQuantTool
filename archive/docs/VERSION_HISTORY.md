# MyQuantTool 版本历史

**最后更新**: 2026-02-02

---

## V9.4.5 (2026-02-02)

### 新增功能
- 新增 `capital_classifier.py` 模块：资金性质分类器
- 新增 `temp/` 目录：用于存放临时文件
- 新增 `scripts/weekly_check_reminder.py`：每周优化检查提醒脚本
- 新增 `weekly_check.bat`：快速启动每周检查
- 新增 `docs/dev/OPTIMIZATION_TODO.md`：持续优化清单

### 优化改进
- 项目结构重组：tools/、tasks/、config/ 目录分类
- 文档分类整理：docs/{user-guide,setup,tech,dev}/
- 修复导入路径错误：logic/dragon_tactics.py 和 logic/signal_generator.py 添加 Any 到 typing 导入
- 修复 stock_ai_tool.py 硬编码路径问题，使用相对路径

### 文档更新
- 新增 `PROJECT_STRUCTURE.md`：项目结构说明文档
- 新增 `.iflow/SYSTEM_PROMPT.md`：AI 助手规范和操作指南
- 更新 `docs/user-guide/startup_guide.md`：修复文档引用路径
- 删除 36 个冗余文件（测试文件、启动脚本、老旧文档）

### Bug 修复
- 修复 logic/dragon_tactics.py 缺少 Any 类型导入
- 修复 logic/signal_generator.py 缺少 Any 类型导入
- 修复 tools/stock_ai_tool.py 硬编码路径问题

---

## V9.4.0 - V9.4.4 (2026-01-15 至 2026-01-28)

### V9.4.4 (2026-01-28)
- 修复超时机制：使用线程超时替代 socket 超时（Windows 兼容）

### V9.4.3 (2026-01-25)
- 修复模块导入卡死问题：移除全局 import akshare
- 所有 akshare 调用添加 10 秒超时限制

### V9.4.2 (2026-01-22)
- 优化 UI 性能：解决主线程阻塞问题
- 使用 @st.cache_resource(ttl=300) 缓存数据

### V9.4.1 (2026-01-20)
- 修复数据清洗逻辑中的严重错误
- 修复炸板率计算

### V9.4.0 (2026-01-15)
- 新增诱多陷阱检测器 (TrapDetector)
- 新增滚动指标计算 (RollingMetricsCalculator)
- 新增资金分类器 (CapitalClassifier)
- 新增风险评估系统

---

## V9.3.0 - V9.3.6 (2025-12-10 至 2025-12-25)

### V9.3.6 (2025-12-25)
- 优化涨跌停计算：添加停牌股过滤 + 精确涨停价计算

### V9.3.5 (2025-12-22)
- 修复行业信息映射：使用板块代码而非股票代码

### V9.3.4 (2025-12-20)
- 修复市场情绪标签页：使用加权平均替代 calculate_composite_index 方法

### V9.3.3 (2025-12-18)
- 修复涨跌停计算：使用 Easyquotation 实时数据 + AkShare 行业信息

### V9.3.2 (2025-12-15)
- 修复更多缺失模块和类型错误
- 从 archived 恢复 UI 模块和 Logic 模块

### V9.3.1 (2025-12-12)
- 修复缺失模块：从 archived 恢复 algo_math/algo_advanced/algo_sentiment/algo_capital

### V9.3.0 (2025-12-10)
- 项目从 V9.4.x 回退到 V9.3 版本

---

## V9.2.0 (2025-11-20)

### 新增功能
- 引入竞价快照系统
- Redis 支持竞价数据保存和恢复
- 新增竞价快照管理器

---

## V9.0.0 - V9.1.0 (2025-10-01 至 2025-11-10)

### V9.1.0 (2025-11-10)
- 新增历史复盘功能
- 新增数据清洗模块

### V9.0.0 (2025-10-01)
- 项目初始化
- 基础数据采集功能
- 技术指标计算
- 资金流向分析

---

## 版本命名规范

### 格式
- `V[主版本].[次版本].[修订号]`

### 规则
- **主版本**：重大架构变更、不兼容更新
- **次版本**：新增功能、重要改进
- **修订号**：Bug 修复、小改进

---

## Git Commit 规范

### 格式
```
[类型] 简短描述
```

### 类型
- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 重构
- `docs`: 文档更新
- `perf`: 性能优化
- `test`: 测试相关

### 示例
```
feat: 新增诱多陷阱检测器
fix: 修复QMT连接超时问题
docs: 更新API文档和使用示例
```

---

**维护者**: MyQuantTool 团队