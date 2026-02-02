# MyQuantTool AI 助手 System Prompt

**最后更新**: 2026-02-02  
**版本**: 1.0

---

## 📋 项目概述

MyQuantTool 是一个量化交易分析工具，支持：
- AkShare + QMT 双数据源
- 实时数据采集和分析
- 技术指标计算
- 资金流向分析
- 诱多陷阱检测
- 历史复盘
- 龙头战法策略

**当前版本**: V9.4.5

---

## 📁 项目结构规范

### 核心目录

```
MyQuantTool/
├── temp/               # 临时文件（用完即删）
├── tools/              # 可复用工具
├── tasks/              # 定时任务
├── scripts/            # 维护脚本
├── config/             # 配置文件
├── logic/              # 核心逻辑
├── ui/                 # Streamlit UI
├── tests/              # 测试文件（按模块分类）
├── data/               # 数据文件
├── logs/               # 日志文件
├── docs/               # 永久文档
├── models/             # ML 模型
├── venv_qmt/           # QMT 虚拟环境
├── xtquant/            # QMT XTQuant
├── easyquotation/      # 实时数据源
└── PROJECT_STRUCTURE.md # 项目结构文档（根目录）
```

### 文档结构

```
docs/
├── user-guide/         # 用户指南
├── setup/              # 安装配置
├── tech/               # 技术文档
├── dev/                # 开发规划
└── temp/               # 临时文档（用完删除）
```

---

## 🔧 文件管理规范

### 1. 文件分类

#### 临时文件（用完即删）
```
temp/
├── tests/              # 临时测试脚本
├── debug/              # 调试输出
└── logs/               # 临时日志
```

#### 永久文件（分类存放）
```
tools/                  # 可复用工具
tasks/                  # 定时任务
scripts/                # 维护脚本
docs/                   # 永久文档
config/                 # 配置文件
tests/                  # 测试文件
```

### 2. 文件创建流程

```
✅ 第1步：检查是否已存在
✅ 第2步：判断文件用途（临时/永久）
✅ 第3步：选择正确目录
✅ 第4步：遵循命名规范
✅ 第5步：创建文件
✅ 第6步：更新相关引用（如有必要）
```

### 3. 文件命名规范

#### 临时文件
```
格式：[用途]_temp_[日期].[ext]
示例：
- test_redis_temp_20260202.py
- debug_auction_temp_20260202.txt
- temp_data_20260202.json
```

#### 测试文件
```
格式：test_[功能].[ext]
位置：tests/[模块]/
示例：
- tests/core/test_redis.py
- tests/logic/test_trap_detector.py
- tests/tools/test_stock_analyzer.py
```

#### 调试文件
```
格式：debug_[功能].[ext]
位置：temp/debug/
示例：
- debug_auction_snapshot.txt
- debug_market_data.json
```

#### 永久文件
```
工具类：*_tool.py 或 *_analyzer.py
任务类：run_*.py
脚本类：动词开头（clean、generate、init）
策略类：strategy_*.py
UI 类：页面名称（如 dashboard_home.py）
```

### 4. 任务完成清理清单

```
✅ 删除所有临时文件
✅ 清理 temp/ 目录
✅ 更新相关文档（如有变更）
✅ 检查是否有遗留的调试代码
✅ 提交代码前确认无临时文件
```

---

## 🛠️ 常用工具和命令

### 文件操作（Windows）

```batch
# 查看目录
dir
dir tools

# 创建目录
mkdir temp
mkdir temp\tests

# 删除文件
del temp\test.py
del /q temp\*  # 删除所有文件

# 移动文件
move file.py tools\
move *.py tools\

# 复制文件
copy file.py tools\
```

### 文件查看（Windows）

```batch
# 查看文件内容
type README.md
type config\config.json

# 分页查看
type README.md | more

# 搜索内容
type README.md | findstr "Redis"
```

### Python 操作

```bash
# 运行主程序
python main.py

# 运行脚本
python scripts\clean_project.py
python scripts\init_qmt.py

# 运行任务
python tasks\run_dashboard.py
python tasks\run_scan_v19_final.py

# 安装依赖
pip install -r requirements.txt
pip install akshare
```

### Git 操作

```bash
# 查看状态
git status

# 添加文件
git add .
git add tools\*.py

# 提交
git commit -m "feat(tools): 添加诱多陷阱检测功能"

# 推送
git push

# 查看日志
git log -n 3
git log --oneline
```

### Redis 操作

```bash
# 检查 Redis 是否运行
tasklist | findstr redis-server

# 测试连接
redis-cli ping

# 查看状态
redis-cli info
redis-cli info memory

# 清理竞价快照
redis-cli --scan --pattern "auction:*" | xargs redis-cli del
```

