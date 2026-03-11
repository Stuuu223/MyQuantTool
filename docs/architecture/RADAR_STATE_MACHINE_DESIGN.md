# 实盘雷达状态机架构设计

> CTO架构重构方案 - 解决伪时间折算和无状态扫描问题
> Date: 2026-03-11
> Version: V1.0

## 一、当前架构问题诊断

### 1.1 伪时间折算（致命脑补）
```python
# 当前错误代码 (run_live_trading_engine.py:L298)
flow_15min = current_amount * 0.35  # 用全天总量乘以拍脑袋系数
flow_5min = current_amount * 0.15   # 谎称是15分钟/5分钟流入
```
**问题**: 用当日累计成交额乘以硬编码系数，完全违背物理学真实计算原则

### 1.2 无状态扫描（失忆式雷达）
```python
# 当前问题
- 每次get_full_tick独立计算
- 没有历史状态维持
- 股票满足条件上榜，下一秒不满足就消失
```

### 1.3 导致的严重后果
- 000533.SZ Sustain=11.21x但CHG%=+0.85%（天量滞涨陷阱）
- 粗筛只有3只，真龙被错误公式挡在外面
- 拿着VIP Token当普通行情用

---

## 二、新架构设计：动态蓄水池（Stateful Pool）

### 2.1 核心概念

```
┌─────────────────────────────────────────────────────────────┐
│                    实盘雷达状态机架构                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 宽进粗筛 (Wide Funnel)                            │
│  ├── 输入: 全市场5191只股票                                  │
│  ├── 标准: Price_Momentum>0.8 + 换手率>阈值                  │
│  └── 输出: Candidate_Pool (候选蓄水池)                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Tick切片跟踪 (Tick Slicer)                        │
│  ├── 为每只候选股维护deque(maxlen=300)                       │
│  ├── 存储: (timestamp, price, amount, volume)               │
│  └── 计算: 真实ΔAmount = current - 15min_ago                │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 精细打分 (Precision Scoring)                      │
│  ├── 输入: 真实flow_15min, flow_5min                        │
│  ├── 计算: Sustain, MFE, Inflow_Ratio                       │
│  └── 输出: Top_Targets (机会池)                             │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: 动态剔除 (Dynamic Elimination)                    │
│  ├── 触发: MFE<1.2且Volume_Ratio>3.0                       │
│  ├── 触发: 价格跌破15分钟VWAP                               │
│  └── 动作: 从蓄水池剔除，打标签                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 状态定义

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from collections import deque
from typing import Optional

class StockState(Enum):
    """股票在雷达中的生命周期状态"""
    OUTSIDE = "outside"           # 在蓄水池外
    CANDIDATE = "candidate"       # 进入候选池
    TRACKING = "tracking"         # 正在跟踪
    OPPORTUNITY = "opportunity"   # 确认为机会
    ELIMINATED = "eliminated"     # 被剔除

@dataclass
class TickSnapshot:
    """Tick快照数据结构"""
    timestamp: datetime
    price: float
    amount: float          # 累计成交额
    volume: float          # 累计成交量
    high: float
    low: float
    open: float

@dataclass  
class StockTracker:
    """股票跟踪器 - 维持状态"""
    stock_code: str
    state: StockState
    enter_time: datetime   # 进入候选池时间
    tick_history: deque[TickSnapshot]  # 300个Tick历史
    
    # 实时计算指标
    current_price: float = 0.0
    current_amount: float = 0.0
    
    # 15分钟切片指标
    flow_15min: float = 0.0
    flow_5min: float = 0.0
    
    # 打分结果
    final_score: float = 0.0
    sustain_ratio: float = 0.0
    mfe: float = 0.0
```

### 2.3 核心算法

