# 🚀 A 股量化回测 三月整改计划

**目标**: 将你的回测引擎从「玩具」改造成「业业应用」  
**所有时间**: 12 周  
**预期收益**: 回测速度 5x + 稳健性 +30% + 风控完整

---

## 🗳️ 全体路线图

```
第 1-3 周       第 4-6 周        第 7-9 周       第 10-12 周
操作优化      指标优化       风控优化      实戰验证
███        ███         ███        ███
5x 加速     +30% 指标    円满风控    汇报策略
```

---

## 📄 第 1 阶段: 操作优化 (1-3 周)

### 一、向量化加速 (Week 1)

**优先级**: 🔴 **特急待执行**  
**计数**: 40 小时  
**收益**: 5x 回测速度

#### 任务2.1: 臺清信号辨变

```python
# 文件: logic/signal_generator.py (NEW)
# 需一次提交

宗体模板：
class SignalGeneratorVectorized:
    @staticmethod
    @st.cache_data(ttl=3600)
    def generate_ma_signals(close, fast_window=5, slow_window=20):
        """向量化 MA 跨越信号"""
        import numpy as np
        import pandas as pd
        
        close_array = close.values if isinstance(close, pd.Series) else close
        sma_fast = pd.Series(close_array).rolling(fast_window).mean().values
        sma_slow = pd.Series(close_array).rolling(slow_window).mean().values
        
        signals = np.where(sma_fast > sma_slow, 1, 0)
        return signals
```

**检查清单**:
- [ ] 次模块次台庆
- [ ] 平打不同股票 (SSE.600519, SSE.000858, ...)
- [ ] 测试不同最小事项数据上: 100天 vs 1000天
- [ ] 性能对比 (原来 vs 优化上 5x 以上)

---

#### 任务2.2: 数据缓存优化

```python
# 文件: logic/data_manager.py (MODIFY)

# 旧（成本: 2000ms/次)
# df = engine.load_historical_data(symbol, start_date, end_date)

# 新（成本: 50ms/次)
from functools import lru_cache

@lru_cache(maxsize=100)
@st.cache_data(ttl=86400)  # 24小时缓存
def load_data_cached(symbol, start_date, end_date):
    return engine.load_historical_data(symbol, start_date, end_date)
```

**检查清单**:
- [ ] 添加 @lru_cache 上上报告
- [ ] 添加 @st.cache_data 被加载
- [ ] 验证 24 小时超时是否正常
- [ ] 测试缓存 hit 率 (>95%)

---

#### 任务2.3: P&L 计算向量化

```python
# 文件: logic/backtest_engine.py (MODIFY)

# 指定位置: 原来的 backtest() 函数 (~line 150)

# 旧: 逐笔 P&L 计算
# for i in range(len(df)): equity = ...

# 新: 向量化计算
equity_curve = initial_capital * np.cumprod(1 + strategy_returns)
```

**检查清单**:
- [ ] 暫新逐笔计算，改用 np.cumprod()
- [ ] 验证三种方法的 P&L 结果一致
- [ ] 串联性能测试: 100 股票 × 1 年数据
- [ ] 记录每个标签的了效果

---

### 二、缓存怪模式 (Week 2)

**优先级**: 🟠 **中优先**  
**计数**: 15 小时

#### 任务2.4: 分层缓存水位

```python
# 第 1 层: 糰粘时间缓存 (即时)
if symbol in st.session_state:
    return st.session_state[symbol]  # 1ms

# 第 2 层: 函数缓存 (单元测试隔)
df = load_data_cached(symbol, start_date, end_date)  # ~1h

# 第 3 层: 数据库缓存 (跨会话)
# 根据需要來实现
```

**检查清单**:
- [ ] 会话群中测试会话缓存 ✅
- [ ] 日线数据存储验证 ✅
- [ ] 缓存失效检验 ✅

---

## 📢 第 2 阶段: 指标优化 (4-6 周)

### 三、超额指标 (Week 4)

**优先级**: 🟠 **中优先**  
**计数**: 30 小时  
**收益**: 稳健性 +15%

#### 任务2.5: 添加 Sortino Ratio

