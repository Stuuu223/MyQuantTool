# V17 技术债清单

## 已修复 ✅

### 1. 最大回撤计算 (2026-02-18)
- **问题**: max_drawdown始终返回0.0
- **修复**: 基于equity_curve滚动计算peak和drawdown
- **验证**: V3回测显示MDD=5.00%

### 2. 成本模型参数化 (2026-02-18)
- **问题**: 硬编码万三费率
- **修复**: CostModel类，默认万0.85（真实账户费率）+ 10bp滑点
- **验证**: JSON报告包含cost_assumptions字段

### 3. Signal Layer三层统计 (2026-02-18)
- **问题**: signal_layer全部为0
- **修复**: 分离Raw/Executable/Executed三层统计
- **验证**: V3回测显示Raw open=31, Executable=61, Executed=30

### 4. 涨跌停检查 (2026-02-18)
- **问题**: 无涨跌停约束
- **修复**: _check_limit_price方法，支持10cm/20cm/30cm
- **验证**: 压力测试通过（test_limit_price.py）

## 待优化 ⚠️

### 1. V12.1.0过滤器硬编码与失效（2026-02-18发现）🔥

### 2. T+1 Tick Backtester资金管理重写或废弃（2026-02-19发现）🔥
**当前状态**: 已标记EXPERIMENTAL/V12 DEMO
**问题严重性**: 🔴 高（资金管理完全违规）

**具体缺陷：**
| 模块 | V12硬编码 | V17架构要求 | 冲突状态 |
|-----|----------|------------|---------|
| 手续费 | commission_rate=0.0003（硬编码） | 集中配置StrategyService | ❌ 冲突 |
| 仓位控制 | position_size=0.3（硬编码） | Portfolio层决策 | ❌ 冲突 |
| 止损 | stop_loss=-0.08（硬编码） | RiskService统一管理 | ❌ 冲突 |
| 止盈 | take_profit=0.25（硬编码） | RiskService统一管理 | ❌ 冲突 |
| 资金计算 | capital * position_size（自定义逻辑） | Portfolio标准模块 | ❌ 冲突 |

**证据：**
- 网宿科技58天回测：资金从100K莫名掉到50，持仓逻辑完全偏离
- 交易判断"资金不足，跳过买入"：脚本内部if条件，非架构定义规则

**根本原因：**
- V12时代的实验脚本，自带一套资金/风控硬编码
- 未通过StrategyService + Portfolio + RiskService统一栈
- 与V17架构铁律"禁止硬编码阈值"直接冲突

**决策（2026-02-19 CTO）：**
- ✅ 允许用途：Tick数据加载验证、信号触发行为验证、TrapDetector诱多检测
- ❌ 禁止用途：资金收益率评估、最大回撤/胜率统计、任何资金相关指标验收

**修复方案：**
- 短期：标记EXPERIMENTAL，禁止用于资金验收
- 中期：重写资金管理模块，走Portfolio统一栈
- 长期：废弃此脚本，使用V17官方回测链路

### 3. Tick/分K回放链路重写（2026-02-19规划）🔥
**当前状态**: 规划中
**优先级**: 🔴 高（核心验收工具缺失）

**目标：**
- 构建合规的Tick事件回放链 + 单独的资金/Portfolio回测链
- Tick回放：只验证行为（哪几天标机会、TrapDetector是否挡住诱多）
- 资金回测：走日K/分K级别，使用Portfolio模块和风控规则

**技术要求：**
- 通过StrategyService统一调用策略（HALFWAY/TRUE_ATTACK/LEADER/TRAP）
- 通过Portfolio层统一管理仓位（断层优势、持仓vs候选PK、小资金1-3只）
- 通过RiskService统一管理风控（最大回撤、单票风控、机会成本约束）
- 禁止策略脚本私自写止盈止损数字