#### 算法1: 真实时间切片计算
```python
def calculate_real_flow(self, tracker: StockTracker) -> tuple[float, float]:
    """
    真实计算15分钟和5分钟流入
    不是用乘数，而是用真实的历史快照差值
    """
    if len(tracker.tick_history) < 2:
        return 0.0, 0.0
    
    current = tracker.tick_history[-1]
    
    # 找15分钟前的快照
    target_time_15min = current.timestamp - timedelta(minutes=15)
    snapshot_15min_ago = self._find_nearest_snapshot(tracker.tick_history, target_time_15min)
    
    # 找5分钟前的快照
    target_time_5min = current.timestamp - timedelta(minutes=5)
    snapshot_5min_ago = self._find_nearest_snapshot(tracker.tick_history, target_time_5min)
    
    # 真实流入 = 当前累计 - 历史累计
    flow_15min = current.amount - snapshot_15min_ago.amount if snapshot_15min_ago else 0.0
    flow_5min = current.amount - snapshot_5min_ago.amount if snapshot_5min_ago else 0.0
    
    return flow_15min, flow_5min
```

#### 算法2: 宽进粗筛标准
```python
def should_enter_candidate_pool(self, tick: TickSnapshot, pre_close: float) -> bool:
    """
    宽进粗筛：只有价格动能和换手率标准
    不计算复杂指标，快速筛选
    """
    # 价格动能 > 0.8 (死死咬住日内最高点)
    price_momentum = (tick.price - tick.low) / (tick.high - tick.low) if tick.high > tick.low else 0.0
    
    # 换手率 > 基础阈值 (如1%)
    turnover_rate = self._calculate_turnover(tick)
    
    return price_momentum > 0.8 and turnover_rate > 0.01
```

#### 算法3: 动态剔除机制
```python
def should_eliminate(self, tracker: StockTracker) -> tuple[bool, str]:
    """
    动态剔除：从蓄水池中移除不合格股票
    """
    # 剔除条件1: MFE<1.2且Volume_Ratio>3.0 (天量滞涨)
    if tracker.mfe < 1.2 and tracker.volume_ratio > 3.0:
        return True, "天量滞涨: 高换手低效率"
    
    # 剔除条件2: 价格跌破15分钟VWAP
    vwap_15min = self._calculate_vwap_15min(tracker)
    current_price = tracker.tick_history[-1].price if tracker.tick_history else 0.0
    if current_price < vwap_15min * 0.99:  # 跌破VWAP 1%
        return True, "跌破VWAP: 资金退潮"
    
    # 剔除条件3: Sustain>5.0但CHG%<2.0 (动能悖论)
    change_pct = self._calculate_change_pct(tracker)
    if tracker.sustain_ratio > 5.0 and change_pct < 0.02:
        return True, "动能悖论: 高Sustain低涨幅"
    
    return False, ""
```

---

## 三、实施计划

### Phase 1: 建立Tick历史队列
- 修改run_live_trading_engine.py
- 为每只候选股维护deque(maxlen=300)
- 每次get_full_tick更新队列

### Phase 2: 实现真实时间切片
- 替换flow_15min = current_amount * 0.35
- 实现真实ΔAmount计算
- 测试验证

### Phase 3: 宽进粗筛+动态蓄水池
- 简化粗筛标准
- 实现Candidate_Pool状态机
- 实现动态剔除逻辑

### Phase 4: 动能悖论熔断
- 添加Sustain>5.0且CHG%<2.0的剔除逻辑
- 验证000533.SZ案例

---

## 四、预期效果

### 修复前
```
000533.SZ: Sustain=11.21x, CHG%=+0.85%, MFE=3.2
→ 错误上榜，天量滞涨陷阱
```

### 修复后
```
000533.SZ: Sustain=11.21x, CHG%=+0.85%
→ 触发"动能悖论"剔除条件
→ 从蓄水池移除，打标签"派发剔除"
→ 不进入Top_Targets
```

### 修复前
```
粗筛: 3只 (错误公式挡出真龙)
```

### 修复后
```
粗筛: 300-500只进入Candidate_Pool
精细打分后: 20-30只真龙进入Top_Targets
```

---

## 五、CTO铁律检查清单

- [ ] 废除所有硬编码乘数（*0.35, *0.15等）
- [ ] 实现真实时间切片计算（ΔAmount）
- [ ] 建立300个Tick的内存队列
- [ ] 实现宽进粗筛（Price_Momentum>0.8）
- [ ] 实现动态蓄水池（进入后持续跟踪）
- [ ] 实现动态剔除（MFE<1.2且Volume_Ratio>3.0）
- [ ] 实现动能悖论熔断（Sustain>5.0且CHG%<2.0）
- [ ] 验证000533.SZ案例正确处理
