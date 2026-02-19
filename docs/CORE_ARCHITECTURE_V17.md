---
version: V17.0.0
updated: 2026-02-19
scope: 技术架构总览
author: MyQuantTool Team
---

# MyQuantTool 核心架构 V17

> **权威关系**: 本文档为知识库的技术化压缩，业务细节以 `KNOWLEDGE_BASE_V17.md` 为准。

---

## 系统分层

```
┌─────────────────────────────────────────────────────────────┐
│                    用户入口层                                │
│  main.py / start_app.py / CLI                               │
├─────────────────────────────────────────────────────────────┤
│                    调度层                                    │
│  EventDrivenMonitor / FullMarketScanner / Portfolio         │
├─────────────────────────────────────────────────────────────┤
│                    服务层                                    │
│  StrategyService / CapitalService / RiskService             │
├─────────────────────────────────────────────────────────────┤
│                    数据层                                    │
│  ICapitalFlowProvider (level2/level1/qmt_tick/dongcai)      │
├─────────────────────────────────────────────────────────────┤
│                    基础设施层                                │
│  QMT / Tushare / AkShare / 本地缓存                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. EventDrivenMonitor

**文件**: `tasks/run_event_driven_monitor.py`

**职责**: 盘中实时抓右侧起爆

**关键流程**:
```
候选池 → 三漏斗筛选 → 策略评分 → Portfolio决策 → 执行
```

### 2. FullMarketScanner

**文件**: `logic/strategies/full_market_scanner.py`

**职责**: 盘后/历史复盘

**关键流程**:
```
全市场 → 三漏斗筛选 → 策略评分 → 结果输出
```

### 3. Portfolio层

**文件**: `logic/portfolio/capital_allocator.py`

**职责**: 账户级资金调度

**关键逻辑**:
- 断层优势检测: Top1 > Top2 × 1.5 → 单吊
- 持仓vs候选PK: 更优机会 → 换仓
- 动态仓位: 1只(90%) / 2只(60%+40%) / 3只(50%+30%+20%)

---

## 三漏斗架构

```
┌──────────────────────────────────────────┐
│  Level 1: 流动性筛选                      │
│  - 成交额 > 阈值                          │
│  - 换手率 > 阈值                          │
├──────────────────────────────────────────┤
│  Level 2: 形态筛选                        │
│  - 涨跌幅区间                             │
│  - 价格位置                               │
├──────────────────────────────────────────┤
│  Level 3: 资金筛选                        │
│  - 主力净流入分位数                       │
│  - 资金攻击强度                           │
└──────────────────────────────────────────┘
```

---

## 数据流架构

### 资金流抽象

```python
ICapitalFlowProvider (抽象接口)
    ├── Level2TickProvider   # Level-2 逐笔（付费）
    ├── Level1InferenceProvider  # Level-1 推断（免费）
    ├── QmtTickCapitalFlowProvider  # QMT Tick 推断
    └── DongCaiT1Provider    # 东方财富 T-1
```

**降级链**: level2 → level1 → qmt_tick → dongcai

**工厂方法**:
```python
# 实时模式
provider = DataProviderFactory.create_for_mode('live')

# 回放模式
provider = DataProviderFactory.create_for_mode('replay')
```

---

## 版本变更记录

| 版本 | 关键变更 |
|------|----------|
| V17.0.0 | Portfolio层、相对分位数、文档精简、资金流路线A |
| V16.x | 去掉新闻、Rich CLI |
| V12.1.0 | 初始架构（V12过滤器已废弃） |

---

**详细设计**: 参见 `KNOWLEDGE_BASE_V17.md`
