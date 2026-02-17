# MyQuantTool 信号与资金分配接口契约文档

**版本**: V1.0  
**日期**: 2026-02-17  
**作者**: CTO + AI项目总监  
**目的**: 统一战法信号层、扫描层、资金分配层之间的接口规范，确保工程方向一致

---

## 一、整体数据流与分层约定

系统按数据流可分为四层，每一层都有清晰输入/输出约定：

### 1. 数据层（DataProvider / CapitalFlowProvider）
负责将 QMT Tick / Level2 / Level1 / AkShare T-1 等，抽象成统一的行情快照与资金流特征。

### 2. 事件层（Event / Detector / UnifiedWarfareCore）
负责在单票/多票数据上识别 HalfwayBreakout、LeaderCandidate、DipBuyCandidate 这类战法事件，输出统一的 TradingEvent。

### 3. 扫描层（FullMarketScanner / EventDrivenScanner）
负责在全市场维度聚合事件和因子，形成"机会池"和多维打分，用于后续资金分配。

### 4. 资金分配层（CapitalAllocator / Portfolio）
负责基于机会池、资金约束与风险约束，输出下单/减仓/清仓决策，这是**唯一的资金调度入口**。

### 核心原则

所有模块必须遵守：
- **战法模块只产生事件/打分，不得直接做下单决策**
- **资金模块只消费标准化信号/事件，不得向下依赖具体战法实现**

---

## 二、数据层接口契约

### 2.1 行情快照接口：MarketSnapshot

数据层向上暴露的最小行情信息单位为 MarketSnapshot，对应某一时刻、某一股票的基础行情。

#### 结构约定

```python
{
    "code": str,                    # 股票代码，如 "300750.SZ"
    "timestamp": datetime,          # 毫秒精度时间戳，对齐 QMT Tick / 1m bar 的时间
    "price": float,                 # 当前成交价（若为 bar，则为收盘价）
    "open": float | None,           # 可选，若有 1m/5m K 线数据则填充
    "high": float | None,           # 同上
    "low": float | None,            # 同上
    "close": float | None,          # 同上
    "volume": float,                # 当日累计成交量（股或手），Tick/分钟线统一用"从日内 0 开始递增"的口径
    "amount": float,                # 当日累计成交额
    "bid_price1~5": float | None,   # Level2/Level1 挂单价，如无则为 None
    "ask_price1~5": float | None,   # 同上
    "bid_vol1~5": float | None,     # 对应档位挂单量
    "ask_vol1~5": float | None      # 同上
}
```

#### 来源约定

- 有 Level2 → 直接填
- 无 Level2 有 Tick/Level1 → 从 Tick 推断填
- 无 Tick 时不得伪造，字段保持 None，仅可用于日级回测

### 2.2 资金流接口：CapitalFlowSnapshot

资金流向是项目哲学的底座，统一封装为 CapitalFlowSnapshot。

#### 结构约定

```python
{
    "code": str,                    # 股票代码
    "timestamp": datetime,          # 时间戳
    "main_net_inflow": float,       # 主力净流入金额（元），正为流入，负为流出
    "main_buy": float,              # 主力买入金额
    "main_sell": float,             # 主力卖出金额
    "retail_net_inflow": float,     # 散户净流入，方向同上
    "turnover_rate": float | None,  # 当日换手率（可来自 Tushare/日线）
    "source": str                   # 明确标记数据来源："LEVEL2" / "TICK_L1" / "AK_T1"
}
```

#### DataProvider / CapitalFlowProvider 约定

```python
class DataProvider:
    def get_market_snapshot(code: str, ts: datetime) -> MarketSnapshot:
        """获取行情快照"""
        pass
    
    def get_capital_flow(code: str, ts: datetime) -> CapitalFlowSnapshot:
        """获取资金流快照"""
        pass
    
    def is_realtime() -> bool:
        """判断当前是否为实盘模式"""
        pass
    
    def is_backtest() -> bool:
        """判断当前是否为回测模式"""
        pass
```

---

## 三、事件层接口契约

### 3.1 事件类型：EventType

统一使用枚举型事件类型，至少包含：

- `OPENING_WEAK_TO_STRONG`（竞价弱转强）
- `HALFWAY_BREAKOUT`（半路突破）
- `LEADER_CANDIDATE`（龙头候选）
- `DIP_BUY_CANDIDATE`（低吸候选）

