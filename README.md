# MyQuantTool - 右侧极端换手起爆时间机器

**版本**: V20.0.0 (Phase 16 熔断机制版)  
**核心定位**: A股右侧极端换手起爆点 + 横向资金吸血PK  
**数据源**: QMT Tick (Level-1/Level-2 VIP) + Tushare粗筛  
**架构**: 唯一事实来源 + 常识护栏 + 统一CLI入口 + QMT原教旨主义

---

## 🎯 五大基石 (CTO最终审计)

1. **QMT原教旨主义**: VIP → Local L1 → 熔断，禁止降级Tushare
2. **算子收口**: 所有核心算子在`logic/core/`，禁止分散
3. **跨日记忆**: 记忆衰减机制(0.5系数)，连续2日不上榜删除
4. **VWAP惩罚**: 跌破均价线-20分，final_score永不为0
5. **统一入口**: 所有操作必须通过`main.py`，禁止野脚本

---

## ⚡ 系统宪法 (8条铁律)

1. **真实涨跌幅**: 必须基于 `pre_close` 计算，禁止用 `open`
2. **零硬编码路径**: 所有路径通过 `PathResolver` 解析
3. **零魔法数字**: 所有指标必须显式定义在 `MetricDefinitions`
4. **Fail Fast**: 异常立即抛，禁止静默吞没
5. **接口隔离**: 业务层严禁直接导入 `xtdata`
6. **流通市值单位**: QMT返回 shares，无需再乘10000
7. **成交量单位**: 手→股必须显式转换 (×100)
8. **统一CLI入口**: 所有操作必须通过 `main.py`

---

## 🧠 核心架构 (Phase 9.2 纯净核心)

### 唯一事实来源 (SSOT)
```
logic/core/
├── metric_definitions.py   # 全球度量定义
├── path_resolver.py        # 路径解析器
├── sanity_guards.py        # 数据验证护栏
└── version.py              # 版本控制
```

### 三漏斗粗筛 (全市场5000→约500)
```
第一层: 静态过滤 (ST/退市/北交所)
第二层: 金额过滤 (5日成交额 > 3000万)
第三层: 量比过滤 (量比 > 3.0)
```

### V18 验证机 (三层防线)
```
第一层: 高分率基础分 (线性极值映射0-100分)
第二层: 横向吸血乘数 (资金净流入占比排名)
第三层: VWAP惩罚打分 (跌破均价线-20分)
```

---

## 🛠️ 极简使用指南

### 1. 环境配置
```bash
# 创建.env文件，填入token
echo "TUSHARE_TOKEN=your_token" > .env
echo "QMT_VIP_TOKEN=your_vip_token" >> .env
```

### 2. 数据下载
```bash
# 下载Tick数据 (前台透明执行)
python main.py download --date 20251231 --type tick
```

### 3. 全息时间机器 (核心功能 - 跨日连贯流)
```bash
# 12月24日至1月5日跨日回测
python main.py backtest --start_date 20251224 --end_date 20260105 --full_market --strategy v18 --save

# 输出: data/backtest_out/time_machine/time_machine_YYYYMMDD.json (每日Top 20)
#       data/backtest_out/time_machine/time_machine_summary_*.json (汇总报告)
```

### 4. 单日验证
```bash
# 单日回测 (粗筛 + 三防线)
python main.py backtest --date 20251231 --full_market --strategy v18
```

### 5. 实盘监控
```bash
# 启动实时监控系统
python main.py monitor
```

---

## 📋 CLI 使用手册

### 快速开始
```bash
# 显示帮助
python main.py --help

# 显示版本
python main.py --version

# 查看具体命令帮助
python main.py backtest --help
python main.py scan --help
```

### 命令概览

| 命令 | 功能 | 常用场景 |
|------|------|----------|
| `backtest` | 执行回测 | 策略验证、历史回演 |
| `scan` | 全市场扫描 | 盘前/盘中/盘后扫描 |
| `analyze` | 单股分析 | 个股诊断、信号验证 |
| `download` | 数据下载 | 批量获取Tick/K线数据 |
| `verify` | 数据验证 | 检查数据完整性 |
| `monitor` | 实时监控 | 启动事件驱动监控 |
| `simulate` | 历史模拟 | Phase 0.5/3 测试 |

### 详细命令说明

#### 1. backtest - 回测
```bash
python main.py backtest --date 20260105 --universe 300986.SZ
```

**参数**:
- `--date`, `-d`: 交易日期 (YYYYMMDD, 必需)
- `--universe`, `-u`: 股票池: 单只或CSV文件路径
- `--strategy`, `-s`: 策略: right_side_breakout/v18/time_machine
- `--output`, `-o`: 输出目录
- `--save`: 保存结果到文件
- `--target`: 目标股票代码（验证用）

