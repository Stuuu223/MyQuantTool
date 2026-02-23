# MyQuantTool CLI 使用手册

> **Phase 7 统一CLI入口** - 所有操作必须通过 `main.py` 执行  
> **版本**: V20.0.0  
> **日期**: 2026-02-23  

---

## 快速开始

### 环境检查
```bash
# 确保使用正确的Python版本 (3.10)
E:\MyQuantTool\venv_qmt\Scripts\python.exe --version

# 安装依赖
pip install -r requirements.txt
```

### 基础用法
```bash
# 显示帮助
python main.py --help

# 显示版本
python main.py --version

# 查看具体命令帮助
python main.py backtest --help
python main.py scan --help
```

---

## 命令概览

| 命令 | 功能 | 常用场景 |
|------|------|----------|
| `backtest` | 执行回测 | 策略验证、历史回演 |
| `scan` | 全市场扫描 | 盘前/盘中/盘后扫描 |
| `analyze` | 单股分析 | 个股诊断、信号验证 |
| `download` | 数据下载 | 批量获取Tick/K线数据 |
| `verify` | 数据验证 | 检查数据完整性 |
| `monitor` | 实时监控 | 启动事件驱动监控 |
| `simulate` | 历史模拟 | Phase 0.5/3 测试 |

---

## 详细命令说明

### 1. backtest - 回测

执行策略回测，支持多种回测模式。

```bash
python main.py backtest --date 20260105 --universe 300986.SZ
```

#### 参数

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--date` | `-d` | ✅ | 交易日期 (YYYYMMDD) |
| `--universe` | `-u` | - | 股票池: 单只或CSV文件路径 |
| `--strategy` | `-s` | - | 策略: right_side_breakout/v18/time_machine |
| `--output` | `-o` | - | 输出目录 |
| `--save` | - | - | 保存结果到文件 |
| `--target` | - | - | 目标股票代码（验证用） |

#### 示例

```bash
# 基础回测 - 单只股票
python main.py backtest --date 20260105 --universe 300986.SZ

# V18策略回测
python main.py backtest --date 20260105 --universe data/cleaned_candidates_66.csv --strategy v18

# 时间机器回测（两段式筛选）
python main.py backtest --date 20260105 --strategy time_machine --target 300986 --save

# 行为回测并保存
python main.py backtest --date 20260105 --universe 300986.SZ --save --output data/results
```

---

### 2. scan - 市场扫描

执行全市场扫描，发现交易机会。

```bash
python main.py scan --mode premarket
```

#### 参数

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--date` | `-d` | - | 交易日期 (默认今天) |
| `--mode` | `-m` | - | 模式: premarket/intraday/postmarket/full/triple_funnel |
| `--max-stocks` | - | - | 最大扫描股票数 (默认100) |
| `--output` | `-o` | - | 输出目录 |
| `--source` | - | - | 数据源: qmt/tushare (默认qmt) |

#### 示例

```bash
# 盘前扫描
python main.py scan --mode premarket

# 盘中扫描
python main.py scan --mode intraday

# 盘后扫描指定日期
python main.py scan --date 20260105 --mode postmarket

# 三漏斗扫描
python main.py scan --mode triple_funnel --max-stocks 200

# 完整扫描流程
python main.py scan --mode full --max-stocks 150 --output data/scan_results
```

---

### 3. analyze - 股票分析

分析单只股票的技术指标和信号。

```bash
python main.py analyze --stock 300986.SZ --date 20260105
```

#### 参数

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--stock` | `-s` | ✅ | 股票代码 (如 300986.SZ 或 300986) |
| `--date` | `-d` | - | 分析单个日期 |
| `--start-date` | - | - | 开始日期 (与--date互斥) |
| `--end-date` | - | - | 结束日期 (与--date互斥) |
| `--detail` | - | - | 显示详细分析 |

#### 示例

```bash
# 分析单日
python main.py analyze --stock 300986.SZ --date 20260105

# 分析日期范围
python main.py analyze --stock 300986.SZ --start-date 20251231 --end-date 20260105

# 详细分析
python main.py analyze --stock 300986.SZ --date 20260105 --detail

# 简写形式
python main.py analyze -s 300986 -d 20260105
```

---

### 4. download - 数据下载

批量下载Tick/K线数据。

```bash
python main.py download --date 20260105 --type tick
```

#### 参数

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--date` | `-d` | - | 交易日期 (默认今天) |
| `--type` | - | - | 数据类型: tick/kline/all (默认all) |
| `--universe` | `-u` | - | 股票池CSV文件路径 |
| `--workers` | `-w` | - | 并发workers (默认4) |

#### 示例

```bash
# 下载今日所有数据
python main.py download

# 下载指定日期Tick数据
python main.py download --date 20260105 --type tick

# 下载指定股票池数据
python main.py download --date 20260105 --universe data/cleaned_candidates_66.csv

# 高并发下载
python main.py download --date 20260105 --workers 8
```

---

### 5. verify - 数据验证

验证数据完整性并可选自动修复。

```bash
python main.py verify --date 20260105
```

#### 参数

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--date` | `-d` | - | 交易日期 (默认今天) |
| `--type` | - | - | 验证类型: tick/kline/all (默认all) |
| `--fix` | - | - | 自动修复缺失数据 |

#### 示例

```bash
# 验证今日数据
python main.py verify

# 验证指定日期
python main.py verify --date 20260105