实现上可以是 Enum/字符串常量，但在日志和存储中必须使用一致的标识。

### 3.2 交易事件：TradingEvent

战法检测器、UnifiedWarfareCore、EventDrivenScanner 全部以 TradingEvent 为统一载体。

#### 字段约定

```python
{
    "event_type": EventType,        # 事件类别
    "stock_code": str,              # 如 "300750.SZ"
    "timestamp": datetime,          # 触发事件的时间戳
    "confidence": float,            # 0.0–1.0 的置信度
    "factors": Dict[str, Any],      # 事件的关键因子
    "context": Dict[str, Any],      # 额外信息
    "trace_id": str | None          # 可选，用于串联一次扫描/决策流程中的所有事件
}
```

#### confidence 语义约定

- **0.0–0.3**：弱信号/噪音
- **0.3–0.6**：一般性机会
- **0.6–1.0**：高置信度事件

#### factors 示例

**Halfway事件**：
```python
{
    "volatility": 0.02,             # 平台期波动率
    "volume_surge": 2.5,            # 量能放大倍数
    "breakout_strength": 0.03       # 突破强度
}
```

**Leader事件**：
```python
{
    "sector_rank": 1,               # 板块排名
    "change_pct": 0.08,             # 涨幅
    "leader_gap": 1.5               # 领先幅度
}
```

### 3.3 战法检测器接口：BaseEventDetector

所有战法检测器必须实现统一接口，不允许出现"战法直接下单"的行为。

#### 接口约定

```python
class BaseEventDetector(Protocol):
    def detect(
        self, 
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TradingEvent | None:
        """
        检测事件
        
        Args:
            tick_data: 当前 tick 或 bar 的精简字段（code, price, volume, timestamp 等）
            context: 已准备好的上下文，如：
                    - 最近 N 个价格/成交量序列
                    - 当日资金流特征
                    - 行业/概念数据
                    
        Returns:
            检测到则返回 TradingEvent，否则返回 None
        """
        pass
```

#### 检测器不得做的事

- ❌ 不允许内部计算仓位或资金分配
- ❌ 不允许调用下单接口
- ✅ 只负责"判有没有事件、事件质量如何"

### 3.4 统一战法核心：UnifiedWarfareCore

UnifiedWarfareCore 作为事件路由中心，负责管理多个 Detector 并统一对外暴露接口。

#### 核心接口

```python
class UnifiedWarfareCore:
    def process_tick(
        self,
        tick_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> list[TradingEvent]:
        """
        处理单个tick，检测所有战法事件
        
        Args:
            tick_data: 单只股票当前tick
            context: 上下文
            
        Returns:
            该tick下所有触发的TradingEvent列表（可能为0~多条）
        """
        pass
```

#### 内部职责

1. 注册各类 Detector（Halfway、Leader、DipBuy 等）
2. 统一处理异常（单个 Detector 异常不能拖垮整个 Core）
3. 负责为 Detector 准备一致的 context 结构

---

## 四、扫描层与事件驱动接口契约

### 4.1 FullMarketScanner 输出契约

FullMarketScanner 是全市场机会筛选的总控，输出的是"当日机会池"，而不是具体下单指令。

#### 输出结构：ScanResult

```python
{
    "date": str,                    # 日期
    "candidates": list[Candidate]   # 候选列表
}
```

#### Candidate 结构

```python
{
    "code": str,                    # 股票代码
    "score": float,                 # 0–1 综合机会分
    "reasons": list[str],           # 例如：["L2_inflow_strong", "sector_resonance_A+B"]
    "signals": list[TradingEvent]   # 将 UnifiedWarfareCore 提供的事件附在这里
}
```

### 4.2 EventDrivenScanner 接口

EventDrivenScanner 负责实时订阅 Tick 并发布事件。

#### 接口约定

```python
class EventDrivenScanner:
    def on_tick(self, tick: MarketSnapshot):
        """
        1. 更新内部context（价格/量/资金历史等）
        2. 调用 UnifiedWarfareCore.process_tick 获取TradingEvent列表
        3. 将事件发布给 EventPublisher
        """
        pass
```

#### EventPublisher

```python
class EventPublisher:
    def subscribe(
        self, 
        event_type: EventType, 
        callback: Callable[[TradingEvent], None]
    ):
        """订阅特定类型的事件"""
        pass
    
    def publish(self, event: TradingEvent):
        """发布事件"""
        pass
```