**示例**:
```bash
# 基础回测 - 单只股票
python main.py backtest --date 20260105 --universe 300986.SZ

# V18策略回测
python main.py backtest --date 20260105 --universe data/candidates.csv --strategy v18

# 时间机器回测（两段式筛选）
python main.py backtest --date 20260105 --strategy time_machine --target 300986 --save
```

#### 2. scan - 市场扫描
```bash
python main.py scan --mode premarket
```

**参数**:
- `--date`, `-d`: 交易日期 (默认今天)
- `--mode`, `-m`: 模式: premarket/intraday/postmarket/full/triple_funnel
- `--max-stocks`: 最大扫描股票数 (默认100)
- `--output`, `-o`: 输出目录
- `--source`: 数据源: qmt/tushare (默认qmt)

**示例**:
```bash
# 盘前扫描
python main.py scan --mode premarket

# 盘中扫描
python main.py scan --mode intraday

# 盘后扫描指定日期
python main.py scan --date 20260105 --mode postmarket
```

#### 3. analyze - 股票分析
```bash
python main.py analyze --stock 300986.SZ --date 20260105
```

**参数**:
- `--stock`, `-s`: 股票代码 (如 300986.SZ 或 300986, 必需)
- `--date`, `-d`: 分析单个日期
- `--start-date`: 开始日期 (与--date互斥)
- `--end-date`: 结束日期 (与--date互斥)
- `--detail`: 显示详细分析

**示例**:
```bash
# 分析单日
python main.py analyze --stock 300986.SZ --date 20260105

# 分析日期范围
python main.py analyze --stock 300986.SZ --start-date 20251231 --end-date 20260105

# 详细分析
python main.py analyze --stock 300986.SZ --date 20260105 --detail
```

#### 4. download - 数据下载
```bash
python main.py download --date 20260105 --type tick
```

**参数**:
- `--date`, `-d`: 交易日期 (默认今天)
- `--type`: 数据类型: tick/kline/all (默认all)
- `--universe`, `-u`: 股票池CSV文件路径
- `--workers`, `-w`: 并发workers (默认4)

**示例**:
```bash
# 下载今日所有数据
python main.py download

# 下载指定日期Tick数据
python main.py download --date 20260105 --type tick

# 下载指定股票池数据
python main.py download --date 20260105 --universe data/candidates.csv

# 高并发下载
python main.py download --date 20260105 --workers 8
```

#### 5. verify - 数据验证
```bash
python main.py verify --date 20260105
```

**参数**:
- `--date`, `-d`: 交易日期 (默认今天)
- `--type`: 验证类型: tick/kline/all (默认all)
- `--fix`: 自动修复缺失数据

**示例**:
```bash
# 验证今日数据
python main.py verify

# 验证指定日期
python main.py verify --date 20260105

# 验证并修复
python main.py verify --date 20260105 --fix
```

#### 6. monitor - 实时监控
```bash
python main.py monitor --mode event
```

**参数**:
- `--mode`, `-m`: 模式: event/cli/auction (默认event)
- `--interval`, `-i`: 监控间隔秒数 (默认3)

**示例**:
```bash
# 启动事件驱动监控（推荐）
python main.py monitor

# 或明确指定
python main.py monitor --mode event

# 启动CLI监控终端
python main.py monitor --mode cli

# 启动集合竞价监控
python main.py monitor --mode auction
```

#### 7. simulate - 历史模拟
```bash
python main.py simulate --start-date 20260224 --end-date 20260228
```

**参数**:
- `--start-date`: 开始日期 (YYYYMMDD, 必需)
- `--end-date`: 结束日期 (YYYYMMDD, 必需)
- `--watchlist`: 关注列表CSV文件
- `--phase`: Phase版本: 0.5/3 (默认0.5)

**示例**:
```bash
# Phase 0.5: 50样本历史回测
python main.py simulate --start-date 20260224 --end-date 20260228

# Phase 3: 实盘测试
python main.py simulate --phase 3 --watchlist data/watchlist.csv
```

---

## 🏗️ 项目架构

