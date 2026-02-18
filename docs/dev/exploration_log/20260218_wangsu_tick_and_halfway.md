# CASE: 网宿 Tick + HALFWAY + 资金事件 + 热门池
# ID: CASE_2026_02_WANGSU_TICK_AND_FUNDS

## CASE 元信息

- **Owner**: AI项目总监
- **Status**: OPEN
- **Universe**:
  - 时间窗口: 2026-01-15 ~ 2026-02-18
  - 热门定义: daily_top30_by_turnover+turnover_rate (TOP30_V1)
  - 额外个股: 网宿科技（300017.SZ）、经典诱多票（欢乐家、有友食品）
- **Data Sources**:
  - QMT Tick: data/qmt_data/datadir/
  - Tushare:日线/市值（成交额、换手率、涨跌幅、流通市值）
  - AkShare: 可选补充（资金流/DDE）

---

## 步骤1: 构建"CASE 宇宙"

### 1.1 时间窗口
- 热门池窗口: 2026-01-15 ~ 2026-02-18（20个交易日）
- Tick回放窗口: 2026-01-25 ~ 2026-02-18（保证Tick有数据）

### 1.2 宇宙构成
- **U_hot**: 最近20日的热门Top30去重池（来自 `data/hot_universe/monthly_pool/hot_pool_*.json`）
- **U_case_specific**: 网宿科技（300017.SZ）、经典诱多票（欢乐家、有友食品）
- **CASE总宇宙**: U = U_hot ∪ U_case_specific

**统计**: |U_hot| = X, |U_case_specific| = Y, |U| = Z（去重后）

---

## 步骤2: 资金事件标注规范

### 2.1 标注规则版本
- **Annotator Version**: V1.0
- **配置**: logic/utils/capital_event_annotator.py

### 2.2 阈值口径
- **市场攻击**: ratio ≥ 市场前3%, price_strength ≥ 市场前10%
- **行业攻击**: ratio ≥ 行业前1%, price_strength ≥ 行业前10%

### 2.3 数据源
- **ratio**: 主力净流入 / 流通市值（从资金流Provider + Tushare市值）
- **price_strength**: (当前价格 - 开盘价) / 开盘价

### 2.4 分位数参考集
- **market_reference**: 当日全市场有成交的股票
- **hot_reference**: 当日热门池子（可选，作为对照）

### 2.5 输出格式
- **路径**: `data/capital_events/{CASE_ID}/YYYYMMDD.json`
- **结构**: 见CTO方案

---

## 步骤3: Tick 回测规范

### 3.1 Tick数据宇宙
- **声明**: Tick数据是否覆盖U中所有股票
- **缺失**: 记录missing_tick_codes列表
- **数据目录**: `data/qmt_data/datadir/`

### 3.2 策略组合
- **strategies**: ["TRIVIAL", "HALFWAY"]
- **参数版本**: 
  - TRIVIAL: V17.0.0
  - HALFWAY: V17.0.0

### 3.3 回测配置
- **初始资金**: 100000
- **仓位规则**: 全仓进出
- **成本模型**:
  - 佣金: 万0.85
  - 印花税: 卖出千1
  - 滑点: 10bp
- **交易规则**: T+1限制、涨跌停阻断

---

## 步骤4: 报告输出规范

### 4.1 报告结构
- **CASE宇宙说明**: 时间窗口、热门池构造规则、总股票数、Tick覆盖率
- **资金事件统计**: 总攻击次数、按attack_type统计、攻击发生位置
- **策略响应情况**: TRIVIAL/HALFWAY的出手次数/胜率/平均收益
- **"资金事件触发但策略沉默"**: 发生日期列表
- **重点票明细**: 网宿1-26的资金事件标签、策略行为、后续表现

### 4.2 报告文件
- **路径**: `backtest/results/{CASE_ID}_REPORT_YYYYMMDD.md`
- **命名**: `CASE_2026_02_WANGSU_TICK_AND_FUNDS_REPORT_20260219.md`

---

## 0. 背景 & 目标