资金层或日志模块只需订阅自己关心的 EventType。

---

## 五、资金分配层接口契约

### 5.1 分配输入：SignalForAllocation

CapitalAllocator 的输入不是"裸事件"，而是对每只股票在当前时刻的综合画像。

#### 结构约定

```python
{
    "stock_code": str,                  # 股票代码
    "timestamp": datetime,              # 时间戳
    "opportunity_score": float,         # 来自 full_market_scanner 的综合机会分
    "events": list[TradingEvent],       # 当日/当刻所有重要事件列表
    "capital_factors": Dict[str, float],# 来自资金流的特征
    "risk_factors": Dict[str, float]    # 风险因子
}
```

#### capital_factors 示例

```python
{
    "main_net_inflow_ratio": 0.05,      # 主力净流入 / 流通市值
    "sustained_inflow_score": 0.7,      # 持续流入评分
    "tail_rally_risk": 0.2              # 尾盘拉升风险
}
```

### 5.2 组合状态：PortfolioState

Allocator 还需要全局组合信息。

#### 结构约定

```python
{
    "cash_available": float,            # 可用现金
    "current_positions": Dict[str, Position],  # 当前持仓
    "max_drawdown_limit": float,        # 最大回撤限制，例如 -0.05
    "risk_budget": float                # 当前允许的整体风险暴露
}
```

#### Position 结构

```python
{
    "code": str,                        # 股票代码
    "shares": int,                      # 持仓数量
    "cost_price": float,                # 成本价
    "current_price": float,             # 当前价格
    "buy_time": datetime,               # 买入时间
    "unrealized_pnl": float,            # 浮动盈亏
    "return_pct": float,                # 收益率
    "hold_days": int                    # 持有天数
}
```

### 5.3 分配输出：AllocationDecision

#### 结构约定

```python
{
    "stock_code": str,                  # 股票代码
    "action": str,                      # "BUY" / "SELL" / "HOLD" / "REDUCE"
    "target_position": float,           # 目标仓位（相对总权益的比例，如 0.05 表示 5% 仓位）
    "reason": str,                      # 简要说明（如 "HALFWAY_BREAKOUT + Strong Inflow"）
    "stop_loss": float | None,          # 止损价格或比例
    "take_profit": float | None         # 止盈价格或比例
}
```

#### CapitalAllocator 接口

```python
class CapitalAllocator:
    def allocate(
        self,
        signals: list[SignalForAllocation],
        portfolio: PortfolioState
    ) -> list[AllocationDecision]:
        """
        资金分配决策
        
        Args:
            signals: 全市场或当前关注列表的 SignalForAllocation
            portfolio: 当前组合状态
            
        Returns:
            一串下单/调仓决策，交给执行层
        """
        pass
```

#### 硬约束

- ✅ 所有实际下单前必须经 CapitalAllocator 决策
- ❌ 战法模块和扫描模块不得直接构造订单

---

## 六、回测与实盘执行契约

### 回测引擎接口

```python
def run_backtest(
    engine: BacktestEngine,
    data_provider: DataProvider,
    strategy: Callable[[MarketSnapshot, CapitalFlowSnapshot], AllocationDecision]
):
    """
    运行回测
    
    Args:
        engine: 回测引擎
        data_provider: 数据提供器
        strategy: 策略函数，接收行情和资金流，返回分配决策
    """
    pass
```

### 实盘执行

实盘执行模块订阅 CapitalAllocator 的决策流，并与 QMT 下单 API 对接。

### 核心原则

无论回测还是实盘，**事件层 / 扫描层 / 资金层接口保持完全一致**，保证"所见即所得"，避免逻辑分叉。

---

## 七、实施路线图

### V17.0（2/24前）：资金流主线优先

- ✅ 冻结统一战法功能开发（保留代码，但不参与实盘）
- ✅ 确保 FullMarketScanner + CapitalAllocator 接口符合本契约
- ✅ 统一战法事件仅作被动记录（不参与下单）

### V17.1（2/24-3月中）：离线评估统一战法

- ✅ 使用 `halfway_sample_miner.py` 自动挖掘候选样本
- ✅ 人工标注 20-50 个正负样本
- ✅ 使用 `run_halfway_replay_backtest.py` 做专题回放