```
MyQuantTool/
├── main.py                     # 🎯 唯一CLI入口
├── SYSTEM_CONSTITUTION.md      # ⚖️ 系统宪法
├── logic/                      # 核心业务逻辑
│   ├── core/                   # 唯一事实来源 (SSOT)
│   │   ├── metric_definitions.py
│   │   ├── path_resolver.py
│   │   └── sanity_guards.py
│   ├── strategies/             # 策略引擎
│   │   ├── unified_warfare_core.py      # V18验证机
│   │   └── unified_warfare_scanner_adapter.py
│   ├── backtest/               # 回测引擎
│   │   ├── time_machine_engine.py       # 跨日连贯流
│   │   └── trade_interface.py           # 模拟/QMT交易
│   └── data_providers/         # 数据抽象层
│       └── qmt_manager.py
├── config/                     # 配置文件
├── data/                       # 数据池
│   ├── cache/                  # 原始数据缓存
│   └── backtest_out/           # 回测输出
│   └── memory/                 # 跨日记忆 (ShortTermMemory)
├── tests/                      # 单元测试
│   └── unit/core/              # 核心算法测试
```

---

## 🧠 V18 核心特性
### 高分率基础分 (线性极值映射)
```python
# 换手率和涨幅的二维插值
base_score = interpolate2d(
    turnover=[5, 10, 15, 20],      # 换手档位
    change=[5, 8, 10],             # 涨幅档位
    score_matrix=[[10,20,30],      # 5%换手
                  [25,35,45],      # 10%换手
                  [40,50,60],      # 15%换手
                  [55,65,75]]      # 20%换手
)
```

### 横向吸血乘数 (Cross-Sectional PK)
```python
# 资金净流入占比 = 净流入 / 流通市值
# 全市场排名，前10%×1.5，前30%×1.3，前50%×1.0，后50%×0.7
multiplier = cross_sectional_ranking(ratio_stock, percentile_map)
```

### VWAP 惩罚打分制
```python
# 修复前(Bug): final_score = base_score × multiplier × (sustain/100)  # 导致0.0
# 修复后(正确): final_score = base_score × multiplier - penalty

final_score = base_score * multiplier
if current_price < vwap:
    final_score -= 20  # 惩分，不是乘数
final_score = max(0, final_score)  # 永不为0
```

---

## ⏰ 全息时间机器 (跨日连贯流)

### 跨日记忆衰减机制
```python
# ShortTermMemory.json 存储强势股
# 每日收盘后执行衰减
# 1. 记忆值*= 0.5
# 2. 连续2日不上榜 -> 删除
# 3. 分数 < 10 -> 删除

{
  "300875.SZ": {
    "score": 85.5,
    "absent_days": 0,
    "last_decay_date": "20251231"
  }
}
```

### 每日回测流程
```
1. QMT SNAPSHOT粗筛(5000→约500)
2. 三防线过滤 (~500→约50)
3. V18验证机打分
4. 生成当日战报Top 20
5. 执行记忆衰减
6. 次日继承记忆
```

---

## ✅ 测试验证

```bash
# 运行单元测试
pytest tests/unit/core/ -v

# 测试内容包括:
# - Test 01: Sustain惩罚制测试
# - Test 02: 高分率基础分测试
# - Test 03: VWAP惩罚打分制测试
# - Test 04: final_score永不为0测试
# - Test 05: 优质股vs垃圾股区分度测试
```

---

## 📊 历史版本演进

| 版本 | 核心特性 | 状态 |
|------|----------|------|
| V11-V16 | 半路战法 + 龙头战法 | 🗑️ 已废弃 |
| V17 | Portfolio层资金调度 | 🗑️ 已废弃 |
| V18 | 高分率基础分 + VWAP惩罚 | ✅ 核心 |
| P9 | 架构重造 (492,542行删除) | ✅ 已合并 |
| P9.2 | 真相隔离 (真Core vs 假Core) | ✅ 已合并 |
| P14 | QMTRouter熔断机制 | ✅ 已合并 |
| P15 | 记忆衰减机制 | ✅ 当前 |

---

## 🔧 核心模块

| 模块 | 路径 | 说明 |
|------|------|------|
| QMTRouter | `logic/data_providers/fallback_provider.py` | VIP→L1→熔断责任制链 |
| TimeMachine | `logic/backtest/time_machine_engine.py` | 跨日连贯流+记忆衰减 |
| MetricDefinitions | `logic/core/metric_definitions.py` | 统一算子字典 |
| SanityGuards | `logic/core/sanity_guards.py` | 数据护栏 |

---

## ❌ 禁止事项

1. 🗑️**禁止** 在主目录创建 `.py` 文件 (野脚本)
2. 🗑️**禁止** 使用模拟数据 (必须真实Tushare/QMT)
3. 🗑️**禁止** 直接运行子模块 (`python logic/xxx.py`)
4. 🗑️**禁止** 硬编码路径或魔法数字
5. 🗑️**禁止** 异常静默吞没 (必须Fail Fast)
6. 🗑️**禁止** 创建tools/目录下的新文件

---

**最终强调**: 所有操作必须通过 `main.py` CLI入口。QMT是唯一数据源，熔断即停止。