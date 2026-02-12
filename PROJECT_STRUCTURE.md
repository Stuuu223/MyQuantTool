# MyQuantTool 项目结构说明

> **版本**: V11.2.0
> **创建日期**: 2026-02-02
> **最后更新**: 2026-02-12
> **定位**: 项目结构说明（文件组织）
> **相关文档**:
>   - `Q_AND_A_ALIGNMENT.md` - 核心策略文档（三大战法 + Q&A对齐）
>   - `CLI_USAGE.md` - 使用指南（命令行操作 + Rich CLI）
>   - `PROJECT_ARCHITECTURE.md` - 技术架构文档（系统设计）

---

## 📁 项目根目录

### 核心文件
- `main.py` - 主程序入口
- `start_app.py` - 应用启动脚本
- `start_event_driven_monitor.bat` - 事件驱动监控启动脚本
- `qmt_auction_monitor.py` - QMT 竞价监控主程序
- `CLI_USAGE.md` - 命令行使用指南
- `PROJECT_ARCHITECTURE.md` - 技术架构文档
- `Q_AND_A_ALIGNMENT.md` - 核心策略文档

### 配置文件
- `pytest.ini` - 测试配置
- `requirements.txt` - Python 依赖列表
- `my_quant_cache.sqlite` - 缓存数据库

### 安装工具
- `install_dependencies.bat` - 依赖安装脚本
- `pip.bat` - pip 工具快捷方式

---

## 📂 tools/ - 工具目录

### 核心监控工具（V11.2.0 核心）
- `cli_monitor.py` - Rich CLI 监控终端（零延迟、轻量级、事件驱动）
- `run_event_driven_monitor.py` - 事件驱动监控脚本

### 数据获取工具
- `fetch_1m_data.py` - 分钟 K 线数据获取器
- `download_from_list.py` - 从股票列表下载 QMT 数据
- `download_real_batch_1m.py` - 批量下载（Tushare Pro 集成）
- `get_hot_stocks_v2.py` - 热股选择器 V2（防封增强版）

### 个股分析工具
- `comprehensive_stock_tool.py` - 综合分析工具（AkShare + QMT）
- `enhanced_stock_analyzer.py` - 增强分析器（技术指标 + 诱多检测）
- `stock_analyzer.py` - 统一股票分析器（自动场景检测）
- `intraday_decision.py` - 盘中决策工具（买入/卖出/等待）

### 回测工具
- `run_backtest_1m_v2.py` - 回测引擎 V2（修复幸存者偏差）
- `run_backtest_1m.py` - 基础回测工具

### 验证工具
- `verify_t1_performance.py` - T+1 性能验证
- `check_qmt_environment.py` - QMT 环境检查器

### 维护工具
- `archive_daily_logs.py` - 自动归档日志
- `daily_update.py` - 每日数据更新脚本
- `generate_concept_map.py` - 生成概念映射表

**使用方式**:
```bash
# 启动 CLI 监控终端
python tools/cli_monitor.py

# 个股分析
python tools/comprehensive_stock_tool.py 002514.SZ

# 回测
python tools/run_backtest_1m_v2.py
```

---

## 📂 tasks/ - 任务/运行目录

### 运行任务
- `run_dashboard.py` - 运行主仪表板
- `run_dashboard_home.py` - 运行主页仪表板
- `run_pre_market_warmup.py` - 盘前预热任务
- `run_scan_v19_final.py` - 运行扫描任务（V19版）

**使用方式**:
```bash
python tasks/run_dashboard.py
python tasks/run_scan_v19_final.py
```

---

## 📂 scripts/ - 脚本目录

### 维护脚本
- `clean_project.py` - 项目清理脚本
- `daily_update.py` - 每日更新脚本
- `generate_concept_map.py` - 生成概念映射
- `init_qmt.py` - QMT 初始化脚本
- `streamlit_fixer.py` - Streamlit 修复脚本

**使用方式**:
```bash
python scripts/clean_project.py
python scripts/init_qmt.py
```

---

## 📂 config/ - 配置目录

### 配置文件
- `config.json` - 主配置文件
- `config_system.py` - 系统配置类
- `config_database.json` - 数据库配置
- `balanced_monitor_list.json` - 平衡监控列表
- `monitor_list.json` - 监控列表

**使用方式**:
```python
from config.config_system import Config
config = Config()
```

---

## 📂 logic/ - 核心逻辑目录

### 三把斧体系（V11.2.0 核心）
- `triple_funnel.py` - 三把斧体系主模块（三大战法核心逻辑）
- `defense_axe.py` - 防守斧（四层拦截）
- `qualification_axe.py` - 资格斧（场景分类）
- `timing_axe.py` - 时机斧（板块共振）

### 数据抽象层（V11.2.0 新增）
- `data_provider_factory.py` - 数据提供者工厂
- `data_provider/base.py` - 数据提供者接口（ICapitalFlowProvider）
- `data_provider/level2_provider.py` - Level2 数据提供者
- `data_provider/level1_provider.py` - Level1 数据提供者（QMT Tick 推断）
- `data_provider/dongcai_provider.py` - 东方财富数据提供者（T-1 历史）