---

## 🔍 常用分析工具

### 1. 个股分析工具

```python
from tools.stock_ai_tool import analyze_stock

# 基础分析（10天）
result = analyze_stock('603697', mode='basic')

# 增强分析（90天，含诱多检测）
result = analyze_stock('603697', days=90, mode='enhanced', auto_save=True)
```

**返回数据结构**：
```python
{
    'code': '603697',
    'name': '五矿发展',
    'basic': {...},           # 基础数据
    'technical': {...},       # 技术指标
    'capital': {...},         # 资金流向
    'trap_detection': {...},  # 诱多检测（enhanced模式）
    'risk_assessment': {...}, # 风险评估（enhanced模式）
    'file_path': '...'        # 保存路径（auto_save=True）
}
```

### 2. 综合分析工具

```python
from tools.comprehensive_stock_tool import comprehensive_stock_analysis

# 综合分析（AkShare + QMT）
result, file_path = comprehensive_stock_analysis(
    '603697', 
    days=30, 
    use_qmt=True, 
    auto_save=True
)
```

### 3. 增强分析器

```python
from tools.enhanced_stock_analyzer import analyze_stock_enhanced

# 增强分析（JSON格式）
result = analyze_stock_enhanced('603697', days=90)
```

**返回数据结构**：
```python
{
    'stock_info': {...},
    'rolling_metrics': {...},    # 滚动指标
    'trap_detection': {...},     # 诱多检测
    'capital_analysis': {...},   # 资金分类
    'risk_assessment': {...}     # 风险评估
}
```

### 4. 快速分析

```python
from tools.comprehensive_stock_tool import quick_analysis

# 快速分析（基础信息）
result = quick_analysis('603697')
```

---

## 📊 核心功能模块

### 1. 数据源

```python
from logic.data_provider_factory import get_data_provider

# 获取数据提供者
provider = get_data_provider(use_qmt=True)

# 获取实时数据
data = provider.get_realtime_data(['600058', '300997'])

# 获取历史数据
history = provider.get_stock_history('600058', days=30)
```

### 2. 诱多陷阱检测

```python
from logic.trap_detector import TrapDetector

detector = TrapDetector()
result = detector.detect_traps(daily_data)

# 返回
{
    'has_trap': True,
    'trap_type': 'HOT_MONEY_RAID',
    'confidence': 0.85,
    'description': '...'
}
```

### 3. 资金分类

```python
from logic.capital_classifier import CapitalClassifier

classifier = CapitalClassifier()
result = classifier.classify(daily_data)

# 返回
{
    'capital_type': 'INSTITUTIONAL',
    'confidence': 0.75,
    'features': {...}
}
```

### 4. 滚动指标

```python
from logic.rolling_metrics import RollingMetricsCalculator

calculator = RollingMetricsCalculator()
result = calculator.calculate(daily_data)

# 返回
{
    'net_inflow_5d': 1000000,
    'net_inflow_10d': 2000000,
    'net_inflow_20d': 3000000,
    'flow_rank_5d': 0.85
}
```

---

## 📝 代码规范

### 1. 导入顺序

```python
# 标准库
import os
import sys
from datetime import datetime

# 第三方库
import pandas as pd
import streamlit as st
import akshare as ak

# 本地模块（按层级）
from config.config_system import Config
from logic.data_manager import DataManager
from tools.stock_ai_tool import analyze_stock
```

### 2. 函数注释

```python
def analyze_stock(code: str, days: int = 10) -> dict:
    """
    分析股票数据
    
    Args:
        code: 股票代码（6位数字）
        days: 分析天数，默认10天
    
    Returns:
        包含分析结果的字典
    
    Raises:
        ValueError: 当股票代码格式不正确时
    """
    pass
```

### 3. 错误处理

```python
try:
    # 操作
    result = analyze_stock(code)
except ValueError as e:
    logger.error(f"参数错误: {e}")
    raise
except Exception as e:
    logger.critical(f"未知错误: {e}")
    raise
```

### 4. 日志规范

```python
import logging
logger = logging.getLogger(__name__)

# 日志级别
logger.debug("调试信息")
logger.info("常规信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

---

## 🌿 Git 提交规范

### 提交信息格式

```
<type>(<scope>): <subject>

类型：
- feat: 新功能
- fix: 修复
- docs: 文档
- style: 格式（不影响代码运行）
- refactor: 重构
- test: 测试
- chore: 构建过程或辅助工具

示例：
feat(tools): 添加诱多陷阱检测功能
fix(logic): 修复资金分类计算错误
docs(structure): 更新项目结构文档
refactor(core): 优化数据获取性能
test(redis): 添加 Redis 连接测试
```

---

## 🔐 安全规范

### 敏感信息处理

```python
# ❌ 错误：硬编码密码
password = "123456"

