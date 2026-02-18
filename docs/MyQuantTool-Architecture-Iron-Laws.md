# MyQuantTool 架构铁律

> 版本: V1.0  
> 生效日期: 2026-02-18  
> 最后更新: 2026-02-18  
> 制定人: CTO + 老板  
> 执行监督: AI项目总监

---

## 一、策略与阈值铁律

### 1.1 禁止魔法数字进核心引擎

**红线**:
- ❌ 回测引擎/实盘引擎内不允许出现拍脑袋阈值
- ❌ 如 `main_inflow > 1e8`、`price_strength > 0.05` 等硬编码

**正确做法**:
- ✅ 已验证的经验公式（如 `ratio = mainnetinflow / circ_mv + DynamicThreshold`）
- ✅ 显式配置文件（`config/*.json`），在实验脚本中读取使用
- ✅ 核心引擎只负责数据流和信号传递，策略参数外置

**Code Review检查点**:
```python
# 出现以下模式直接打回
if main_inflow > 100_000_000:  # ❌ 魔法数字
if price_change > 0.05:        # ❌ 固定百分比
```

---

### 1.2 一切强弱判定优先用"相对尺度"

**资金强度**:
- 一律用 `ratio = mainnetinflow / circulating_cap + 分位数`
- 禁止用净流入绝对值大小（如"1亿就是强"）

**价格强度**:
- 用相对开盘/前收的涨跌幅 + 市场/板块分位
- 禁止"固定 5% 就叫强"

**正确示例**:
```python
# 相对尺度（推荐）
ratio = main_net_inflow / circulating_cap
ratio_percentile = calculate_percentile(ratio, all_stocks_ratios)
if ratio_percentile > 0.99:  # 市场前1%
    trigger_capital_attack()
```

---

### 1.3 情绪与阈值必须联动

**原则**:
- 止盈/止损/资金阈值，必须根据情绪周期（分歧、极度一致、退潮等）调整
- 禁止"全市场一个阈值打天下"

**实现**:
- 使用 `SentimentStage` 枚举（start/main/climax/divergence/recession/freeze）
- 动态阈值管理器根据情绪阶段自动调整系数（0.8x ~ 1.2x）

---

## 二、数据与Tick链路铁律

### 2.1 Tick数据必须通过唯一Provider获取

**红线**:
- ❌ 禁止任何业务脚本/策略直接 `import xtdata` 或 `import xtdatacenter`
- ❌ 禁止脚本自己初始化xtdatacenter、自己连VIP、自己算数据目录

**统一接口**:
```python
# 唯一合法入口
from logic.data_providers.tick_provider import TickProvider

provider = TickProvider(config)
provider.ensure_history('300017.SZ', '2025-11-13', '2026-02-13')
df = provider.load_ticks('300017.SZ', '2026-01-26', '2026-01-26')
```

**Provider职责**:
- 初始化 xtdatacenter + Token + 监听端口
- 管理 `QMT_DATA_DIR/datadir/...` 路径
- 提供 `ensure_history()` / `load_ticks()` 统一接口

---

### 2.2 明示tick覆盖范围，不准假想

**要求**:
- Provider必须能返回每只票tick的真实可用日期段（录制 vs 回灌）
- 策略/回测在tick不足时，必须显式退化到1m/日线
- 必须在日志中标注"数据降级"，禁止默默当作有tick

**实现**:
```python
coverage = provider.get_coverage('300017.SZ')
# 返回: ['20251113', '20251114', ...]

if target_date not in coverage:
    logger.warning(f"Tick数据缺失，降级到1m: {target_date}")
    df = provider.load_1m(code, start, end)
```

---

### 2.3 历史vs实时一律标注时效性

**原则**:
- 回测和盘中辅助决策严格区分
- 禁止用 >4小时前的日内数据给出当日交易建议

**日志规范**:
```python
logger.info(f"[历史回测] 日期: {date}, 数据时效: T+1")
logger.info(f"[实时决策] 时间: {now}, 数据延迟: {delay_ms}ms")
```

---

## 三、过滤与防守轴铁律

### 3.1 过滤器优先"评分制"，慎用"一票否决"

**原则**:
- 板块共振、竞价强度、市值过滤等，应输出0-1评分或标签
- 只在极少数明确"高风险"场景使用硬拒绝（如明显TRAP、极端尾盘偷袭）

**对比**:
```python
# ❌ 一票否决（V12.1.0错误做法）
if not wind_filter.check(code):
    continue  # 直接跳过，不再检查其他条件

# ✅ 评分制（V11正确做法）
wind_score = wind_filter.calculate_score(code)
total_score = 0.3 * wind_score + 0.4 * capital_score + 0.3 * trap_score
if total_score > 0.6:
    approve()
```

---

### 3.2 禁止在新模块重复发明过滤器

**红线**:
- ❌ 所有新过滤逻辑必须基于V11 triplefunnel/defenseaxe已验证的防守轴抽象
- ❌ 禁止在tick回测、单票实验等新文件中单独硬写一套wind_filter/dynamic_threshold/auction_validator

**正确做法**:
- 复用 `logic/strategies/defense_axe.py` 的统一过滤层
- 新策略通过配置参数调整行为，不复制逻辑

---

### 3.3 过滤器改动必须有回测对照

**强制样本集**:
1. **顽主TopList实际区间**（2026-02-04~2026-02-13，131只）
2. **典型强势票**（网宿科技、志特新材、欢乐家、有友食品）