- **为什么开始这条探索**：网宿科技（300017.SZ）在2026-01-26涨停，但HALFWAY策略未触发，需要研究原因
- **想回答的关键问题**：
  1. HALFWAY策略为什么错过网宿1月26日涨停？
  2. 资金攻击检测能否捕捉到网宿的涨停信号？
  3. 如何设计"形态错过但资金捕捉"的策略？
  4. 热门池资金事件分布如何？

---

## 1. 当天进展 (2026-02-18)

### 1.1 做了什么
- 下载网宿科技tick数据（2025-11-18至2026-02-13）
- 运行基础tick回测（09:35买入，14:55卖出）
- 验证资金攻击检测（1月26日涨停日）
- 创建资金事件标注器（简化版V1）
- 接入资金事件标注到回测流程
- 运行热门样本回测（网宿+顽主30只）
- 创建热门Top30生成脚本（`scripts/build_daily_hot30.py`）
- 检查TickProvider迁移需求
- 更新CASE文档为最小闭环规范（按CTO要求）

### 1.2 关键发现
- **tick数据**：成功下载80+个交易日的tick数据
- **基础回测结果**：胜率59.09%，总收益14.80%
- **资金攻击检测**：1月26日正确触发（净流入122亿，评分1.00）
- **资金事件标注**：网宿1-26稳定点亮（ratio前3%，price_strength前10%）
- **热门样本回测**：
  - TRIVIAL: 出手1次，胜率100%
  - HALFWAY: 出手0次，胜率N/A
  - 资金事件触发次数: 1次（100%）
  - "资金事件触发但策略沉默"日期: 无
- **HALFWAY策略**：未触发（开盘急拉，不满足平台期特征）
- **TickProvider迁移**：发现3个脚本直接import xtdata（待迁移）
- **热门池构建**：创建`scripts/build_daily_hot30.py`，使用Tushare数据源

### 1.3 决策/动作
- **V12.1.0过滤器**：标记EXPERIMENTAL，默认禁用
- **资金事件标注**：创建`logic/utils/capital_event_annotator.py`（简化版V1）
- **热门样本回测**：创建`backtest/run_hot_cases_suite.py`并运行
- **TickProvider迁移**：3个脚本待迁移（顽主+网宿链路）
- **热门池构建**：创建`scripts/build_daily_hot30.py`（TOP30_V1规则）
- **下一步**：
  - 测试`build_daily_hot30.py`
  - 确保后台tick下载器能处理热股
  - 2-25前完成TickProvider迁移

---

## 2. 未解决问题

- **必填**：
  - 真实Tick数据验证：网宿1-26的资金事件标注需要在真实市场数据上验证
  - 热门池数据获取：`build_daily_hot30.py`需要配置Tushare Token并测试
  - TickProvider接口定义：需要实现`ensure_history`和`load_ticks`接口
  - 资金事件JSON输出：改造`CapitalEventAnnotator`增加`save_daily_events()`方法
  - Tick回测引擎改造：读取CASE宇宙+资金事件JSON
  - 2-25必须完成的任务：TickProvider迁移顽主+网宿链路

---

## 3. 回顾链接

- **相关代码文件**：
  - `logic/utils/capital_event_annotator.py` - 资金事件标注器（V1.0）
  - `scripts/build_daily_hot30.py` - 热门Top30生成脚本（TOP30_V1）
  - `backtest/run_tick_backtest.py` - 基础tick回测（已修复）
  - `backtest/exp_capital_attack_backtest.py` - 资金攻击实验脚本
  - `logic/strategies/halfway_tick_strategy.py` - HALFWAY策略
  - `scripts/download_wangsu_tick.py` - 网宿tick下载脚本
  - `scripts/download_wanzhu_tick_data.py` - 顽主tick下载脚本

- **相关数据**：
  - `data/qmt_data/datadir/SZ/0/300017/20260126` - 1月26日涨停日tick数据
  - `data/hot_universe/` - 热门池数据目录
  - `data/capital_events/` - 资金事件JSON目录
  - `backtest/results/exp_capital_attack_wangsu.csv` - 资金攻击实验结果
  - `backtest/results/hot_cases_report_v1_20260218.md` - 热门样本回测报告V1

---

**Owner**: AI项目总监  
**Status**: OPEN