# ✅ 正确：使用环境变量
import os
password = os.getenv('DB_PASSWORD')

# ✅ 正确：使用配置文件
from config.config_system import Config
config = Config()
password = config.get('database.password')
```

### 配置文件安全

```json
// config/config.json 敏感信息示例
{
  "redis": {
    "password": ""  // 留空或使用环境变量
  },
  "database": {
    "password": ""  // 不提交到 Git
  }
}
```

---

## 📦 依赖管理

### requirements.txt 格式

```
# 核心依赖
streamlit==1.29.0
pandas==2.1.4
numpy==1.26.2
akshare==1.12.0

# 数据库
redis==5.0.1
sqlite3

# QMT 相关
xtquant

# 可选依赖
plotly==5.18.0
```

---

## 🧪 测试规范

### 测试文件命名

```
tests/
├── core/
│   ├── test_redis.py
│   └── test_database.py
├── logic/
│   ├── test_data_adapter.py
│   └── test_trap_detector.py
├── tools/
│   └── test_stock_analyzer.py
└── integration/
    └── test_full_flow.py
```

### 测试函数命名

```python
def test_stock_analysis():
    """测试股票分析功能"""
    # Arrange
    code = "600058"
    
    # Act
    result = analyze_stock(code)
    
    # Assert
    assert result is not None
    assert result['code'] == code
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/logic/test_trap_detector.py

# 运行特定函数
pytest tests/logic/test_trap_detector.py::test_detect_traps

# 详细输出
pytest -v
```

---

## 📚 常用文档位置

### 快速参考

```
docs/user-guide/README_快速开始.md     # 快速开始
docs/user-guide/个股分析工具使用指南.md # 分析工具使用
docs/setup/redis_setup_guide.md        # Redis 配置
docs/setup/qmt_setup_guide.md          # QMT 配置
docs/tech/数据源架构设计文档.md         # 数据源架构
PROJECT_STRUCTURE.md                   # 项目结构（根目录）
```

---

## 🎯 工作流程

### 新功能开发

```
1. 分析需求 → 创建开发计划（docs/dev/temp/）
2. 实现 → 创建必要文件（tools/scripts/tasks）
3. 测试 → 创建测试文件（tests/[模块]/）
4. 清理 → 删除临时文件（temp/）
5. 文档 → 更新永久文档（docs/）
```

### 问题修复

```
1. 定位问题 → 创建调试文件（temp/debug/）
2. 修复 → 修改代码
3. 验证 → 测试文件（tests/[模块]/）
4. 清理 → 删除调试文件
5. 文档 → 更新相关文档（如有必要）
```

### 任务完成检查

```
✅ 删除所有临时文件
✅ 清理 temp/ 目录
✅ 更新相关文档
✅ 运行测试
✅ 提交代码前确认无遗留文件
```

---

## 🚨 常见问题

### 1. Redis 连接失败

```bash
# 检查 Redis 是否运行
tasklist | findstr redis-server

# 启动 Redis
redis-server

# 测试连接
redis-cli ping
```

### 2. QMT 数据获取失败

```python
# 检查 QMT 是否初始化
from logic.qmt_manager import QMTManager
manager = QMTManager()
print(manager.is_connected())

# 重新初始化
python scripts/init_qmt.py
```

### 3. 数据源切换

```python
from logic.data_provider_factory import get_data_provider

# 使用 AkShare
provider = get_data_provider(use_qmt=False)

# 使用 QMT
provider = get_data_provider(use_qmt=True)

# 自动切换（QMT优先）
provider = get_data_provider()
```

---

## 📞 快速命令参考

```bash
# 启动应用
start.bat

# 运行仪表板
python tasks/run_dashboard.py

# 运行扫描
python tasks/run_scan_v19_final.py

# 清理项目
python scripts/clean_project.py

# 初始化 QMT
python scripts/init_qmt.py

# 测试 Redis
python tests/core/test_redis.py

# 查看项目结构
type PROJECT_STRUCTURE.md
```

---

## 🎉 总结

**记住这些关键点**：

1. **文件管理**：临时文件放 temp/，永久文件分类存放
2. **命名规范**：临时文件加日期和 _temp 标记
3. **清理任务**：任务完成后必须删除临时文件
4. **文档更新**：修改代码后更新相关文档
5. **测试优先**：新功能必须有测试
6. **安全第一**：敏感信息不硬编码
7. **Git 规范**：遵循提交信息格式
8. **善用工具**：熟悉常用工具和命令

---

**最后更新**: 2026-02-02  
**维护者**: iFlow CLI