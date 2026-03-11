# 实盘雷达状态机架构设计文档

> **版本**: V1.0  
> **日期**: 2026-03-11  
> **作者**: CTO架构团队  
> **状态**: 已实施（部分）

---

## 一、问题背景

### 1.1 原有架构缺陷

旧版实盘雷达存在三大致命问题：

1. **伪时间折算**: 使用 `flow_15min = current_amount * 0.35` 估算，而非真实15分钟切片
2. **无状态扫描**: 每次get_full_tick都是独立计算，股票满足条件就上榜，下一秒不满足就消失
3. **双轨竞态**: `_run_radar_main_loop` 主循环与 `_on_tick_data` EventBus回调并行运行，共享signal_queue等dict，无锁保护

### 1.2 系统哲学

> "Live 和 Scan 同一个壳同一个灵魂，Scan 接收 Mock Tick 数据加速模拟真实实盘，参数只改一边，两边行为完全一致。"

---

## 二、状态机架构设计

### 2.1 四层漏斗架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 粗筛层 (UniverseBuilder)                          │
│  - 静态过滤: ST/退市/北交所                                  │
│  - 金额过滤: 5日均额 > 3000万                               │
│  - 量比过滤: >= 1.5倍                                       │
│  - 换手率过滤: 3% ~ 70%                                     │
│  输出: 5000只 → ~300只候选池                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: 候选池层 (Candidate Pool)                         │
│  - 宽进标准: price_momentum > 0.8                           │
│  - 维持15分钟Tick历史队列 (300个Tick)                       │
│  - 真实时间切片计算 flow_5min / flow_15min                  │
│  状态: CANDIDATE → TRACKING 或 ELIMINATED                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 跟踪层 (Tracking)                                 │
│  - 精细打分: 动能打分引擎计算 final_score                   │
│  - 动能悖论熔断: sustain > 5.0 且 change_pct < 2% → 剔除   │
│  - 动态淘汰: MFE < 1.2 且 volume_ratio > 3.0 → 剔除        │
│  状态: TRACKING → OPPORTUNITY 或 ELIMINATED                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: 机会/淘汰层                                       │
│  - OPPORTUNITY: 进入开火候选，等待3分钟抗重力测试           │
│  - ELIMINATED: 负样本收集，记录淘汰原因                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 状态定义

```python
class StockState(Enum):
    OUTSIDE = "outside"        # 在候选池外
    CANDIDATE = "candidate"    # 刚进入候选池
    TRACKING = "tracking"      # 正在跟踪打分
    OPPORTUNITY = "opportunity" # 确认机会
    ELIMINATED = "eliminated"  # 被剔除
```

### 2.3 状态转换规则

| 当前状态 | 条件 | 下一状态 | 原因 |
|---------|------|---------|------|
| OUTSIDE | price_momentum > 0.8 && turnover > 1% | CANDIDATE | 宽进粗筛通过 |
| CANDIDATE | 维持15分钟Tick历史 | TRACKING | 进入跟踪 |
| TRACKING | sustain > 5.0 && change_pct < 2% | ELIMINATED | 动能悖论熔断 |
| TRACKING | MFE < 1.2 && volume_ratio > 3.0 | ELIMINATED | 动态淘汰 |
| TRACKING | final_score >= 70 | OPPORTUNITY | 确认机会 |
| OPPORTUNITY | sustain_ratio < 1.2 | ELIMINATED | 3分钟测试失败 |

---

## 三、核心数据结构

### 3.1 TickSnapshot

```python
@dataclass
class TickSnapshot:
    timestamp: datetime
    price: float
    amount: float      # 累计成交额
    volume: float      # 累计成交量
    high: float
    low: float
    open: float
```

### 3.2 StockTracker

```python
@dataclass
class StockTracker:
    stock_code: str
    state: StockState
    enter_time: datetime
    tick_history: deque = field(default_factory=lambda: deque(maxlen=300))
    current_price: float = 0.0
    current_amount: float = 0.0
    flow_15min: float = 0.0
    flow_5min: float = 0.0
    final_score: float = 0.0
    sustain_ratio: float = 0.0
    mfe: float = 0.0
    elimination_reason: str = ""
```

---

## 四、核心算法

### 4.1 真实时间切片计算

