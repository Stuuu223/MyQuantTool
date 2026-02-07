# MyQuantTool 任务进度与方向

## 项目定位
**本系统目标**：在短线交易中，避免被资金出货坑杀，同时捕捉资金有序进攻的标的。

**风格定位**：
- 周期：短线为主
- 因子来源：偏资金 + 情绪
  - 资金面：主力净流入、多日资金合计、资金类型（HOTMONEY / INSTITUTIONAL）
  - 情绪面：诱多陷阱、冲高回落、连续涨停等模式
- 技术价量作为辅助（3日涨幅、连涨特征等）

## 今天完成的工作（2026-02-08）

### 1. 实现第3.5关：3日连涨资金不跟
- 创建 `logic/rolling_risk_features.py`，实现多日风险特征计算
- 修改 `logic/full_market_scanner.py`，添加第3.5关决策逻辑
- 决策树规则：`is_price_up_3d_capital_not_follow and ratio < 1%` → TRAP❌

### 2. 扩展equity_info数据覆盖
- 创建 `tasks/extract_multi_date_codes.py`，提取多日股票代码
- 创建 `tasks/sync_equity_info_multi_date.py`，同步多日股本数据
- 成功同步 2026-02-05 和 2026-02-06 两天的股本数据（92只股票）

### 3. 单元测试验证
- 添加3个新测试用例到 `tests/test_decision_tree_regression.py`
- 所有16个测试全部通过 ✅
- 修正了测试用例预期（ratio=0.8%且无特征时，应返回BLOCK❌而非PASS❌）

### 4. Git提交
- 代码已提交到本地git（commit待推送）
- GitHub推送因网络问题未完成

---

## 明天及后续任务方向

### A. 卖出决策树（优先级：高）
**目标**：回答"拿了的票明天怎么办？"

**需要实现**：
1. 创建独立的卖出决策树模块
2. 定义卖出触发条件：
   - is_risk_score_spike（风险评分飙升）
   - is_big_outflow_after_up（大涨后大幅流出）
   - is_break_down_ma（跌破均线）
   - is_capital_not_follow（资金不跟）
3. 输出决策：
   - 继续持有
   - 减仓
   - 清仓（止损/止盈/风险事件）

**文件规划**：
- `logic/sell_decision_tree.py` - 卖出决策树核心逻辑
- `tests/test_sell_decision_tree.py` - 单元测试

---

### B. 模拟持仓 + 回测框架（优先级：中）
**目标**：实现可回测的交易系统，验证策略收益率、胜率

**需要实现**：
1. 模拟持仓管理模块
   - 持仓列表（股票代码、数量、成本价、持仓时间）
   - 每日用快照驱动持仓更新

2. 简化回测引擎
   - 输入：历史快照序列
   - 逻辑：
     - 按买入决策树下单
     - 按卖出决策树处理持仓
     - 用收盘价/次日开盘价结算
   - 输出：
     - 总收益率、年化、最大回撤
     - 交易次数、胜率、平均盈亏、盈亏比

**文件规划**：
- `logic/portfolio_manager.py` - 持仓管理
- `logic/backtest_engine.py` - 回测引擎
- `tests/test_backtest.py` - 回测测试

---

### C. 用Tushare重建历史快照（优先级：低）
**目标**：补充历史数据，做长周期验证

**需要实现**：
1. 历史重建脚本
   - 输入：日期范围 + 标的池
   - 输出：模拟版 `full_market_snapshot_YYYYMMDD.json`

2. 重建逻辑
   - 调Tushare拉日线/技术因子
   - 按当前特征层逻辑生成布尔特征
   - 走同样的决策树，得到decision_tag

3. 数据分类
   - "真实快照"：QMT实盘扫描产生
   - "历史快照"：Tushare离线重建
   - 两者统一喂给回测引擎

**文件规划**：
- `tasks/rebuild_historical_snapshots.py` - 历史快照重建脚本
- `tests/test_historical_rebuild.py` - 重建测试

---

## 决策树当前状态

### 买入决策树（已实现）
```
第1关：ratio < 0.5% → PASS❌
第2关：ratio > 5% → TRAP❌
第3关：诱多 + 高风险 → BLOCK❌
第3.5关：3日连涨资金不跟 + ratio < 1% → TRAP❌
第4关：1-3% + 低风险 + 无诱多 → FOCUS✅
兜底：BLOCK❌
```

### 卖出决策树（待实现）
```
待设计...
```

---

## Git状态
- 分支：master
- 本地领先：1 commit
- 远程推送：待完成（网络问题）

---

## 下次启动AI时，直接问：
"## 项目架构

### 核心模块
```
MyQuantTool/
├── logic/                          # 核心逻辑层
│   ├── full_market_scanner.py      # 全市场扫描器（决策树主入口）
│   ├── rolling_risk_features.py    # 多日风险特征计算
│   ├── trap_detector.py            # 诱多陷阱检测
│   ├── capital_classifier.py       # 资金性质分类
│   ├── cache_replay_provider.py    # 快照回放提供器
│   └── data_manager.py             # 数据管理器
├── tasks/                          # 任务脚本
│   ├── run_event_driven_monitor.py # 事件驱动监控（主程序）
│   ├── sync_equity_info_multi_date.py # 股本数据同步
│   └── extract_multi_date_codes.py  # 提取多日股票代码
├── tests/                          # 单元测试
│   └── test_decision_tree_regression.py # 决策树回归测试
├── data/                           # 数据目录
│   ├── scan_results/               # 扫描快照
│   └── equity_info_tushare.json    # 股本信息
├── config/                         # 配置文件
│   └── config_system.py            # 系统配置
└── TASK_PLAN.md                    # 任务进度与方向
```

### 核心文件说明

| 文件 | 作用 | 优先级 |
|------|------|--------|
| `logic/full_market_scanner.py` | 决策树核心，包含所有关卡逻辑 | ⭐⭐⭐ |
| `logic/rolling_risk_features.py` | 多日风险特征计算（第3.5关特征层） | ⭐⭐⭐ |
| `logic/trap_detector.py` | 诱多陷阱检测（第3关特征层） | ⭐⭐⭐ |
| `logic/capital_classifier.py` | 资金性质分类（HOTMONEY/INSTITUTIONAL） | ⭐⭐ |
| `logic/cache_replay_provider.py` | 快照回放，用于复盘和回测 | ⭐⭐ |
| `tests/test_decision_tree_regression.py` | 决策树单元测试 | ⭐⭐⭐ |

### 数据流

```
QMT实时数据 → full_market_scanner → 决策树 → decision_tag
                                              ↓
                                    快照保存 (scan_results/)
                                              ↓
                                    回放 (cache_replay_provider)
```

### 必读文档

1. **TASK_PLAN.md**（本文件）
   - 任务进度与方向
   - 决策树状态
   - 下一步工作

2. **PROJECT_ARCHITECTURE.md**
   - 项目架构详解
   - 模块依赖关系
   - 开发规范

3. **tests/test_decision_tree_regression.py**
   - 决策树测试用例
   - 理解每个关卡的边界条件

---

## 下次启动AI时，直接问：
"请读取 TASK_PLAN.md 和 PROJECT_ARCHITECTURE.md，告诉我当前任务进度和下一步应该做什么？""