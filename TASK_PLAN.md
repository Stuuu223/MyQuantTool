# MyQuantTool 任务进度与方向

## 项目定位

**本系统目标**：在短线交易中，避免被资金出货坑杀，同时捕捉资金有序进攻的标的。

**风格定位**：
- **短线、资金面为主，情绪/技术做过滤的防雷 + 打板辅助系统**
- 周期：短线为主
- 因子来源：偏资金 + 情绪
  - 资金面：主力净流入、多日资金合计、资金类型（HOTMONEY / INSTITUTIONAL）
  - 情绪面：诱多陷阱、冲高回落、连续涨停等模式
- 技术价量作为辅助（3日涨幅、连涨特征等）

**明确两类场景**：
1. **避坑**：诱多、冲高回落、资金出货
2. **进攻**：资金有序进攻、低风险 FOCUS✅

---

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

### 4. 创建文档和示例
- 创建 `TASK_PLAN.md` 和 `PROJECT_ARCHITECTURE.md`
- 创建 `temp_gate35_example.json`，展示第3.5关触发时的JSON结构

### 5. Git提交
- 代码已成功推送到 GitHub ✅

---

## 明天具体安排（2026-02-09）

### 整体目标
做一个最简闭环：**买入信号 → 模拟持仓 → 卖出逻辑 → 回测统计**，同时给未来 Tushare 补历史留接口。

---

### Step 1：定"系统赚什么钱"（5分钟）

**写死一句风格描述**：
> 短线、资金面为主，情绪/技术做过滤的防雷 + 打板辅助系统。

**明确两类场景**：
1. **避坑**：诱多、冲高回落、资金出货
2. **进攻**：资金有序进攻、低风险 FOCUS✅

**输出**：更新 README.md 或 TASK_PLAN.md 的"项目定位"部分。

---

### Step 2：定义"卖出决策树 v0"（拿了的票明天怎么办）

**只做一个最小可用版本，输入也是布尔特征，不碰原始 K 线**

**输入特征示例**（都可以从现有/可补数据算出来）：
- `is_big_outflow_after_up`：放量上涨后的大额净流出
- `is_risk_score_spike`：risk_score 突然从 <0.4 跳到 ≥0.6
- `is_break_down_recent_low`：跌破最近 N 日低点
- `is_gain_over_x_percent`：浮盈超过比如 8%

**输出标签**：HOLD / PART_EXIT / FULL_EXIT

**建议格式**：先用伪代码/表格把这棵树写出来（最多10行以内）

**示例**：
```
if is_gain_over_8_percent:
    return PART_EXIT  # 浮盈8%，先减一半

if is_big_outflow_after_up:
    return FULL_EXIT  # 放量上涨后大幅流出，清仓

if is_risk_score_spike:
    return FULL_EXIT  # 风险评分飙升，清仓

if is_break_down_recent_low:
    return FULL_EXIT  # 跌破近期低点，清仓

return HOLD  # 默认持有
```

---

### Step 3：搭"模拟持仓 + 回测骨架"

**不追求完美撮合，只要能跑完一段历史/快照**

**状态结构**：
```python
positions = {
    "code": {
        "qty": 1000,          # 持股数量
        "cost": 10.5,         # 成本价
        "first_buy_date": "2026-02-06"
    }
}
cash = 1000000  # 初始资金
```

**每个交易日流程**：
1. 读当日快照（真实或未来的 Tushare 重建快照）
2. 对所有标记为 FOCUS✅ 的票，按简单规则开仓（例如最多同时持 N 只，每只固定 5% 仓位）
3. 对已有持仓，调用"卖出决策树 v0"，决定是否部分/全部卖出
4. 用日线收盘价结算持仓市值，记录账户净值

**输出统计**：
- 曲线：每日净值
- 汇总：总收益率、最大回撤、交易次数、胜率、平均盈亏

**明天可以先把这个"伪代码流程 + 状态结构"确定下来**

---

### Step 4：给 Tushare 补历史留接口（只设计数据结构）

**先不真的撸数据，先定"历史快照"的规范**

**文件名**：`full_market_snapshot_YYYYMMDD_rebuild.json`

**最少字段**：
```json
{
  "scan_time": "2026-02-06T09:45:21.390438",
  "mode": "rebuild",
  "results": {
    "opportunities": [
      {
        "code": "601869.SH",
        "date": "2026-02-06",
        "price": 10.5,
        "pct_chg": 2.5,
        "volume": 500000000,
        "flow_3d_sum": -4200000.0,  // 可为空
        "tech_factors": {
          "ma5": 10.2,
          "ma10": 9.8
        },
        "decision_tag": "FOCUS✅"
      }
    ]
  }
}
```

**规则**：
- 能从 Tushare 算到的特征 → 和现在特征层同名
- 算不到的 → 用 null，让决策树自动走兜底

**以后只要写一个 `rebuild_snapshot_from_tushare(date)` 按这个 schema 存文件，就能直接喂给 Step 3 的回测引擎**