**实现路径：**
1. 创建 backtest/run_v17_replay_suite.py（V17官方回测脚本）
2. 确认/创建 logic/services/{strategy,capital,risk}_service.py
3. 确认/创建 logic/portfolio/* 统一模块
4. 所有回测路径走统一入口，禁止绕过Service/Portfolio

**验收标准：**
- 顽主150只58天Tick：只验证行为（机会标记/诱多过滤）
- 资金回测：走StrategyService + Portfolio + RiskService统一栈
- 所有资金/回撤类指标：基于Portfolio回测主线

### 4. V12.1.0过滤器硬编码与失效（2026-02-18发现）🔥
**当前状态**: 已标记EXPERIMENTAL，默认禁用
**问题严重性**: 🔴 高（实际数据严重失效）

**具体缺陷：**
| 组件 | 硬编码问题 | 实际表现 |
|-----|-----------|---------|
| 板块共振 | 涨停≥3只/上涨≥35% | 通过率3.8% |
| 动态阈值 | 市值50-1000亿 | 误杀小盘起爆股 |
| 竞价校验 | prev_close*0.99估算 | 回测失真 |
| 串联架构 | 一票否决 | 综合通过率0.11% |

**数据对比：**
- 模拟数据：胜率93.33%，收益率+9.32%
- 实际数据：胜率25.00%，收益率-21.01%

**根因分析：**
1. 阈值基于理想环境设计，未考虑真实市场分布
2. 串联架构导致单点失效（3.8% × 32.7% × 50% ≈ 0.6%）
3. 市值过滤误杀右侧起爆核心标的（20-50亿小盘股）

**修复方案（已规划）：**
- 短期：禁用V12.1.0，使用V11 TripleFunnel评分制替代
- 中期：重构为"评分贡献"模式，非一票否决
- 长期：统一过滤层抽象，动态阈值+分位数判断

**验证要求：**
- 必须在网宿/顽主热门票上验证通过
- 禁止在全市场扫描前未经验证进主线

---

### 2. Tick数据通路未封装（2026-02-18发现）🔥
**当前状态**: 散落在5+个脚本中，无统一入口
**问题严重性**: 🔴 高（重复踩坑，效率低下）

**散落在哪：**
| 脚本 | 问题 |
|-----|------|
| `tasks/data_prefetch.py` | xtdatacenter初始化逻辑 |
| `scripts/download_wanzhu_tick_data.py` | 又一套connect/download |
| `temp/test_wangsu_*.py` | 临时脚本各写各的 |
| `backtest/t1_tick_backtester.py` | 独立路径处理 |
| `tools/download_from_list.py` | 只处理1m K线 |

**导致的重复踩坑：**
- ❌ 尝试xtdata.connect(vipsxmd1...)直接连VIP（错误）
- ❌ 端口58609占用，不知道在下载（缺乏查询机制）
- ❌ 日期格式混乱（2025 vs 2026）
- ❌ 列名不一致（price vs lastPrice）

**封装规范（已输出）：**
- 文档: `.iflow/tick_provider_spec.md`
- 接口: `TickProvider.ensure_history()` / `TickProvider.load_ticks()`
- 规则: 所有脚本禁止直接import xtdata/xtdatacenter

**下一步：**
- 实现 `logic/data_providers/tick_provider.py`
- 迁移所有脚本使用统一接口
- Code Review红线：出现`xtdata.connect`直接打回

---

### 3. Raw Close Signal重复统计
**当前状态**: 87,439笔（过高）
**原因**: 每个tick都检查平仓条件，首次满足后仍持续计数
**建议方案**: 
- 在T1Position添加first_exit_signal_timestamp字段
- 只记录"首次满足平仓条件"的那个tick
- 预期结果: Raw close ≈ 30（与Executed同量级）

**优先级**: 中
**阻塞性**: 不阻塞主线（Executable/Executed统计正确）
**计划**: 在80×64基线后实施

### 2. HALFWAY策略A/B测试
**当前状态**: TRIVIAL V3已完成，HALFWAY待跑
**阻塞**: HalfwaySignalAdapter需要验证
**下一步**: 
- 运行HALFWAY 20×30
- 对比TRIVIAL vs HALFWAY的三层信号统计
- 分析策略质量差异

**优先级**: 高
**阻塞性**: 阻塞80×64扩量

## 下一步行动 (按CTO指示)

1. **立即**: 完成HALFWAY 20×30 A/B测试
2. **随后**: 80×64扩量建立V17正式基线
3. **技术债**: Raw close首触发计数改造（择机实施）

---

## 2026-02-18 重要更新（V17.1.0关键决策记录）

### 今日完成 ✅

**1. V12.1.0过滤器问题发现与处置**
- 发现实际数据通过率仅0.11%，收益率-21%（vs模拟数据+9%）
- 根因：硬编码阈值过高 + 串联一票否决架构
- 决策：标记为EXPERIMENTAL，默认禁用
- 文档更新：`docs/CORE_ARCHITECTURE.md`新增0.4节

**2. 资金攻击检测实验（网宿科技验证）**
- 脚本：`backtest/exp_capital_attack_backtest.py`
- 结果：1月26日涨停日正确触发（评分1.0，净流入122亿）
- 关键验证：资金检测有效，但需从绝对值改为相对分位数

**3. 架构铁律新增（老板定调）**
> "心中无顶底，跟随市场。禁止硬编码阈值，使用相对分位数。"

- 禁止：`> 100_000_000`、`> 0.05`等魔法数字
- 正确：`ratio = main_inflow / circ_mv` + 市场分位数

**4. Tick Provider规范输出**
- 文档：`.iflow/tick_provider_spec.md`
- Code Review红线：禁止直接`import xtdata`

**5. 热门样本回测原则确立**
- 强制样本：网宿科技、顽主TopList 131只
- 工程规范：PR必须附带热门票回测报告

### 明日计划 📋

- [ ] TRIVIAL基线（网宿）
- [ ] HALFWAY形态（网宿）
- [ ] 顽主131只资金扫描
- [ ] 对比触发率统计
