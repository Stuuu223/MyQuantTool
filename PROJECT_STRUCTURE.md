# MyQuantTool 项目结构说明

**更新时间**: 2026-02-02  
**版本**: V9.4.5

---

## 📁 项目根目录

### 核心文件
- `main.py` - 主程序入口
- `start_app.py` - 应用启动脚本
- `start.bat` - Windows 启动脚本
- `quick_start.bat` - 快速启动脚本

### 配置文件
- `pytest.ini` - 测试配置
- `requirements.txt` - Python 依赖列表
- `my_quant_cache.sqlite` - 缓存数据库

### 安装工具
- `install_dependencies.bat` - 依赖安装脚本
- `pip.bat` - pip 工具快捷方式

---

## 📂 tools/ - 工具目录

### 个股分析工具
- `comprehensive_stock_tool.py` - 综合分析工具（AkShare + QMT）
- `enhanced_stock_analyzer.py` - 增强分析器（技术指标 + 诱多检测）
- `stock_ai_tool.py` - AI 便捷接口（统一调用入口）

### 数据工具
- `generate_static_map.py` - 生成静态映射
- `harvest_data.py` - 数据采集工具
- `update_concepts.py` - 更新概念数据

**使用方式**:
```python
from tools.comprehensive_stock_tool import comprehensive_stock_analysis
from tools.enhanced_stock_analyzer import analyze_stock_enhanced
from tools.stock_ai_tool import analyze_stock
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

### 核心模块
- `algo*.py` - 算法模块（基础算法、高级算法、资金流向算法等）
- `data_adapter*.py` - 数据适配器（支持多数据源）
- `fund_flow_*.py` - 资金流向分析（收集器、分析器、调度器）
- `market_*.py` - 市场分析（市场情绪、市场状态、市场周期等）
- `trap_detector.py` - 诱多陷阱检测器（V9.4.5 新增）
- `capital_classifier.py` - 资金性质分类器（V9.4.5 新增）
- `rolling_metrics.py` - 滚动指标计算器（V9.4.5 新增）

### 数据模块
- `data_*.py` - 数据管理（采集、清洗、健康监控等）
- `database_manager.py` - 数据库管理
- `cache_manager.py` - 缓存管理

### QMT 模块
- `qmt_*.py` - QMT 数据提供（历史数据、Tick数据）
- `code_converter.py` - 代码转换器

### 策略模块
- `strategy_*.py` - 策略库（策略工厂、策略比较、投资组合优化等）

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

### 数据文件
- `stock_analysis/` - 个股分析数据（按股票代码分类）
- `concept_map.json` - 概念映射数据
- `stock_sector_map.json` - 股票板块映射
- `kline_cache/` - K线缓存
- `review_cases/` - 复盘案例
- `execution_record.json` - 执行记录
- `scheduled_alerts.json` - 定时任务告警

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
| 根目录 | 10 | 核心配置和启动文件 |
| tools/ | 6 | 工具和分析模块 |
| tasks/ | 4 | 运行任务和定时任务 |
| scripts/ | 5 | 维护和初始化脚本 |
| config/ | 5 | 配置文件 |
| logic/ | 180+ | 核心逻辑模块 |
| ui/ | 70+ | Streamlit UI 页面 |
| docs/ | 16 | 文档文件（分4个子目录） |
| tests/ | - | 测试文件 |
| models/ | - | ML 模型文件 |
| logs/ | - | 日志文件 |
| data/ | - | 数据文件 |
| easyquotation/ | - | 实时数据源 |
| xtquant/ | - | QMT 数据源 |
| venv_qmt/ | - | QMT 虚拟环境 |

---

## 🚀 快速开始

### 1. 启动应用
```bash
# Windows
start.bat

# 或者
python main.py
```

### 2. 运行工具
```python
# 使用分析工具
from tools.stock_ai_tool import analyze_stock
result = analyze_stock('603697', days=90, mode='enhanced')
```

### 3. 运行任务
```bash
# 运行仪表板
python tasks/run_dashboard.py

# 运行扫描
python tasks/run_scan_v19_final.py
```

### 4. 运行脚本
```bash
# 清理项目
python scripts/clean_project.py

# 初始化 QMT
python scripts/init_qmt.py
```

---

## 📝 更新日志

### V9.4.5 (2026-02-02)
- ✨ 新增诱多陷阱检测系统
- ✨ 新增资金性质分类功能
- ✨ 新增风险评分系统
- ✨ 新增滚动指标计算
- ✨ 项目结构重组（工具、任务、配置分类）
- ✨ 新增 tasks/ 目录
- ✨ 更新所有导入路径

---

**最后更新**: 2026-02-02  
**版本**: V9.4.5