### 事件检测系统
- `event_detector.py` - 事件检测器基类
- `dip_buy_event_detector.py` - 黄金坑买入点检测
- `leader_event_detector.py` - 龙头加速检测
- `late_trading_scanner.py` - 尾盘急拉检测
- `halfway_event_detector.py` - 半路事件检测
- `intraday_turnaround_detector.py` - 倒V反转检测

### 核心算法模块
- `algo*.py` - 算法模块（基础算法、高级算法、资金流向算法等）
- `trap_detector.py` - 诱多陷阱检测器
- `capital_classifier.py` - 资金性质分类器
- `rolling_risk_features.py` - 多日风险特征计算

### 数据模块
- `data_*.py` - 数据管理（采集、清洗、健康监控等）
- `data_adapter*.py` - 数据适配器（支持多数据源）
- `database_manager.py` - 数据库管理
- `cache_manager.py` - 缓存管理
- `cache_replay_provider.py` - 快照回放提供者

### 资金流向分析
- `fund_flow_*.py` - 资金流向分析（收集器、分析器、调度器）
- `sector_resonance.py` - 板块共振计算器

### 市场分析
- `market_*.py` - 市场分析（市场情绪、市场状态、市场周期等）

### QMT 模块
- `qmt_*.py` - QMT 数据提供（历史数据、Tick数据）
- `code_converter.py` - 代码转换器

### 策略模块
- `strategy_*.py` - 策略库（策略工厂、策略比较、投资组合优化等）

### 回测引擎
- `backtest_engine.py` - 回测引擎 V2（修复幸存者偏差）
- `backtest_framework.py` - 回测框架

### 风控模块
- `risk_control.py` - 风控管理器
- `iron_rule_*.py` - 铁律系统

### UI 辅助模块
- `monitor.py` - 监控模块
- `logger.py` - 日志模块
- `error_handler.py` - 错误处理
- `rate_limiter.py` - 速率限制器

---

## 📂 ui/ - UI 目录

### Streamlit 页面
- `main_dashboard.py` - 主仪表板
- `dashboard_home.py` - 主页仪表板
- `single_stock.py` - 个股分析页面
- `historical_replay.py` - 历史复盘页面
- `capital*.py` - 资金分析相关页面
- `dragon_strategy.py` - 龙头战法页面
- `limit_up*.py` - 涨停板分析页面
- `backtest.py` - 回测页面
- `strategy_*_tab.py` - 策略相关标签页

**使用方式**:
```bash
streamlit run ui/main_dashboard.py
streamlit run ui/single_stock.py
```

---

## 📂 data/ - 数据目录

### 核心数据文件
- `monitor_state.json` - 监控状态文件（1秒刷新）
- `stock_sector_map.json` - 股票板块映射（申万行业，5552只股票）
- `equity_info.json` - 股本信息数据
- `stock_names.json` - 股票名称映射

### 数据目录
- `scan_results/` - 扫描结果目录（按时间点存储）
- `kline_cache/` - K线缓存
- `minute_data/` - 分钟 K 线数据
- `minute_data_hot/` - 热股分钟数据
- `rebuild_snapshots/` - 历史快照重建目录
- `decision_logs/` - 决策日志
- `review_cases/` - 复盘案例
- `tracking/` - 跟踪数据

### 事件记录
- `event_records.csv` - 事件记录 CSV
- `event_records.xlsx` - 事件记录 Excel
- `test_event_records.csv` - 测试事件记录

### 其他数据
- `execution_record.json` - 执行记录
- `scheduled_alerts.json` - 定时任务告警
- `my_quant_cache.sqlite` - SQLite 缓存数据库

---

## 📂 docs/ - 文档目录

### 📖 user-guide/ - 用户指南
- `README_快速开始.md` - 快速开始指南
- `新手使用指南.md` - 新手入门
- `startup_guide.md` - 启动指南
- `个股分析工具使用指南.md` - 个股分析工具使用指南（V9.4.5 新增）
- `QMT使用说明.md` - QMT 使用说明

### ⚙️ setup/ - 安装配置
- `redis_setup_guide.md` - Redis 设置指南
- `qmt_setup_guide.md` - QMT 环境配置指南
- `QMT环境配置指南-Python310.md` - QMT Python 3.10 配置
- `qmt_module_installation.md` - QMT 模块安装文档
- `QMT模块安装问题解决方案.md` - QMT 模块安装问题解决
- `database_guide.md` - 数据库指南

### 🔬 tech/ - 技术文档
- `数据源架构设计文档.md` - 数据源架构设计
- `速率限制说明.md` - 速率限制说明
- `indicators_explanation.md` - 指标说明
- `auto_maintenance_setup.md` - 自动维护设置

### 🚀 dev/ - 开发规划
- `MyQuantTool_Optimization_Plan.md` - 优化方案（V9.4.5）

---

## 📂 tests/ - 测试目录

### 测试文件
- 单元测试文件
- 集成测试文件
- 测试配置（`pytest.ini` 在根目录）