# 验证并修复
python main.py verify --date 20260105 --fix

# 仅验证Tick数据
python main.py verify --date 20260105 --type tick
```

---

### 6. monitor - 实时监控

启动实时监控系统。

```bash
python main.py monitor --mode event
```

#### 参数

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--mode` | `-m` | - | 模式: event/cli/auction (默认event) |
| `--interval` | `-i` | - | 监控间隔秒数 (默认3) |

#### 示例

```bash
# 启动事件驱动监控（推荐）
python main.py monitor

# 或明确指定
python main.py monitor --mode event

# 启动CLI监控终端
python main.py monitor --mode cli

# 启动集合竞价监控
python main.py monitor --mode auction

# 自定义监控间隔
python main.py monitor --mode intraday --interval 5
```

#### 退出监控

按 `Ctrl+C` 优雅退出。

---

### 7. simulate - 历史模拟

运行Phase 0.5或Phase 3历史模拟测试。

```bash
python main.py simulate --start-date 20260224 --end-date 20260228
```

#### 参数

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--start-date` | - | ✅ | 开始日期 (YYYYMMDD) |
| `--end-date` | - | ✅ | 结束日期 (YYYYMMDD) |
| `--watchlist` | - | - | 关注列表CSV文件 |
| `--phase` | - | - | Phase版本: 0.5/3 (默认0.5) |

#### 示例

```bash
# Phase 0.5: 50样本历史回测
python main.py simulate --start-date 20260224 --end-date 20260228

# Phase 3: 实盘测试
python main.py simulate --phase 3 --watchlist data/watchlist.csv

# 指定日期范围
python main.py simulate --phase 0.5 --start-date 20260101 --end-date 20260131
```

---

## 典型工作流

### 工作流1: 日常盘前准备

```bash
# 1. 验证昨日数据完整性
python main.py verify --date 20260104

# 2. 下载最新数据
python main.py download --date 20260105 --type tick

# 3. 盘前扫描
python main.py scan --date 20260105 --mode premarket

# 4. 分析重点股票
python main.py analyze --stock 300986.SZ --date 20260105 --detail
```

### 工作流2: 策略回测验证

```bash
# 1. 对候选股票池执行回测
python main.py backtest --date 20260105 --universe data/candidates.csv --strategy v18 --save

# 2. 分析特定股票表现
python main.py analyze --stock 300986.SZ --start-date 20251231 --end-date 20260105

# 3. 生成扫描报告
python main.py scan --date 20260105 --mode postmarket --output data/reports
```

### 工作流3: 实时监控

```bash
# 1. 启动事件驱动监控
python main.py monitor --mode event

# 2. 或在另一个终端启动CLI监控
python main.py monitor --mode cli

# 3. 盘中快速扫描
python main.py scan --mode intraday --max-stocks 50
```

---

## 数据规范

### 日期格式
所有日期参数统一使用 **YYYYMMDD** 格式：
- ✅ 正确: `20260105`
- ❌ 错误: `2026-01-05`, `01/05/2026`

### 股票代码格式
支持多种格式，内部会自动标准化：
- ✅ `300986.SZ` (推荐)
- ✅ `300986` (自动识别为深圳)
- ✅ `600001.SH` (上海)
- ✅ `000001` (自动识别)

### 文件路径
- 使用相对路径（相对于项目根目录）
- CSV文件默认格式：第一列为股票代码

---

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 执行成功 |
| 1 | 执行失败/错误 |
| 130 | 用户中断 (Ctrl+C) |

---

## 注意事项

### ⚠️ 弃用警告
以下脚本已弃用，请勿直接调用：
```bash
# ❌ 已弃用 - 不要直接使用
python tasks/run_time_machine_backtest.py
python tasks/run_full_market_scan.py
python tasks/run_v18_holographic_replay.py
python tasks/run_triple_funnel_scan.py
python tasks/run_realtime_phase3_test.py
python tasks/run_historical_simulation.py
python tasks/tushare_market_filter.py
```

请改用对应的 `main.py` 命令。

### 🔒 数据隔离
- 所有数据操作统一使用 **QMT (xtquant)**
- 禁止直接调用 Tushare API（已通过 UniverseBuilder 封装）

### 📊 性能建议
- 扫描大量股票时适当增加 `--workers`
- 回测时使用 `--save` 保存结果便于复盘
- 监控模式下避免同时运行多个实例

---

## 故障排除

### ImportError: No module named 'click'
```bash
pip install click>=8.1.0
```

### Python版本错误
确保使用 venv_qmt 虚拟环境：
```bash
E:\MyQuantTool\venv_qmt\Scripts\python.exe main.py --help
```

### 数据缺失错误
```bash
# 先执行数据验证和修复
python main.py verify --date 20260105 --fix
```

### 编码错误 (Windows)
脚本已内置编码处理，如仍有问题：
```bash
chcp 65001
set PYTHONIOENCODING=utf-8
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V20.0.0 | 2026-02-23 | Phase 7: 统一CLI入口，架构标准化 |
| V11.1.0 | 2026-02-20 | 旧版argparse CLI |

---

## 相关文档

- [项目README](../README.md)
- [架构文档](CORE_ARCHITECTURE_V17.md)
- [开发范式](.iflow/DEVELOPMENT_PARADIGM.md)

---

> **提示**: 本文档随版本更新，如有疑问请检查当前版本 `python main.py --version`