**验证指标**:
- 触发频率变化（vs上一版本）
- 胜率变化
- 收益/回撤变化

**禁止**:
- ❌ 未经热门票回测直接全市场扫描
- ❌ 只在模拟数据/理想环境测试

---

## 四、资金为王铁律

### 4.1 形态可以错过，资金不能整体沉默

**原则**:
- 对成交量、持续性都极强的票，如果资金轴（TrueAttack/ratio/分位攻击事件）完全无信号，视为系统缺陷
- 必须排查：Tick估算是否接入、动态阈值是否过严、过滤链路是否错误短路

**验收标准（网宿科技1月26日测试）**:
- 净流入122亿 + 价格强度12.7%
- 资金攻击评分必须触发（≥0.99分位数）
- 若完全静默 → 系统缺陷，必须修复

---

### 4.2 资金攻击必须"跟随市场"而非拍头

**判定标准**（优先级从高到低）:
1. **单票ratio** = mainnetinflow / circulating_cap
2. **当日市场/板块分位**（如前1%/3%）
3. **历史表现自校准**（触发样本后续收益反馈调整阈值）

**禁止**:
- ❌ 长期依赖固定绝对数（1亿、5%等）做核心标准

---

### 4.3 三轴决策必须同时看完再下结论

**三轴**:
1. **行业风向**（WindFilter/sector resonance）
2. **资金攻击**（TrueAttack/ratio）
3. **陷阱检测**（TrapDetector）

**决策模板**:
```
给任何票定性之前，必须说明：
- 板块是否共振？（WindFilter score）
- 资金是否"真攻击"？（TrueAttack flag + ratio percentile）
- 有无TRAP信号？（TrapDetector alert）
```

---

## 五、流程与验证铁律

### 5.1 任何核心改动，先跑"热门样本回测"，再谈全市场

**最小必选样本集**:
- 顽主真实区间的TopList（已映射代码的131只）
- 几只典型强势与失败样本（网宿、志特、欢乐家、有友）

**流程**:
```
代码修改 → 热门票验证 → 通过才进PR → 全市场测试
     ↑___________________________|
     （不通过禁止合入主线）
```

**禁止**:
- ❌ 未经热门票验证的改动进入全市场扫描/实盘

---

### 5.2 实盘决策永远以"条件结论"表述，不给绝对命令

**禁止**:
- ❌ "应该卖出"/"必须买入"这种绝对结论

**标准表述**:
```
"如果 A（资金继续流入且无陷阱）成立 → 倾向继续持有；
 如果 B（资金转为净流出或出现TRAP）成立 → 倾向减仓/退出。"
```

---

### 5.3 禁止在代码里写故事，只写事实和理由

**禁止**:
- ❌ 日志/报告中出现"春节前最后一个交易日""情绪如何如何"等未校验叙述
- ❌ "我感觉"/"可能"/"应该"等主观表述

**正确做法**:
- ✅ 用可验证的数据字段说话：日期、价格、量、ratio、分位、事件标记等
- ✅ 每个结论必须附带数据支撑

**日志规范**:
```python
# ❌ 错误
logger.info("春节前最后一个交易日，情绪高涨")

# ✅ 正确
logger.info(f"日期: {date}, 成交量: {vol}, ratio: {ratio:.4f}, 分位: {percentile:.2%}")
```

---

## 六、Code Review检查清单

### PR模板必须勾选：

```markdown
## Code Review Checklist

- [ ] 无魔法数字（所有阈值来自配置或经验公式）
- [ ] 使用相对尺度（ratio + 分位数，非绝对值）
- [ ] Tick数据通过Provider获取（无直接xtdata调用）
- [ ] 过滤器基于V11防守轴抽象（非重新发明）
- [ ] 已在热门票样本验证（附回测报告）
- [ ] 日志使用数据字段（无主观叙述）

**如有违反，必须显式说明原因并经CTO批准**
```

---

## 七、违规处置

| 违规类型 | 处置措施 |
|---------|---------|
| 核心引擎出现魔法数字 | PR直接打回，要求外置到配置 |
| 直接import xtdata/xtdatacenter | PR直接打回，要求使用TickProvider |
| 未经验证进全市场扫描 | 回滚代码，重新跑热门票验证 |
| 日志出现主观叙述 | 要求改为数据字段表述 |
| 重复发明过滤器 | 要求复用V11防守轴抽象 |

---

## 八、历史教训

### 2026-02-18 V12.1.0过滤器失效事件

**违规项**:
- ❌ 硬编码阈值（涨停≥3只/上涨≥35%/市值50-1000亿）
- ❌ 串联一票否决架构
- ❌ 未在热门票验证直接全市场扫描

**后果**:
- 实际通过率0.11%，收益率-21%（vs模拟数据+9%）
- 右侧起爆核心标的被系统性截杀

**处置**:
- V12.1.0标记为EXPERIMENTAL，默认禁用
- 回滚到V11 TripleFunnel评分制
- 制定本铁律文档，防止重复犯错

---

**文档维护**:
- 生效日期: 2026-02-18
- 制定人: CTO + 老板
- 执行监督: AI项目总监
- 更新频率: 按需更新（重大架构决策后）
- 下次评审: 2026-03-01

**相关文档**:
- `docs/CORE_ARCHITECTURE.md` - 核心架构
- `docs/V17_TECH_DEBT.md` - 技术债务清单
- `docs/dev/exploration_log/` - 探索日志（CASE记录）