```python
def _calculate_real_flow(self, tracker: StockTracker) -> Tuple[float, float]:
    """
    计算真实的15分钟和5分钟资金流入
    
    原理: 从tick_history中找到15分钟前和5分钟前的快照，
          用当前amount减去历史amount得到真实增量
    
    Returns:
        (flow_15min, flow_5min): 单位元
    """
    if len(tracker.tick_history) < 2:
        return 0.0, 0.0
    
    current = tracker.tick_history[-1]
    
    # 找到15分钟前的快照
    target_time_15min = current.timestamp - timedelta(minutes=15)
    snapshot_15min = self._find_nearest_snapshot(tracker.tick_history, target_time_15min)
    
    # 找到5分钟前的快照
    target_time_5min = current.timestamp - timedelta(minutes=5)
    snapshot_5min = self._find_nearest_snapshot(tracker.tick_history, target_time_5min)
    
    # 计算真实增量（amount是累计值，用差值）
    flow_15min = current.amount - snapshot_15min.amount if snapshot_15min else 0.0
    flow_5min = current.amount - snapshot_5min.amount if snapshot_5min else 0.0
    
    return flow_15min, flow_5min
```

### 4.2 动能悖论熔断

```python
def _check_kinetic_paradox(self, tracker: StockTracker, pre_close: float) -> Tuple[bool, str]:
    """
    检查动能悖论：高sustain但低涨幅
    
    案例: 000533.SZ Sustain=11.21x 但 CHG%=+0.85%
    含义: 主力努力但股价不涨，可能是天量滞涨陷阱
    
    Returns:
        (is_paradox, reason): 是否触发熔断及原因
    """
    if pre_close <= 0:
        return False, ""
    
    change_pct = (tracker.current_price - pre_close) / pre_close
    
    if tracker.sustain_ratio > self.kinetic_paradox_sustain_threshold and \
       change_pct < self.kinetic_paradox_change_threshold:
        return True, f"动能悖论: sustain={tracker.sustain_ratio:.2f}x 但涨幅={change_pct*100:.2f}%"
    
    return False, ""
```

### 4.3 动态淘汰

```python
def _should_eliminate(self, tracker: StockTracker) -> Tuple[bool, str]:
    """
    判断是否应该将股票从蓄水池中剔除
    
    淘汰条件:
    1. MFE < 1.2 且 Volume_Ratio > 3.0: 资金退潮，无量上涨
    2. 价格跌破入场价 5%: 技术性止损
    
    Returns:
        (should_eliminate, reason): 是否应该淘汰及原因
    """
    # 条件1: MFE做功效率低且量比高（资金在撤退）
    if tracker.mfe < self.eliminate_mfe_threshold and \
       tracker.current_volume_ratio > self.eliminate_volume_ratio_threshold:
        return True, f"MFE={tracker.mfe:.2f} < {self.eliminate_mfe_threshold}, 资金退潮"
    
    return False, ""
```

---

## 五、实施状态

### 5.1 已完成

- [x] StockState / TickSnapshot / StockTracker 类定义
- [x] candidate_pool / opportunity_pool / eliminated_pool 池结构
- [x] _update_stock_tracker / _calculate_real_flow / _find_nearest_snapshot 方法
- [x] _check_kinetic_paradox / _should_eliminate / _transition_state 方法
- [x] calculate_time_slice_flows 量纲错误修复

### 5.2 进行中

- [ ] _on_tick_data / EventBus 双轨制废除
- [ ] Live主循环接入真实时间切片
- [ ] Scan/Live同源：MockAdapter接管get_full_tick
- [ ] _micro_defense_check NameError修复

### 5.3 待验证

- [ ] 000533.SZ动能悖论案例测试
- [ ] 15分钟Tick队列内存压力测试
- [ ] Live模式启动稳定性验证

---

## 六、关键代码位置

| 组件 | 文件路径 | 行号范围 |
|-----|---------|---------|
| 状态机类定义 | tasks/run_live_trading_engine.py | L33-70 |
| 池初始化 | tasks/run_live_trading_engine.py | L218-224 |
| _update_stock_tracker | tasks/run_live_trading_engine.py | L269-315 |
| _calculate_real_flow | tasks/run_live_trading_engine.py | L317-347 |
| _check_kinetic_paradox | tasks/run_live_trading_engine.py | L408-434 |
| _should_eliminate | tasks/run_live_trading_engine.py | L436-486 |
| calculate_time_slice_flows | tasks/run_live_trading_engine.py | L2820-2900 |

---

## 七、CTO裁决

> "完成这三步，我们就彻底摆脱了过去被残缺数据牵着鼻子走的泥潭：
> 1. 建立内存时间序列（Ring Buffer）
> 2. 真实计算: 当前amount - 15分钟前amount
> 3. 宽进粗筛 + 动态蓄水池"

**当前进度**: ~60%  
**下一步**: 完成EventBus废除 + Live主循环接入 + MockAdapter同源

---

*本文档为CTO架构团队设计，作为状态机重构的权威参考。*