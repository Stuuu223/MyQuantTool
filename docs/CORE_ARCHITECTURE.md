---
version: V17.0.0
updated: 2026-02-16
scope: logic/full_market_scanner.py, tasks/run_event_driven_monitor.py, logic/data_providers/akshare_manager.py, logic/portfolio/capital_allocator.py
author: MyQuantTool Team
---

# MyQuantTool 核心架构文档

## 🚨 核心原则（开发必须遵守）

### 0. 💰 资金为王，拒绝噪音（V16.3.0新增）

**核心哲学：**
> "新闻是噪音，只认资金。新闻基本都是滞后的，大资金肯定先收到消息。"

**具体要求：**
1. **禁止使用新闻数据**：所有新闻API（`ak.stock_news_em`、`get_news`等）已移除
2. **资金流向是唯一真相**：所有决策基于主力资金流向数据
3. **新闻风险检测已废弃**：`logic/core/algo.py`中的新闻风险检测模块已注释
4. **性能优化**：移除新闻模块后，预热速度提升30%+

**技术实现：**
- ✅ 已移除：`AkShareDataManager.get_news()` 方法
- ✅ 已移除：预热流程中的新闻数据获取
- ✅ 已移除：`logic/core/algo.py`中的新闻风险检测
- ✅ 已移除：`tests/test_akshare_single.py`中的新闻测试

**数据流向：**
```
实时行情（QMT）
    ↓
资金流向分析（AkShare）← 唯一数据源
    ↓
FullMarketScanner（资金为王）
    ↓
EventDrivenMonitor（拒绝噪音）
    ↓
Portfolio层（V17.0.0新增：账户级资金调度）
    ↓
实盘执行
```

### 0.1 💰 账户曲线向上，机会成本最小化（V17.0.0新增）

**核心理念更新（V17.0.0重大变更）**：
> "账户曲线向上 > 单笔收益故事，机会成本最小化 > 死守某只股票，哪里赚钱最优去哪里，能赚就赚 > 风格教条"

**具体要求**：
1. **废除单笔收益目标**：移除"单只股票30%-50%收益"的硬性要求
2. **动态风险管理**：最大回撤-12%（软约束，非硬性红线）
3. **断层优势识别**：Top1评分>Top2的1.5倍时单吊
4. **机会成本管理**：持有股票表现不佳且有更优机会时，优先换仓
5. **T+1约束处理**：A股T+1，今日买入今日不能卖出
6. **风格不重要**：日内/隔夜/持有几天都可以，只要能赚钱

**技术实现（V17.0.0新增）**：
- ✅ 新增：`logic/portfolio/capital_allocator.py` - 账户级资金调度器
- ✅ 新增：`logic/portfolio/portfolio_metrics.py` - 业务指标追踪
- ✅ 新增：`config/portfolio_config.json` - Portfolio层配置
- ✅ 功能：实时重新评分（不看历史标签）
- ✅ 功能：换仓决策（持仓 vs 候选池实时PK）
- ✅ 功能：动态仓位分配（1只90%、2只60%+40%、3只50%+30%+20%）

**关键参数**：
```json
{
  "max_positions": 3,
  "max_drawdown": -0.12,
  "single_position_threshold": 1.5,
  "t_plus_one": true
}
```

### 0.2 ❌ 禁止硬编码阈值 - 相对强度而非绝对值（V17.1.0新增）

**核心铁律：**
> "心中无顶底，跟随市场。资金强度是相对概念，不是绝对数值。"

**禁止行为（红线）：**
```python
# ❌ 严禁在核心引擎中硬编码
if main_inflow > 100_000_000:  # 绝对值阈值
    trigger()
if price_strength > 0.05:      # 绝对百分比
    trigger()
```

**正确做法（三层相对化）：**

**第一层：个股相对尺度**
```python
# 使用相对比率而非绝对值
ratio = main_net_inflow / circulating_cap  # 净流入占流通市值比
price_strength = (current_price - open_price) / open_price
```

**第二层：市场分位数（推荐）**
```python
# 每天自动计算市场分布，用分位数判断强弱
ratio_percentile = calculate_percentile(ratio, all_stocks_ratios)
price_percentile = calculate_percentile(price_strength, all_stocks_strengths)

# 综合评分（0-1）
attack_score = 0.5 * ratio_percentile + 0.5 * price_percentile

# 触发条件：排在市场前1%（自适应，不硬编码）
if attack_score > 0.99:
    trigger_capital_attack()
```