---

## 下次工作顺序建议

结合当前状态，下次建议顺序：

1. **筛出真实样本、做一张10-20只票的3.5关命中效果表**
   - 使用 `temp_gate35_example.json` 作为结构范本
   - 从真实快照中筛选出被第3.5关拦截的股票
   - 分析这些股票的后续走势，验证第3.5关的有效性

2. **先把"卖出决策树 v0"的规则表画出来**（最多10行以内）

3. **再把"模拟持仓 + 回测"的状态和每日日志结构定清楚**

4. **最后再看重建历史快照需要哪些字段，顺手把 schema 定了**

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
预计输出：HOLD / PART_EXIT / FULL_EXIT
```

---

## 项目架构

### 核心模块
```
MyQuantTool/
├── logic/                          # 核心逻辑层
│   ├── full_market_scanner.py      # 全市场扫描器（决策树主入口）
│   ├── rolling_risk_features.py    # 多日风险特征计算
│   ├── trap_detector.py            # 诱多陷阱检测
│   ├── capital_classifier.py       # 资金性质分类
│   ├── cache_replay_provider.py    # 快照回放提供器
│   ├── sell_decision_tree.py       # 卖出决策树（待实现）
│   ├── portfolio_manager.py        # 持仓管理（待实现）
│   └── backtest_engine.py          # 回测引擎（待实现）
├── tasks/                          # 任务脚本
│   ├── run_event_driven_monitor.py # 事件驱动监控（主程序）
│   ├── sync_equity_info_multi_date.py # 股本数据同步
│   ├── extract_multi_date_codes.py  # 提取多日股票代码
│   └── rebuild_historical_snapshots.py # 历史快照重建（待实现）
├── tests/                          # 单元测试
│   ├── test_decision_tree_regression.py # 决策树回归测试
│   ├── test_sell_decision_tree.py  # 卖出决策树测试（待实现）
│   └── test_backtest.py            # 回测测试（待实现）
├── data/                           # 数据目录
│   ├── scan_results/               # 扫描快照
│   │   ├── *_intraday.json         # 实时快照
│   │   └── *_rebuild.json          # 重建快照（待实现）
│   └── equity_info_tushare.json    # 股本信息
├── config/                         # 配置文件
│   └── config_system.py            # 系统配置
├── TASK_PLAN.md                    # 任务进度与方向（本文件）
└── PROJECT_ARCHITECTURE.md         # 项目架构详解
```

### 核心文件说明

| 文件 | 作用 | 优先级 | 状态 |
|------|------|--------|------|
| `logic/full_market_scanner.py` | 决策树核心，包含所有关卡逻辑 | ⭐⭐⭐ | ✅ 已实现 |
| `logic/rolling_risk_features.py` | 多日风险特征计算（第3.5关特征层） | ⭐⭐⭐ | ✅ 已实现 |
| `logic/trap_detector.py` | 诱多陷阱检测（第3关特征层） | ⭐⭐⭐ | ✅ 已实现 |
| `logic/capital_classifier.py` | 资金性质分类（HOTMONEY/INSTITUTIONAL） | ⭐⭐ | ✅ 已实现 |
| `logic/cache_replay_provider.py` | 快照回放，用于复盘和回测 | ⭐⭐ | ✅ 已实现 |
| `logic/sell_decision_tree.py` | 卖出决策树核心逻辑 | ⭐⭐⭐ | 🔜 待实现 |
| `logic/portfolio_manager.py` | 持仓管理 | ⭐⭐ | 🔜 待实现 |
| `logic/backtest_engine.py` | 回测引擎 | ⭐⭐ | 🔜 待实现 |
| `tests/test_decision_tree_regression.py` | 决策树单元测试 | ⭐⭐⭐ | ✅ 已实现 |
| `temp_gate35_example.json` | 第3.5关触发示例 | ⭐⭐ | ✅ 已创建 |

### 数据流

```
QMT实时数据 → full_market_scanner → 决策树 → decision_tag
                                              ↓
                                    快照保存 (scan_results/)
                                              ↓
                                    回放 (cache_replay_provider)
                                              ↓
                                    卖出决策树 (sell_decision_tree)
                                              ↓
                                    持仓管理 (portfolio_manager)
                                              ↓
                                    回测引擎 (backtest_engine)
```

---

## Git状态
- 分支：master
- 远程状态：已同步 ✅
- 最新提交：Add project architecture and task plan documentation (e7bfb8d)

---

## 下次启动AI时，直接问：

"请读取 TASK_PLAN.md 和 PROJECT_ARCHITECTURE.md，告诉我当前任务进度和下一步应该做什么？"

**或者更具体的问题**：
1. "筛出真实样本，做一张10-20只票的3.5关命中效果表"
2. "定义卖出决策树 v0 的规则表"
3. "设计模拟持仓 + 回测的状态结构和流程"
4. "定义 Tushare 重建历史快照的 schema"