### V18.0（3月后）：战法融合

- ✅ 按本契约设计"资金×战法融合公式"
- ✅ 在 CapitalAllocator 中增加战法信号权重维度
- ✅ 小仓位验证融合效果

---

## 八、违规检查清单

在代码审查时，检查以下违规行为：

- [ ] Detector 内部是否计算了仓位？
- [ ] Detector 是否直接调用了下单接口？
- [ ] CapitalAllocator 是否向下依赖了具体战法实现？
- [ ] 战法事件是否符合 TradingEvent 标准格式？
- [ ] 资金流数据是否标记了 source 字段？
- [ ] 回测和实盘是否使用了不同的接口？

---

## 附录：快速参考

### 数据流向图

```
MarketSnapshot / CapitalFlowSnapshot
    ↓
BaseEventDetector.detect() → TradingEvent
    ↓
UnifiedWarfareCore.process_tick() → list[TradingEvent]
    ↓
FullMarketScanner / EventDrivenScanner → ScanResult + TradingEvent
    ↓
CapitalAllocator.allocate() → AllocationDecision
    ↓
实盘执行 / 回测引擎
```

### 关键接口速查

| 接口 | 输入 | 输出 | 职责 |
|-----|------|------|------|
| BaseEventDetector.detect | tick_data, context | TradingEvent | 检测战法事件 |
| UnifiedWarfareCore.process_tick | tick_data, context | list[TradingEvent] | 路由多个检测器 |
| FullMarketScanner.scan | date, stock_list | ScanResult | 全市场筛选 |
| CapitalAllocator.allocate | signals, portfolio | list[AllocationDecision] | 资金分配决策 |

---

## 九、V17阶段生产约束（强制）

### 9.1 统一战法冻结状态（硬约束）

**状态**：🔒 **冻结（仅记录，不参与实盘决策）**

**实施方式**：
```python
# config/portfolio_config.json 中的硬开关
{
  "unified_warfare": {
    "enabled": false,           # V17阶段禁用
    "mode": "observe_only",     # 仅观察模式
    "log_events": true,         # 记录事件但不参与评分
    "participate_in_allocation": false  # 不参与资金分配
  }
}
```

**代码层检查点**：
- CapitalAllocator.allocate() 必须检查 `config['unified_warfare']['participate_in_allocation']`
- 为false时，TradingEvent只能被记录，不能影响SignalForAllocation.opportunity_score

### 9.2 唯一回测流水线（生死线）

**V17上线前唯一认可的回测命令**：
```bash
python backtest/run_tick_replay_backtest.py \
  --stock-codes config/hot_stocks.json \
  --start-date 2026-01-01 \
  --end-date 2026-02-15 \
  --output backtest/results/v17_validation.json
```

**使用的引擎**：`logic.strategies.backtest_engine.BacktestEngine`（统一引擎）

**禁止作为上线依据的脚本**：
- ❌ `backtest/run_halfway_replay_backtest.py`（私有引擎，研究用途）
- ❌ `backtest/run_tick_backtest.py`（TickBacktestEngine，私有实现）
- ❌ `backtest/run_comprehensive_backtest.py`（SimpleBacktestEngine，私有实现）

### 9.3 私有回测引擎降级声明

以下脚本已标记为**研究用途**，不得在V17上线决策中使用：

| 脚本 | 引擎类型 | 用途 | 状态 |
|------|---------|------|------|
| `run_halfway_replay_backtest.py` | 独立函数实现 | Halfway战法专题研究 | 🔒 研究用途 |
| `run_tick_backtest.py` | TickBacktestEngine | Tick策略快速验证 | 🔒 研究用途 |
| `run_comprehensive_backtest.py` | SimpleBacktestEngine | 综合策略测试 | 🔒 研究用途 |

**V18任务**：将这些脚本统一迁移到`BacktestEngine`框架下（Issue #待创建）

### 9.4 契约一致性检查（CI强制）

**必须通过的测试**：
```bash
python tests/test_contract_compliance.py
```

**检查项**：
1. Detector返回值schema合规性
2. strategies目录无交易接口import
3. CapitalAllocator输入输出契约合规性

**失败后果**：CI阻断，禁止合并到master

---

**文档维护**：本契约应由 CTO 和 AI项目总监共同维护，任何接口变更需双方确认。