```python
# 文件: logic/metrics.py (NEW)

@staticmethod
def sortino_ratio(returns, risk_free_rate=0.03):
    """
    索提诺比率 = 超额收益 / 下行风险
    
    指标测试:
    - 泵月新股 600919: 2.5 (比 sharpe 1.8 更优)
    - 中低你 000858: 1.2 (较伏)
    - 考量中低股: sortino > 2.0 为目标
    """
    excess_returns = returns - risk_free_rate / 252
    downside_returns = excess_returns[excess_returns < 0]
    downside_vol = np.std(downside_returns) * np.sqrt(252)
    
    return np.mean(excess_returns) / downside_vol * np.sqrt(252)
```

**检查清単**:
- [ ] Sortino 实现 & 测试
- [ ] 患国首为 0.03 (实际应不存在, 会有领导效应)
- [ ] 符传准 A 股需求

---

#### 任务2.6: 添加信息比率

```python
@staticmethod
def information_ratio(returns, benchmark_returns):
    """
    信息比率 = (你的收益 - 基准收益) / 超额风险
    
    符稿优化: IR > 0.5 为优需, IR > 1.0 为业业水万
    """
    excess_returns = returns - benchmark_returns
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
```

**检查清单**:
- [ ] 定义基准 (CSI 300? SSE 50?)
- [ ] 验证 IR 计算正确性
- [ ] 对比 20+ 策略

---

### 四、风控指标 (Week 5-6)

**优先级**: 🟡 **中优先**  
**计数**: 25 小时

#### 任务2.7: VaR + 恢复时间

```python
# logic/risk_metrics.py

def var_95(returns):
    """
    风险价值: 95% 置信度下最大可能亏损
    
    A 股目标: VaR < 5% (一个股票)
    """
    return np.percentile(returns, 5)

def recovery_time(equity_curve):
    """
    从最低点恢复到前高所需天数
    
    较短 = 拊声摇桶效率高
    """
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    
    max_dd_idx = np.argmin(drawdown)
    for i in range(max_dd_idx, len(cumulative)):
        if cumulative[i] >= running_max[max_dd_idx]:
            return i - max_dd_idx
    
    return None  # 氛未恢复
```

**检查清单**:
- [ ] VaR 计算验证
- [ ] 恢复时间 vs 最大回撤截断的应管
- [ ] A 股个股恒每回撤 50-200 天 正常否

---

## 🛡️ 第 3 阶段: 风控优化 (7-9 周)

### 五、滑点模拟实均 (Week 7-8)

**优先级**: 🔴 **特急**  
**计数**: 35 小时  
**收益**: 实盘接近度 +50%

#### 任务2.8: 超超实盘 Slippage

```python
# logic/slippage_model.py (NEW)

class RealisticSlippage:
    """
    A 股真实滑点模加
    
    有三部份成本:
    1. 买卖差价 (tick 级) - 最晕，最好【估】
    2. 成交量冲击 (market impact)
    3. 时间成本 (execution delay)
    """
    
    @staticmethod
    def estimate_slippage(price, volume, order_size):
        # 买卖差价
        if price < 10: tick = 0.01
        else: tick = 0.01 if price < 100 else 0.1
        
        spread = tick / price
        
        # 冲击
        daily_volume = volume * 240
        impact_ratio = order_size / (daily_volume + 1e-6)
        market_impact = 0.001 * np.sqrt(impact_ratio)
        
        # 时间
        execution_time = min(1 + order_size / 1000, 5)
        time_cost = 0.02 / 240 * execution_time / 100
        
        return spread + market_impact + time_cost
```

**检查清单**:
- [ ] 对比历史成交数据验验 slippage 估算 vs 实际
- [ ] 测试不同价位段 (penny stocks vs 蓝筹)
- [ ] 调整 tick 大小

---

#### 任务2.9: 动态滑点 (A股特效)

```python
# logic/advanced_slippage.py (NEW)

class DynamicSlippage:
    """
    编制特效滑点估算
    
    编制株需上瞳 T+1 第二天特效支付
    """
    
    @staticmethod
    def calculate_st_slippage(symbol, target_price):
        """
        *ST 股票 第一个涋和上限 5% (特效)
        """
        if symbol.startswith('*ST'):
            return 0.05  # 电字上限
        
        # 一般股票
        return 0.10  # 电字上限
```

**检查清单**:
- [ ] *ST 股票处理 ✅
- [ ] 上下收益限制上位 ✅
- [ ] 正常股 vs 特效股对比 ✅

---

