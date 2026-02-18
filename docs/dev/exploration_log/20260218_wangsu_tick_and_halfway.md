# CASE: 网宿 Tick + HALFWAY + 资金攻击
# ID: CASE_2026_02_WANGSU

## 0. 背景 & 目标

- **为什么开始这条探索**：网宿科技（300017.SZ）在2026-01-26涨停，但HALFWAY策略未触发，需要研究原因
- **想回答的关键问题**：
  1. HALFWAY策略为什么错过网宿1月26日涨停？
  2. 资金攻击检测能否捕捉到网宿的涨停信号？
  3. 如何设计"形态错过但资金捕捉"的策略？

---

## 1. 当天进展 (2026-02-18)

### 1.1 做了什么
- 下载网宿科技tick数据（2025-11-18至2026-02-13）
- 运行基础tick回测（09:35买入，14:55卖出）
- 验证资金攻击检测（1月26日涨停日）
- 创建资金事件标注器（简化版V1）
- 接入资金事件标注到回测流程
- 运行热门样本回测（网宿+顽主30只）
- 检查TickProvider迁移需求

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

### 1.3 决策/动作
- **V12.1.0过滤器**：标记EXPERIMENTAL，默认禁用
- **资金事件标注**：创建`logic/utils/capital_event_annotator.py`（简化版V1）
- **热门样本回测**：创建`backtest/run_hot_cases_suite.py`并运行
- **TickProvider迁移**：3个脚本待迁移（顽主+网宿链路）
- **下一步**：TickProvider迁移顽主+网宿链路

---

## 2. 未解决问题

- **必填**：
  - 资金攻击的分位数阈值尚未确定（需要在顽主样本上回测）
  - OpeningTickStrategy尚未接入tick回测框架
  - 如何整合形态（HALFWAY）和资金（TrueAttack）两轴决策

---

## 3. 回顾链接

- **相关代码文件**：
  - `backtest/run_tick_backtest.py` - 基础tick回测（已修复）
  - `backtest/exp_capital_attack_backtest.py` - 资金攻击实验脚本
  - `logic/strategies/halfway_tick_strategy.py` - HALFWAY策略
  - `scripts/download_wangsu_tick.py` - 网宿tick下载脚本

- **相关数据**：
  - `data/qmt_data/datadir/SZ/0/300017/20260126` - 1月26日涨停日tick数据
  - `backtest/results/exp_capital_attack_wangsu.csv` - 资金攻击实验结果

---

**Owner**: AI项目总监  
**Status**: OPEN