**第三层：动态自校准**
```python
# 每月根据历史表现调整分位线
if hit_rate_too_low:
    lower_percentile_threshold()  # 放宽
elif too_many_false_signals:
    raise_percentile_threshold()  # 收紧
```

**工程规范：**
- ✅ 核心引擎（backtest/*, logic/core/*）禁止任何硬编码阈值
- ✅ 实验参数必须放在 `config/exp_*.json`，通过独立脚本读取
- ✅ 生产参数走 `DynamicThreshold` 类，按市值/情绪/时间动态计算
- ❌ 代码审查红线：出现 `> 100_000_000` 或 `> 0.05` 等魔法数字直接打回

**历史教训（2026-02-18）：**
- V12.1.0过滤器因硬编码阈值（涨停≥3只/35%上涨/市值50-1000亿）导致实际数据通过率仅0.11%
- 资金攻击实验初期错误使用硬编码（1亿/5%），已纠正为相对分位数方案

---

### 0.3 🔥 热门样本回测原则（V17.1.0新增）

**核心铁律：**
> "任何策略/过滤修改，必须在热门强势样本上验证才能进主线。全市场扫描之前，先看热门票能不能抓住。"

**强制样本集合：**

| 样本类型 | 标的 | 时间区间 | 验证重点 |
|---------|------|---------|---------|
| **基准强势股** | 网宿科技 300017.SZ | 2025-11-13 ~ 2026-02-13 | 资金攻击检测能否识别1月26日涨停 |
| **顽主杯真实区间** | TopList 131只 | 2026-02-04 ~ 2026-02-13 | HALFWAY/资金轴在真实上榜前的触发率 |
| **经典形态票** | 志特新材、欢乐家等 | 主升启动日 ±5天 | 平台突破策略的适配性 |

**验证流程（强制）：**
```
1. 代码修改 → 2. 热门票验证 → 3. 通过才进PR → 4. 全市场测试
      ↑___________________________|
      （不通过禁止合入主线）
```

**禁止行为：**
- ❌ 未经热门票验证直接全市场扫描
- ❌ 只在模拟数据/理想环境测试
- ❌ 用"我感觉能抓住"代替实证数据

**工程实现：**
- ✅ 提供 `backtest/exp_*_backtest.py` 独立实验脚本
- ✅ 热门票列表维护在 `config/hot_sample_stocks.json`
- ✅ CI/CD检查：PR必须附带热门票回测报告

---

### 0.4 ⚠️ V12.1.0过滤器状态：EXPERIMENTAL（V17.1.0更新）

**当前状态：**
> **已标记为实验性功能，默认禁用，禁止用于生产环境**

**问题总结（2026-02-18复盘）：**

| 过滤器 | 设计缺陷 | 实际表现 |
|-------|---------|---------|
| **板块共振** | 阈值过高（涨停≥3只/上涨≥35%） | 通过率仅3.8%，过度过滤 |
| **动态阈值** | 市值范围过窄（50-1000亿） | 误杀小盘起爆股 |
| **竞价校验** | 使用估算数据（prev_close*0.99） | 回测失真 |
| **串联架构** | 一票否决制 | 综合通过率0.11%，几乎全拒 |

**实际数据 vs 模拟数据：**
- 模拟数据：胜率93.33%（理想环境）
- 实际数据：胜率25.00%，收益率-21%（严重失效）

**处置方案：**
```python
# backtest/t1_tick_backtester.py
self.enable_filters = False  # 默认禁用
# 如需实验，显式开启：
# backtester = T1TickBacktester()
# backtester.enable_filters = True  # 标记为EXPERIMENTAL
```

**后续规划：**
- 短期：使用V11 TripleFunnel评分制防守轴替代
- 中期：将V12.1.0过滤器重构为"评分贡献"而非"一票否决"
- 长期：统一过滤层抽象，供1m/tick回测复用

---

### 1. 必须使用虚拟环境
**所有Python命令必须使用虚拟环境运行：**

```bash
# Windows
E:\MyQuantTool\venv_qmt\Scripts\python.exe your_script.py

# 或先激活虚拟环境
E:\MyQuantTool\venv_qmt\Scripts\activate
python your_script.py
```

**为什么？**
- QMT（xtquant）依赖虚拟环境
- 所有第三方库（akshare、tushare等）安装在虚拟环境中
- 不使用虚拟环境会导致"模块找不到"或"DLL加载失败"

### 2. QMT 状态强制检查规范

**凡是用 QMT 数据做实时决策，必须显式检查：**

1. 行情主站是否登录成功
2. 当前是否交易时间
3. 行情模式是否为订阅模式（实时），不能只依赖本地文件模式

**强制自检入口：**

```python
from logic.qmt_health_check import check_qmt_health, require_realtime_mode

# 方式1：检查并打印状态
result = check_qmt_health()
# 输出：
# QMT 客户端: ✅ 已启动 (5187 只股票)
# 行情主站: ✅ 已登录 (20260206 15:00:00)
# 市场状态: ✅ 工作日
# 交易时间: ⚠️  当前不在交易时间 (盘后)
# 数据模式: ⚠️  本地文件模式 (滞后 3059 分钟)

# 方式2：强制要求实时模式（如果不满足会抛出异常）
require_realtime_mode()
# RuntimeError: 当前不在交易时间 (盘后)，无法进行实时决策
```

**在以下场景必须调用自检：**
- `FullMarketScanner` 初始化时
- `EventDrivenMonitor` 启动时
- 任何需要获取实时Tick数据的函数入口

### 3. 数据源优先级和限速策略

**核心系统数据源（按优先级）：**

| 数据源 | 用途 | 实时性 | 限速 | 备注 |
|--------|------|--------|------|------|
| **QMT (xtquant)** | Level 1 技术面粗筛 | 实时 | 无 | 全市场Tick数据，本地可控 |
| **AkShare** | Level 2 资金流向分析 | 1天延迟 | 60次/分钟, 2000次/小时 | 金额单位：元，数据从旧到新排序 |
| **Tushare** | 历史快照生成、回测 | 1天延迟 | API限流 | moneyflow的amount单位：千元 |
| **EasyQuotation** | 备用实时行情 | 实时 | 无 | 轻量级Tick数据 |

**V16.3.0变更：**
- ❌ 已移除：新闻数据（`stock_news_em`）- 根据"资金为王，拒绝噪音"原则
- ✅ 优化：预热速度提升30%+（移除500+次新闻API调用）

**AkShare限速防封（必须遵守）：**
```python
from logic.rate_limiter import RateLimiter
limiter = RateLimiter(
    max_requests_per_minute=60,
    max_requests_per_hour=2000,
    min_request_interval=0.1
)
# 每次调用前检查
limiter.wait_if_needed()
```

**数据单位对照表：**
- AkShare 资金流：金额（元）✅
- Tushare daily amount：金额（千元）
- Tushare moneyflow amount：金额（千元）
- Tushare moneyflow vol：股数（手）❌ 不要用！

### 3. 实时主线优先

---

## ⚠️ 重要提醒：核心系统定位（V17.0.0更新）

**所有代码修改必须围绕以下三个核心模块展开：**

### 🫀 核心心脏：`logic/full_market_scanner.py`
- 全市场三漏斗扫描器
- Level 1: 技术面粗筛（QMT批量）
- Level 2: 资金流向分析（AkShare）
- Level 3: 诱多陷阱检测和资金性质分类
- **这是实时决策的核心逻辑**

### 🧠 核心大脑：`tasks/run_event_driven_monitor.py`
- 事件驱动持续监控
- 实时Tick监控和事件检测
- 候选池管理和深度扫描
- **这是实盘执行的调度中心**

### 💰 资金调度器：`logic/portfolio/capital_allocator.py`（V17.0.0新增）
- 账户级资金调度管理
- 实时重新评分（不看历史标签）
- 换仓决策（持仓 vs 候选池实时PK）
- 动态仓位分配（1只/2只/3只）
- **这是账户曲线向上的核心引擎**

---

## 🔄 数据流向（必须牢记）

```
实时行情（QMT）
    ↓
FullMarketScanner（实时扫描）
    ↓
打分/过滤（三漏斗）
    ↓
EventDrivenMonitor（事件驱动监控）
    ↓
实盘/仿真下单
    ↓
快照保存 → 历史回测
```

---

## ⚡ 核心原则（开发必须遵守）

### 1. 实时主线优先
**任何因子、打分、资金逻辑的修改，必须先考虑：**
- `FullMarketScanner` 能不能实时承载？
- `EventDrivenMonitor` 能不能稳定跑？
- **如果回测和实时逻辑不一致，以实时逻辑为准，回测要跟着对齐**

### 2. 数据/回测是配套设施
- 快照生成、回放、回测引擎，都要明确写在注释里：
  > "此处逻辑必须与 FullMarketScanner / 实盘决策保持一致"
- 任何在回测里新增的逻辑，都要问一句：
  > "这段将来要不要同步到实时？如果要，准备同步到哪一层？"

### 3. 紧箍咒（AI团队必须记住）
**以后讨论任何改动，如果三句话里没有提到 run_event_driven_monitor.py 或 FullMarketScanner，默认视为没对齐核心系统。**

---

## 🎯 工作顺序硬约束

### 实时主线（核心，最高优先级）
1. 修改任何因子、资金逻辑、决策规则
2. 必须先在 `FullMarketScanner` 验证
3. 必须在 `EventDrivenMonitor` 验证
4. **实时逻辑为真**

### 数据/回测（配套设施，优先级次之）
1. 历史快照生成（`tasks/batch_rebuild_snapshots.py`）
2. 回测引擎（`logic/backtest_framework.py`）
3. 回测结果仅用于验货，不是主角

---

## 📊 核心系统数据流详情

### FullMarketScanner 资金流数据源
- **数据源**: AkShare 接口
- **接口**: `ak.stock_individual_fund_flow(stock=code, market=market)`
- **字段**:
  - `超大单净流入-净额`: 超大单净流入金额（元）
  - `大单净流入-净额`: 大单净流入金额（元）
  - `中单净流入-净额`: 中单净流入金额（元）
  - `小单净流入-净额`: 小单净流入金额（元）
- **单位**: 金额（元）✅
- **数据排序**: 从旧到新（最新数据在最后）
- **数据获取代码**:
  ```python
  from logic.fund_flow_analyzer import FundFlowAnalyzer
  analyzer = FundFlowAnalyzer()
  data = analyzer.get_fund_flow(stock_code, days=5)
  latest = data['latest']  # 最新数据
  ```
- **注意事项**:
  - AkShare数据是1天延迟的（T+1）
  - 必须使用`df.tail(days)`取最新数据，不要用`head()`
  - `latest`应该是`records[-1]`，不是`records[0]`

### EventDrivenMonitor 调度逻辑
```
竞价阶段 (9:15-9:25)
    ↓
竞价事件检测
    ↓
开盘后 (9:30-11:30, 13:00-15:00)
    ↓
Tick监控 → 事件触发
    ↓
候选池管理（Level1初筛）
    ↓
深度扫描（FullMarketScanner + Level2+Level3）
    ↓
生成交易信号
    ↓
实盘/仿真下单
```

---

## 🔍 核心系统检查清单

每次修改代码前，先自检：

- [ ] 我的修改是否影响 `FullMarketScanner`？
- [ ] 我的修改是否影响 `EventDrivenMonitor`？
- [ ] 资金流逻辑的单位是否正确（AkShare是金额元）？
- [ ] 如果我在回测里改了逻辑，是否需要在实时系统里同步？
- [ ] 我能否在实时环境里复现这个问题/效果？

---

## 🚫 常见错误（禁止）

1. **只在回测里改逻辑，不同步到实时系统** ❌
   - 正确做法：实时系统为真，回测跟着对齐

2. **忽略核心系统，只改回测引擎** ❌
   - 正确做法：先在核心系统验证，再同步到回测

3. **不检查资金流数据单位** ❌
   - 正确做法：AkShare是金额（元），Tushare moneyflow的amount是千元

4. **修改后不验证实时性能** ❌
   - 正确做法：任何修改都要在 `FullMarketScanner` 和 `EventDrivenMonitor` 验证

---

## 📝 版本历史

### V16.3.0 (2026-02-16) - 去除噪音/资金为王

**核心理念变更：**
> "新闻是噪音，只认资金。新闻基本都是滞后的，大资金肯定先收到消息。"

**主要修改：**

1. **移除新闻模块**
   - ✅ 删除 `AkShareDataManager.get_news()` 方法（51行代码）
   - ✅ 移除预热流程中的新闻数据获取（4行代码）
   - ✅ 注释 `logic/core/algo.py` 中的新闻风险检测模块（59行代码）
   - ✅ 注释 `tests/test_akshare_single.py` 中的新闻测试（11行代码）

2. **性能优化**
   - 预热流程API调用减少500+次（每50只股票）
   - 预热速度提升30%+（待验证）
   - 内存占用减少（无新闻缓存文件）

3. **架构文档更新**
   - 新增核心原则："资金为王，拒绝噪音"
   - 更新数据源优先级表（移除新闻）
   - 更新数据流向图（强调资金为王）

**影响范围：**
- `logic/data_providers/akshare_manager.py` - 核心数据管理模块
- `logic/core/algo.py` - 风险检测模块
- `tests/test_akshare_single.py` - 单元测试
- `docs/CORE_ARCHITECTURE.md` - 架构文档

**向后兼容性：**
- ⚠️ 破坏性变更：`get_news()` 方法已移除
- ⚠️ 破坏性变更：新闻风险检测已废弃
- ✅ 兼容：所有资金流、基本面、龙虎榜功能保持不变

**验证方法：**
- [ ] 预热流程中不再出现新闻日志
- [ ] 预热速度提升30%+
- [ ] 所有单元测试通过
- [ ] 实时监控系统正常运行

---

## 📝 修改记录模板

每次修改核心系统，必须记录：

```markdown
## 修改日期: YYYY-MM-DD
## 修改模块: FullMarketScanner / EventDrivenMonitor
## 修改原因:
## 修改内容:
## 影响范围:
## 验证方法:
## 是否同步到回测: 是/否
```

---

## 🎓 核心概念解释

### 三漏斗扫描
- **Level 1**: 技术面粗筛（QMT批量，5000+ → 300-500只）
- **Level 2**: 资金流向分析（AkShare，300-500 → 50-100只）
- **Level 3**: 诱多陷阱检测（50-100 → 机会池/观察池/黑名单）

### 事件驱动监控
- **固定间隔模式**: 每N分钟执行一次全市场扫描
- **事件驱动模式**: 检测到事件时触发扫描（推荐）
- **候选池管理**: 动态维护热门股票池，TTL机制

### Attack评分
- **主力流入评分**: 100万=20分，400万=100分
- **涨幅评分**: 5%=0分，10%=80分，15%+=100分
- **成交额评分**: 越小越容易推动（0.05亿=100分）

### 风险评分
- **综合风险评分**: 0-1，越低越安全
- **诱多信号**: 暴量、长+巨、突袭等
- **资金性质分类**: HOT_MONEY、INSTITUTIONAL、LONG_TERM

### Momentum Band（动量波段）
- **定义**: 根据涨幅和资金占比组合的分类体系
- **计算公式**: `主力净流入 / 当日成交额`

| Band | 条件 | 样本特征 | 次日表现 | 池位 |
|------|------|----------|----------|------|
| BAND_0 | 占比<2% 或 涨幅<5% | 噪声 | - | 黑名单 |
| BAND_1 | 5-8%涨幅 + 2-5%占比 | 保守小肉 | 100%盈利，+1.45% | 观察池 |
| BAND_2 | 8-10%涨幅 + 2-5%占比 | 半路推背主战区 | 59.4%涨停，96.9%盈利，+7.32% | 机会池 |
| BAND_3 | 8-10%涨幅 + ≥5%占比 | 推背加强版 | 84.6%涨停，100%盈利，+8.71% | 机会池 |

**关键发现**：
- 所有BAND_2/BAND_3样本都是主板10cm，无20cm污染
- 创业板/科创板8-10%涨幅的样本资金占比都<2%，被自动过滤
- "≥2%占比"是20cm垃圾情绪票的天然防火墙

**策略定位**：
- **主板10cm主战**: BAND_2/BAND_3 + 热点行业 + 风控
- **20cm游击**: 单独设计（未来）
- **保守小肉**: BAND_1单独策略

---

## 📞 核心问题自检

每次遇到问题，先问自己：

1. **这个问题在实时系统里存在吗？**
   - 如果只在回测里出现，可能是回测逻辑有问题

2. **这个问题在 `FullMarketScanner` 里能复现吗？**
   - 如果不能，说明问题可能在回测引擎

3. **我的修改会不会影响实时性能？**
   - 实时系统对性能敏感，回测可以慢一点

4. **资金流数据单位对吗？**
   - AkShare是金额（元）
   - Tushare daily的amount是千元
   - Tushare moneyflow的amount是千元

---

**最后强调：所有东西最终要喂给 FullMarketScanner 和事件驱动监控。回测只是验货，不是主角。**