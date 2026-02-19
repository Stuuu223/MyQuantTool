---
version: V17.0.0
updated: 2026-02-19
scope: 全项目权威知识库
author: MyQuantTool Team
---

# MyQuantTool 项目知识库 V17

> **权威声明**: 本知识库为 MyQuantTool 的**唯一权威业务与策略说明文档**。
> 所有架构文档（如 CORE_ARCHITECTURE）在出现冲突时，**以本知识库的最新版本为准**。

---

## 目录

1. [系统哲学](#系统哲学)
2. [系统核心](#系统核心)
3. [策略服务](#策略服务)
4. [资金服务](#资金服务)
5. [风险控制](#风险控制)
6. [数据接口](#数据接口)
7. [资金流抽象](#资金流抽象)
8. [研究样本](#研究样本)
9. [回测系统](#回测系统)
10. [历史实验记录](#历史实验记录)
11. [开发制度](#开发制度)

---

> **开发流程与角色分工详见 `.iflow/DEVELOPMENT_PARADIGM.md`**  
> 该文档是 AI 与工程协作的**唯一规范文档**，所有开发参与者必须遵守。

---

## 系统哲学

### 核心理念

```
资金为王 · 顺势而为 · 追随市场短线大哥 · 排除杂毛 · 小资金效率极致化 · 利用体量优势
```

### 关键决策

1. **禁止硬编码绝对阈值**：统一使用相对分位数 + 自校准
2. **资金流长期路线**：QMT Tick 实时推断为主，AkShare DDE T+1 为辅
3. **Portfolio 层**：账户曲线向上 + 机会成本最小化，最大回撤软约束 -12%

---

## 系统核心

### 三大核心入口

| 组件 | 文件 | 职责 |
|------|------|------|
| **eventdriven** | `tasks/run_event_driven_monitor.py` | 盘中实时抓右侧起爆（实盘执行） |
| **fullmarketscanner** | `logic/strategies/full_market_scanner.py` | 盘后/历史复盘同一套规则（研究/统计） |
| **Portfolio层** | `logic/portfolio/capital_allocator.py` | 仓位与账户决策：断层优势、持仓vs候选PK |

### 辅助组件

| 组件 | 职责 |
|------|------|
| **premarket** | 盘前预热：生成当日关注列表（顽主杯/龙虎榜/热门股） |
| **triple_funnel** | 三漏斗筛选：流动性/形态/资金三层过滤 |
| **monitor** | 系统监控：统一查看各模块状态与异常 |
| **竞价管理器** | 竞价数据收集 + 质量评估（虚高开/虚封单/竞价强度） |
| **下载管理器** | 统一下载 tick/分K/日线等历史数据 |
| **Universe管理** | 样本维护与分层（wanzhu_selected_150等） |

---

## 策略服务

### StrategyService

统一策略出口，不直接散落调用。

**战法列表**：

| 战法 | 说明 |
|------|------|
| **HALFWAY** | 半路战法：右侧起爆中段入场 |
| **TRUE_ATTACK** | 真资金攻击：主力大单突破 |
| **LEADER** | 龙头战法：板块领涨识别 |
| **TRAP** | 诱多识别：假突破过滤 |

---

## 资金服务

### CapitalService

资金因子统一出口，"资金为王"的落地实现。

**核心指标**：
- 主力净流入
- 资金分位数（相对阈值）
- 攻击强度

---

## 风险控制

### RiskService

给 Portfolio 和 eventdriven 提红线。

**约束条件**：
- 最大回撤 ≤ -12%（软约束）
- 单票风控
- 机会成本约束

---

## 数据接口

### 数据源优先级

| 优先级 | 数据源 | 用途 | 特点 |
|--------|--------|------|------|
| **1** | QMT | 优先 Level-2 逐笔，过期则用 Tick Level-1 推断 | 实时数据，盘中决策 |
| **2** | Tushare | 龙虎榜/概念/资金等辅助数据 | 研究辅助 |
| **3** | AkShare | T-1 资金/复盘辅助 | 限流、封禁风险，仅研究用 |

### 资金流数据路线

```
长期目标：QMT Tick 实时推断资金流
当前实现：AkShare DDE T+1 + QMT Level-1 推断
```

---

## 资金流抽象

### ICapitalFlowProvider

资金流必须通过统一抽象层，策略不直接碰 QMT 或 AkShare。

**接口定义** (`logic/data_providers/base.py`)：

```python
class ICapitalFlowProvider(ABC):
    def get_realtime_flow(self, code: str) -> CapitalFlowSignal
    def get_historical_flow(self, code: str, days: int) -> Dict
    def get_data_freshness(self, code: str) -> int
    def get_full_tick(self, code_list: List[str]) -> Dict
```

**实现类**：

| Provider | 说明 | 用途 |
|----------|------|------|
| Level2TickProvider | Level-2 逐笔数据 | 付费用户，实时决策 |
| Level1InferenceProvider | Level-1 Tick 推断 | 免费用户，实时决策 |
| QmtTickCapitalFlowProvider | QMT Tick 推断 | 回放/历史分析 |
| DongCaiT1Provider | 东方财富 T-1 DDE | 回测/研究 |

**自动降级链**：

```
level2 → level1 → qmt_tick → dongcai
```

**工厂创建** (`logic/data_providers/factory.py`)：

```python
# 实时模式
provider = DataProviderFactory.create_for_mode('live')

# 回放模式
provider = DataProviderFactory.create_for_mode('replay')
```

---

## 研究样本

### 样本分层

| 层级 | 来源 | 用途 |
|------|------|------|
| **核心** | 顽主杯 | 短线情绪周期大哥，主战场 |
| **辅助** | 龙虎榜 | 游资动向参考 |
| **辅助** | 热门股 | 市场热度参考 |
| **辅助** | 涨停板 | 强势股筛选 |

### Universe 管理

- 当前：`data/wanzhu_data/processed/wanzhu_selected_150.csv`
- 未来：迁移到远程 DB 统一管理

---

## 回测系统

### 核心能力

- Tick/分K 回放
- 参数优化
- 与实盘同一套策略

### 验证目标

研究哪些右侧起爆"有持续性"，反推策略参数，回灌 eventdriven/fullmarketscanner。

---

## 历史实验记录

### V12.1.0 过滤器（已废弃）

> **警告**: 以下过滤器已在 V17 标记为 **EXPERIMENTAL**，默认禁用。
> 真实数据通过率仅 0.11%，几乎全拒。

**包含内容**：
- 板块共振过滤器
- 动态阈值联级过滤
- 竞价校验联级

**废弃原因**：通过率过低，无法用于生产。

**未来方向**：从"一票否决"改造为"评分贡献"。

---

## 开发制度

> **详细规范见**: `.iflow/DEVELOPMENT_PARADIGM.md`

### 角色分工摘要

| 角色 | 职责 | 禁止事项 |
|------|------|----------|
| 老板 | 战略目标 + 红线 | 不负责实现细节 |
| CTO | 架构 + PR闸门 | 不得下放核心抽象修改权 |
| iFlow总监 | 拆任务 + 排节奏 | 不得改战略/架构红线 |
| AI项目总监 | 子任务Owner | 不得引入新架构层 |
| AI开发专家 | 实现 + 自测 | 不得无设计卡改核心模块 |

### 流水线四步

```
需求卡 → 设计卡 → 实现+自测 → CTO审计
```

### 越权红线

- 修改 `logic/data_providers/base.py` / `factory.py` → 必须CTO批准
- 删除脚本/模块 → 必须老板确认
- 调整资金流路线 → 必须老板确认

---

## 版本历史

| 版本 | 日期 | 关键变更 |
|------|------|----------|
| V17.0.0 | 2026-02-19 | 知识库重写，资金流路线A确认，文档精简 |
| V16.x | 2026-02-15 | 去掉新闻，引入 Portfolio |
| V12.1.0 | 2026-02-15 | 初始版本（过滤器已废弃） |

---

**维护说明**：所有重大裁决必须同步更新本知识库。
