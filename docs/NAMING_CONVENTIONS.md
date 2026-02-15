# MyQuantTool 命名规范 (V15.0)

**作者**: AI总监 + CTO  
**日期**: 2026-02-15  
**版本**: V15.0  
**目的**: 统一项目命名规范，解决"AI总监命名混乱"问题

---

## 目录

1. [通用命名原则](#通用命名原则)
2. [目录命名规范](#目录命名规范)
3. [文件命名规范](#文件命名规范)
4. [代码命名规范](#代码命名规范)
5. [数据命名规范](#数据命名规范)
6. [配置命名规范](#配置命名规范)
7. [日志命名规范](#日志命名规范)
8. [禁止使用的命名](#禁止使用的命名)
9. [工具和检查](#工具和检查)

---

## 通用命名原则

### 核心原则

1. **清晰性**: 命名应该清晰表达意图，避免缩写和模糊的名称
2. **一致性**: 同类型的实体使用相同的命名风格
3. **简洁性**: 在保证清晰的前提下，命名应该简洁
4. **可读性**: 命名应该易于阅读和理解

### 语言规范

- **中文**: 注释和文档使用中文
- **英文**: 代码、变量名、函数名、类名使用英文
- **拼音**: 禁止使用拼音命名

### 大小写规范

- **snake_case**: 小写字母+下划线（变量、函数、目录、文件）
- **PascalCase**: 首字母大写（类名、模块名）
- **UPPER_CASE**: 全大写+下划线（常量）

---

## 目录命名规范

### 原则

- 使用小写字母和下划线（snake_case）
- 使用复数形式（复数名表示包含多个实体）
- 后缀标识用途（`_hot`, `_real`, `_mock`）
- 禁止嵌套目录
- 禁止使用驼峰命名

### 示例

```
✅ data/                    # 正确：小写
✅ logic/                   # 正确：小写
✅ logic/strategies/        # 正确：snake_case
✅ data/qmt_data/           # 正确：下划线
✅ data/minute_data_hot/    # 正确：后缀标识用途
✅ backtest_results/        # 正确：复数形式
❌ QmtData/                 # 错误：驼峰命名
❌ data/data/               # 错误：嵌套目录
❌ MinuteDataHot/           # 错误：驼峰命名
❌ logic/Strategy/          # 错误：大写开头
❌ backtest_result/         # 错误：单数形式
```

### data/目录规范

```
data/
├── qmt_data/              # QMT核心数据（永保留）
├── datadir/               # QMT数据目录（自动管理）
├── minute_data_hot/       # 热门股票K线（定期更新）
├── minute_data_real/      # 实时K线数据（7天轮转）
├── minute_data_mock/      # 测试K线数据（可删除）
├── backtest_results_real/ # 实盘回测结果（永久保留）
├── backtest_results_random/ # 随机回测结果（7天轮转）
├── cache/                 # 运行时缓存（清理）
├── scan_results/          # 扫描结果（4h轮转）
└── README.md              # 目录说明
```

### logic/目录规范

```
logic/
├── core/                  # 核心模块
├── data/                  # 数据模块
├── strategies/            # 策略模块
├── analyzers/             # 分析器模块
├── monitors/              # 监控模块
├── sentiment/             # 情感分析模块
├── sectors/               # 板块分析模块
├── utils/                 # 工具模块
└── tests/                 # 测试模块
```

---

## 文件命名规范

### 原则

- 使用小写字母和下划线（snake_case）
- 扩展名全部小写
- 日期格式统一（YYYYMMDD）
- 股票代码格式统一（000002.SZ）

### Python文件命名

```
✅ data_manager.py         # 正确：snake_case
✅ heartbeat_checker.py    # 正确：snake_case
✅ failsafe.py             # 正确：snake_case
❌ DataManager.py          # 错误：驼峰命名
❌ HeartbeatChecker.py     # 错误：驼峰命名
❌ failsafe.PY             # 错误：扩展名大写
```

### 数据文件命名

#### 股票代码格式

```
格式: {股票代码}_{周期}_{日期}.{扩展名}
示例: 000002.SZ_1m_20260215.csv
```

**详细说明**:
- 股票代码：`000002.SZ`（完整格式，带交易所后缀）
- 周期：`1m`（1分钟）、`5m`（5分钟）、`1d`（日K）、`tick`（Tick）
- 日期：`20260215`（YYYYMMDD格式）
- 扩展名：`.csv`、`.json`、`.dat`（全部小写）

**示例**:
```
000002.SZ_1m_20260215.csv          # 1分钟K线
000002.SZ_5m_20260215.csv          # 5分钟K线
000002.SZ_1d_20260215.csv          # 日K线
000002.SZ_tick_20260215.dat        # Tick分笔
600000.SH_1m_20260215.csv          # 上交所1分钟K线
```

#### 分析结果命名

```
格式: {股票代码}_analysis_{日期}.json
示例: 300997_analysis_20260215.json
```

#### 回测结果命名

```
格式: backtest_{日期}_{策略名}_{版本}.json
示例: backtest_20260215_midway_strategy_v12_1_0.json
```

#### 扫描结果命名

```
格式: {日期}_{时间}_{类型}.json
示例: 2026-02-15_093000_intraday.json
```

### 配置文件命名

```
✅ config.json             # 正确：小写
✅ config.local.json       # 正确：小写+下划线
✅ phase1_config.yaml      # 正确：小写
❌ Config.json             # 错误：大写开头
❌ config.JSON             # 错误：扩展名大写
❌ CONFIG.json             # 错误：全大写
```

### 文档文件命名

```
✅ README.md               # 正确：全大写
✅ CHANGELOG.md            # 正确：全大写
✅ ARCHITECTURE.md         # 正确：全大写
❌ readme.md               # 错误：小写
❌ Readme.md               # 错误：大小写混合
```

### 日志文件命名

```
格式: {模块}_{日期}_{时间}.log
示例: qmt_manager_20260215_093000.log
```

---

## 代码命名规范

### 类命名

**原则**: 使用PascalCase（首字母大写）

```
✅ DataManager             # 正确：PascalCase
✅ HeartbeatChecker        # 正确：PascalCase
✅ FailSafeManager         # 正确：PascalCase
❌ dataManager             # 错误：camelCase
❌ heartbeat_checker       # 错误：snake_case
❌ DATAMANAGER             # 错误：全大写
```

### 函数命名

**原则**: 使用snake_case（小写字母+下划线）

```
✅ get_stock_data()        # 正确：snake_case
✅ check_heartbeat()       # 正确：snake_case
✅ calculate_macd()        # 正确：snake_case
❌ getStockData()          # 错误：camelCase
❌ GetStockData()          # 错误：PascalCase
❌ get_stock_data()        # 正确：snake_case
```

### 变量命名

**原则**: 使用snake_case（小写字母+下划线）

```
✅ stock_code              # 正确：snake_case
✅ last_price              # 正确：snake_case
✅ volume                  # 正确：snake_case
❌ stockCode               # 错误：camelCase
❌ lastPrice               # 错误：camelCase
❌ stock_code              # 正确：snake_case
```

### 常量命名

**原则**: 使用UPPER_CASE（全大写+下划线）

```
✅ MAX_RETRY_COUNT         # 正确：UPPER_CASE
✅ DEFAULT_TIMEOUT         # 正确：UPPER_CASE
✅ QMT_SERVER_ADDRESS      # 正确：UPPER_CASE
❌ maxRetryCount           # 错误：camelCase
❌ MaxRetryCount           # 错误：PascalCase
❌ max_retry_count         # 错误：snake_case
```

### 私有变量命名

**原则**: 前缀下划线

```
✅ _internal_data          # 正确：前缀下划线
✅ _private_method()       # 正确：前缀下划线
❌ __internal_data         # 错误：双下划线（Python魔法方法）
❌ privateData             # 错误：无下划线
```

### 布尔变量命名

**原则**: 使用`is_`、`has_`、`can_`、`should_`前缀

```
✅ is_connected            # 正确：is_前缀
✅ has_permission          # 正确：has_前缀
✅ can_trade               # 正确：can_前缀
✅ should_buy              # 正确：should_前缀
❌ connected               # 错误：无前缀
❌ hasPermission           # 错误：驼峰命名
```

---

## 数据命名规范

### 股票代码格式

**原则**: 使用完整格式，带交易所后缀

```
格式: {6位代码}.{交易所后缀}
示例: 000002.SZ, 600000.SH
```

**交易所后缀**:
- `.SZ` - 深交所
- `.SH` - 上交所
- `.BJ` - 北交所

**示例**:
```
✅ 000002.SZ               # 正确：完整格式
✅ 600000.SH               # 正确：完整格式
❌ 000002                  # 错误：缺少交易所后缀
❌ 000002sz                # 错误：小写后缀
❌ SZ000002                # 错误：交易所前缀
```

### 日期格式

**原则**: 使用YYYYMMDD格式

```
格式: YYYYMMDD
示例: 20260215
```

**示例**:
```
✅ 20260215                # 正确：YYYYMMDD
✅ 2026-02-15              # 正确：YYYY-MM-DD（可读性更好）
❌ 2026/02/15              # 错误：使用斜杠
❌ 02/15/2026              # 错误：美国格式
❌ 15-02-2026              # 错误：欧洲格式
```

### 时间格式

**原则**: 使用HHMMSS格式

```
格式: HHMMSS
示例: 093000
```

**示例**:
```
✅ 093000                  # 正确：HHMMSS
✅ 09:30:00                # 正确：HH:MM:SS（可读性更好）
❌ 9:30:00                 # 错误：单数字小时
❌ 09:30am                 # 错误：使用AM/PM
```

### 数值格式

**原则**: 使用下划线分隔千位（Python 3.6+）

```
✅ 1_000_000               # 正确：下划线分隔
✅ 1000000                 # 正确：无分隔（小数字）
❌ 1,000,000               # 错误：使用逗号
❌ 1 000 000               # 错误：使用空格
```

---

## 配置命名规范

### 配置键命名

**原则**: 使用snake_case

```
✅ qmt_server_address      # 正确：snake_case
✅ max_retry_count         # 正确：snake_case
✅ default_timeout         # 正确：snake_case
❌ qmtServerAddress        # 错误：camelCase
❌ QMT_SERVER_ADDRESS      # 错误：UPPER_CASE
```

### 配置文件命名

**原则**: 使用snake_case，扩展名小写

```
✅ config.json             # 正确：snake_case
✅ config.local.json       # 正确：snake_case
✅ phase1_config.yaml      # 正确：snake_case
❌ Config.json             # 错误：大写开头
❌ config.JSON             # 错误：扩展名大写
```

---

## 日志命名规范

### 日志级别

```
✅ DEBUG                   # 正确：调试信息
✅ INFO                    # 正确：常规信息
✅ WARNING                 # 正确：警告信息
✅ ERROR                   # 正确：错误信息
✅ CRITICAL                # 正确：严重错误
```

### 日志格式

```
格式: [{级别}] [{模块}] {时间} {消息}
示例: [DEBUG] [qmt_manager] 2026-02-15 09:30:00 连接成功
```

---

## 禁止使用的命名

### 禁止使用拼音

```
❌ gu_piao_ma              # 错误：股票代码的拼音
❌ zheng_qu_shu_ju         # 错误：证券数据的拼音
```

### 禁止使用中文变量名

```
❌ 股票代码                # 错误：中文变量名
❌ 最新价格                # 错误：中文变量名
```

### 禁止使用单字母变量名（除循环变量）

```
❌ a, b, c, d             # 错误：无意义的单字母
✅ i, j, k, l            # 正确：循环变量
✅ index, count, sum     # 正确：有意义的变量名
```

### 禁止使用缩写（除通用缩写）

```
❌ st_data                # 错误：不明确的缩写
❌ qty                    # 错误：不明确的缩写
✅ stock_data             # 正确：完整单词
✅ quantity               # 正确：完整单词
✅ qty                    # 正确：通用缩写（quantity）
```

### 禁止使用保留字

```
❌ class, def, return, if, else  # 错误：Python保留字
✅ class_name, return_value     # 正确：避免保留字
```

---

## 工具和检查

### 自动化检查脚本

```bash
# 检查命名规范
python tools/check_naming_conventions.py

# 自动修复命名问题
python tools/fix_naming_conventions.py

# 生成命名规范报告
python tools/report_naming_conventions.py
```

### IDE插件

- **PyLint**: Python代码检查
- **Black**: Python代码格式化
- **isort**: Python导入排序
- **flake8**: Python代码风格检查

### Git钩子

```bash
# 安装pre-commit钩子
pip install pre-commit

# 运行pre-commit
pre-commit run --all-files
```

---

## 违规处理

### 发现违规时的处理流程

1. **识别违规**: 使用自动化工具检测
2. **评估影响**: 评估违规对项目的影响
3. **制定方案**: 制定修复方案
4. **执行修复**: 执行修复（重构或重命名）
5. **测试验证**: 测试修复后的代码
6. **文档更新**: 更新相关文档

### 常见违规和修复

#### 硬编码路径

```python
# ❌ 错误：硬编码路径
data_path = "E:/MyQuantTool/data/qmt_data/SH/0/600000/20260215.dat"

# ✅ 正确：使用配置文件
from config.paths import DATA_DIR
data_path = DATA_DIR / "qmt_data" / "SH" / "0" / "600000" / "20260215.dat"
```

#### 命名不一致

```python
# ❌ 错误：命名不一致
def getStockData(stockCode):
    return data[stockCode]

# ✅ 正确：命名一致
def get_stock_data(stock_code):
    return data[stock_code]
```

#### 文件扩展名大小写

```python
# ❌ 错误：扩展名大写
import pandas as pd
df = pd.read_csv("data/stock_data.CSV")

# ✅ 正确：扩展名小写
import pandas as pd
df = pd.read_csv("data/stock_data.csv")
```

---

## 版本历史

### V15.0 (2026-02-15)
- 创建全项目命名规范
- 解决"AI总监命名混乱"问题
- 统一目录、文件、代码命名规范
- 添加自动化检查工具

---

## 联系方式

如有疑问或问题，请参考：

- **AI总监**: 负责命名规范和文档维护
- **CTO**: 负责架构审查和代码审查
- **检查工具**: `tools/check_naming_conventions.py`
- **修复工具**: `tools/fix_naming_conventions.py`

---

**最后更新**: 2026-02-15  
**下次审查**: 2026-03-15