---

## 📂 models/ - 模型目录

### 机器学习模型
- 训练好的模型文件
- 模型配置文件

---

## 📂 logs/ - 日志目录

### 日志文件
- 应用运行日志
- 错误日志
- 性能日志

---

## 📂 easyquotation/ - EasyQuotation 目录

### 实时数据源
- EasyQuotation 实时行情数据接口
- 支持沪深两市实时数据

---

## 📂 xtquant/ - QMT XTQuant 目录

### QMT 数据源
- QMT XTQuant 模块
- 支持历史数据、Tick数据、订单数据

---

## 📂 venv_qmt/ - QMT 虚拟环境

### Python 虚拟环境
- QMT 专用的 Python 3.10 虚拟环境
- 包含 QMT 相关依赖

---

## 📂 .streamlit/ - Streamlit 配置

### Streamlit 配置
- Streamlit 全局配置文件
- 主题配置、页面设置等

---

## 📂 __pycache__/ - Python 缓存

### Python 字节码缓存
- Python 编译的字节码缓存文件
- 自动生成，可删除

---

## 🔧 命名规范

### 文件命名
- 工具类：`*_tool.py` 或 `*_analyzer.py`
- 任务类：`run_*.py`
- 脚本类：动词开头（clean、generate、init）
- 策略类：`strategy_*.py`
- UI 类：页面名称（如 `dashboard_home.py`）

### 目录命名
- 小写字母，使用下划线分隔
- 复数形式（如 `tools/`, `scripts/`, `tasks/`）

---

## 📊 目录统计

| 目录 | 文件数 | 用途 |
|------|--------|------|
| 根目录 | 15+ | 核心配置和启动文件 |
| tools/ | 30+ | 工具和分析模块（含 Rich CLI 监控终端） |
| tasks/ | 4+ | 运行任务和定时任务 |
| scripts/ | 45+ | 维护和初始化脚本 |
| config/ | 12+ | 配置文件 |
| logic/ | 200+ | 核心逻辑模块（含三把斧体系、数据抽象层） |
| ui/ | 70+ | Streamlit UI 页面 |
| docs/ | 20+ | 文档文件（分4个子目录） |
| tests/ | - | 测试文件 |
| logs/ | - | 日志文件 |
| data/ | - | 数据文件（含监控状态、快照等） |
| data_sources/ | 1+ | 数据源模块 |
| easyquotation/ | - | 实时数据源 |
| xtquant/ | - | QMT 数据源 |
| venv_qmt/ | - | QMT 虚拟环境 |

**总计**: 400+ 文件

---

## 🚀 快速开始

### 1. 启动 Rich CLI 监控终端（推荐）
```bash
# 启动 CLI 监控终端（零延迟、轻量级、事件驱动）
python tools/cli_monitor.py

# 使用 bat 文件启动
start_event_driven_monitor.bat
```

### 2. 启动 UI 应用
```bash
# 启动 Streamlit UI
streamlit run ui/main_dashboard.py

# 或使用启动脚本
start.bat
```

### 3. 运行分析工具
```python
# 使用综合分析工具
from tools.comprehensive_stock_tool import comprehensive_stock_analysis
result = comprehensive_stock_analysis('002514.SZ')

# 使用统一分析器
from tools.stock_analyzer import analyze_stock
result = analyze_stock('002514.SZ')
```

### 4. 运行回测
```bash
# 运行回测引擎 V2（修复幸存者偏差）
python tools/run_backtest_1m_v2.py
```

### 5. 运行脚本
```bash
# 初始化 QMT
python scripts/init_qmt.py

# 每日数据更新
python scripts/daily_update.py

# 生成概念映射
python scripts/generate_concept_map.py
```

---

## 📝 更新日志

### V11.2.0 (2026-02-12)
- ✨ **三把斧体系**：防守斧、资格斧、时机斧（三大战法核心逻辑）
- ✨ **Rich CLI 监控终端**：零延迟、轻量级、事件驱动（1秒刷新）
- ✨ **数据抽象层**：Level2→Level1→DongCai 自动降级
- ✨ **事件驱动监控**：实时事件触发扫描和响应
- ✨ **信号记录系统**：4表结构追踪交易绩效
- ✨ **回测引擎 V2**：修复幸存者偏差
- ✨ **QMT Tick 推断逻辑**：从 Tick 数据推断资金流向
- ✨ **板块共振计算**：Leaders ≥ 3 + Breadth ≥ 35%
- ✨ **文档对齐**：Q_AND_A_ALIGNMENT.md、CLI_USAGE.md、PROJECT_ARCHITECTURE.md 保持一致

### V9.4.5 (2026-02-02)
- ✨ 新增诱多陷阱检测系统
- ✨ 新增资金性质分类功能
- ✨ 新增风险评分系统
- ✨ 新增滚动指标计算
- ✨ 项目结构重组（工具、任务、配置分类）
- ✨ 新增 tasks/ 目录
- ✨ 更新所有导入路径

---

**最后更新**: 2026-02-12  
**版本**: V11.2.0