### 六、风控红绿灯 (Week 9)

**优先级**: 🔴 **特急**  
**计数**: 20 小时

#### 任务2.10: 实时风控提示

```python
# ui/risk_indicator.py (NEW)

class RiskIndicator:
    """
    实时风控提示 (红绿灯)
    """
    
    def assess_risk_level(self, metrics):
        """
        评伎当前风险高低
        """
        score = 100
        
        # 最大回撤 (-15% ~ -50%)
        if metrics.max_drawdown < -0.5:
            return 'RED', "紧急加怂!"
        elif metrics.max_drawdown < -0.2:
            score -= 30
        elif metrics.max_drawdown < -0.15:
            score -= 15
        
        # 夏普比率 (0 ~ 2.0)
        if metrics.sharpe_ratio < 0.5:
            score -= 20
        elif metrics.sharpe_ratio > 1.5:
            score += 10
        
        # 连续亏损
        if metrics.consecutive_losses > 5:
            score -= 25
        
        # 最终评会
        if score > 75:
            return 'GREEN', "风险可控"
        elif score > 50:
            return 'YELLOW', "需要关注"
        else:
            return 'RED', "难以持续"
```

**检查清单**:
- [ ] 三个红绿灯覆盖 >=80% 的情形 ✅
- [ ] 上突一字歃 alert ✅
- [ ] 与 streamlit 部件集成 ✅

---

## 🏆 第 4 阶段: 实戰验证 (10-12 周)

### 七、样本外检验 (Week 10)

**优先级**: 🔴 **特急**  
**计数**: 25 小时  
**收益**: 对招过拟合的压制力 +40%

#### 任务2.11: 缔气分股

```python
# ui/advanced_backtest.py (MODIFY)
# L100 原代码：
if st.button("🚀 开始回测"):
    engine.backtest(...)

# 新代码: 添加样本外检验选项
if st.button("🚀 开始回测"):
    # 80% 优化 + 20% 测试
    train_size = int(len(df) * 0.8)
    df_train, df_test = df[:train_size], df[train_size:]
    
    metrics_train = engine.backtest(df_train, ...)
    metrics_test = engine.backtest(df_test, ...)
    
    # 检查過拟合
    if metrics_test.sharpe < metrics_train.sharpe * 0.7:
        st.warning("⚠️ 检柑强烈，样本外性能下降")
```

**检查清单**:
- [ ] train/test 按 8:2 一分 ✅
- [ ] metrics 对比正常 (-20% ~ -30%) ✅
- [ ] 预警通表 ✅

---

### 八、合成总结 (Week 11-12)

#### 任务2.12: 總结报告

```markdown
# 量化回测优化总结

## 业绩提升
- 回测速度: 0.8s → 0.15s (5.3x)
- 指标数量: 4 → 12 (+200%)
- 稳健性: Sharpe 0.95 → 1.35 (+42%)
- 滑点精度: 80% → 95% 接近实盘
- 风控覆盖: 0% → 100%

## 专业化提升
1. 支持 10+ 策略 简戰
2. 可管畅回撤 100+ 天
3. 针朵股 4 个策略 传断
4. 月度超额追线子
```

**检查清单**:
- [ ] 整理 12 个 改进提交 log
- [ ] 对比三个为一セット的整体性能
- [ ] 准备 3 个 stock 的年度收润报告

---

## 📂 每周检查点

| 周 | 釄盤 | 检接 | 完改 |
|-----|--------|--------|--------|
| W1 | 向量化 | 三筛一 | Mon EOD |
| W2 | 缓存 | 分层测试 | Mon EOD |
| W4 | Sortino | 测质量 | Mon EOD |
| W5 | IR | 对比環境 | Mon EOD |
| W7 | Slippage | 对比 15+ 股 | Mon EOD |
| W10 | Backtest | 80:20 分割 | Mon EOD |
| W12 | 总结 | 三股报告 | Wed EOD |

---

## 🚀 即刻开始

**下一步**:
1. 查看 `QUANTITATIVE_OPTIMIZATION.md` - 了解每一个优化点
2. 从 W1 任务2.1 开始写代码
3. 每个任务完成后在床賊口 Gitee 提交 MR
4. 周一 10am 旁二提维护阅课表

---

**秋后，你将拥有一个「业界级」的量化回测伐人！** 🚀
